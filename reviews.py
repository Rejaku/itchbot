# coding=utf-8
import os
import time

from bs4 import BeautifulSoup
from requests_html import HTMLSession

from models import Session, Review

ITCH_USER = os.environ['ITCH_USER']
ITCH_PASSWORD = os.environ['ITCH_PASSWORD']

url = "https://itch.io/login"
request_session = HTMLSession()
login = request_session.get(url)
s = BeautifulSoup(login.text, "html.parser")
csrf_token = s.find("input", {"name": "csrf_token"})["value"]
request_session.post(
    url,
 {"username": ITCH_USER, "password": ITCH_PASSWORD, "csrf_token": csrf_token}
)

# Get the oldest timestamp
session = Session()
oldest_review = session.query(Review).order_by(Review.event_id.asc()).first()

start_event_id = None
if oldest_review:
    start_event_id = oldest_review.event_id

while True:
    print('[reviews] Loop start: ' + str(start_event_id))
    start_event_id = Review.import_reviews(request_session, start_event_id)
    if start_event_id is None or start_event_id < 19600000:
        break
    print('[reviews] Loop end: ' + str(start_event_id))
    time.sleep(10)
