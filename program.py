#!/usr/bin/env python3
"""
AHL Game Data CLI - Load and manage hockey game data.

/// script
dependencies = [
    "httpx>=0.28.1",
    "pydantic>=2.12.5",
    "pydantic-sqlite>=0.5.1",
    "rich>=14.3.3",
    "click>=8.0.0",
]
///
"""

from datetime import date, datetime
import httpx
import json
import sqlite3
import time
from functools import wraps
from pydantic import BaseModel, Field
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ============================================================================
# Caching & Retry Optimization
# ============================================================================

# Global cache for player details (session-wide)
_player_details_cache: dict[int, dict] = {}

# Track which players exist in DB (set, much faster than repeated SELECTs)
_existing_players: set[int] = set()
_existing_players_loaded = False

def _load_existing_players(conn: sqlite3.Connection):
    """Load all existing player IDs into memory for fast lookups."""
    global _existing_players, _existing_players_loaded
    if _existing_players_loaded:
        return
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM player')
        _existing_players = {row[0] for row in cursor.fetchall()}
        _existing_players_loaded = True
    except Exception:
        _existing_players_loaded = True


def retry_with_backoff(max_retries: int = 3, base_delay: float = 0.5):
    """Decorator to retry failed network requests with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                    continue
            raise last_exception if last_exception else Exception("Unknown error")
        return wrapper
    return decorator

# ============================================================================
# Pydantic Models
# ============================================================================

class Person(BaseModel):
    person_id: int
    first_name: str
    last_name: str
    birth: date


class Team(BaseModel):
    team_id: int
    team_code: str
    active: bool
    name: str
    city: str
    nickname: str


class Venue(BaseModel):
    venue_id: int
    name: str


class Season(BaseModel):
    season_id: int
    season_name: str
    shortname: str
    career: bool
    playoff: bool
    start_date: date
    end_date: date


class GameData(BaseModel):
    game_id: int
    season_id: int
    away_team_id: int
    away_team_score: int
    home_team_id: int
    home_team_score: int
    game_status: str
    game_date: date
    game_attendance: int
    home_team_shots: int
    away_team_shots: int
    game_number: int
    venue_id: int


class GameOfficial(BaseModel):
    game_id: int
    person_id: int
    official_type_id: int


class Official(BaseModel):
    person_id: int
    jersey_number: int


class Player(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: str
    height: str
    weight: str
    shoots: str
    birth: date
    birth_place: str
    draft_team: str
    draft_round: int
    draft_pick: int


class GameRoster(BaseModel):
    game_id: int
    player_id: int
    starter: bool
    team_id: int


class PenaltyClass(BaseModel):
    penalty_class_id: int
    penalty_class_description: str


class Penalty(BaseModel):
    penalty_id: int
    penalty_class_id: int
    penalty_description: str


class GamePenalties(BaseModel):
    game_id: int
    home: bool
    period_id: int
    powerplay: bool = Field(validation_alias="pp")
    bench: bool
    penalty_shot: bool
    minutes: int
    penalty: int
    time_of_penalty_seconds: int = Field(validation_alias="s")
    player_penalized: int = Field(validation_alias="player_penalized_info")
    player_server: int = Field(validation_alias="player_served_info")


# ============================================================================
# Database Functions
# ============================================================================

def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect('my_database.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> sqlite3.Connection:
    """Initialize database connection and create tables if needed."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables for each model
    tables = {
        'person': '''
            CREATE TABLE IF NOT EXISTS person (
                person_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                birth DATE
            )
        ''',
        'team': '''
            CREATE TABLE IF NOT EXISTS team (
                team_id INTEGER PRIMARY KEY,
                team_code TEXT,
                active BOOLEAN,
                name TEXT,
                city TEXT,
                nickname TEXT
            )
        ''',
        'venue': '''
            CREATE TABLE IF NOT EXISTS venue (
                venue_id INTEGER PRIMARY KEY,
                name TEXT
            )
        ''',
        'season': '''
            CREATE TABLE IF NOT EXISTS season (
                season_id INTEGER PRIMARY KEY,
                season_name TEXT,
                shortname TEXT,
                career BOOLEAN,
                playoff BOOLEAN,
                start_date DATE,
                end_date DATE
            )
        ''',
        'gamedata': '''
            CREATE TABLE IF NOT EXISTS gamedata (
                game_id INTEGER PRIMARY KEY,
                season_id INTEGER,
                away_team_id INTEGER,
                away_team_score INTEGER,
                home_team_id INTEGER,
                home_team_score INTEGER,
                game_status TEXT,
                game_date DATE,
                game_attendance INTEGER,
                home_team_shots INTEGER,
                away_team_shots INTEGER,
                game_number INTEGER,
                venue_id INTEGER
            )
        ''',
        'gameofficial': '''
            CREATE TABLE IF NOT EXISTS gameofficial (
                game_id INTEGER,
                person_id INTEGER,
                official_type_id INTEGER,
                PRIMARY KEY (game_id, person_id)
            )
        ''',
        'official': '''
            CREATE TABLE IF NOT EXISTS official (
                person_id INTEGER PRIMARY KEY,
                jersey_number INTEGER
            )
        ''',
        'player': '''
            CREATE TABLE IF NOT EXISTS player (
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                height TEXT,
                weight TEXT,
                shoots TEXT,
                birth DATE,
                birth_place TEXT,
                draft_team TEXT,
                draft_round INTEGER,
                draft_pick INTEGER
            )
        ''',
        'gameroster': '''
            CREATE TABLE IF NOT EXISTS gameroster (
                game_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                starter BOOLEAN,
                PRIMARY KEY (game_id, player_id, team_id)
            )
        ''',
        'penaltyclass': '''
            CREATE TABLE IF NOT EXISTS penaltyclass (
                penalty_class_id INTEGER PRIMARY KEY,
                penalty_class_description TEXT
            )
        ''',
        'penalty': '''
            CREATE TABLE IF NOT EXISTS penalty (
                penalty_id INTEGER PRIMARY KEY,
                penalty_class_id INTEGER,
                penalty_description TEXT
            )
        ''',
        'gamepenalties': '''
            CREATE TABLE IF NOT EXISTS gamepenalties (
                game_id INTEGER,
                home BOOLEAN,
                period_id INTEGER,
                powerplay BOOLEAN,
                bench BOOLEAN,
                penalty_shot BOOLEAN,
                minutes INTEGER,
                penalty INTEGER,
                time_of_penalty_seconds INTEGER,
                player_penalized INTEGER,
                player_server INTEGER,
                PRIMARY KEY (game_id, home, period_id, player_penalized),
                FOREIGN KEY (penalty) REFERENCES penalty(penalty_id)
            )
        ''',
    }

    for table_sql in tables.values():
        cursor.execute(table_sql)

    conn.commit()
    return conn


