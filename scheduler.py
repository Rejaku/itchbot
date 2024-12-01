import datetime
import json
import threading
import time

import backoff
import requests
import schedule

import models
from models import engine, Session, Base, Game

Base.metadata.create_all(engine)


def refresh_tags_and_rating():
    print("\n[refresh_tags_and_rating] Start\n")
    with Session() as session:
        games = session.query(Game).filter(Game.visible == True).all()
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


def refresh_version(itch_api_key, status=None):
    print("\n[refresh_version] Start\n")
    with Session() as session:
        if status:
            games = session.query(Game) \
                .filter(Game.visible == True, Game.status.in_(status)) \
                .order_by(Game.id) \
                .all()
        else:
            games = session.query(Game) \
                .filter(Game.status != 'Abandoned', Game.status != 'Canceled') \
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

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError),
                          jitter=None,
                          base=60)
    def update_watchlist_page(self, page: int):
        with models.proxy_request(
                'get',
                'https://api.itch.io/collections/' + self.itch_collection_id + '/collection-games?page=' + str(page),
                headers={'Authorization': self.itch_api_key}
        ) as response:
            collection = json.loads(response.text)
            if len(collection['collection_games']) == 0:
                print("\nNo more!\n")
                return False

            with Session() as session:
                for collection_entry in collection['collection_games']:
                    game = session.query(Game) \
                        .filter(Game.game_id == collection_entry['game']['id']) \
                        .first()
                    # Update if already in DB
                    if game:
                        if not game.visible:
                            game.visible = True
                            game.updated_at = datetime.datetime.utcnow()
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
                        session.commit()
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
                            version='unknown',
                            visible=True,
                        )
                        session.add(game)
                        session.commit()
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
        schedule.every(15).minutes.do(models.Rating.import_latest_reviews)
        schedule.every(6).hours.do(refresh_version, self.itch_api_key, ['In development'])
        schedule.every().day.at("00:00").do(self.update_watchlist)
        schedule.every().day.at("03:00").do(refresh_tags_and_rating)
        schedule.every().monday.at("06:00").do(refresh_version, self.itch_api_key, ['Released', 'Prototype'])
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(30)
