# coding=utf-8

import datetime
import json
import os
import re
import subprocess
import zipfile
import tarfile
import shutil
import time

import backoff
import requests
from requests import RequestException
from requests_html import HTMLSession
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, BOOLEAN, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from bs4 import BeautifulSoup
from shlex import quote

engine = create_engine(
    f'mariadb+pymysql://{os.environ["DB_USER"]}:{os.environ["DB_PASSWORD"]}@db/{os.environ["DB"]}?charset=utf8mb4',
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=True
)
Session = sessionmaker(bind=engine)

Base = declarative_base()


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    hidden = Column(BOOLEAN, default=0)
    service = Column(String(50), nullable=False)
    game_id = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(200))
    url = Column(String(250), nullable=False)
    thumb_url = Column(String(250))
    latest_version = Column(String(20))
    devlog = Column(String(250))
    tags = Column(String(250))
    languages = Column(String(250))
    rating = Column(Float)
    rating_count = Column(Integer)
    status = Column(String(50))
    error = Column(Text)
    platform_windows = Column(Integer, nullable=False, default=0)
    platform_linux = Column(Integer, nullable=False, default=0)
    platform_mac = Column(Integer, nullable=False, default=0)
    platform_android = Column(Integer, nullable=False, default=0)
    platform_web = Column(Integer, nullable=False, default=0)
    stats_blocks = Column(Integer, nullable=False, default=0)
    stats_menus = Column(Integer, nullable=False, default=0)
    stats_options = Column(Integer, nullable=False, default=0)
    stats_words = Column(Integer, nullable=False, default=0)
    game_engine = Column(String(50))
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer)
    nsfw = Column(BOOLEAN, default=0)
    reviews = relationship("Review", back_populates="game")

    def __init__(self, service, game_id, name, description, url, thumb_url, latest_version='unknown', devlog=None,
                 tags=None, languages=None, rating=None, rating_count=None, status='In development',
                 platform_windows=0, platform_linux=0, platform_mac=0, platform_android=0, platform_web=0,
                 stats_blocks=0, stats_menus=0, stats_options=0, stats_words=0, game_engine='unknown',
                 created_at=0, updated_at=0, hidden=0, nsfw=0):
        self.service = service
        self.game_id = game_id
        self.name = name
        self.description = description
        self.url = url
        self.thumb_url = thumb_url
        self.latest_version = latest_version
        self.devlog = devlog
        self.tags = tags
        self.languages = languages
        self.rating = rating
        self.rating_count = rating_count
        self.status = status
        self.platform_windows = platform_windows
        self.platform_linux = platform_linux
        self.platform_mac = platform_mac
        self.platform_android = platform_android
        self.platform_web = platform_web
        self.stats_blocks = stats_blocks
        self.stats_menus = stats_menus
        self.stats_options = stats_options
        self.stats_words = stats_words
        self.game_engine = game_engine
        self.created_at = created_at
        self.updated_at = updated_at
        self.hidden = hidden
        self.nsfw = nsfw

    def to_dict(self):
        return {
            'id': self.id,
            'service': self.service,
            'game_id': self.game_id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'thumb_url': self.thumb_url,
            'latest_version': self.latest_version,
            'devlog': self.devlog,
            'tags': self.tags,
            'languages': self.languages,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'status': self.status,
            'platform_windows': self.platform_windows,
            'platform_linux': self.platform_linux,
            'platform_mac': self.platform_mac,
            'platform_android': self.platform_android,
            'platform_web': self.platform_web,
            'stats_blocks': self.stats_blocks,
            'stats_menus': self.stats_menus,
            'stats_options': self.stats_options,
            'stats_words': self.stats_words,
            'game_engine': self.game_engine,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'nsfw': self.nsfw
        }

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError,
                           RequestException),
                          jitter=None,
                          base=60)
    def refresh_tags_and_rating(self):
        print("\n[refresh_tags_and_rating] URL: " + self.url + "\n")
        with requests.get(self.url, timeout=5, allow_redirects=True) as response:
            if response.status_code == 404:
                print("\n[refresh_tags_and_rating] Status 404\n")
                return
            elif response.status_code != 200:
                print("\n[refresh_tags_and_rating] Status != 200: " + str(response.status_code) + "\n")
                raise RequestException("Status code not 200, retrying")

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            if self.status not in ['Abandoned', 'Canceled', 'Released']:
                game_info = soup.find("div", {"class": "game_info_panel_widget"}).find_all("a", href=True)
                if game_info:
                    self.status = game_info[0].text
            devlog = soup.find("section", id="devlog")
            if devlog:
                devlog_links = devlog.find_all('a', href=True)
                if devlog_links:
                    devlog_link = devlog_links[0]['href']
                    with Session as session:
                        game_version = session.query(GameVersion).filter(GameVersion.game_id == self.id) \
                            .order_by(GameVersion.created_at.desc()).first()
                        if game_version and game_version.devlog == '':
                            game_version.devlog = devlog_link
                            session.commit()
                    self.devlog = devlog_link
            rating = soup.find("div", itemprop="ratingValue")
            rating_count = soup.find("span", itemprop="ratingCount")
            if rating and rating_count:
                self.rating = rating['content']
                self.rating_count = rating_count['content']
            info_table = soup.find("div", {"class": "game_info_panel_widget"}).find("table")
            for tr in info_table.findAll('tr'):
                if tr.text.find('Languages') > -1:
                    self.languages = tr.text.strip()[9:]
                if tr.text.find('Tags') > -1:
                    self.tags = tr.text.strip()[4:]
            nsfw = soup.find("div", {"class": "content_warning_inner"})
            if nsfw:
                self.nsfw = 1
            else:
                self.nsfw = 0

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError,
                           RequestException),
                          jitter=None,
                          base=60)
    def refresh_base_info(self, itch_api_key):
        url = 'https://api.itch.io/games/' + str(self.game_id)
        print("\n[refresh_base_info] URL: " + url + "\n")
        with requests.get(url, headers={'Authorization': itch_api_key}, timeout=5, allow_redirects=True) as response:
            if response.status_code == 404:
                print("\n[refresh_base_info] Status 404\n")
                return
            elif response.status_code != 200:
                print("\n[refresh_base_info] Status != 200: " + str(response.status_code) + "\n")
                raise RequestException("Status code not 200, retrying")

            game = json.loads(response.text)
            if 'game' in game:
                self.created_at = int(datetime.datetime.fromisoformat(
                    game['game']['published_at']
                ).timestamp())
                self.thumb_url = game['game']['cover_url']

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError,
                           RequestException),
                          jitter=None,
                          base=60)
    def refresh_version(self, itch_api_key, force: bool = False):
        url = 'https://api.itch.io/games/' + str(self.game_id) + '/uploads'
        print("\n[refresh_version] URL: " + url + "\n")
        with requests.get(url, headers={'Authorization': itch_api_key}, timeout=5, allow_redirects=True) as response:
            if response.status_code == 404:
                print("\n[refresh_version] Status 404\n")
                return
            elif response.status_code != 200:
                print("\n[refresh_version] Status != 200: " + str(response.status_code) + "\n")
                raise RequestException("Status code not 200, retrying")

            uploads = json.loads(response.text)
            if 'uploads' in uploads:
                self.platform_windows = 0
                self.platform_linux = 0
                self.platform_mac = 0
                self.platform_android = 0
                self.platform_web = 0
                linux_upload = None
                windows_upload = None
                android_upload = None
                for upload in uploads['uploads']:
                    # For games that have no traits, check for a zip and assume Windows
                    if windows_upload is None and 'filename' in upload and upload['filename'].endswith('.zip'):
                        self.platform_windows = 1
                        windows_upload = upload
                    if upload['traits']:
                        if 'p_windows' in upload['traits']:
                            self.platform_windows = 1
                            windows_upload = upload
                        if 'p_linux' in upload['traits']:
                            self.platform_linux = 1
                            linux_upload = upload
                        if 'p_osx' in upload['traits']:
                            self.platform_mac = 1
                        if 'p_android' in upload['traits']:
                            self.platform_android = 1
                            android_upload = upload
                # Force update check by setting latest_timestamp to 0
                save_latest_timestamp = True
                if force and (linux_upload is not None or windows_upload is not None or android_upload is not None):
                    latest_timestamp = 0
                else:
                    latest_timestamp = self.updated_at or 0
                for upload in [linux_upload, windows_upload, android_upload]:
                    if upload is None:
                        continue
                    element = datetime.datetime.strptime(upload['updated_at'], "%Y-%m-%dT%H:%M:%S.%f000Z")
                    timestamp = int(datetime.datetime.timestamp(element))
                    # Take the newest timestamp from the uploads
                    if latest_timestamp < timestamp:
                        latest_timestamp = timestamp
                        for version_number_source in ['build.user_version', 'filename', 'display_name']:
                            if version_number_source == 'build.user_version' and upload.get('build') and upload['build'].get('user_version'):
                                save_latest_timestamp = False
                                latest_version = upload['build']['user_version']
                                if self.latest_version == latest_version:
                                    continue
                                self.updated_at = timestamp
                                self.latest_version = latest_version
                                if upload is linux_upload or (upload is windows_upload and linux_upload is None):
                                    self.get_script_stats(itch_api_key, upload)
                                break
                            elif upload.get(version_number_source):
                                version_number_string = upload[version_number_source]
                                # Extract version number from source string, matches anything from 1 to 1.2.3.4...
                                matches = re.compile(r'\d+(=?\.(\d+(=?\.(\d+)*)*)*)*').search(version_number_string)
                                if matches:
                                    save_latest_timestamp = False
                                    latest_version = matches.group(0).rstrip('.')
                                    if self.latest_version == latest_version:
                                        continue
                                    self.updated_at = timestamp
                                    self.latest_version = latest_version
                                    if upload is linux_upload or (upload is windows_upload and linux_upload is None):
                                        self.get_script_stats(itch_api_key, upload)
                                    break
                    if upload['type'] == 'html':
                        self.platform_web = 1
                if save_latest_timestamp and latest_timestamp > 0:
                    with Session() as session:
                        # Add the new version to the database
                        game_version = GameVersion(self.id, self.latest_version, '', self.platform_windows,
                                                   self.platform_linux, self.platform_mac, self.platform_android,
                                                   self.platform_web, self.stats_blocks, self.stats_menus,
                                                   self.stats_options, self.stats_words, int(time.time()),
                                                   self.updated_at)
                        session.add(game_version)
                        session.commit()
                    self.updated_at = latest_timestamp

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError),
                          jitter=None,
                          base=60)
    def get_script_stats(self, itch_api_key, upload_info):
        # Only continue if the game is made with Ren'Py or unknown
        if self.game_engine != "Ren'Py" and self.game_engine != "unknown":
            return
        # Reset status to 0
        self.stats_blocks = 0
        self.stats_menus = 0
        self.stats_options = 0
        self.stats_words = 0
        url = self.url + '/file/' + str(upload_info['id'])
        print("\n[get_script_stats] URL: " + url + "\n")
        # Download the game
        with requests.post(url, headers={'Authorization': itch_api_key}, timeout=5) as response:
            download = json.loads(response.text)
            if 'url' in download:
                download_path = 'tmp/' + upload_info['filename']
                try:
                    file = requests.get(download['url'], allow_redirects=True)
                    open(download_path, 'wb').write(file.content)
                except RequestException as error:
                    self.error = error
                    if os.path.isfile(download_path):
                        os.remove(download_path)
                    return
                extract_directory = f'tmp/{upload_info["id"]}'
                if download_path.endswith('.zip'):
                    try:
                        with zipfile.ZipFile(download_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_directory)
                    except (zipfile.BadZipfile, IOError, EOFError) as error:
                        base = os.path.splitext(download_path)[0]
                        os.rename(download_path, base + '.tar.bz2')
                        download_path = base + '.tar.bz2'
                if download_path.endswith('.tar.gz'):
                    try:
                        file = tarfile.open(download_path)
                        file.extractall(extract_directory)
                        file.close()
                    except (tarfile.ReadError, IOError, EOFError) as error:
                        if os.path.isfile(download_path):
                            os.remove(download_path)
                        return
                elif download_path.endswith('.tar.bz2'):
                    try:
                        file = tarfile.open(download_path, "r:bz2")
                        file.extractall(extract_directory)
                        file.close()
                    except (tarfile.ReadError, IOError, EOFError) as error:
                        if os.path.isfile(download_path):
                            os.remove(download_path)
                        return
                directory_listing = []
                game_dir_files = []
                if os.path.isdir(extract_directory):
                    directory_listing = os.listdir(extract_directory)
                if len(directory_listing) == 1:
                    game_dir = extract_directory + '/' + directory_listing[0]
                    if os.path.isdir(game_dir):
                        game_dir_files = os.listdir(game_dir)
                else:
                    game_dir = extract_directory
                    game_dir_files = directory_listing
                if len(game_dir_files) > 0 and os.path.isdir(game_dir + "/game"):
                    shutil.copyfile('./renpy/wordcounter.rpy', game_dir + '/game/wordcounter.rpy')
                    if not os.path.isdir(game_dir + '/lib/py2-linux-x86_64') and not os.path.isdir(game_dir + '/lib/py3-linux-x86_64') and not os.path.isdir(game_dir + '/lib/linux-x86_64'):
                        shutil.copyfile('./renpy/renpy.py', game_dir + '/renpy.py')
                        shutil.copyfile('./renpy/renpy.sh', game_dir + '/renpy.sh')
                        shutil.copytree('./renpy/py3-linux-x86_64', game_dir + '/lib/py3-linux-x86_64', dirs_exist_ok=True)
                        # Refresh the directory listing
                        game_dir_files = os.listdir(game_dir)
                    for game_dir_file in game_dir_files:
                        if game_dir_file.endswith('.sh'):
                            subprocess.run(f'chmod -R +x *',
                                           cwd=game_dir, shell=True)
                            subprocess.run(f'./{quote(game_dir_file)} game test',
                                           cwd=game_dir, shell=True)
                            if os.path.isfile(game_dir + '/stats.json'):
                                stats_file = open(game_dir + '/stats.json')
                                stats = json.load(stats_file)
                                stats_file.close()
                                if stats:
                                    self.stats_blocks = stats['blocks']
                                    self.stats_menus = stats['menus']
                                    self.stats_options = stats['options']
                                    self.stats_words = stats['words']
                                    self.game_engine = "Ren'Py"
                                os.remove(download_path)
                if os.path.isdir(extract_directory):
                    shutil.rmtree(extract_directory)

