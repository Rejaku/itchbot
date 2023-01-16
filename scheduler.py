import json
import threading
import time
import urllib.request

import schedule

from models import engine, Session, Base, Game

Base.metadata.create_all(engine)


def refresh_tags_and_rating(itch_api_key):
    session = Session()
    games = session.query(Game).all()
    for game in games:
        game.refresh_tags_and_rating(itch_api_key)
        session.commit()
        time.sleep(1)
    session.close()

def refresh_version(itch_api_key):
    session = Session()
    games = session.query(Game).all()
    for game in games:
        game.refresh_version(itch_api_key)
        session.commit()
    session.close()


class Scheduler:

    def __init__(self):
        self.itch_api_key = None
        self.itch_collection_id = None

    def update_watchlist(self):
        session = Session()
        page = 0
        while True:
            page += 1
            req = urllib.request.Request(
                'https://api.itch.io/collections/' + self.itch_collection_id + '/collection-games?page=' + str(page)
            )
            req.add_header('Authorization', self.itch_api_key)
            with urllib.request.urlopen(req) as url:
                collection = json.load(url)
                if len(collection['collection_games']) == 0:
                    print('No more!')
                    break

                for collection_entry in collection['collection_games']:
                    game = session.query(Game) \
                        .filter(Game.service == 'itch', Game.game_id == collection_entry['game']['id']) \
                        .first()
                    # Update if already in DB
                    if game:
                        if collection_entry['game'].get('short_text') != game.description \
                                or collection_entry['game'].get('cover_url') != game.thumb_url:
                            game.description = collection_entry['game'].get('short_text')
                            game.thumb_url = collection_entry['game'].get('cover_url')
                            game.updated_at = time.time()
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
                            created_at=int(time.time()),
                            updated_at=0
                        )
                        session.add(game)
                        session.commit()
                pass
        session.close()

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
        self.update_watchlist()
        #update_version(self.itch_api_key)
        schedule.every().day.do(self.update_watchlist)
        schedule.every().day.do(refresh_tags_and_rating)
        schedule.every().hour.do(refresh_version)
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(1)
