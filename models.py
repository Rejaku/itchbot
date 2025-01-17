# coding=utf-8

import os

from sqlalchemy import create_engine, Column, String, Integer, Float, Text, BOOLEAN, DateTime, BigInteger, \
    Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

engine = create_engine(
    f'postgresql+psycopg2://{os.environ["DB_USER"]}:{os.environ["DB_PASSWORD"]}@db/{os.environ["DB"]}?client_encoding=utf8',
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=True
)
Session = sessionmaker(bind=engine)

Base = declarative_base()
request_session = None
COOKIES_FILE = 'itch_cookies.pkl'


class Game(Base):
    __tablename__ = 'games'

    id = Column(BigInteger, (Identity()), primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    initially_published_at = Column(DateTime)
    game_id = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(String(50))
    is_visible = Column(BOOLEAN, default=False)
    is_nsfw = Column(BOOLEAN, default=False)
    description = Column(String(200))
    url = Column(String(250), nullable=False)
    thumb_url = Column(String(250))
    tags = Column(String(250))
    game_engine = Column(String(50))
    error = Column(Text)
    authors = Column(Text)
    custom_tags = Column(String(250), nullable=False)
    uploads = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    is_feedless = Column(BOOLEAN, nullable=False, default=False)
    slug = Column(String(250))
    ratings = relationship("Rating", back_populates="game")


class GameVersion(Base):
    __tablename__ = 'game_versions'

    id = Column(BigInteger, (Identity()), primary_key=True)
    game_id = Column(Integer, nullable=False)
    version = Column(String(20))
    devlog = Column(String(250))
    is_windows = Column(BOOLEAN, nullable=False, default=False)
    is_linux = Column(BOOLEAN, nullable=False, default=False)
    is_mac = Column(BOOLEAN, nullable=False, default=False)
    is_android = Column(BOOLEAN, nullable=False, default=False)
    is_web = Column(BOOLEAN, nullable=False, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    published_at = Column(DateTime, nullable=False)
    rating = Column(Float)
    rating_count = Column(Integer)
    is_latest = Column(BOOLEAN, nullable=False, default=False)
    language_stats = relationship("VersionLanguageStats", back_populates="game_version")
    character_stats = relationship("VersionCharacterStats", back_populates="game_version")


class User(Base):
    __tablename__ = 'discord_users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(DateTime, nullable=False)