class GameVersion(Base):
    __tablename__ = 'game_versions'

    id = Column(Integer, primary_key=True)
    game_id = Column(String(50), nullable=False)
    version = Column(String(20))
    devlog = Column(String(250))
    platform_windows = Column(Integer, nullable=False, default=0)
    platform_linux = Column(Integer, nullable=False, default=0)
    platform_mac = Column(Integer, nullable=False, default=0)
    platform_android = Column(Integer, nullable=False, default=0)
    platform_web = Column(Integer, nullable=False, default=0)
    stats_blocks = Column(Integer, nullable=False, default=0)
    stats_menus = Column(Integer, nullable=False, default=0)
    stats_options = Column(Integer, nullable=False, default=0)
    stats_words = Column(Integer, nullable=False, default=0)
    created_at = Column(Integer, nullable=False)
    released_at = Column(Integer, nullable=False)

    def __init__(self, game_id, version, devlog, platform_windows, platform_linux, platform_mac, platform_android,
                 platform_web, stats_blocks, stats_menus, stats_options, stats_words, created_at, released_at):
        self.game_id = game_id
        self.version = version
        self.devlog = devlog
        self.platform_windows = platform_windows
        self.platform_linux = platform_linux
        self.platform_mac = platform_mac
        self.platform_android = platform_android
        self.platform_web = platform_web
        self.stats_blocks = stats_blocks
        self.stats_menus = stats_menus
        self.stats_options = stats_options
        self.stats_words = stats_words
        self.created_at = created_at
        self.released_at = released_at

    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'version': self.version,
            'devlog': self.devlog,
            'platform_windows': self.platform_windows,
            'platform_linux': self.platform_linux,
            'platform_mac': self.platform_mac,
            'platform_android': self.platform_android,
            'platform_web': self.platform_web,
            'stats_blocks': self.stats_blocks,
            'stats_menus': self.stats_menus,
            'stats_options': self.stats_options,
            'stats_words': self.stats_words,
            'created_at': self.created_at,
            'released_at': self.released_at
        }

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(Integer, nullable=False)

    def __init__(self, discord_id, processed_at):
        self.discord_id = discord_id
        self.processed_at = processed_at


