# coding=utf-8

import datetime
import json
import os
import re
import urllib.request

from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    f'mariadb+pymysql://{os.environ["DB_USER"]}:{os.environ["DB_PASSWORD"]}@db/{os.environ["DB"]}?charset=utf8mb4',
    echo=True
)
Session = sessionmaker(bind=engine)

Base = declarative_base()


class VisualNovel(Base):
    __tablename__ = 'visual_novels'

    id = Column(Integer, primary_key=True)
    service = Column(String(50), nullable=False)
    game_id = Column(String(50), nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(200))
    url = Column(String(250), nullable=False)
    thumb_url = Column(String(250))
    latest_version = Column(String(20))
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer)

    def __init__(self, service, game_id, name, description, url, thumb_url, latest_version, created_at, updated_at):
        self.service = service
        self.game_id = game_id
        self.name = name
        self.description = description
        self.url = url
        self.thumb_url = thumb_url
        self.latest_version = latest_version
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
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def refresh_data(self, itch_api_key):
        req = urllib.request.Request('https://api.itch.io/games/' + self.game_id + '/uploads')
        req.add_header('Authorization', itch_api_key)
        with urllib.request.urlopen(req) as url:
            uploads = json.load(url)
            for upload in uploads['uploads']:
                if 'p_windows' in upload['traits']:
                    element = datetime.datetime.strptime(upload['updated_at'], "%Y-%m-%dT%H:%M:%S.%f000Z")
                    timestamp = int(datetime.datetime.timestamp(element))
                    # Only process if the timestamp differs from already stored info
                    if self.updated_at != timestamp:
                        # Most projects just put the version number into the filename, so extract from there
                        version_number_source = upload['filename']
                        # A few use the version number field in itch.io, prefer that, if set
                        if upload.get('build') and upload['build'].get('user_version'):
                            version_number_source = upload['build']['user_version']
                        # Extract version number from source string, matches anything from 1 to 1.2.3.4...
                        matches = re.compile(r'\d+(=?\.(\d+(=?\.(\d+)*)*)*)*').search(version_number_source)
                        if matches:
                            version = matches.group(0).rstrip('.')
                        else:
                            version = 'unknown'
                        self.latest_version = version
                        self.updated_at = timestamp
                    break


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(Integer, nullable=False)

    def __init__(self, discord_id, processed_at):
        self.discord_id = discord_id
        self.processed_at = processed_at
