# coding=utf-8

import datetime
import json
import os
import random
import re
import subprocess
import zipfile
import tarfile
import shutil
import time

import requests
from requests import RequestException
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, BOOLEAN, ForeignKey, DateTime, BigInteger, \
    Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from bs4 import BeautifulSoup
from shlex import quote
from tenacity import *

engine = create_engine(
    f'postgresql+psycopg2://{os.environ["DB_USER"]}:{os.environ["DB_PASSWORD"]}@db/{os.environ["DB"]}?client_encoding=utf8',
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=True
)
Session = sessionmaker(bind=engine)
proxy_list = os.environ["PROXY_LIST"].split(',')

Base = declarative_base()
request_session = None
COOKIES_FILE = 'itch_cookies.pkl'

@retry(wait=wait_exponential(multiplier=2, min=30, max=120))
def proxy_request(request_type, url, **kwargs):
    proxy = random.randint(0, len(proxy_list) - 1)
    proxies = {
        "http": 'http://' + os.environ["PROXY_USER"] + ':' + os.environ["PROXY_PASSWORD"] + '@' + proxy_list[proxy],
        "https": 'https://' + os.environ["PROXY_USER"] + ':' + os.environ["PROXY_PASSWORD"] + '@' + proxy_list[proxy],
    }
    print(f"[proxy_request] Proxy currently being used: {proxy_list[proxy]}")
    print(f"[proxy_request] URL requested: {url}")
    time.sleep(10)
    response = requests.request(request_type, url, proxies=proxies, timeout=(3.05, 30), **kwargs)
    if response.status_code != requests.codes.ok:
        print("\n[proxy_request] Status != 200: " + str(response.status_code) + "\n")
    if response.status_code != 200 and response.status_code != 400 and response.status_code != 404:
        raise RequestException("Status code not 200, 400 or 404, retrying")
    return response