def insert_model(conn: sqlite3.Connection, model: BaseModel, table_name: str, replace: bool = False) -> bool:
    """Insert a pydantic model into the database."""
    try:
        cursor = conn.cursor()
        data = model.model_dump()

        # Convert date objects to ISO format strings for SQLite
        for key, value in data.items():
            if isinstance(value, date) and not isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, datetime):
                data[key] = value.isoformat()

        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        command = 'INSERT OR REPLACE' if replace else 'INSERT OR IGNORE'
        sql = f'{command} INTO {table_name} ({columns}) VALUES ({placeholders})'
        cursor.execute(sql, tuple(data.values()))
        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error inserting into {table_name}: {e}[/red]")
        return False


# ============================================================================
# API Functions
# ============================================================================

def get_season_ids() -> list[int]:
    """Fetch season IDs from the API."""
    url = 'https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&view=seasons&key=ccb91f29d6744675&client_code=ahl'
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            return []

        seasons = data.get('SiteKit', {}).get('Seasons', [])
        if not seasons:
            return []

        # API returns season_id as string, convert to int
        season_ids = [int(season.get('season_id')) for season in seasons if season.get('season_id')]
        return sorted(season_ids)
    except httpx.TimeoutException:
        console.print("[red]✗ Timeout: API request took too long[/red]")
        return []
    except httpx.HTTPStatusError as e:
        console.print(f"[red]✗ HTTP Error {e.response.status_code}[/red]")
        return []
    except httpx.HTTPError as e:
        console.print(f"[red]✗ HTTP Error: {e}[/red]")
        return []
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ JSON Decode Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]✗ Error fetching season IDs: {type(e).__name__}: {e}[/red]")
        return []


def get_seasons_with_names() -> dict[int, str]:
    """Fetch season IDs with their names from the API."""
    url = 'https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&view=seasons&key=ccb91f29d6744675&client_code=ahl'
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        seasons = data.get('SiteKit', {}).get('Seasons', [])
        if not seasons:
            return {}

        # Return dict of season_id -> season_name
        return {
            int(season.get('season_id')): season.get('season_name', 'Unknown')
            for season in seasons
            if season.get('season_id')
        }
    except Exception:
        return {}


def get_season_data(season_id: int) -> dict:
    """Fetch season data from API including dates."""
    url = 'https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&view=seasons&key=ccb91f29d6744675&client_code=ahl'
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        seasons = data.get('SiteKit', {}).get('Seasons', [])
        for season in seasons:
            if int(season.get('season_id', 0)) == season_id:
                return season
        return {}
    except Exception:
        return {}