class Reviewer(Base):
    __tablename__ = 'reviewers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    user_name = Column(String(100), nullable=False)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)
    reviews = relationship("Review", back_populates="reviewer")

    def __init__(self, user_id, user_name, created_at=0, updated_at=0):
        self.user_id = user_id
        self.user_name = user_name
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name
        }


class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'))
    reviewer_id = Column(Integer, ForeignKey('reviewers.id'))
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    hidden = Column(BOOLEAN, default=0)
    game = relationship("Game", back_populates="reviews")
    reviewer = relationship("Reviewer", back_populates="reviews")
    has_review = Column(BOOLEAN, nullable=False, default=0)

    def __init__(self, event_id, created_at, updated_at, game_id, reviewer_id, rating, review, hidden=0):
        self.event_id = event_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.game_id = game_id
        self.reviewer_id = reviewer_id
        self.rating = rating
        self.review = review
        self.hidden = hidden
        self.has_review = (review != '')

    def to_dict(self):
        return {
            'event_id': self.event_id,
            'updated_at': self.updated_at,
            'reviewer_id': self.reviewer_id,
            'game_id': self.game_id,
            'rating': self.rating,
            'review': self.review
        }

    @staticmethod
    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError,
                           TypeError),
                          jitter=None,
                          base=60)
    def get_request_sesstion():
        ITCH_USER = os.environ['ITCH_USER']
        ITCH_PASSWORD = os.environ['ITCH_PASSWORD']

        url = "https://itch.io/login"
        request_session = HTMLSession()
        login = request_session.get(url)
        s = BeautifulSoup(login.text, "html.parser")
        csrf_token = s.find("input", {"name": "csrf_token"})["value"]
        request_session.post(
            url,
            {"username": ITCH_USER, "password": ITCH_PASSWORD, "csrf_token": csrf_token}
        )
        return request_session

    @staticmethod
    def import_latest_reviews():
        # Get the newest timestamp
        end_event_id = None
        with Session() as session:
            newest_review = session.query(Review).order_by(Review.event_id.desc()).first()
            if newest_review:
                end_event_id = newest_review.event_id

        start_event_id = None

        while True:
            print("\n[reviews] Loop start: " + str(start_event_id) + "\n")
            start_event_id = Review.import_reviews(Review.get_request_sesstion(), start_event_id)
            if start_event_id is None or start_event_id < end_event_id:
                print("\n[reviews] Import finished: ", str(start_event_id), " ", str(end_event_id), "\n")
                break
            print("\n[reviews] Loop end: " + str(start_event_id) + "\n\n")
            time.sleep(30)

    @staticmethod
    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError),
                          jitter=None,
                          base=60)
    def import_reviews(request_session, start_event_id = None):
        url = 'https://itch.io/feed?filter=ratings&format=json'
        previous_start_event_id = start_event_id
        if start_event_id is not None:
            url += '&from_event=' + str(start_event_id)
        print("\n[import_reviews] URL: " + url + "\n")
        with request_session.get(url, timeout=5) as response, Session() as session:
            print("\n[import_reviews] Received response\n")
            events = json.loads(response.text)
            start_event_id = None
            if 'next_page' in events:
                start_event_id = int(events['next_page'])
            if 'content' in events:
                soup = BeautifulSoup(events['content'], 'html.parser')
                reviews = soup.find_all("div", {"class": "event_row"})
                for review in reviews:
                    script = review.find("script", {"type": "text/javascript"})
                    itch_user_id = re.findall(r"user_id.*:(\d+)", script.text).pop(0)
                    user_name = review.find("a", {"data-label": "event_user", "class": "event_source_user"}, href=True).text
                    event_time = review.find("a", {"class": "event_time"}, href=True)
                    event_id = int(event_time['href'].split('/')[-1])
                    updated_at = int(datetime.datetime.fromisoformat(
                        event_time['title'] + '+00:00'
                    ).timestamp())
                    game_info = review.find("a", {"class": "object_title"}, href=True)
                    game_name = game_info.text
                    game_url = game_info['href']
                    game_cell = review.find("div", {"class": "game_cell"})
                    if game_cell:
                        itch_game_id = int(game_cell['data-game_id'])
                    else:
                        time.sleep(30)
                        itch_game_id = int(Review.get_game_id(game_url))
                    rating = len(review.find_all("span", {"class": "icon-star"}))
                    rating_blurb = review.find("div", {"class": "rating_blurb"})
                    review_text = ''
                    if rating_blurb:
                        review_text = rating_blurb
                    existing_reviewer = session.query(Reviewer).filter_by(user_id=itch_user_id).first()
                    if existing_reviewer is None:
                        new_reviewer = Reviewer(itch_user_id, user_name, updated_at, updated_at)
                        session.add(new_reviewer)
                        session.commit()
                        session.flush()
                        reviewer_id = new_reviewer.id
                    elif user_name != existing_reviewer.user_name:
                        existing_reviewer.user_name = user_name
                        existing_reviewer.updated_at = updated_at
                        session.commit()
                    if existing_reviewer is not None:
                        reviewer_id = existing_reviewer.id
                    existing_game = session.query(Game).filter_by(game_id=itch_game_id).first()
                    if existing_game is None:
                        new_game = Game('itch', itch_game_id, game_name, '', game_url, '', hidden=1)
                        session.add(new_game)
                        session.commit()
                        session.flush()
                        game_id = new_game.id
                    elif existing_game.name != game_name or existing_game.url != game_url:
                        existing_game.name = game_name
                        existing_game.url = game_url
                        session.commit()
                    if existing_game is not None:
                        game_id = existing_game.id
                    existing_review = session.query(Review).filter_by(event_id=event_id).first()
                    if existing_review is None:
                        new_review = Review(event_id, updated_at, updated_at, game_id, reviewer_id, rating, review_text)
                        session.query(Review). \
                            filter(Review.game_id == new_review.game_id, Review.reviewer_id == new_review.reviewer_id). \
                            update({'hidden': True})
                        session.commit()
                        session.add(new_review)
                        session.commit()
                    if start_event_id is None or start_event_id > event_id:
                        start_event_id = event_id
            if start_event_id is None and previous_start_event_id is not None:
                start_event_id = previous_start_event_id - 1

        return start_event_id

    @staticmethod
    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError,
                           RequestException,
                           RuntimeError),
                          jitter=None,
                          base=60)
    def get_game_id(url):
        print("\n[get_game_id] URL: " + url + "\n")
        with requests.get(url, timeout=5, allow_redirects=True) as response:
            if response.status_code == 404:
                print("\n[get_game_id] Status 404\n")
                return None
            elif response.status_code != 200:
                print("\n[get_game_id] Status != 200: " + str(response.status_code) + "\n")
                raise RequestException("Status code not 200, retrying")

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            itch_path = soup.find("meta", {"name": "itch:path"})
            if itch_path and itch_path['content']:
                game_id = itch_path['content'].split('/')[-1]
                print("\n[get_game_id] Game ID: " + game_id + "\n")
            else:
                print("\n[get_game_id] Could not find game ID, retrying: " + html + "\n")
                raise RuntimeError("Could not find game ID")

            return game_id
