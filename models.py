# coding=utf-8

import os
from sqlalchemy import create_engine, Column, String, Integer, FLOAT
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
    created_at = Column(FLOAT, nullable=False)
    updated_at = Column(FLOAT, nullable=False)

    def __init__(self, service, game_id, name, description, url, thumb_url, created_at):
        self.service = service
        self.game_id = game_id
        self.name = name
        self.description = description
        self.url = url
        self.thumb_url = thumb_url
        self.created_at = created_at
