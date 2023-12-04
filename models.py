# coding=utf-8

import datetime
import json
import os
import re
import subprocess
import urllib.request
import zipfile
import tarfile
import shutil
from urllib.error import ContentTooShortError, HTTPError

from sqlalchemy import create_engine, Column, String, Integer, Float
from sqlalchemy.orm import declarative_base, sessionmaker
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

    def __init__(self, service, game_id, name, description, url, thumb_url, latest_version='unknown', devlog=None,
                 tags=None, languages=None, rating=None, rating_count=None, status='In development',
                 platform_windows=0, platform_linux=0, platform_mac=0, platform_android=0, platform_web=0,
                 stats_blocks=0, stats_menus=0, stats_options=0, stats_words=0, game_engine='unknown',
                 created_at=0, updated_at=0):
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
            'updated_at': self.updated_at
        }

    def refresh_tags_and_rating(self, itch_api_key, force: bool = False):
        req = urllib.request.Request(self.url)
        req.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req) as url:
            html = url.read().decode("utf8")
            soup = BeautifulSoup(html, 'html.parser')
            if force or self.status not in ['Abandoned', 'Canceled']:
                game_info = soup.find("div", {"class": "game_info_panel_widget"}).find_all("a", href=True)
                if game_info:
                    self.status = game_info[0].text
            devlog = soup.find("section", id="devlog")
            if devlog:
                devlog_links = devlog.find_all('a', href=True)
                if devlog_links:
                    self.devlog = devlog_links[0]['href']
            json_lds = soup.findAll("script", {"type": "application/ld+json"})
            for json_ld in json_lds:
                json_content = json.loads("".join(json_ld.contents))
                if json_content.get('aggregateRating'):
                    self.rating = json_content['aggregateRating'].get('ratingValue')
                    self.rating_count = json_content['aggregateRating'].get('ratingCount')
            info_table = soup.find("div", {"class": "game_info_panel_widget"}).find("table")
            for tr in info_table.findAll('tr'):
                if tr.text.find('Languages') > -1:
                    self.languages = tr.text.strip()[9:]
                if tr.text.find('Published') > -1:
                    self.created_at = tr.text.strip()[9:]
                if tr.text.find('Tags') > -1:
                    self.tags = tr.text.strip()[4:]

    def refresh_base_info(self, itch_api_key):
        req = urllib.request.Request('https://api.itch.io/games/' + self.game_id)
        req.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req) as url:
            game = json.load(url)
            if 'game' in game:
                publish_datetime = datetime.datetime.strptime(
                    game['game']['published_at'],
                    '%Y-%m-%dT%H:%M:%S.000000000Z'
                )
                self.created_at = publish_datetime.timestamp()
                self.thumb_url = game['game']['cover_url']

    def refresh_version(self, itch_api_key, force: bool = False):
        req = urllib.request.Request('https://api.itch.io/games/' + self.game_id + '/uploads')
        req.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req) as url:
            uploads = json.load(url)
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
                latest_timestamp = 0
                # Force update check by setting updated_at to 0
                if force and (linux_upload or windows_upload or android_upload):
                    self.updated_at = 0
                for upload in [linux_upload, windows_upload, android_upload]:
                    if upload is None:
                        continue
                    element = datetime.datetime.strptime(upload['updated_at'], "%Y-%m-%dT%H:%M:%S.%f000Z")
                    timestamp = int(datetime.datetime.timestamp(element))
                    if latest_timestamp < timestamp:
                        latest_timestamp = timestamp
                    # Take the newest timestamp from the uploads
                    if self.updated_at < timestamp:
                        for version_number_source in ['build.user_version', 'filename', 'display_name']:
                            if version_number_source == 'build.user_version' and upload.get('build') and upload['build'].get('user_version'):
                                self.updated_at = timestamp
                                self.latest_version = upload['build']['user_version']
                                if upload is linux_upload:
                                    self.get_script_stats(itch_api_key, linux_upload)
                                break
                            elif upload.get(version_number_source):
                                version_number_string = upload[version_number_source]
                                # Extract version number from source string, matches anything from 1 to 1.2.3.4...
                                matches = re.compile(r'\d+(=?\.(\d+(=?\.(\d+)*)*)*)*').search(version_number_string)
                                if matches:
                                    self.updated_at = timestamp
                                    self.latest_version = matches.group(0).rstrip('.')
                                    if upload is linux_upload:
                                        self.get_script_stats(itch_api_key, linux_upload)
                                    break
                    if upload['type'] == 'html':
                        self.platform_web = 1
                self.updated_at = latest_timestamp

    def get_script_stats(self, itch_api_key, upload_info):
        # Only continue if the game is made with Ren'Py or unknown
        if self.game_engine != "Ren'Py" and self.game_engine != "unknown":
            return
        # Reset status to 0
        self.stats_blocks = 0
        self.stats_menus = 0
        self.stats_options = 0
        self.stats_words = 0
        # Download the game
        req_download = urllib.request.Request(
            self.url + '/file/' + str(upload_info['id']),
            method='POST'
        )
        req_download.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req_download) as download_url:
            download = json.load(download_url)
            if 'url' in download:
                download_path = 'tmp/' + upload_info['filename']
                try:
                    urllib.request.urlretrieve(download['url'], download_path)
                except (ContentTooShortError, HTTPError):
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
                game_dir = []
                game_dir_files = []
                if os.path.isdir(extract_directory):
                    directory_listing = os.listdir(extract_directory)
                if len(directory_listing) == 1:
                    game_dir = extract_directory + '/' + quote(directory_listing[0])
                    if os.path.isdir(game_dir):
                        game_dir_files = os.listdir(game_dir)
                if len(game_dir_files) > 0 and os.path.isdir(game_dir + "/game"):
                    shutil.copyfile('./renpy/wordcounter.rpy', game_dir + '/game/wordcounter.rpy')
                    for game_dir_file in game_dir_files:
                        if game_dir_file.endswith('.sh'):
                            subprocess.run(f'chmod -R +x {quote(directory_listing[0])}',
                                           cwd=extract_directory, shell=True)
                            subprocess.run(f'{quote(directory_listing[0])}/{quote(game_dir_file)} {quote(directory_listing[0])}/game test',
                                           cwd=extract_directory, shell=True)
                            if os.path.isfile(extract_directory + '/stats.json'):
                                stats_file = open(extract_directory + '/stats.json')
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

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(Integer, nullable=False)

    def __init__(self, discord_id, processed_at):
        self.discord_id = discord_id
        self.processed_at = processed_at
