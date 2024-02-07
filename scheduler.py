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


def refresh_tags_and_rating(itch_api_key):
    print('[refresh_tags_and_rating] Start')
    with Session() as session:
        games = session.query(Game).filter(Game.hidden == 0).all()
        for game in games:
            try:
                game.refresh_tags_and_rating(itch_api_key)
                game.error = None
            except Exception as exception:
                print('[Update Error]', exception)
                game.error = exception
            session.commit()
            time.sleep(10)
    print('[refresh_tags_and_rating] End')


def refresh_version(itch_api_key, status=None):
    print('[refresh_version] Start')
    with Session() as session:
        if status:
            games = session.query(Game) \
                .filter(Game.hidden == 0, Game.status.in_(status)) \
                .all()
        else:
            games = session.query(Game) \
                .filter(Game.status != 'Abandoned', Game.status != 'Canceled') \
                .all()
        for game in games:
            try:
                game.refresh_version(itch_api_key)
                game.error = None
            except Exception as exception:
                print('[Update Error]', exception)
                game.error = exception
            session.commit()
            time.sleep(10)
    print('[refresh_version] End')


class Scheduler:

    def __init__(self):
        self.itch_api_key = None
        self.itch_collection_id = None

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError),
                          jitter=None,
                          base=10)
    def update_watchlist_page(self, page: int):
        with requests.get(
                'https://api.itch.io/collections/' + self.itch_collection_id + '/collection-games?page=' + str(page),
                headers={'Authorization': self.itch_api_key},
                timeout=5
        ) as response:
            collection = json.loads(response.text)
            if len(collection['collection_games']) == 0:
                print('No more!')
                return False

            with Session() as session:
                for collection_entry in collection['collection_games']:
                    game = session.query(Game) \
                        .filter(Game.hidden == 0, Game.game_id == collection_entry['game']['id']) \
                        .first()
                    # Update if already in DB
                    if game:
                        if collection_entry['game'].get('title') != game.name \
                                or collection_entry['game'].get('short_text') != game.description \
                                or collection_entry['game'].get('cover_url') != game.thumb_url:
                            game.name = collection_entry['game'].get('title')
                            game.description = collection_entry['game'].get('short_text')
                            game.thumb_url = collection_entry['game'].get('cover_url')
                            session.commit()
                        if game.created_at == 0:
                            game.created_at = int(datetime.datetime.fromisoformat(
                                collection_entry['game']['published_at']
                            ).timestamp())
                            session.commit()
                    else:
                        game = Game(
                            service='itch',
                            game_id=collection_entry['game']['id'],
                            name=collection_entry['game']['title'],
                            description=collection_entry['game'].get('short_text'),
                            url=collection_entry['game']['url'],
                            thumb_url=collection_entry['game'].get('cover_url'),
                            latest_version='unknown',
                            created_at=int(datetime.datetime.fromisoformat(
                                collection_entry['game']['published_at']
                            ).timestamp()),
                            updated_at=0
                        )
                        session.add(game)
                        session.commit()
            return True

    def update_watchlist(self):
        print('[update_watchlist] Start')
        page = 0
        while True:
            page += 1
            has_more = self.update_watchlist_page(page)
            if not has_more:
                break
            time.sleep(10)
        print('[update_watchlist] End')

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
        print('[scheduler] Start')
        schedule.every(15).minutes.do(models.Review.import_latest_reviews)
        schedule.every(3).hours.at("00:00").do(refresh_version, self.itch_api_key, ['In development'])
        schedule.every().day.at("00:00").do(self.update_watchlist)
        schedule.every().day.at("03:00").do(refresh_tags_and_rating, self.itch_api_key)
        schedule.every().monday.at("06:00").do(refresh_version, self.itch_api_key, ['Released', 'Prototype'])
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(30)