class Game(Base):
    __tablename__ = 'games'

    id = Column(BigInteger, (Identity()), primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    initially_published_at = Column(DateTime)
    version_published_at = Column(DateTime)
    game_id = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(String(50))
    visible = Column(BOOLEAN, default=False)
    nsfw = Column(BOOLEAN, default=False)
    description = Column(String(200))
    url = Column(String(250), nullable=False)
    thumb_url = Column(String(250))
    version = Column(String(20))
    tags = Column(String(250))
    rating = Column(Float)
    rating_count = Column(Integer)
    devlog = Column(String(250))
    languages = Column(String(250))
    platform_windows = Column(BOOLEAN, nullable=False, default=False)
    platform_linux = Column(BOOLEAN, nullable=False, default=False)
    platform_mac = Column(BOOLEAN, nullable=False, default=False)
    platform_android = Column(BOOLEAN, nullable=False, default=False)
    platform_web = Column(BOOLEAN, nullable=False, default=False)
    stats_blocks = Column(Integer, nullable=False, default=0)
    stats_menus = Column(Integer, nullable=False, default=0)
    stats_options = Column(Integer, nullable=False, default=0)
    stats_words = Column(Integer, nullable=False, default=0)
    game_engine = Column(String(50))
    error = Column(Text)
    authors = Column(Text)
    uploads = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    ratings = relationship("Rating", back_populates="game")

    def __init__(self, created_at=None, updated_at=None, initially_published_at=None, version_published_at=None,
                 game_id=None, name=None,
                 status='In development', visible=0, nsfw=False, description=None, url=None, thumb_url=None,
                 version='unknown',
                 tags=None, rating=None, rating_count=None, devlog=None, languages=None, platform_windows=False,
                 platform_linux=False, platform_mac=False, platform_android=False, platform_web=False,
                 stats_blocks=0, stats_menus=0, stats_options=0, stats_words=0, game_engine='unknown', uploads=None):
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.initially_published_at = initially_published_at
        self.version_published_at = version_published_at
        self.game_id = game_id
        self.name = name
        self.status = status
        self.visible = visible
        self.nsfw = nsfw
        self.description = description
        self.url = url
        self.thumb_url = thumb_url
        self.version = version
        self.tags = tags
        self.rating = rating
        self.rating_count = rating_count
        self.devlog = devlog
        self.languages = languages
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
        self.uploads = uploads or {}

    def to_dict(self):
        return {
            'id': self.id,
            'service': self.service,
            'game_id': self.game_id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'thumb_url': self.thumb_url,
            'version': self.version,
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
            'nsfw': self.nsfw,
            'uploads': self.uploads
        }

    def refresh_tags_and_rating(self):
        print("\n[refresh_tags_and_rating] URL: " + self.url + "\n")
        with proxy_request("get", self.url, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                return
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
                    self.devlog = devlog_link
            rating = soup.find("div", itemprop="ratingValue")
            rating_count = soup.find("span", itemprop="ratingCount")
            if rating and rating_count:
                self.rating = rating['content']
                self.rating_count = rating_count['content']
            info_table = soup.find("div", {"class": "game_info_panel_widget"}).find("table")
            for tr in info_table.findAll('tr'):
                tds = tr.findAll('td')
                if len(tds) < 2:
                    continue

                match tds[0].text:
                    case 'Languages':
                        self.languages = tds[1].text.strip()
                    case 'Tags':
                        self.tags = tds[1].text.strip()
                    case 'Author' | 'Authors':
                        self.authors = ''
                        for author in tds[1].findAll("a", href=True):
                            if self.authors != '':
                                self.authors += ',<br>'
                            self.authors += f'<a href="{author["href"]}" target="_blank">{author.text}</a>'
            nsfw = soup.find("div", {"class": "content_warning_inner"})
            if nsfw:
                self.nsfw = True
            else:
                self.nsfw = False

    def refresh_base_info(self, itch_api_key):
        url = 'https://api.itch.io/games/' + str(self.game_id)
        print("\n[refresh_base_info] URL: " + url + "\n")
        with proxy_request("get", url, headers={'Authorization': itch_api_key}, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                return
            game = json.loads(response.text)
            if 'game' in game:
                self.created_at = datetime.datetime.fromisoformat(
                    game['game']['published_at']
                )
                self.thumb_url = game['game']['cover_url']

    def refresh_version(self, itch_api_key, force: bool = False):
        url = f'https://api.itch.io/games/{self.game_id}/uploads'
        print(f"\n[refresh_version] URL: {url}\n")
        with proxy_request("get", url, headers={'Authorization': itch_api_key}, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                print(f"\n[refresh_version] Status 400, disabling game ID {self.id}\n")
                self.visible = False
                return

            seen_uploads = self.uploads or {}
            uploads_data = json.loads(response.text)

            if 'uploads' not in uploads_data:
                print("\n[refresh_version] No uploads found in response\n")
                return

            has_changes = False
            candidate_uploads = []

            self.platform_windows = False
            self.platform_linux = False
            self.platform_mac = False
            self.platform_android = False
            self.platform_web = False

            for upload in uploads_data['uploads']:
                file_id = str(upload['id'])
                current_filename = upload['filename']
                current_display_name = upload.get('display_name')
                current_md5 = upload.get('md5_hash')
                current_updated_at = upload['updated_at']
                current_build_id = upload.get('build_id')
                current_build = upload.get('build', {})
                current_user_version = current_build.get('user_version')
                current_build_updated_at = current_build.get('updated_at')

                # Update platform flags
                if 'traits' in upload:
                    if 'p_windows' in upload['traits']:
                        self.platform_windows = True
                    if 'p_linux' in upload['traits']:
                        self.platform_linux = True
                    if 'p_osx' in upload['traits']:
                        self.platform_mac = True
                    if 'p_android' in upload['traits']:
                        self.platform_android = True
                if upload['type'] == 'html':
                    self.platform_web = True

                # Check if the upload is new or changed
                is_new_or_changed = (
                        file_id not in seen_uploads or
                        seen_uploads[file_id].get('md5_hash') != current_md5 or
                        seen_uploads[file_id].get('updated_at') != current_updated_at or
                        seen_uploads[file_id].get('build_id') != current_build_id or
                        seen_uploads[file_id].get('build_updated_at') != current_build_updated_at
                )

                if is_new_or_changed:
                    has_changes = True
                    seen_uploads[file_id] = {
                        'display_name': current_display_name,
                        'md5_hash': current_md5,
                        'updated_at': current_updated_at,
                        'build_id': current_build_id,
                        'build_updated_at': current_build_updated_at,
                        'user_version': current_user_version,
                        'filename': current_filename
                    }
                    candidate_uploads.append(upload)

            self.uploads = seen_uploads

            if not has_changes and not force:
                return

            candidate_uploads.sort(key=lambda u: (
                'p_linux' in u.get('traits', []),
                'p_windows' in u.get('traits', []),
                u['filename'].lower().endswith('.zip'),
                datetime.datetime.fromisoformat(u['updated_at'].replace('Z', '+00:00')),
                datetime.datetime.fromisoformat(
                    u.get('build', {}).get('updated_at', '1970-01-01T00:00:00Z').replace('Z', '+00:00')
                ),
            ), reverse=True)
            upload_to_process = candidate_uploads[0] if candidate_uploads else None

            if upload_to_process:
                new_version = self.extract_version(upload_to_process)
                upload_timestamp = datetime.datetime.fromisoformat(
                    upload_to_process['updated_at'].replace('Z', '+00:00'))

                if self.version != new_version or force:
                    with Session() as session:
                        self.version = new_version
                        self.version_published_at = upload_timestamp

                        # Get script stats for the selected upload
                        self.get_script_stats(itch_api_key, upload_to_process)

                        # Update the game's info & devlog link
                        time.sleep(10)
                        self.refresh_tags_and_rating()

                        # Add the new version to the database
                        game_version = GameVersion(
                            self.id, self.version, self.devlog, self.platform_windows,
                            self.platform_linux, self.platform_mac, self.platform_android,
                            self.platform_web, self.stats_blocks, self.stats_menus,
                            self.stats_options, self.stats_words, datetime.datetime.utcnow(),
                            datetime.datetime.utcnow(), self.version_published_at, self.rating,
                            self.rating_count
                        )
                        session.add(game_version)
                        session.commit()

    def extract_version(self, upload):
        def parse_semantic_version(version_str):
            """Parse a version string into tuple of integers for comparison"""
            try:
                # Remove any leading 'v' or 'version'
                version_str = re.sub(r'^[vV]ersion\s*', '', version_str)
                # Split on dots and convert to integers
                parts = [int(x) for x in version_str.split('.')]
                # Pad with zeros to ensure at least 3 components
                while len(parts) < 3:
                    parts.append(0)
                return parts
            except (ValueError, AttributeError):
                return None

        def is_probable_year(version_parts):
            """Check if the version number looks like a year"""
            if len(version_parts) >= 1:
                first_num = version_parts[0]
                return 1990 <= first_num <= 2100

        def is_probable_version(version_str):
            """Check if a string looks like a probable version number"""
            if not version_str:
                return False

            parts = parse_semantic_version(version_str)
            if not parts:
                return False

            # Reject if first number is too large (unless it's a probable year)
            if parts[0] > 100 and not is_probable_year(parts):
                return False

            # Reject if any part is suspiciously large (likely a timestamp or file size)
            if any(p > 10000 for p in parts):
                return False

            return True

        def compare_versions(ver1, ver2):
            """Compare two version strings, return the higher one"""
            if not ver1:
                return ver2
            if not ver2:
                return ver1

            parts1 = parse_semantic_version(ver1)
            parts2 = parse_semantic_version(ver2)

            if not parts1:
                return ver2
            if not parts2:
                return ver1

            # If one is a year and the other isn't, prefer the non-year
            year1 = is_probable_year(parts1)
            year2 = is_probable_year(parts2)
            if year1 and not year2:
                return ver2
            if year2 and not year1:
                return ver1

            # Compare parts
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return ver1
                if p2 > p1:
                    return ver2
            return ver1  # If equal, return first

        # Collect all possible version numbers from various sources
        version_regex = r'(\d+(?:\.\d+){0,3})'
        version_candidates = []

        # Check build.user_version
        if 'build' in upload and upload['build'] and upload['build'].get('user_version'):
            version_candidates.append(upload['build']['user_version'])

        # Check display_name
        display_name = upload.get('display_name')
        if display_name:
            versions = re.finditer(version_regex, display_name)
            version_candidates.extend(match.group(1) for match in versions)

        # Check filename
        filename = upload.get('filename', '')
        versions = re.finditer(version_regex, filename)
        version_candidates.extend(match.group(1) for match in versions)

        # Filter to probable versions and remove duplicates
        version_candidates = list(set(
            ver for ver in version_candidates
            if is_probable_version(ver)
        ))

        if not version_candidates:
            # If no valid versions found, use timestamp
            timestamp = datetime.datetime.fromisoformat(upload['updated_at'].replace('Z', '+00:00'))
            return timestamp.strftime("%Y.%m.%d")

        # Compare all candidates to find the highest version
        highest_version = version_candidates[0]
        for version in version_candidates[1:]:
            highest_version = compare_versions(highest_version, version)

        return highest_version

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
        with proxy_request("post", url, headers={'Authorization': itch_api_key}) as response:
            if response.status_code == 400 or response.status_code == 404:
                return
            download = json.loads(response.text)
            if 'url' in download:
                print("\n[get_script_stats] Download response: " + download['url'] + "\n")
                download_path = 'tmp/' + upload_info['filename']
                try:
                    file = proxy_request("get", download['url'], allow_redirects=True)
                    if response.status_code == 400 or response.status_code == 404:
                        return
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
                    if not os.path.isdir(game_dir + '/lib/py2-linux-x86_64') and not os.path.isdir(
                            game_dir + '/lib/py3-linux-x86_64') and not os.path.isdir(game_dir + '/lib/linux-x86_64'):
                        shutil.copyfile('./renpy/renpy.py', game_dir + '/renpy.py')
                        shutil.copyfile('./renpy/renpy.sh', game_dir + '/renpy.sh')
                        shutil.copytree('./renpy/py3-linux-x86_64', game_dir + '/lib/py3-linux-x86_64',
                                        dirs_exist_ok=True)
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

    id = Column(BigInteger, (Identity()), primary_key=True)
    game_id = Column(Integer, nullable=False)
    version = Column(String(20))
    devlog = Column(String(250))
    platform_windows = Column(BOOLEAN, nullable=False, default=False)
    platform_linux = Column(BOOLEAN, nullable=False, default=False)
    platform_mac = Column(BOOLEAN, nullable=False, default=False)
    platform_android = Column(BOOLEAN, nullable=False, default=False)
    platform_web = Column(BOOLEAN, nullable=False, default=False)
    stats_blocks = Column(Integer, nullable=False, default=0)
    stats_menus = Column(Integer, nullable=False, default=0)
    stats_options = Column(Integer, nullable=False, default=0)
    stats_words = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    published_at = Column(DateTime, nullable=False)
    rating = Column(Float)
    rating_count = Column(Integer)

    def __init__(self, game_id, version, devlog, platform_windows, platform_linux, platform_mac, platform_android,
                 platform_web, stats_blocks, stats_menus, stats_options, stats_words, created_at, updated_at,
                 published_at, rating, rating_count):
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
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.published_at = published_at
        self.rating = rating
        self.rating_count = rating_count

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
            'updated_at': self.updated_at,
            'published_at': self.published_at,
            'rating': self.rating,
            'rating_count': self.rating_count
        }


class User(Base):
    __tablename__ = 'discord_users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(DateTime, nullable=False)

    def __init__(self, discord_id, processed_at):
        self.discord_id = discord_id
        self.processed_at = processed_at


class Rater(Base):
    __tablename__ = 'raters'

    id = Column(BigInteger, (Identity()), primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(Text(), nullable=False)
    username = Column(Text())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    ratings = relationship("Rating", back_populates="rater")

    def __init__(self, user_id, name, username=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.name = name
        self.username = username
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name
        }


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(BigInteger, (Identity()), primary_key=True)
    event_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    published_at = Column(DateTime, nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'))
    rater_id = Column(Integer, ForeignKey('raters.id'))
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    visible = Column(BOOLEAN, default=False)
    has_review = Column(BOOLEAN, nullable=False, default=False)
    game = relationship("Game", back_populates="ratings")
    rater = relationship("Rater", back_populates="ratings")

    def __init__(self, event_id, created_at, updated_at, published_at, game_id, rater_id, rating, review, visible=True):
        self.event_id = event_id
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.published_at = published_at
        self.game_id = game_id
        self.rater_id = rater_id
        self.rating = rating
        self.review = review
        self.visible = visible
        self.has_review = (review != '')

    def to_dict(self):
        return {
            'event_id': self.event_id,
            'updated_at': self.updated_at,
            'rater_id': self.rater_id,
            'game_id': self.game_id,
            'rating': self.rating,
            'review': self.review
        }

    @staticmethod
    @retry(wait=wait_exponential(multiplier=2, min=30, max=120))
    def get_request_session():
        global request_session

        # Try to load existing session with cookies
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'rb') as f:
                cookies = pickle.load(f)
                request_session = requests.Session()
                request_session.cookies.update(cookies)

                # Verify the session is still valid with a test request
                try:
                    test_response = request_session.get('https://itch.io/dashboard', timeout=5)
                    if test_response.status_code == 200 and 'login' not in test_response.url:
                        return request_session
                except:
                    pass

        # If no valid session exists, create a new one
        if request_session is None:
            print("\n[get_request_session] Attempting Login\n")

            ITCH_USER = os.environ['ITCH_USER']
            ITCH_PASSWORD = os.environ['ITCH_PASSWORD']

            request_session = requests.Session()

            # Get CSRF token
            url = "https://itch.io/login"
            time.sleep(10)
            login = request_session.get(url, timeout=5)
            if login.status_code != 200:
                raise RequestException("Status code not 200, retrying")

            soup = BeautifulSoup(login.text, "html.parser")
            csrf_token = soup.find("input", {"name": "csrf_token"})["value"]

            # Login
            time.sleep(10)
            response = request_session.post(
                url,
                data={
                    "username": ITCH_USER,
                    "password": ITCH_PASSWORD,
                    "csrf_token": csrf_token
                },
                timeout=5
            )

            if response.status_code != 200:
                raise RequestException("Status code not 200, retrying")

            # Save cookies for future use
            with open(COOKIES_FILE, 'wb') as f:
                pickle.dump(request_session.cookies, f)

        return request_session

    @staticmethod
    def import_latest_reviews():
        # Get the newest timestamp
        end_event_id = None
        with Session() as session:
            newest_review = session.query(Rating).order_by(Rating.event_id.desc()).first()
            if newest_review:
                end_event_id = newest_review.event_id

        start_event_id = None

        request_session = Rating.get_request_session()

        while True:
            print("\n[reviews] Loop start: " + str(start_event_id) + "\n")
            start_event_id = Rating.import_reviews(request_session, start_event_id)
            if start_event_id is None or start_event_id < end_event_id:
                print("\n[reviews] Import finished: ", str(start_event_id), " ", str(end_event_id), "\n")
                break
            print("\n[reviews] Loop end: " + str(start_event_id) + "\n\n")
            time.sleep(30)

    @staticmethod
    @retry(wait=wait_exponential(multiplier=2, min=30, max=120))
    def import_reviews(request_session, start_event_id=None):
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
                    user_name = review.find("a", {"data-label": "event_user", "class": "event_source_user"},
                                            href=True).text
                    user_username = \
                    review.find("a", {"data-label": "event_user", "class": "event_source_user"}, href=True)[
                        'href'].split('/')[-1].split('.')[0]
                    event_time = review.find("a", {"class": "event_time"}, href=True)
                    event_id = int(event_time['href'].split('/')[-1])
                    updated_at = datetime.datetime.fromisoformat(
                        event_time['title'] + '+00:00'
                    )
                    game_info = review.find("a", {"class": "object_title"}, href=True)
                    game_name = game_info.text
                    game_url = game_info['href']
                    game_cell = review.find("div", {"class": "game_cell"})
                    if game_cell:
                        itch_game_id = int(game_cell['data-game_id'])
                    else:
                        itch_game_id = int(Rating.get_game_id(game_url))
                    rating = len(review.find_all("span", {"class": "icon-star"}))
                    rating_blurb = review.find("div", {"class": "rating_blurb"})
                    review_text = ''
                    if rating_blurb:
                        review_text = rating_blurb
                    existing_reviewer = session.query(Rater).filter_by(user_id=itch_user_id).first()
                    if existing_reviewer is None:
                        new_reviewer = Rater(itch_user_id, str(user_name), str(user_username), updated_at, updated_at)
                        session.add(new_reviewer)
                        session.commit()
                        session.flush()
                        reviewer_id = new_reviewer.id
                    elif user_name != existing_reviewer.name:
                        existing_reviewer.name = user_name
                        existing_reviewer.updated_at = updated_at
                        session.commit()
                    elif user_username != existing_reviewer.username:
                        existing_reviewer.username = user_username
                        existing_reviewer.updated_at = updated_at
                        session.commit()
                    if existing_reviewer is not None:
                        reviewer_id = existing_reviewer.id
                    existing_game = session.query(Game).filter_by(game_id=itch_game_id).first()
                    if existing_game is None:
                        new_game = Game(game_id=itch_game_id, name=str(game_name), url=game_url, visible=False)
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
                    existing_review = session.query(Rating).filter_by(event_id=event_id).first()
                    if existing_review is None:
                        new_review = Rating(event_id, updated_at, updated_at, updated_at, game_id, reviewer_id, rating,
                                            str(review_text))
                        session.query(Rating). \
                            filter(Rating.game_id == new_review.game_id, Rating.rater_id == new_review.rater_id). \
                            update({'visible': False})
                        session.commit()
                        session.add(new_review)
                        session.commit()
                    if start_event_id is None or start_event_id > event_id:
                        start_event_id = event_id
            if start_event_id is None and previous_start_event_id is not None:
                start_event_id = previous_start_event_id - 1

        return start_event_id

    @staticmethod
    def get_game_id(url):
        print("\n[get_game_id] URL: " + url + "\n")
        with proxy_request("get", url, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                raise RuntimeError("Could not find game ID")
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
