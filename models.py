# coding=utf-8

from sqlalchemy import create_engine, Column, String, Integer, FLOAT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///VNs.db', echo=True)
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