def get_season_game_ids(season_id: int) -> list[int]:
    """Fetch all game IDs for a given season from the API."""
    game_ids = []
    url = f'https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&view=schedule&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl'
    try:
        data = httpx.get(url).json()
        schedule = data.get('SiteKit', {}).get('Schedule', [])
        game_ids = [item.get('id') for item in schedule if item.get('id')]
    except Exception as e:
        console.print(f"[red]Error fetching game IDs for season {season_id}: {e}[/red]")
    return game_ids


def get_games_by_date(target_date: date) -> list[int]:
    """Fetch game IDs for a specific date from all seasons efficiently."""
    game_ids = []

    # Get all seasons with their year ranges upfront (single API call)
    seasons_with_years = {}
    try:
        url = 'https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&view=seasons&key=ccb91f29d6744675&client_code=ahl'
        response = httpx.get(url, timeout=10)
        data = response.json()
        seasons = data.get('SiteKit', {}).get('Seasons', [])
        for season in seasons:
            season_id = int(season.get('season_id', 0))
            season_name = season.get('season_name', '')
            if season_name:
                # Extract years from season name (e.g., "2025-26" or just "2025")
                import re
                year_range_match = re.search(r'(\d{4})-(\d{2})', season_name)
                if year_range_match:
                    start_year = int(year_range_match.group(1))
                    end_year_suffix = int(year_range_match.group(2))
                    # Handle "2025-26" format: 26 -> 2026 (2000 + 26)
                    century = (start_year // 100) * 100
                    end_year = century + end_year_suffix
                    # Store both years to handle mid-season date transitions
                    seasons_with_years[season_id] = (start_year, end_year)
                else:
                    # Single year season (like all-star)
                    year_match = re.search(r'^(\d{4})', season_name)
                    if year_match:
                        year = int(year_match.group(1))
                        seasons_with_years[season_id] = (year, year)
    except Exception:
        return []

    # Now fetch schedules and filter by date
    for season_id, (start_year, end_year) in seasons_with_years.items():
        url = f'https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&view=schedule&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl'
        try:
            data = httpx.get(url, timeout=10).json()
            schedule = data.get('SiteKit', {}).get('Schedule', [])

            for item in schedule:
                game_id = item.get('id')
                if game_id:
                    # Parse game date from schedule - format is "Oct. 10" or similar
                    game_date_str = item.get('date')
                    if game_date_str:
                        try:
                            # Try with end_year first (for March-April games), then start_year
                            parsed_date = None
                            try:
                                parsed_date = datetime.strptime(f"{game_date_str} {end_year}", '%b. %d %Y').date()
                            except ValueError:
                                parsed_date = datetime.strptime(f"{game_date_str} {start_year}", '%b. %d %Y').date()

                            if parsed_date == target_date:
                                game_ids.append(game_id)
                        except (ValueError, AttributeError):
                            continue
        except Exception:
            continue

    return game_ids


def get_game_data(game_id: int) -> dict:
    url: str = f'https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=gamesummary&game_id={game_id}&key=ccb91f29d6744675&client_code=ahl'
    game_data = httpx.get(url).json()
    return game_data


def _get_game_meta_data(game_id: int, item: str):
    json_data = get_game_data(game_id)
    gc = json_data.get("GC")
    if gc is None:
        return None
    gamesummary = gc.get("Gamesummary")
    if gamesummary is None:
        return None
    meta_data = gamesummary.get("meta")
    if meta_data is None:
        return None
    meta_data_item = meta_data.get(item)
    return meta_data_item


def _get_game_game_summary_data(game_id: int, item: str):
    json_data = get_game_data(game_id)
    gc = json_data.get("GC")
    if gc is None:
        return None
    gamesummary = gc.get("Gamesummary")
    if gamesummary is None:
        return None
    data_item = gamesummary.get(item)
    return data_item


def is_game_played(game_id: int) -> bool:
    """Check if a game has been played (status_title == 'End')."""
    status_title = _get_game_game_summary_data(game_id, "status_title")
    return status_title == "End"


@retry_with_backoff(max_retries=3, base_delay=0.5)
def _fetch_player_details_from_api(player_id: int, season_id: int) -> dict:
    """Internal function to fetch player details from API (no caching)."""
    url = f'https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=player&player_id={player_id}&season_id={season_id}&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1&statsType=skaters'
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    text = response.text.strip()

    # Handle JSONP response - strip outer parentheses if present
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]

    data = json.loads(text)
    return data.get('info', {}) if isinstance(data, dict) else {}


def get_player_details(player_id: int, season_id: int = 90) -> dict:
    """Fetch detailed player information from statviewfeed API with caching."""
    # Check in-memory cache first
    if player_id in _player_details_cache:
        return _player_details_cache[player_id]

    # Try to fetch from API with retry
    try:
        details = _fetch_player_details_from_api(player_id, season_id)
        _player_details_cache[player_id] = details
        return details
    except Exception:
        _player_details_cache[player_id] = {}
        return {}


