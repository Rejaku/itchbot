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
start_event_id = None
with Session() as session:
    oldest_review = session.query(Review).order_by(Review.event_id.asc()).first()
    if oldest_review:
        start_event_id = oldest_review.event_id

while True:
    print('[reviews] Loop start: ' + str(start_event_id))
    start_event_id = Review.import_reviews(request_session, start_event_id)
    if start_event_id is None or start_event_id < 12000000:
        break
    print('[reviews] Loop end: ' + str(start_event_id) + "\n\n")
    time.sleep(10)
