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
                            created_at=time.time()
                        )
                        session.add(visual_novel)
                        session.commit()
                pass

    def update_version(self):
        visual_novels = session.query(VisualNovel).all()
        for visual_novel in visual_novels:
            req = urllib.request.Request('https://api.itch.io/games/' + visual_novel.game_id + '/uploads')
            req.add_header('Authorization', self.itch_api_key)
            with urllib.request.urlopen(req) as url:
                uploads = json.load(url)
                for upload in uploads['uploads']:
                    if 'p_windows' in upload['traits']:
                        element = datetime.datetime.strptime(upload['updated_at'], "%Y-%m-%dT%H:%M:%S.%f000Z")
                        timestamp = datetime.datetime.timestamp(element)
                        # Only process if the timestamp differs from already stored info
                        if visual_novel.updated_at != timestamp:
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
                            visual_novel.latest_version = version
                            visual_novel.updated_at = timestamp
                            session.commit()
                        break

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
        #self.update_watchlist()
        #self.update_version()
        schedule.every().day.do(self.update_watchlist)
        schedule.every().hour.do(self.update_version)
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(1)
