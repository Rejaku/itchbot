import datetime
import json
import threading
import time
from typing import Optional

from bs4 import BeautifulSoup
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
        self.request_session = None

    def get_request_session(self):
        """Get or create an authenticated request session"""
        if self.request_session is None:
            self.request_session = Rating.get_request_session()
        return self.request_session

    def process_feed_page(self, from_event: Optional[int] = None) -> Optional[int]:
        """Process a single feed page and return the next page event ID if available"""
        url = 'https://itch.io/my-feed?filter=posts&format=json'
        if from_event:
            url += f'&from_event={from_event}'

        print(f"\n[process_feed_page] URL: {url}\n")

        session = self.get_request_session()
        response = session.get(url, timeout=30)
        if response.status_code != 200:
            print(f"\n[process_feed_page] Error: Status code {response.status_code}\n")
            return None

        feed_data = json.loads(response.text)

        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(feed_data['content'], 'html.parser')

        # Find all event rows
        event_rows = soup.find_all("div", {"class": "event_row"})

        with Session() as db_session:
            # Get highest processed event ID once before the loop
            highest_processed = db_session.query(ProcessedEvent) \
                .order_by(desc(ProcessedEvent.event_id)) \
                .first()
            highest_event_id = highest_processed.event_id if highest_processed else None

            for event_row in event_rows:
                # Get event ID from the like button
                like_btn = event_row.find("span", {"class": "like_btn"})
                if not like_btn:
                    continue

                event_id = int(like_btn['data-like_url'].split('/')[-2])

                # If we've reached an event ID that's lower than or equal to our highest processed ID,
                # we can stop processing entirely
                if highest_event_id and event_id <= highest_event_id:
                    return None  # This will break the pagination loop too

                event_id = int(like_btn['data-like_url'].split('/')[-2])

                # Check if we've already processed this event
                existing_event = db_session.query(ProcessedEvent).filter_by(event_id=event_id).first()
                if existing_event:
                    continue

                # Look for uploads
                upload_list = event_row.find("div", {"class": "upload_list_widget"})
                if not upload_list:
                    continue

                # Get game ID
                game_cell = event_row.find("div", {"class": "game_cell"})
                if not game_cell or 'data-game_id' not in game_cell.attrs:
                    continue

                game_id = int(game_cell['data-game_id'])

                # Get game from database
                game = db_session.query(Game).filter_by(game_id=game_id).first()

                # If game doesn't exist, create it with basic info
                if not game:
                    # Extract basic game info from the feed
                    game_cell_link = game_cell.find("a", {"class": "game_link"})
                    if not game_cell_link:
                        continue

                    game_url = game_cell_link.get('href', '')
                    game_thumb = game_cell.find("img")
                    game_thumb_url = game_thumb.get('data-lazy_src') if game_thumb else None

                    # Get game title from the object_short_summary
                    short_summary = event_row.find("div", {"class": "object_short_summary"})
                    game_title = None
                    if short_summary:
                        game_link = short_summary.find("a")
                        if game_link:
                            game_title = game_link.text

                    if not game_title or not game_url:
                        continue

                    print(f"\n[process_feed_page] Creating new game {game_id}: {game_title}\n")

                    # Create new game entry - note visible=False
                    game = Game(
                        game_id=game_id,
                        name=game_title,
                        description=None,  # We'll get this during refresh
                        url=game_url,
                        thumb_url=game_thumb_url,
                        version='unknown',
                        visible=False  # Let collection process handle visibility
                    )
                    db_session.add(game)
                    db_session.commit()

                print(f"\n[process_feed_page] Processing update for game {game_id}\n")

                try:
                    game.refresh_version(self.itch_api_key)
                    game.error = None

                    # Record that we processed this event
                    processed_event = ProcessedEvent(event_id, game_id)
                    db_session.add(processed_event)

                except Exception as exception:
                    print(f"\n[Update Error] {exception}\n")
                    game.error = str(exception)
                db_session.commit()
                time.sleep(10)

        return feed_data.get('next_page')

    def process_feed(self):
        """Process the feed starting from the last processed event"""
        print("\n[process_feed] Start\n")

        with Session() as session:
            # Get highest event ID we've processed
            last_processed = session.query(ProcessedEvent) \
                .order_by(desc(ProcessedEvent.event_id)) \
                .first()
            last_event_id = last_processed.event_id if last_processed else None

        current_page = None
        while True:
            next_page = self.process_feed_page(current_page)

            if not next_page:
                break

            if last_event_id and next_page <= last_event_id:
                break

            current_page = next_page
            time.sleep(30)  # Delay between pages

        print("\n[process_feed] End\n")

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
        schedule.every(15).minutes.do(self.process_feed)  # New feed processing
        schedule.every(15).minutes.do(models.Rating.import_latest_reviews)
        schedule.every().day.at("00:00").do(self.update_watchlist)
        schedule.every().day.at("03:00").do(refresh_tags_and_rating)
        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            schedule.run_pending()
            time.sleep(30)
