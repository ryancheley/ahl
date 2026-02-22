"""
Player data scraper for collecting player biographical information from the AHL.

Scrapes player profiles from the hockeytech statviewfeed API including:
- Name, position, height, weight
- Birth date and birthplace
- Draft information (team, year, round, pick number)
"""

import json
import sqlite3
import time
from typing import Optional, Dict, List
from dataclasses import dataclass

import requests


# API URL for player data
PLAYER_API_URL = (
    "https://lscluster.hockeytech.com/feed/index.php"
    "?feed=statviewfeed&view=player"
    "&player_id={player_id}&season_id=90&site_id=3"
    "&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1&statsType=skaters"
)


@dataclass
class PlayerInfo:
    """Container for player information."""
    player_id: int
    first_name: str
    last_name: str
    position: str
    height: str  # e.g., "6-2"
    weight: str  # e.g., "214"
    shoots: str  # "L" or "R"
    birth_date: str  # "1983-06-08"
    birth_place: str
    draft_team: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.position})"


def fetch_player_data(player_id: int) -> Optional[Dict]:
    """
    Fetch player data from the hockeytech API.

    Args:
        player_id: The player ID to fetch

    Returns:
        Parsed JSON dict if successful, None otherwise
    """
    try:
        url = PLAYER_API_URL.format(player_id=player_id)
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse JSONP response - strip outer parentheses
        text = response.text.strip()
        if text.startswith('(') and text.endswith(')'):
            text = text[1:-1]

        data = json.loads(text)

        # Empty player returns an empty list []
        if not isinstance(data, dict) or 'info' not in data:
            return None

        return data
    except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError):
        return None


def extract_player_info(player_id: int, data: Dict) -> Optional[PlayerInfo]:
    """
    Extract player information from API response.

    Args:
        player_id: The player ID
        data: Parsed API response dict

    Returns:
        PlayerInfo object if extraction successful, None otherwise
    """
    try:
        info = data.get('info', {})

        # Required fields
        first_name = info.get('firstName', '').strip()
        last_name = info.get('lastName', '').strip()
        position = info.get('position', '').strip()
        height = info.get('height', '').strip()
        weight = info.get('weight', '').strip()
        shoots = info.get('shoots', '').strip()
        birth_date = info.get('birthDate', '').strip()
        birth_place = info.get('birthPlace', '').strip()

        # All required fields must be present
        if not all([first_name, last_name, position]):
            return None

        # Extract draft information (first draft if multiple)
        draft_team = None
        draft_year = None
        draft_round = None
        draft_pick = None

        drafts = info.get('drafts', [])
        if drafts and isinstance(drafts, list) and len(drafts) > 0:
            draft = drafts[0]
            draft_team = draft.get('draft_team') or None
            if draft.get('draft_year'):
                draft_year = int(draft['draft_year'])
            if draft.get('draft_round'):
                draft_round = int(draft['draft_round'])
            if draft.get('draft_rank'):
                draft_pick = int(draft['draft_rank'])

        return PlayerInfo(
            player_id=player_id,
            first_name=first_name,
            last_name=last_name,
            position=position,
            height=height,
            weight=weight,
            shoots=shoots,
            birth_date=birth_date,
            birth_place=birth_place,
            draft_team=draft_team,
            draft_year=draft_year,
            draft_round=draft_round,
            draft_pick=draft_pick,
        )
    except (KeyError, ValueError, AttributeError):
        return None


def player_exists_in_database(player_id: int, db_path: str = "games_new.db") -> bool:
    """
    Check if a player already exists in the database.

    Args:
        player_id: The player ID to check
        db_path: Path to the database file

    Returns:
        True if player exists, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM players WHERE player_id = ? LIMIT 1", (player_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except sqlite3.Error:
        return False


def write_player_to_database(player_info: PlayerInfo, db_path: str = "games_new.db") -> bool:
    """
    Write player information to the database.

    Args:
        player_info: PlayerInfo object to write
        db_path: Path to the database file

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                height TEXT,
                weight TEXT,
                shoots TEXT,
                birth_date TEXT,
                birth_place TEXT,
                draft_team TEXT,
                draft_year INTEGER,
                draft_round INTEGER,
                draft_pick INTEGER
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO players
            (player_id, first_name, last_name, position, height, weight,
             shoots, birth_date, birth_place, draft_team, draft_year,
             draft_round, draft_pick)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_info.player_id,
            player_info.first_name,
            player_info.last_name,
            player_info.position,
            player_info.height,
            player_info.weight,
            player_info.shoots,
            player_info.birth_date,
            player_info.birth_place,
            player_info.draft_team,
            player_info.draft_year,
            player_info.draft_round,
            player_info.draft_pick,
        ))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error:
        return False


def scrape_player(player_id: int, db_path: str = "games_new.db") -> Optional[PlayerInfo]:
    """
    Scrape a single player and write to database.

    Args:
        player_id: The player ID to scrape
        db_path: Path to the database file

    Returns:
        PlayerInfo object if successful, None otherwise
    """
    # Check if player already exists
    if player_exists_in_database(player_id, db_path):
        return None

    # Fetch and extract
    data = fetch_player_data(player_id)
    if not data:
        return None

    player_info = extract_player_info(player_id, data)
    if not player_info:
        return None

    # Write to database
    if not write_player_to_database(player_info, db_path):
        return None

    return player_info


def scrape_player_id_range(
    start_player_id: int,
    num_players: int = 50,
    db_path: str = "games_new.db",
    delay: float = 0.5
) -> List[PlayerInfo]:
    """
    Scrape a range of player IDs sequentially.

    Args:
        start_player_id: Starting player ID
        num_players: Number of players to scrape
        db_path: Path to the database file
        delay: Delay in seconds between requests

    Returns:
        List of PlayerInfo objects for successful scrapes
    """
    results = []

    for i in range(num_players):
        player_id = start_player_id + i

        print(f"[{i+1}/{num_players}] Scraping player {player_id}...", end=" ")

        # Skip players that are already in the database
        if player_exists_in_database(player_id, db_path):
            print("↻ Already in database")
            time.sleep(delay)
            continue

        try:
            data = fetch_player_data(player_id)
            if not data:
                print("⊘ No data")
                time.sleep(delay)
                continue

            player_info = extract_player_info(player_id, data)
            if not player_info:
                print("⊘ No data")
                time.sleep(delay)
                continue

            if write_player_to_database(player_info, db_path):
                results.append(player_info)
                print(f"✓ {player_info}")
            else:
                print("✗ Database write failed")

        except Exception as e:
            print(f"✗ Error: {e}")

        time.sleep(delay)

    return results


if __name__ == "__main__":
    # Example: scrape player 988 (Grant McNeill)
    player_info = scrape_player(988, "games_new.db")
    if player_info:
        print(f"Scraped: {player_info}")
    else:
        print("Failed to scrape player")