def get_penalties(game_id: int) -> list[GamePenalties]:
    penalties: list[GamePenalties] = []

    penalty_data_list = _get_game_game_summary_data(game_id, 'penalties')
    if not penalty_data_list:
        return penalties

    for penalty_data in penalty_data_list:
        try:
            # Extract and convert all fields properly
            home_val = penalty_data.get('home', 0)
            period_val = penalty_data.get('period_id', 0)
            pp_val = penalty_data.get('pp', 0)
            bench_val = penalty_data.get('bench', 0)
            penalty_shot_val = penalty_data.get('penalty_shot', 0)
            minutes_val = penalty_data.get('minutes', 0)
            s_val = penalty_data.get('s', 0)

            home: bool = bool(int(home_val) if isinstance(home_val, (str, int)) else 0)
            period_id: int = int(period_val) if isinstance(period_val, (str, int)) else 0
            pp: bool = bool(int(pp_val) if isinstance(pp_val, (str, int)) else 0)
            bench: bool = bool(int(bench_val) if isinstance(bench_val, (str, int)) else 0)
            penalty_shot: bool = bool(int(penalty_shot_val) if isinstance(penalty_shot_val, (str, int)) else 0)
            minutes: int = int(minutes_val) if isinstance(minutes_val, (str, int)) else 0
            s: int = int(s_val) if isinstance(s_val, (str, int)) else 0

            # Create consistent penalty_id from penalty description
            penalty_description = penalty_data.get('lang_penalty_description', '')
            penalty: int = 0
            if isinstance(penalty_description, str):
                penalty = abs(hash(penalty_description)) % 10000

            # Safely extract player IDs
            player_penalized_info = penalty_data.get('player_penalized_info')
            player_served_info = penalty_data.get('player_served_info')

            player_penalized_id: int = 0
            player_served_id: int = 0

            if player_penalized_info and isinstance(player_penalized_info, dict):
                penalized_val = player_penalized_info.get('player_id', 0)
                player_penalized_id = int(penalized_val) if isinstance(penalized_val, (str, int)) else 0
            elif isinstance(player_penalized_info, int):
                player_penalized_id = int(player_penalized_info)

            if player_served_info and isinstance(player_served_info, dict):
                served_val = player_served_info.get('player_id', 0)
                player_served_id = int(served_val) if isinstance(served_val, (str, int)) else 0
            elif isinstance(player_served_info, int):
                player_served_id = int(player_served_info)

            penalties.append(GamePenalties(
                game_id=game_id,
                home=home,
                period_id=period_id,
                powerplay=pp,
                bench=bench,
                penalty_shot=penalty_shot,
                minutes=minutes,
                penalty=penalty,
                time_of_penalty_seconds=s,
                player_penalized=player_penalized_id,
                player_server=player_served_id
            ))
        except Exception:
            # Skip malformed penalty records
            continue

    return penalties


def get_game_team_instance(game_id: int, team_type: str) -> Team:
    """Extract team data and return Team instance."""
    keys_to_use = ["team_id", "team_code", "active", "name", "city", "nickname"]
    team_data = _get_game_game_summary_data(game_id, team_type)
    filtered_team_data = {k: team_data[k] for k in keys_to_use if k in team_data}
    return Team(**filtered_team_data)


