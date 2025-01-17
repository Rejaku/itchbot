import datetime
import json
import threading
import time

import schedule
from sqlalchemy import Column, Integer, DateTime, desc

import models
from models import engine, Session, Base, Game, Rating

Base.metadata.create_all(engine)


class ProcessedEvent(Base):
    __tablename__ = 'processed_events'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, nullable=False, index=True)
    game_id = Column(Integer, nullable=False)
    processed_at = Column(DateTime, nullable=False)

    def __init__(self, event_id, game_id):
        self.event_id = event_id
        self.game_id = game_id
        self.processed_at = datetime.datetime.utcnow()


def refresh_tags_and_rating():
    print("\n[refresh_tags_and_rating] Start\n")
    with Session() as session:
        games = session.query(Game).filter(Game.is_visible == True).all()
        for game in games:
            try:
                game.refresh_tags_and_rating()
                game.error = None
            except Exception as exception:
                print("\n[Update Error] ", exception, "\n")
                game.error = exception
            session.commit()
            time.sleep(10)
    print("\n[refresh_tags_and_rating] End\n")


def refresh_version(itch_api_key):
    print("\n[refresh_version] Start\n")
    with Session() as session:
        games = session \
            .query(Game) \
            .filter(Game.is_visible == True) \
            .filter(Game.is_feedless == True) \
            .order_by(Game.id) \
            .all()
        for game in games:
            try:
                game.refresh_version(itch_api_key)
                game.error = None
            except Exception as exception:
                print("\n[Update Error] ", exception, "\n")
                game.error = str(exception)
            session.commit()
            time.sleep(10)
    print("\n[refresh_version] End\n")


class Scheduler:
    def __init__(self):
        self.itch_api_key = None
        self.itch_collection_id = None
        self.request_session = None

    def get_request_session(self):
        """Get or create an authenticated request session"""
        if self.request_session is None:
            self.request_session = Rating.get_request_session()
        return self.request_session


    def update_watchlist_page(self, page: int):
        with models.make_request(
                'get',
                'https://api.itch.io/collections/' + self.itch_collection_id + '/collection-games?page=' + str(page),
                headers={'Authorization': self.itch_api_key}
        ) as response:
            if response.status_code == 400 or response.status_code == 404:
                return False
            collection = json.loads(response.text)
            if len(collection['collection_games']) == 0:
                print("\nNo more!\n")
                return False

            with Session() as session:
                for collection_entry in collection['collection_games']:
                    game = session.query(Game) \
                        .filter(Game.game_id == collection_entry['game']['id']) \
                        .first()

                    should_load_details = False

                    # Update if already in DB
                    if game:
                        if not game.is_visible:
                            game.updated_at = datetime.datetime.utcnow()
                            should_load_details = True
                        if collection_entry['game'].get('title') != game.name \
                                or collection_entry['game'].get('short_text') != game.description \
                                or collection_entry['game'].get('cover_url') != game.thumb_url:
                            game.name = collection_entry['game'].get('title')
                            game.description = collection_entry['game'].get('short_text')
                            game.thumb_url = collection_entry['game'].get('cover_url')
                            game.updated_at = datetime.datetime.utcnow()
                        if game.initially_published_at is None:
                            game.initially_published_at = datetime.datetime.fromisoformat(
                                collection_entry['game']['published_at']
                            )
                            game.updated_at = datetime.datetime.utcnow()
                    else:
                        game = Game(
                            initially_published_at=datetime.datetime.fromisoformat(
                                collection_entry['game']['published_at']
                            ),
                            game_id=collection_entry['game']['id'],
                            name=collection_entry['game']['title'],
                            description=collection_entry['game'].get('short_text'),
                            url=collection_entry['game']['url'],
                            thumb_url=collection_entry['game'].get('cover_url'),
                        )
                        session.add(game)
                        session.flush()
                        should_load_details = True

                    # Load full details if needed
                    if should_load_details:
                        try:
                            game.is_visible = True
                            game.load_full_details(self.itch_api_key)
                        except Exception as e:
                            print(f"Failed to load full details for game {game.id}: {str(e)}")
                    session.commit()

                    time.sleep(10)  # Rate limiting between games
            return True

    def update_watchlist(self):
        print("\n[update_watchlist] Start\n")
        page = 0
        while True:
            page += 1
            has_more = self.update_watchlist_page(page)
            if not has_more:
                break
            time.sleep(30)
        print("\n[update_watchlist] End\n")

    def run(
            self,
            itch_api_key: str,
            itch_collection_id: str
    ) -> None:
        self.itch_api_key = itch_api_key
        self.itch_collection_id = itch_collection_id

        # makes our logic non-blocking
        thread = threading.Thread(target=self.scheduler)
        thread.start()

    def scheduler(self):
        print("\n[scheduler] Start\n")
        schedule.every().day.at("00:00").do(self.update_watchlist)
        schedule.every().day.at("03:00").do(refresh_tags_and_rating)
        # Once a day, check games that don't use feed updates
        schedule.every().day.at("06:00").do(refresh_version, self.itch_api_key)
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(30)