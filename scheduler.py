import datetime
import json
import re
import threading
import time
import urllib.request

import schedule
from models import engine, Session, Base, VisualNovel

Base.metadata.create_all(engine)
session = Session()


def update_version(itch_api_key):
    visual_novels = session.query(VisualNovel).all()
    for visual_novel in visual_novels:
        visual_novel.refresh_data(itch_api_key)
        session.commit()


class Scheduler:

    def __init__(self):
        self.itch_api_key = None
        self.itch_collection_id = None

    def update_watchlist(self):
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
                    visual_novel = session.query(VisualNovel) \
                        .filter(VisualNovel.service == 'itch', VisualNovel.game_id == collection_entry['game']['id']) \
                        .first()
                    # Update if already in DB
                    if visual_novel:
                        if collection_entry['game'].get('short_text') != visual_novel.description \
                                or collection_entry['game'].get('cover_url') != visual_novel.thumb_url:
                            visual_novel.description = collection_entry['game'].get('short_text')
                            visual_novel.thumb_url = collection_entry['game'].get('cover_url')
                            visual_novel.updated_at = time.time()
                            session.commit()
                    else:
                        visual_novel = VisualNovel(
                            service='itch',
                            game_id=collection_entry['game']['id'],
                            name=collection_entry['game']['title'],
                            description=collection_entry['game'].get('short_text'),
                            url=collection_entry['game']['url'],
                            thumb_url=collection_entry['game'].get('cover_url'),
                            latest_version='unknown',
                            created_at=time.time(),
                            updated_at=0
                        )
                        session.add(visual_novel)
                        session.commit()
                pass

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
        schedule.every().hour.do(update_version)
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(1)