def get_game_instance(game_id: int) -> GameData:
    """Extract game data and return flattened GameData instance."""
    away_team = get_game_team_instance(game_id, "visitor")
    home_team = get_game_team_instance(game_id, "home")

    # Get shots data with safe handling
    total_shots = _get_game_game_summary_data(game_id, "totalShots")
    home_shots_val = total_shots.get("home", 0) if total_shots else 0
    away_shots_val = total_shots.get("visitor", 0) if total_shots else 0
    home_shots: int = int(home_shots_val or 0)
    away_shots: int = int(away_shots_val or 0)

    # Parse date_played string to date object
    date_played_str = _get_game_meta_data(game_id, "date_played")
    game_date: date
    if isinstance(date_played_str, str):
        try:
            game_date = datetime.strptime(date_played_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            game_date = datetime.now().date()
    else:
        game_date = datetime.now().date()

    # Extract and convert all fields with explicit types
    season_id_val = _get_game_meta_data(game_id, "season_id")
    season_id: int = int(season_id_val or 0) if isinstance(season_id_val, (str, int)) else 0

    away_score_val = _get_game_meta_data(game_id, "visiting_goal_count")
    away_score: int = int(away_score_val or 0) if isinstance(away_score_val, (str, int)) else 0

    home_score_val = _get_game_meta_data(game_id, "home_goal_count")
    home_score: int = int(home_score_val or 0) if isinstance(home_score_val, (str, int)) else 0

    status_val = _get_game_game_summary_data(game_id, "status_value")
    game_status: str = str(status_val or "unknown")

    attendance_val = _get_game_meta_data(game_id, "attendance")
    attendance: int = int(attendance_val or 0) if isinstance(attendance_val, (str, int)) else 0

    game_number_val = _get_game_meta_data(game_id, "game_number")
    game_number: int = int(game_number_val or 0) if isinstance(game_number_val, (str, int)) else 0

    venue_id_val = _get_game_meta_data(game_id, "location")
    venue_id: int = int(venue_id_val or 0) if isinstance(venue_id_val, (str, int)) else 0

    return GameData(
        game_id=game_id,
        season_id=season_id,
        away_team_id=away_team.team_id,
        away_team_score=away_score,
        home_team_id=home_team.team_id,
        home_team_score=home_score,
        game_status=game_status,
        game_date=game_date,
        game_attendance=attendance,
        home_team_shots=home_shots,
        away_team_shots=away_shots,
        game_number=game_number,
        venue_id=venue_id
    )


# ============================================================================
# Data Saving Functions
# ============================================================================

def save_venue(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save venue data from game."""
    try:
        venue_id = int(_get_game_meta_data(game_id, 'location') or 0)
        if venue_id == 0:
            return True

        venue_name = _get_game_game_summary_data(game_id, 'venue')
        if not venue_name or not isinstance(venue_name, str):
            venue_name = f"Venue {venue_id}"

        # Create and insert venue record
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO venue (venue_id, name) VALUES (?, ?)',
            (venue_id, venue_name)
        )
        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error saving venue: {e}[/red]")
        return False


def save_season(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save season data from game."""
    try:
        season_id = int(_get_game_meta_data(game_id, 'season_id') or 0)
        if season_id == 0:
            return True

        cursor = conn.cursor()
        cursor.execute('SELECT season_id FROM season WHERE season_id = ?', (season_id,))
        if cursor.fetchone():
            return True

        # Fetch full season data from API
        season_data = get_season_data(season_id)
        season_name = season_data.get('season_name', f"Season {season_id}")
        shortname = season_data.get('shortname', f"S{season_id}")
        career = season_data.get('career', '0') == '1'
        playoff = season_data.get('playoff', '0') == '1'
        start_date = season_data.get('start_date')
        end_date = season_data.get('end_date')

        cursor.execute(
            'INSERT OR IGNORE INTO season (season_id, season_name, shortname, career, playoff, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (season_id, season_name, shortname, career, playoff, start_date, end_date)
        )
        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error saving season: {e}[/red]")
        return False


def save_players_and_rosters(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save player and game roster data from game."""
    try:
        _load_existing_players(conn)
        cursor = conn.cursor()
        season_id = int(_get_game_meta_data(game_id, 'season_id') or 90)

        # Get home and away team IDs from gamedata
        cursor.execute('SELECT home_team_id, away_team_id FROM gamedata WHERE game_id = ?', (game_id,))
        team_result = cursor.fetchone()
        if not team_result:
            return False
        home_team_id, away_team_id = team_result

        # Get home and away team lineups
        home_lineup = _get_game_game_summary_data(game_id, 'home_team_lineup')
        away_lineup = _get_game_game_summary_data(game_id, 'visitor_team_lineup')
        goalies = _get_game_game_summary_data(game_id, 'goalies')

        # Batch lists for efficient bulk insertion
        players_to_insert = []
        rosters_to_insert = []

        def process_player(player_id: int, first_name: str, last_name: str, position: str, starter: bool, team_id: int):
            """Process a player: fetch details if new, batch for insertion."""
            nonlocal players_to_insert, rosters_to_insert

            if player_id <= 0:
                return

            # Only fetch API details if player is new to database
            if player_id not in _existing_players:
                player_details = get_player_details(player_id, season_id)
                height = player_details.get('height', '')
                weight = player_details.get('weight', '')
                shoots = player_details.get('shoots', '')
                birth_date = player_details.get('birthDate')
                birth_place = player_details.get('birthPlace', '')

                # Extract draft info if available
                drafts = player_details.get('drafts', [])
                draft_team = ''
                draft_round = 0
                draft_pick = 0
                if drafts and isinstance(drafts, list) and len(drafts) > 0:
                    draft_info = drafts[0]
                    draft_team = draft_info.get('draftTeam', '')
                    draft_round = int(draft_info.get('round', 0))
                    draft_pick = int(draft_info.get('pick', 0))

                players_to_insert.append((
                    player_id, first_name, last_name, position,
                    height, weight, shoots, birth_date, birth_place,
                    draft_team, draft_round, draft_pick
                ))
                _existing_players.add(player_id)

            # Always add roster entry with team_id
            rosters_to_insert.append((game_id, player_id, team_id, starter))

        # Process home team roster
        if home_lineup and isinstance(home_lineup, dict):
            for position_group, players_list in home_lineup.items():
                if isinstance(players_list, list):
                    for player in players_list:
                        if isinstance(player, dict):
                            process_player(
                                int(player.get('player_id', 0)),
                                player.get('first_name', ''),
                                player.get('last_name', ''),
                                player.get('position_str', ''),
                                int(player.get('start', 0)) == 1,
                                home_team_id
                            )

        # Process away team roster
        if away_lineup and isinstance(away_lineup, dict):
            for position_group, players_list in away_lineup.items():
                if isinstance(players_list, list):
                    for player in players_list:
                        if isinstance(player, dict):
                            process_player(
                                int(player.get('player_id', 0)),
                                player.get('first_name', ''),
                                player.get('last_name', ''),
                                player.get('position_str', ''),
                                int(player.get('start', 0)) == 1,
                                away_team_id
                            )

        # Process goalies separately
        if goalies and isinstance(goalies, dict):
            for team_type, goalie_list in goalies.items():
                if isinstance(goalie_list, list):
                    for goalie in goalie_list:
                        if isinstance(goalie, dict):
                            # Determine team_id based on team_type (home or visitor)
                            goalie_team_id = home_team_id if team_type == 'home' else away_team_id
                            process_player(
                                int(goalie.get('player_id', 0)),
                                goalie.get('first_name', ''),
                                goalie.get('last_name', ''),
                                'G',
                                True,
                                goalie_team_id
                            )

        # Batch insert players (much faster than individual inserts)
        if players_to_insert:
            cursor.executemany(
                'INSERT OR IGNORE INTO player (id, first_name, last_name, position, height, weight, shoots, birth, birth_place, draft_team, draft_round, draft_pick) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                players_to_insert
            )

        # Batch insert roster entries
        if rosters_to_insert:
            cursor.executemany(
                'INSERT OR IGNORE INTO gameroster (game_id, player_id, team_id, starter) VALUES (?, ?, ?, ?)',
                rosters_to_insert
            )

        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error saving players and rosters: {e}[/red]")
        return False


def save_penalty_classes(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save penalty class and penalty data from game penalties."""
    try:
        penalty_data_list = _get_game_game_summary_data(game_id, 'penalties')
        if not penalty_data_list:
            return True

        cursor = conn.cursor()
        saved_classes = set()
        saved_penalties = set()

        for penalty_data in penalty_data_list:
            if isinstance(penalty_data, dict):
                penalty_class_id = int(penalty_data.get('penalty_class_id', 0))
                penalty_class_desc = penalty_data.get('penalty_class', '')

                # Save penalty class
                if penalty_class_id > 0 and penalty_class_id not in saved_classes:
                    cursor.execute(
                        'INSERT OR IGNORE INTO penaltyclass (penalty_class_id, penalty_class_description) VALUES (?, ?)',
                        (penalty_class_id, penalty_class_desc)
                    )
                    saved_classes.add(penalty_class_id)

                # Save specific penalty type with consistent ID calculation
                penalty_description = penalty_data.get('lang_penalty_description', '')
                if penalty_description:
                    penalty_id = abs(hash(penalty_description)) % 10000
                    if penalty_id not in saved_penalties:
                        cursor.execute(
                            'INSERT OR IGNORE INTO penalty (penalty_id, penalty_class_id, penalty_description) VALUES (?, ?, ?)',
                            (penalty_id, penalty_class_id, penalty_description)
                        )
                        saved_penalties.add(penalty_id)

        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error saving penalty classes: {e}[/red]")
        return False


def save_officials(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save officials data from game."""
    try:
        officials_on_ice = _get_game_game_summary_data(game_id, 'officialsOnIce')
        if not officials_on_ice:
            return True

        cursor = conn.cursor()

        # Handle both list and dict responses
        officials_list = officials_on_ice if isinstance(officials_on_ice, list) else [officials_on_ice]

        for official in officials_list:
            if isinstance(official, dict):
                person_id = int(official.get('person_id', 0))
                if person_id > 0:
                    first_name = official.get('first_name', '')
                    last_name = official.get('last_name', '')
                    jersey_number = int(official.get('jersey_number', 0))
                    official_type_id = int(official.get('official_type_id', 0))

                    # Insert person
                    cursor.execute(
                        'INSERT OR IGNORE INTO person (person_id, first_name, last_name, birth) VALUES (?, ?, ?, ?)',
                        (person_id, first_name, last_name, None)
                    )
                    # Insert official
                    cursor.execute(
                        'INSERT OR IGNORE INTO official (person_id, jersey_number) VALUES (?, ?)',
                        (person_id, jersey_number)
                    )
                    # Insert gameofficial
                    cursor.execute(
                        'INSERT OR IGNORE INTO gameofficial (game_id, person_id, official_type_id) VALUES (?, ?, ?)',
                        (game_id, person_id, official_type_id)
                    )

        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error saving officials: {e}[/red]")
        return False


def save_game_data(conn: sqlite3.Connection, game_id: int) -> tuple[bool, str]:
    """Fetch and save a single game's data to database. Returns (success, message)."""
    try:
        game = get_game_instance(game_id)

        # Smart update: allow overwriting only if game is in the past AND status is "End"
        game_date = game.game_date
        is_past = game_date < datetime.now().date() if game_date else False
        is_ended = is_game_played(game_id)
        should_replace = is_past and is_ended

        insert_model(conn, game, 'gamedata', replace=should_replace)

        away_team = get_game_team_instance(game_id, "visitor")
        home_team = get_game_team_instance(game_id, "home")
        insert_model(conn, away_team, 'team', replace=True)
        insert_model(conn, home_team, 'team', replace=True)

        penalties = get_penalties(game_id)
        for penalty in penalties:
            insert_model(conn, penalty, 'gamepenalties', replace=True)

        # Save venue, season, officials, penalty classes, and rosters
        save_venue(conn, game_id)
        save_season(conn, game_id)
        save_officials(conn, game_id)
        save_penalty_classes(conn, game_id)
        save_players_and_rosters(conn, game_id)

        return True, f"{away_team.name} vs {home_team.name} ({game.away_team_score}-{game.home_team_score})"
    except Exception as e:
        return False, str(e)


# ============================================================================
# CLI Commands
# ============================================================================

@click.group()
def cli():
    """AHL Game Data CLI - Load and manage hockey game data."""
    pass


@cli.command()
def today():
    """Load all games played today with optimizations."""
    console.print(Panel.fit("[bold cyan]Loading Today's Games[/bold cyan]", border_style="cyan"))

    conn = init_database()
    today_date = datetime.now().date()
    console.print(f"[yellow]Date:[/yellow] {today_date}\n")

    saved_count = 0
    error_count = 0
    games_data = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Finding today's games...", total=None)
        # Efficiently fetch only today's game IDs
        game_ids = get_games_by_date(today_date)
        progress.stop()

    if not game_ids:
        console.print("[yellow]⊘ No games found for today[/yellow]")
        return

    console.print(f"[yellow]Found {len(game_ids)} games for today\n[/yellow]")

    # Pre-load existing players for faster lookups
    _load_existing_players(conn)

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Loading games...", total=len(game_ids))

        for game_id in game_ids:
            try:
                # Only load games that have been played
                if not is_game_played(game_id):
                    progress.advance(task)
                    continue

                success, message = save_game_data(conn, game_id)
                if success:
                    game = get_game_instance(game_id)
                    away_team = get_game_team_instance(game_id, "visitor")
                    home_team = get_game_team_instance(game_id, "home")
                    games_data.append({
                        "Game ID": game_id,
                        "Away": away_team.name,
                        "Home": home_team.name,
                        "Score": f"{game.away_team_score}-{game.home_team_score}",
                        "Status": game.game_status,
                    })
                    saved_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1
            finally:
                progress.advance(task)

    # Display results
    if games_data:
        table = Table(title=f"Games Loaded ({saved_count})", show_header=True, header_style="bold cyan")
        table.add_column("Game ID", style="dim")
        table.add_column("Away Team")
        table.add_column("Home Team")
        table.add_column("Score", justify="center")
        table.add_column("Status")

        for game in games_data:
            table.add_row(
                str(game["Game ID"]),
                game["Away"],
                game["Home"],
                game["Score"],
                game["Status"]
            )

        console.print(table)
        console.print(f"\n[green]✓ Loaded {saved_count} games[/green]")

    if error_count > 0:
        console.print(f"[yellow]⚠ {error_count} games skipped due to errors[/yellow]")


@cli.command()
@click.option('--season-id', type=int, required=True, help='Season ID (e.g., 90 for 2025-26)')
@click.option('--limit', type=int, default=None, help='Maximum number of games to load')
def season(season_id: int, limit: int):
    """Load all games for a specific season with checkpointing and resume capability."""
    console.print(Panel.fit(f"[bold cyan]Loading Season {season_id}[/bold cyan]", border_style="cyan"))

    conn = init_database()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching game IDs...", total=None)
        game_ids = get_season_game_ids(season_id)
        progress.stop()

    if not game_ids:
        console.print(f"[red]✗ No games found for season {season_id}[/red]")
        return

    if limit:
        game_ids = game_ids[:limit]

    # Convert game_ids to integers (API returns strings, DB stores ints)
    game_ids = [int(gid) for gid in game_ids]

    # Filter out already-loaded games (skip optimization)
    cursor = conn.cursor()
    try:
        # Use string-safe approach for potentially large IN clauses
        placeholders = ','.join('?' * len(game_ids))
        query = f'SELECT game_id FROM gamedata WHERE season_id = ? AND game_id IN ({placeholders})'
        cursor.execute(query, [season_id] + game_ids)
        results = cursor.fetchall()
        loaded_game_ids = {row[0] for row in results}
        missing_game_ids = [gid for gid in game_ids if gid not in loaded_game_ids]

        if missing_game_ids:
            console.print(f"[yellow]Found {len(game_ids)} total games[/yellow]")
            console.print(f"[cyan]Already loaded: {len(loaded_game_ids)} games[/cyan]")
            console.print(f"[yellow]Missing: {len(missing_game_ids)} games[/yellow]\n")
            game_ids = missing_game_ids
        else:
            console.print(f"[green]✓ All {len(game_ids)} games already loaded![/green]\n")
            return
    except Exception as e:
        console.print(f"[yellow]⚠ Could not check for loaded games: {e}[/yellow]")
        console.print(f"[yellow]Proceeding to scrape all {len(game_ids)} games[/yellow]\n")

    # Load existing players once at the start (optimization)
    _load_existing_players(conn)

    saved_count = 0
    error_count = 0
    games_data = []
    checkpoint_interval = 100  # Save progress every 100 games

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Loading games...",
            total=len(game_ids)
        )

        for idx, game_id in enumerate(game_ids):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    success, message = save_game_data(conn, game_id)

                    if success:
                        games_data.append({"ID": game_id, "Result": message})
                        saved_count += 1
                    else:
                        error_count += 1
                    break  # Success, move to next game
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(1 * (2 ** attempt))  # Exponential backoff
                    else:
                        error_count += 1
                        break

            # Checkpoint: commit every 100 games to survive interruptions
            if (idx + 1) % checkpoint_interval == 0:
                conn.commit()
                progress.console.print(f"[dim]✓ Checkpoint: {idx + 1} games processed[/dim]")

            progress.advance(task)

    # Final commit
    conn.commit()

    # Display results
    if games_data:
        table = Table(title=f"Games Loaded ({saved_count})", show_header=True, header_style="bold green")
        table.add_column("Game ID", style="dim")
        table.add_column("Result")

        for game in games_data[:20]:  # Show first 20
            table.add_row(str(game["ID"]), game["Result"])

        if len(games_data) > 20:
            table.add_row("[dim]...[/dim]", f"[dim]+{len(games_data) - 20} more[/dim]")

        console.print(table)

    console.print(f"\n[green]✓ Saved {saved_count} games[/green]")
    if error_count > 0:
        console.print(f"[yellow]⚠ {error_count} games failed[/yellow]")


@cli.command()
@click.argument('game_id', type=int)
def game(game_id: int):
    """Load a specific game by ID."""
    console.print(Panel.fit(f"[bold cyan]Loading Game {game_id}[/bold cyan]", border_style="cyan"))

    conn = init_database()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        _ = progress.add_task("Fetching game data...", total=None)
        success, message = save_game_data(conn, game_id)
        progress.stop()

    if success:
        console.print("\n[green]✓ Game saved successfully[/green]")
        console.print(f"[cyan]{message}[/cyan]")
    else:
        console.print("\n[red]✗ Failed to load game[/red]")
        console.print(f"[red]{message}[/red]")


@cli.command()
def list_seasons():
    """List all available seasons."""
    console.print(Panel.fit("[bold cyan]Available Seasons[/bold cyan]", border_style="cyan"))

    console.print("[cyan]Fetching seasons from API...[/cyan]")
    season_map = get_seasons_with_names()

    if season_map:
        table = Table(show_header=True, header_style="bold cyan", title=f"Total: {len(season_map)} seasons")
        table.add_column("Season ID", justify="center", style="cyan")
        table.add_column("Season Name", justify="left")

        for sid in sorted(season_map.keys()):
            table.add_row(str(sid), season_map[sid])

        console.print(table)
        console.print(f"\n[green]✓ Found {len(season_map)} seasons[/green]")
    else:
        console.print("[red]✗ Could not fetch seasons from API[/red]")
        console.print("[yellow]The API may be down or the endpoint has changed[/yellow]")


@cli.command()
def init():
    """Initialize the database."""
    console.print(Panel.fit("[bold cyan]Initializing Database[/bold cyan]", border_style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        _ = progress.add_task("Registering models...", total=None)
        init_database()
        progress.stop()

    console.print("[green]✓ Database initialized[/green]")
    console.print("[cyan]Models: Person, Team, Venue, Season, GameData, GameOfficial, Official, Player, GameRoster, PenaltyClass, Penalty, GamePenalties[/cyan]")
    console.print("[dim]Tables will be created automatically on first data insert[/dim]")


if __name__ == "__main__":
    cli()
