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

from sqlalchemy import create_engine, Column, String, Integer, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from bs4 import BeautifulSoup

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
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer)

    def __init__(self, service, game_id, name, description, url, thumb_url, latest_version='unknown', devlog=None,
                 tags=None, languages=None, rating=None, rating_count=None, status='In development',
                 platform_windows=0, platform_linux=0, platform_mac=0, platform_android=0, platform_web=0,
                 stats_blocks=0, stats_menus=0, stats_options=0, stats_words=0,
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
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def refresh_tags_and_rating(self, itch_api_key):
        req = urllib.request.Request(self.url)
        req.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req) as url:
            html = url.read().decode("utf8")
            soup = BeautifulSoup(html, 'html.parser')
            if self.status == 'In development' or self.status == 'On hold':
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
                if tr.text.find('Tags') > -1:
                    self.tags = tr.text.strip()[4:]

    def refresh_version(self, itch_api_key):
        req = urllib.request.Request('https://api.itch.io/games/' + self.game_id + '/uploads')
        req.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req) as url:
            uploads = json.load(url)
            if uploads['uploads']:
                self.platform_windows = 0
                self.platform_linux = 0
                self.platform_mac = 0
                self.platform_android = 0
                self.platform_web = 0
                for upload in uploads['uploads']:
                    linux_upload = None
                    if upload['traits']:
                        if 'p_windows' in upload['traits']:
                            self.platform_windows = 1
                        if 'p_linux' in upload['traits']:
                            self.platform_linux = 1
                            linux_upload = upload
                        if 'p_osx' in upload['traits']:
                            self.platform_mac = 1
                        if 'p_android' in upload['traits']:
                            self.platform_android = 1
                    element = datetime.datetime.strptime(upload['updated_at'], "%Y-%m-%dT%H:%M:%S.%f000Z")
                    timestamp = int(datetime.datetime.timestamp(element))
                    # Take the newest timestamp from the uploads
                    if self.updated_at < timestamp:
                        for version_number_source in ['build.user_version', 'filename', 'display_name']:
                            self.updated_at = timestamp
                            if version_number_source == 'build.user_version' and upload.get('build') and upload['build'].get('user_version'):
                                self.latest_version = upload['build']['user_version']
                                if linux_upload:
                                    self.get_script_stats(itch_api_key, linux_upload)
                                break
                            elif upload.get(version_number_source):
                                version_number_string = upload[version_number_source]
                                # Extract version number from source string, matches anything from 1 to 1.2.3.4...
                                matches = re.compile(r'\d+(=?\.(\d+(=?\.(\d+)*)*)*)*').search(version_number_string)
                                if matches:
                                    self.latest_version = matches.group(0).rstrip('.')
                                    if linux_upload:
                                        self.get_script_stats(itch_api_key, linux_upload)
                                    break
                    if upload['type'] == 'html':
                        self.platform_web = 1

    def get_script_stats(self, itch_api_key, upload_info):
        # Download the game
        req_download = urllib.request.Request(
            self.url + '/file/' + str(upload_info['id']),
            method='POST'
        )
        req_download.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req_download) as download_url:
            download = json.load(download_url)
            if download['url']:
                download_path = 'tmp/' + upload_info['filename']
                urllib.request.urlretrieve(download['url'], download_path)
                extract_directory = f'tmp/{upload_info["id"]}'
                if download_path.endswith('.tar.gz'):
                    file = tarfile.open(download_path)
                    file.extractall(extract_directory)
                    file.close()
                elif download_path.endswith('.tar.bz2'):
                    file = tarfile.open(download_path, "r:bz2")
                    file.extractall(extract_directory)
                    file.close()
                elif download_path.endswith('.zip'):
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_directory)
                directory_listing = os.listdir(extract_directory)
                game_dir = []
                if len(directory_listing) == 1:
                    game_dir = extract_directory + '/' + directory_listing[0]
                    game_dir_files = os.listdir(game_dir)
                if len(game_dir_files) > 0:
                    shutil.copyfile('./renpy/wordcounter.rpy', game_dir + '/game/wordcounter.rpy')
                    for game_dir_file in game_dir_files:
                        if game_dir_file.endswith('.sh'):
                            subprocess.run(directory_listing[0] + '/' + game_dir_file,
                                           cwd=extract_directory, shell=True)
                            if os.path.isfile(extract_directory + '/stats.json'):
                                stats_file = open(extract_directory + '/stats.json')
                                stats = json.load(stats_file)
                                stats_file.close()
                                self.stats_blocks = stats['blocks']
                                self.stats_menus = stats['menus']
                                self.stats_options = stats['options']
                                self.stats_words = stats['words']
                                shutil.rmtree(game_dir)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(Integer, nullable=False)

    def __init__(self, discord_id, processed_at):
        self.discord_id = discord_id
        self.processed_at = processed_at
