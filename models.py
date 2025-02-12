# coding=utf-8

import datetime
import json
import os
import pickle
import re
import subprocess
import zipfile
import tarfile
import shutil
import time

import requests
from requests import RequestException
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, BOOLEAN, ForeignKey, DateTime, BigInteger, \
    Identity, func, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from bs4 import BeautifulSoup
from shlex import quote
from tenacity import *

engine = create_engine(
    f'postgresql+psycopg2://{os.environ["DB_USER"]}:{os.environ["DB_PASSWORD"]}@db/{os.environ["DB"]}?client_encoding=utf8',
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=True
)
Session = sessionmaker(bind=engine)

Base = declarative_base()
request_session = None
COOKIES_FILE = 'itch_cookies.pkl'

def process_language_stats(session, game_version_id, language_code, language_data, game_id):
    """Process language statistics for a given version and language"""
    # Create language stats record
    version_stats = VersionLanguageStats(
        game_version_id=game_version_id,
        iso_code=language_code,  # You might want to map this to ISO codes
        blocks=language_data.get('blocks'),
        words=language_data.get('words'),
        menus=language_data.get('menus'),
        options=language_data.get('options')
    )
    session.add(version_stats)

    # Process character stats if available
    characters = language_data.get('characters', {})
    for char_id, char_data in characters.items():
        char_stats = VersionCharacterStats(
            game_version_id=game_version_id,
            iso_code=language_code,
            character_id=char_id,
            display_name=char_data.get('display_name', char_id),
            blocks=char_data.get('blocks', 0),
            words=char_data.get('words', 0)
        )
        session.add(char_stats)


def generate_placeholder_iso_code(session):
    """Generate a new placeholder ISO code in the qaa-qtz range"""
    # Get the highest placeholder code we've used so far
    highest_placeholder = session.query(LanguageMapping.iso_code) \
        .filter(LanguageMapping.iso_code.like('q%')) \
        .order_by(LanguageMapping.iso_code.desc()) \
        .first()

    if not highest_placeholder:
        # Start with 'qaa' if no placeholders exist
        return 'qaa'

    current = highest_placeholder[0]
    # Generate next code: qaa -> qab -> qac etc.
    last_char = chr(ord(current[-1]) + 1)
    if last_char > 'z':
        middle_char = chr(ord(current[-2]) + 1)
        if middle_char > 'z':
            # We've exhausted all combinations (extremely unlikely)
            raise ValueError("No more placeholder codes available")
        last_char = 'a'
        return f"q{middle_char}{last_char}"
    return f"{current[:-1]}{last_char}"


def map_language_code(session, game_language):
    """Map game language codes to ISO codes using the language_mappings table"""
    # Convert to lowercase for consistent matching
    game_language_lower = game_language.lower()

    # Query the mapping table
    mapping = session.query(LanguageMapping).filter(
        func.lower(LanguageMapping.game_language_key) == game_language_lower
    ).first()

    if mapping:
        return mapping.iso_code

    # If no mapping found, try to find an exact match in languages table
    language = session.query(Language).filter(
        or_(
            func.lower(Language.id) == game_language_lower,
            func.lower(Language.part1) == game_language_lower,
            func.lower(Language.part2b) == game_language_lower,
            func.lower(Language.part2t) == game_language_lower
        )
    ).first()

    if language:
        # Create a mapping for future use
        new_mapping = LanguageMapping(
            game_language_key=game_language,
            iso_code=language.id
        )
        session.add(new_mapping)
        session.commit()
        return language.id

    # No existing mapping or language found, create placeholder
    placeholder_code = generate_placeholder_iso_code(session)

    # Create mapping with placeholder code
    new_mapping = LanguageMapping(
        game_language_key=game_language,
        iso_code=placeholder_code
    )
    session.add(new_mapping)

    session.commit()
    print(f"Created placeholder mapping for {game_language}: {placeholder_code}")
    return placeholder_code

@retry(wait=wait_exponential(multiplier=2, min=30, max=120))
def make_request(request_type, url, **kwargs):
    """
    Make an HTTP request with retry functionality
    """
    print(f"[make_request] URL requested: {url}")
    time.sleep(10)  # Keep the rate limiting
    response = requests.request(request_type, url, timeout=(3.05, 30), **kwargs)

    if response.status_code != requests.codes.ok:
        print(f"\n[make_request] Status != 200: {response.status_code}\n")

    if response.status_code not in [200, 400, 404]:
        raise RequestException("Status code not 200, 400 or 404, retrying")

    return response


class Game(Base):
    __tablename__ = 'games'

    id = Column(BigInteger, (Identity()), primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    initially_published_at = Column(DateTime)
    game_id = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(String(50))
    is_visible = Column(BOOLEAN, default=False)
    is_nsfw = Column(BOOLEAN, default=False)
    description = Column(String(200))
    url = Column(String(250), nullable=False)
    thumb_url = Column(String(250))
    tags = Column(String(250))
    game_engine = Column(String(50))
    error = Column(Text)
    authors = Column(Text)
    custom_tags = Column(String(250), nullable=False)
    uploads = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    is_feedless = Column(BOOLEAN, nullable=False, default=False)
    slug = Column(String(250))
    source_language_id = Column(String(3), ForeignKey('iso_639_3_languages.id'))
    source_language = relationship("Language", foreign_keys=[source_language_id])
    ratings = relationship("Rating", back_populates="game")

    def __init__(self, created_at=None, updated_at=None, initially_published_at=None, game_id=None, name=None,
                 status='In development', is_visible=False, is_nsfw=False, description=None, url=None, thumb_url=None,
                 tags=None, devlog=None, languages=None, game_engine='unknown', uploads=None, is_feedless=False,
                 slug=None, source_language_id=None):
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.initially_published_at = initially_published_at
        self.game_id = game_id
        self.name = name
        self.status = status
        self.is_visible = is_visible
        self.is_nsfw = is_nsfw
        self.description = description
        self.url = url
        self.thumb_url = thumb_url
        self.tags = tags
        self.devlog = devlog
        self.languages = languages
        self.game_engine = game_engine
        self.uploads = uploads or {}
        self.is_feedless = is_feedless
        self.slug = slug
        self.custom_tags = ''
        self.source_language_id = source_language_id

    def load_full_details(self, itch_api_key: str):
        try:
            # First get base info
            self.refresh_base_info(itch_api_key)
            time.sleep(10)  # Respect rate limits

            # Then get tags and ratings
            self.refresh_tags_and_rating()
            time.sleep(10)  # Respect rate limits

            # Finally get version info
            self.refresh_version(itch_api_key)

            # Clear any previous errors
            self.error = None

        except Exception as exception:
            print(f"\n[Load Full Details Error] {exception}\n")
            self.error = str(exception)
            raise

    def refresh_tags_and_rating(self):
        print("\n[refresh_tags_and_rating] URL: " + self.url + "\n")
        with make_request("get", self.url, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                return
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            if self.status not in ['Abandoned', 'Canceled', 'Released']:
                game_info = soup.find("div", {"class": "game_info_panel_widget"}).find_all("a", href=True)
                if game_info:
                    self.status = game_info[0].text
            devlog = soup.find("section", id="devlog")
            if devlog:
                devlog_links = devlog.find_all('a', href=True)
                if devlog_links:
                    devlog_link = devlog_links[0]['href']
                    self.devlog = devlog_link
            rating = soup.find("div", itemprop="ratingValue")
            rating_count = soup.find("span", itemprop="ratingCount")
            if rating and rating_count:
                self.rating = rating['content']
                self.rating_count = rating_count['content']
            info_table = soup.find("div", {"class": "game_info_panel_widget"}).find("table")
            for tr in info_table.findAll('tr'):
                tds = tr.findAll('td')
                if len(tds) < 2:
                    continue

                match tds[0].text:
                    case 'Languages':
                        self.languages = tds[1].text.strip()
                    case 'Tags':
                        self.tags = tds[1].text.strip()
                    case 'Author' | 'Authors':
                        self.authors = ''
                        for author in tds[1].findAll("a", href=True):
                            if self.authors != '':
                                self.authors += ',<br>'
                            self.authors += f'<a href="{author["href"]}" target="_blank">{author.text}</a>'
            nsfw = soup.find("div", {"class": "content_warning_inner"})
            if nsfw:
                self.is_nsfw = True
            else:
                self.is_nsfw = False

    def refresh_base_info(self, itch_api_key):
        url = 'https://api.itch.io/games/' + str(self.game_id)
        print("\n[refresh_base_info] URL: " + url + "\n")
        with make_request("get", url, headers={'Authorization': itch_api_key}, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                return
            game = json.loads(response.text)
            if 'game' in game:
                self.created_at = datetime.datetime.fromisoformat(
                    game['game']['published_at']
                )
                self.thumb_url = game['game']['cover_url']

    def refresh_version(self, itch_api_key, force: bool = False):
        url = f'https://api.itch.io/games/{self.game_id}/uploads'
        print(f"\n[refresh_version] URL: {url}\n")
        with make_request("get", url, headers={'Authorization': itch_api_key}, allow_redirects=True) as response:
            if response.status_code == 400 or response.status_code == 404:
                print(f"\n[refresh_version] Status 400, disabling game ID {self.id}\n")
                self.is_visible = False
                return

            seen_uploads = self.uploads or {}
            uploads_data = json.loads(response.text)

            if 'uploads' not in uploads_data:
                print("\n[refresh_version] No uploads found in response\n")
                return

            has_changes = False
            candidate_uploads = []

            is_windows = False
            is_linux = False
            is_mac = False
            is_android = False
            is_web = False

            for upload in uploads_data['uploads']:
                file_id = str(upload['id'])
                current_filename = upload['filename']
                current_display_name = upload.get('display_name')
                current_md5 = upload.get('md5_hash')
                current_updated_at = upload['updated_at']
                current_build_id = upload.get('build_id')
                current_build = upload.get('build', {})
                current_user_version = current_build.get('user_version')
                current_build_updated_at = current_build.get('updated_at')

                # Update platform flags
                if 'traits' in upload:
                    if 'p_windows' in upload['traits']:
                        is_windows = True
                    if 'p_linux' in upload['traits']:
                        is_linux = True
                    if 'p_osx' in upload['traits']:
                        is_mac = True
                    if 'p_android' in upload['traits']:
                        is_android = True
                if upload['type'] == 'html':
                    is_web = True

                # Check if the upload is new or changed
                is_new_or_changed = (
                        file_id not in seen_uploads or
                        seen_uploads[file_id].get('md5_hash') != current_md5 or
                        seen_uploads[file_id].get('updated_at') != current_updated_at or
                        seen_uploads[file_id].get('build_id') != current_build_id or
                        seen_uploads[file_id].get('build_updated_at') != current_build_updated_at
                )

                if is_new_or_changed:
                    has_changes = True
                    seen_uploads[file_id] = {
                        'display_name': current_display_name,
                        'md5_hash': current_md5,
                        'updated_at': current_updated_at,
                        'build_id': current_build_id,
                        'build_updated_at': current_build_updated_at,
                        'user_version': current_user_version,
                        'filename': current_filename
                    }
                    candidate_uploads.append(upload)

            self.uploads = seen_uploads

            if not has_changes and not force:
                return

            candidate_uploads.sort(key=lambda u: (
                'p_linux' in u.get('traits', []),
                'p_windows' in u.get('traits', []),
                u['filename'].lower().endswith('.zip'),
                datetime.datetime.fromisoformat(u['updated_at'].replace('Z', '+00:00')),
                datetime.datetime.fromisoformat(
                    u.get('build', {}).get('updated_at', '1970-01-01T00:00:00Z').replace('Z', '+00:00')
                ),
            ), reverse=True)
            upload_to_process = candidate_uploads[0] if candidate_uploads else None

            if upload_to_process:
                new_version = self.extract_version(upload_to_process)
                upload_timestamp = datetime.datetime.fromisoformat(
                    upload_to_process['updated_at'].replace('Z', '+00:00'))

                with Session() as session:
                    existing_version = session.query(GameVersion) \
                        .filter(GameVersion.game_id == self.id) \
                        .filter(GameVersion.is_latest == True) \
                        .filter(GameVersion.version == new_version) \
                        .first()

                    if not existing_version or force:
                        # Get script stats for the selected upload
                        stats = self.get_script_stats(itch_api_key, upload_to_process)

                        # Update the game's info & devlog link
                        time.sleep(10)
                        self.refresh_tags_and_rating()

                        # Create new version
                        game_version = GameVersion(
                            game_id=self.id,
                            version=new_version,
                            devlog=self.devlog,
                            is_windows=is_windows,
                            is_linux=is_linux,
                            is_mac=is_mac,
                            is_android=is_android,
                            is_web=is_web,
                            published_at=upload_timestamp,
                            rating=self.rating,
                            rating_count=self.rating_count
                        )
                        session.add(game_version)
                        session.flush()

                        # Process statistics for each language
                        if stats and 'languages' in stats:
                            for lang_key, lang_data in stats['languages'].items():
                                if lang_key == 'default' and self.source_language_id:
                                    iso_code = self.source_language_id
                                else:
                                    iso_code = map_language_code(session, lang_key)
                                process_language_stats(session, game_version.id, iso_code, lang_data, self.id)

                        else:
                            version_stats = VersionLanguageStats(
                                game_version_id=game_version.id,
                                iso_code='eng'
                            )
                            session.add(version_stats)
                        session.commit()

    def extract_version(self, upload):
        """Extract version information from upload metadata."""

        def parse_semantic_version(version_str):
            """Parse a version string into tuple of (integers, suffix) for comparison"""
            if not version_str:
                return None

            # Remove leading 'v' or 'version'
            version_str = re.sub(r'^[vV]ersion\s*', '', version_str)
            version_str = re.sub(r'^[vV]\s*', '', version_str)

            # Match version pattern
            match = re.match(r'(\d+(?:\.\d+)*?)([a-zA-Z])?$', version_str)
            if not match:
                return None

            try:
                parts = [int(x) for x in match.group(1).split('.')]
                suffix = match.group(2) or ''
                return (parts, suffix)
            except (ValueError, AttributeError):
                return None

        def is_probable_version(version_str):
            """Check if a string looks like a probable version number"""
            if not version_str:
                return False

            parsed = parse_semantic_version(version_str)
            if not parsed:
                return False

            parts, _ = parsed

            # Reject if first number is too large or looks like a year
            if parts[0] > 2100 or (parts[0] > 100 and len(str(parts[0])) == 4):
                return False

            # Reject if any part is suspiciously large
            if any(p > 10000 for p in parts):
                return False

            return True

        # Collect version candidates with source and priority
        candidates = []

        # Check build.user_version first (highest priority)
        if upload.get('build') and upload['build'] and upload['build'].get('user_version'):
            version = upload['build']['user_version']
            if is_probable_version(version):
                candidates.append((version, 3))

        # Check display_name (high priority)
        if upload.get('display_name'):
            # Look for explicit version
            version_match = re.search(r'[vV]ersion\s*(\d+(?:\.\d+)*[a-zA-Z]?)', upload['display_name'])
            if version_match and is_probable_version(version_match.group(1)):
                candidates.append((version_match.group(1), 2))
            else:
                # Look for other version patterns
                versions = re.finditer(r'(?:[vV](?:ersion)?)?(\d+(?:\.\d+)*[a-zA-Z]?)(?=[-\s._)]|$)',
                                       upload['display_name'])
                for match in versions:
                    version = match.group(1)
                    if is_probable_version(version):
                        candidates.append((version, 2))

        # Check filename (lowest priority)
        filename = upload.get('filename', '')
        cleaned_filename = re.sub(r'\.(zip|tar\.bz2|tar\.gz)$', '', filename, flags=re.IGNORECASE)

        # Look for build numbers
        build_match = re.search(r'[bB]uild[_\s-]*(\d+)', cleaned_filename)
        if build_match and is_probable_version(build_match.group(1)):
            candidates.append((build_match.group(1), 1))

        # Look for version patterns in filename if no build number found
        if not build_match:
            versions = re.finditer(r'(?:[vV](?:ersion)?)?(\d+(?:\.\d+)*[a-zA-Z]?)(?=[-\s._)]|$)', cleaned_filename)
            for match in versions:
                version = match.group(1)
                if is_probable_version(version):
                    candidates.append((version, 0))

        if candidates:
            # Sort by priority (desc) then version string
            candidates.sort(key=lambda x: (-x[1], x[0]))
            return candidates[0][0]

        # Fallback to timestamp if no versions found
        timestamp = datetime.datetime.fromisoformat(upload['updated_at'].replace('Z', '+00:00'))
        return timestamp.strftime("%Y.%m.%d")

    def get_script_stats(self, itch_api_key, upload_info):
        """
        Extract script statistics from a game archive, including language and character stats
        """
        empty_stats = {
            'languages': {}
        }

        # Only continue if the game is made with Ren'Py or unknown
        if self.game_engine != "Ren'Py" and self.game_engine != "unknown":
            return empty_stats

        url = self.url + '/file/' + str(upload_info['id'])
        print("\n[get_script_stats] URL: " + url + "\n")

        # Download the game
        with make_request("post", url, headers={'Authorization': itch_api_key}) as response:
            if response.status_code == 400 or response.status_code == 404:
                return empty_stats

            download = json.loads(response.text)
            if 'url' not in download:
                return empty_stats

            print("\n[get_script_stats] Download response: " + download['url'] + "\n")
            download_path = 'tmp/' + upload_info['filename']
            try:
                file = make_request("get", download['url'], allow_redirects=True)
                if response.status_code == 400 or response.status_code == 404:
                    return empty_stats
                open(download_path, 'wb').write(file.content)
            except RequestException as error:
                self.error = str(error)
                if os.path.isfile(download_path):
                    os.remove(download_path)
                return empty_stats

            extract_directory = f'tmp/{upload_info["id"]}'

            # Handle different archive formats
            try:
                if download_path.endswith('.zip'):
                    try:
                        with zipfile.ZipFile(download_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_directory)
                    except (zipfile.BadZipfile, IOError, EOFError) as error:
                        base = os.path.splitext(download_path)[0]
                        os.rename(download_path, base + '.tar.bz2')
                        download_path = base + '.tar.bz2'

                if download_path.endswith('.tar.gz'):
                    with tarfile.open(download_path) as tar:
                        tar.extractall(extract_directory)
                elif download_path.endswith('.tar.bz2'):
                    with tarfile.open(download_path, "r:bz2") as tar:
                        tar.extractall(extract_directory)

            except (tarfile.ReadError, IOError, EOFError) as error:
                if os.path.isfile(download_path):
                    os.remove(download_path)
                return empty_stats

            try:
                # Process the extracted files
                directory_listing = []
                game_dir_files = []

                if os.path.isdir(extract_directory):
                    directory_listing = os.listdir(extract_directory)

                if len(directory_listing) == 1:
                    game_dir = os.path.join(extract_directory, directory_listing[0])
                    if os.path.isdir(game_dir):
                        game_dir_files = os.listdir(game_dir)
                else:
                    game_dir = extract_directory
                    game_dir_files = directory_listing

                if not game_dir_files or not os.path.isdir(os.path.join(game_dir, "game")):
                    return empty_stats

                # Copy necessary Ren'Py files
                shutil.copyfile('./renpy/wordcounter.rpy', os.path.join(game_dir, 'game', 'wordcounter.rpy'))

                if not any(os.path.isdir(os.path.join(game_dir, 'lib', d)) for d in
                           ['py2-linux-x86_64', 'py3-linux-x86_64', 'linux-x86_64']):
                    shutil.copyfile('./renpy/renpy.py', os.path.join(game_dir, 'renpy.py'))
                    shutil.copyfile('./renpy/renpy.sh', os.path.join(game_dir, 'renpy.sh'))
                    shutil.copytree('./renpy/py3-linux-x86_64', os.path.join(game_dir, 'lib', 'py3-linux-x86_64'),
                                    dirs_exist_ok=True)
                    game_dir_files = os.listdir(game_dir)

                # Execute the script
                for game_dir_file in game_dir_files:
                    if game_dir_file.endswith('.sh'):
                        subprocess.run('chmod -R +x *', cwd=game_dir, shell=True)
                        subprocess.run(f'./{quote(game_dir_file)} game test', cwd=game_dir, shell=True)

                        stats_path = os.path.join(game_dir, 'stats.json')
                        if not os.path.isfile(stats_path):
                            continue

                        with open(stats_path) as stats_file:
                            stats = json.load(stats_file)
                            if stats and 'languages' in stats:
                                self.game_engine = "Ren'Py"
                                return stats

            finally:
                # Cleanup
                if os.path.isfile(download_path):
                    os.remove(download_path)
                if os.path.isdir(extract_directory):
                    shutil.rmtree(extract_directory)

        return empty_stats


class GameVersion(Base):
    __tablename__ = 'game_versions'

    id = Column(BigInteger, (Identity()), primary_key=True)
    game_id = Column(Integer, nullable=False)
    version = Column(String(20))
    devlog = Column(String(250))
    is_windows = Column(BOOLEAN, nullable=False, default=False)
    is_linux = Column(BOOLEAN, nullable=False, default=False)
    is_mac = Column(BOOLEAN, nullable=False, default=False)
    is_android = Column(BOOLEAN, nullable=False, default=False)
    is_web = Column(BOOLEAN, nullable=False, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    published_at = Column(DateTime, nullable=False)
    rating = Column(Float)
    rating_count = Column(Integer)
    is_latest = Column(BOOLEAN, nullable=False, default=False)
    language_stats = relationship("VersionLanguageStats", back_populates="game_version")
    character_stats = relationship("VersionCharacterStats", back_populates="game_version")

    def __init__(self, game_id, version, devlog, is_windows, is_linux, is_mac, is_android,
                 is_web, published_at, rating, rating_count, is_latest=False):
        self.game_id = game_id
        self.version = version
        self.devlog = devlog
        self.is_windows = is_windows
        self.is_linux = is_linux
        self.is_mac = is_mac
        self.is_android = is_android
        self.is_web = is_web
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        self.published_at = published_at
        self.rating = rating
        self.rating_count = rating_count
        self.is_latest = is_latest

class User(Base):
    __tablename__ = 'discord_users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100), nullable=False)
    processed_at = Column(DateTime, nullable=False)

    def __init__(self, discord_id, processed_at):
        self.discord_id = discord_id
        self.processed_at = processed_at


class Rater(Base):
    __tablename__ = 'raters'

    id = Column(BigInteger, (Identity()), primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(Text(), nullable=False)
    username = Column(Text())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    ratings = relationship("Rating", back_populates="rater")

    def __init__(self, user_id, name, username=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.name = name
        self.username = username
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(BigInteger, (Identity()), primary_key=True)
    event_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    published_at = Column(DateTime, nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'))
    rater_id = Column(Integer, ForeignKey('raters.id'))
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    is_visible = Column(BOOLEAN, default=False)
    is_reviewed = Column(BOOLEAN, nullable=False, default=False)
    game = relationship("Game", back_populates="ratings")
    rater = relationship("Rater", back_populates="ratings")

    def __init__(self, event_id, created_at, updated_at, published_at, game_id, rater_id, rating, review, is_visible=True):
        self.event_id = event_id
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.published_at = published_at
        self.game_id = game_id
        self.rater_id = rater_id
        self.rating = rating
        self.review = review
        self.is_visible = is_visible
        self.is_reviewed = (review != '')

    @staticmethod
    @retry(wait=wait_exponential(multiplier=2, min=30, max=120))
    def get_request_session():
        global request_session

        # Try to load existing session with cookies
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'rb') as f:
                cookies = pickle.load(f)
                request_session = requests.Session()
                request_session.cookies.update(cookies)

                # Verify the session is still valid with a test request
                try:
                    test_response = request_session.get('https://itch.io/dashboard', timeout=5)
                    if test_response.status_code == 200 and 'login' not in test_response.url:
                        return request_session
                except:
                    pass

        # If no valid session exists, create a new one
        if request_session is None:
            print("\n[get_request_session] Attempting Login\n")

            ITCH_USER = os.environ['ITCH_USER']
            ITCH_PASSWORD = os.environ['ITCH_PASSWORD']

            request_session = requests.Session()

            # Get CSRF token
            url = "https://itch.io/login"
            time.sleep(10)
            login = request_session.get(url, timeout=5)
            if login.status_code != 200:
                raise RequestException("Status code not 200, retrying")

            soup = BeautifulSoup(login.text, "html.parser")
            csrf_token = soup.find("input", {"name": "csrf_token"})["value"]

            # Login
            time.sleep(10)
            response = request_session.post(
                url,
                data={
                    "username": ITCH_USER,
                    "password": ITCH_PASSWORD,
                    "csrf_token": csrf_token
                },
                timeout=5
            )

            if response.status_code != 200:
                raise RequestException("Status code not 200, retrying")

            # Save cookies for future use
            with open(COOKIES_FILE, 'wb') as f:
                pickle.dump(request_session.cookies, f)

        return request_session


class Language(Base):
    __tablename__ = 'iso_639_3_languages'

    id = Column(String(3), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    part2b = Column(String(3), nullable=True)
    part2t = Column(String(3), nullable=True)
    part1 = Column(String(2), nullable=True)
    scope = Column(String(1), nullable=False)  # I(ndividual), M(acrolanguage), S(pecial)
    type = Column(String(1), nullable=False)   # A(ncient), C(onstructed), E(xtinct), H(istorical), L(iving), S(pecial)
    ref_name = Column(String(150), nullable=False)
    comment = Column(String(150), nullable=True)
    flag_code = Column(String(2), nullable=False)

    # Relationships
    language_mappings = relationship("LanguageMapping", back_populates="language")
    version_language_stats = relationship("VersionLanguageStats", back_populates="language")
    version_character_stats = relationship("VersionCharacterStats", back_populates="language")

    def __init__(self, id, ref_name, flag_code, scope='I', type='L', part2b=None, part2t=None,
                 part1=None, comment=None, created_at=None, updated_at=None):
        self.id = id
        self.ref_name = ref_name
        self.flag_code = flag_code
        self.scope = scope
        self.type = type
        self.part2b = part2b
        self.part2t = part2t
        self.part1 = part1
        self.comment = comment
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()


class LanguageMapping(Base):
    __tablename__ = 'language_mappings'

    id = Column(BigInteger, Identity(), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    game_language_key = Column(String(50), nullable=False)
    iso_code = Column(String(3), ForeignKey('iso_639_3_languages.id'), nullable=False)

    # Relationship
    language = relationship("Language", back_populates="language_mappings")

    def __init__(self, game_language_key, iso_code, created_at=None, updated_at=None):
        self.game_language_key = game_language_key
        self.iso_code = iso_code
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()


class VersionLanguageStats(Base):
    __tablename__ = 'version_language_stats'

    id = Column(BigInteger, Identity(), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    game_version_id = Column(Integer, ForeignKey('game_versions.id', ondelete='CASCADE'), nullable=False)
    iso_code = Column(String(3), ForeignKey('iso_639_3_languages.id'), nullable=False)
    blocks = Column(Integer, nullable=True)
    words = Column(Integer, nullable=True)
    menus = Column(Integer, nullable=True)
    options = Column(Integer, nullable=True)

    # Relationships
    game_version = relationship("GameVersion", back_populates="language_stats")
    language = relationship("Language", back_populates="version_language_stats")

    def __init__(self, game_version_id, iso_code, blocks=None, words=None, menus=None, options=None,
                 created_at=None, updated_at=None):
        self.game_version_id = game_version_id
        self.iso_code = iso_code
        self.blocks = blocks
        self.words = words
        self.menus = menus
        self.options = options
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()


class VersionCharacterStats(Base):
    __tablename__ = 'version_character_stats'

    id = Column(BigInteger, Identity(), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    game_version_id = Column(Integer, ForeignKey('game_versions.id', ondelete='CASCADE'), nullable=False)
    iso_code = Column(String(3), ForeignKey('iso_639_3_languages.id'), nullable=False)
    character_id = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    blocks = Column(Integer, nullable=False, default=0)
    words = Column(Integer, nullable=False, default=0)

    # Relationships
    game_version = relationship("GameVersion", back_populates="character_stats")
    language = relationship("Language", back_populates="version_character_stats")

    def __init__(self, game_version_id, iso_code, character_id, display_name, blocks=0, words=0,
                 created_at=None, updated_at=None):
        self.game_version_id = game_version_id
        self.iso_code = iso_code
        self.character_id = character_id
        self.display_name = display_name
        self.blocks = blocks
        self.words = words
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
