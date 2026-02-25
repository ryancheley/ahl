#!/usr/bin/env python3
"""
API-Based Game Scraper for AHL

Replaces HTML scraping with clean, structured API calls to hockeytech.
Uses gc (game clock) feed endpoints to fetch all game data.

Endpoints:
  - gc/pxpverbose: Play-by-play data (goals, penalties, shots, events)
  - gc/gamesummary: Game metadata (scores, officials, timing, attendance)

Author: Claude Code
Date: 2026-02-25
"""

import requests
import json
import sqlite3
from dataclasses import dataclass
from typing import Optional, Dict, List, Any

# Configuration
API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"
SEASON_ID = 90
SITE_ID = 3
LEAGUE_ID = 4
LANG = 1

BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"


# =====================================================
# Data Classes
# =====================================================

@dataclass
class Goal:
    """Represents a goal scored in a game."""
    game_id: int
    goal_id: str
    scorer_id: str
    scorer_name: str
    player_number: int
    assist1_id: Optional[str]
    assist1_name: Optional[str]
    assist2_id: Optional[str]
    assist2_name: Optional[str]
    period: int
    time: str
    team_id: str
    power_play: bool
    empty_net: bool
    short_handed: bool
    penalty_shot: bool
    game_winning: bool
    game_tying: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'game_id': self.game_id,
            'goal_id': self.goal_id,
            'scorer_id': self.scorer_id,
            'scorer_name': self.scorer_name,
            'player_number': self.player_number,
            'assist1_id': self.assist1_id,
            'assist1_name': self.assist1_name,
            'assist2_id': self.assist2_id,
            'assist2_name': self.assist2_name,
            'period': self.period,
            'time': self.time,
            'team_id': self.team_id,
            'power_play': int(self.power_play),
            'empty_net': int(self.empty_net),
            'short_handed': int(self.short_handed),
            'penalty_shot': int(self.penalty_shot),
            'game_winning': int(self.game_winning),
            'game_tying': int(self.game_tying),
        }


@dataclass
class Penalty:
    """Represents a penalty in a game."""
    game_id: int
    penalty_id: str
    player_id: str
    player_name: str
    team_id: str
    offense: str
    offense_description: str
    penalty_class: str
    minutes: float
    period: int
    time: str
    power_play: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'game_id': self.game_id,
            'penalty_id': self.penalty_id,
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'offense': self.offense,
            'offense_description': self.offense_description,
            'penalty_class': self.penalty_class,
            'minutes': self.minutes,
            'period': self.period,
            'time': self.time,
            'power_play': int(self.power_play),
        }


@dataclass
class Official:
    """Represents an official in a game."""
    game_id: int
    official_id: str
    official_type_id: int  # 1=Referee, 2=Linesman
    official_type: str  # "Referee 1", "Linesman 2", etc.
    first_name: str
    last_name: str
    jersey_number: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'game_id': self.game_id,
            'official_id': self.official_id,
            'official_type_id': self.official_type_id,
            'official_type': self.official_type,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'jersey_number': self.jersey_number,
        }


@dataclass
class GameData:
    """Complete game data from API."""
    game_id: int
    date_played: str
    home_team_id: str
    visiting_team_id: str
    home_goals: int
    visiting_goals: int
    period: int
    status: str
    attendance: int
    start_time: str
    end_time: str
    timezone: str
    referee1: str
    referee2: str
    linesman1: str
    linesman2: str
    shootout: int
    game_letter: str
    game_number: int
    overtime_periods: int
    game_type: str
    game_format: str
    home_shots: int
    away_shots: int
    goals: List[Goal]
    penalties: List[Penalty]
    officials: List[Official]

    def summary(self) -> str:
        """Return human-readable summary."""
        return (
            f"Game {self.game_id}: "
            f"{self.visiting_team_id} @ {self.home_team_id} "
            f"{self.visiting_goals}-{self.home_goals} "
            f"({self.goals} goals, {self.penalties} penalties, {len(self.officials)} officials)"
        )


# =====================================================
# API Client
# =====================================================

class HockeyTechAPI:
    """Client for HockeyTech StatViewFeed API."""

    def __init__(self, api_key: str = API_KEY, client_code: str = CLIENT_CODE):
        """Initialize API client."""
        self.api_key = api_key
        self.client_code = client_code
        self.session = requests.Session()

    def _get(self, params: Dict[str, Any]) -> Optional[Dict[Any, Any]]:
        """Make API request and return parsed JSON."""
        try:
            response = self.session.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return json.loads(response.text)
        except requests.RequestException as e:
            print(f"API Error: {e}")
            return None

    def fetch_pxpverbose(self, game_id: int, season_id: int = SEASON_ID) -> Optional[Dict[Any, Any]]:
        """Fetch play-by-play verbose data for a game."""
        params = {
            'feed': 'gc',
            'tab': 'pxpverbose',
            'game_id': game_id,
            'season_id': season_id,
            'key': self.api_key,
            'client_code': self.client_code,
        }
        return self._get(params)

    def fetch_gamesummary(self, game_id: int, season_id: int = SEASON_ID) -> Optional[Dict[Any, Any]]:
        """Fetch game summary data for a game."""
        params = {
            'feed': 'gc',
            'tab': 'gamesummary',
            'game_id': game_id,
            'season_id': season_id,
            'key': self.api_key,
            'client_code': self.client_code,
        }
        return self._get(params)


# =====================================================
# Data Parsers
# =====================================================

class PXPVerboseParser:
    """Parser for gc/pxpverbose endpoint responses."""

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to int, handling empty strings and None."""
        if not value or value == '':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def extract_goals(game_id: int, pxp_data: Dict[Any, Any]) -> List[Goal]:
        """Extract goal data from pxpverbose response."""
        goals = []
        pxp_events = pxp_data.get('GC', {}).get('Pxpverbose', [])

        for event in pxp_events:
            if event.get('event') != 'goal':
                continue

            goal_scorer = event.get('goal_scorer', {})
            assist1 = event.get('assist1_player', {})
            assist2 = event.get('assist2_player', {})

            goal = Goal(
                game_id=game_id,
                goal_id=event.get('id', ''),
                scorer_id=goal_scorer.get('player_id', event.get('goal_player_id', '')),
                scorer_name=f"{goal_scorer.get('first_name', '')} {goal_scorer.get('last_name', '')}".strip(),
                player_number=PXPVerboseParser._safe_int(goal_scorer.get('jersey_number', 0)),
                assist1_id=assist1.get('player_id') if assist1 else None,
                assist1_name=f"{assist1.get('first_name', '')} {assist1.get('last_name', '')}".strip() if assist1 else None,
                assist2_id=assist2.get('player_id') if assist2 else None,
                assist2_name=f"{assist2.get('first_name', '')} {assist2.get('last_name', '')}".strip() if assist2 else None,
                period=PXPVerboseParser._safe_int(event.get('period_id', 0)),
                time=event.get('time_formatted', ''),
                team_id=event.get('team_id', ''),
                power_play=bool(PXPVerboseParser._safe_int(event.get('power_play', 0))),
                empty_net=bool(PXPVerboseParser._safe_int(event.get('empty_net', 0))),
                short_handed=bool(PXPVerboseParser._safe_int(event.get('short_handed', 0))),
                penalty_shot=bool(PXPVerboseParser._safe_int(event.get('penalty_shot', 0))),
                game_winning=bool(PXPVerboseParser._safe_int(event.get('game_winning', 0))),
                game_tying=bool(PXPVerboseParser._safe_int(event.get('game_tieing', 0))),
            )
            goals.append(goal)

        return goals

    @staticmethod
    def extract_penalties(game_id: int, pxp_data: Dict[Any, Any]) -> List[Penalty]:
        """Extract penalty data from pxpverbose response."""
        penalties = []
        pxp_events = pxp_data.get('GC', {}).get('Pxpverbose', [])

        for event in pxp_events:
            if event.get('event') != 'penalty':
                continue

            player_info = event.get('player_penalized_info', {})

            penalty = Penalty(
                game_id=game_id,
                penalty_id=event.get('id', ''),
                player_id=player_info.get('player_id', event.get('player_id', '')),
                player_name=f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                team_id=event.get('team_id', ''),
                offense=event.get('offence', ''),
                offense_description=event.get('lang_penalty_description', ''),
                penalty_class=event.get('penalty_class', ''),
                minutes=float(PXPVerboseParser._safe_int(event.get('minutes', 0))),
                period=PXPVerboseParser._safe_int(event.get('period_id', 0)),
                time=event.get('time_off_formatted', ''),
                power_play=bool(PXPVerboseParser._safe_int(event.get('pp', 0))),
            )
            penalties.append(penalty)

        return penalties


class GameSummaryParser:
    """Parser for gc/gamesummary endpoint responses."""

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to int, handling empty strings and None."""
        if not value or value == '':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def extract_game_data(game_id: int, summary_data: Dict[Any, Any]) -> Optional[Dict[str, Any]]:
        """Extract game metadata from gamesummary response."""
        gc_data = summary_data.get('GC', {})
        summary = gc_data.get('Gamesummary', {})
        meta = summary.get('meta', {})

        if not meta:
            return None

        # Map status code to meaningful text
        status_code = meta.get('status', '')
        status_map = {
            '1': 'Scheduled',
            '2': 'In Progress',
            '3': 'Completed',
            '4': 'Final',
            '5': 'Final/OT',
            '6': 'Final/SO',
        }
        game_status = status_map.get(str(status_code), 'Unknown')

        # Calculate overtime periods and game format
        period = GameSummaryParser._safe_int(meta.get('period', 0))
        overtime_periods = max(0, period - 3)  # Regular season has 3 periods
        shootout = GameSummaryParser._safe_int(meta.get('shootout', 0))

        # Determine game format
        if shootout:
            game_format = 'shootout'
        elif overtime_periods > 0:
            game_format = 'overtime'
        else:
            game_format = 'regulation'

        # Extract shots data
        total_shots = summary.get('totalShots', {})
        home_shots = GameSummaryParser._safe_int(total_shots.get('home', 0)) if total_shots else 0
        away_shots = GameSummaryParser._safe_int(total_shots.get('visitor', 0)) if total_shots else 0

        return {
            'game_id': game_id,
            'date_played': meta.get('date_played', ''),
            'home_team_id': meta.get('home_team', ''),
            'visiting_team_id': meta.get('visiting_team', ''),
            'home_goals': GameSummaryParser._safe_int(meta.get('home_goal_count', 0)),
            'visiting_goals': GameSummaryParser._safe_int(meta.get('visiting_goal_count', 0)),
            'period': period,
            'status': game_status,
            'attendance': GameSummaryParser._safe_int(meta.get('attendance', 0)),
            'start_time': meta.get('start_time', ''),
            'end_time': meta.get('end_time', ''),
            'timezone': meta.get('timezone', ''),
            'referee1': meta.get('referee1', ''),
            'referee2': meta.get('referee2', ''),
            'linesman1': meta.get('linesman1', ''),
            'linesman2': meta.get('linesman2', ''),
            'shootout': shootout,
            'game_letter': meta.get('game_letter', ''),
            'game_number': GameSummaryParser._safe_int(meta.get('game_number', 0)),
            'overtime_periods': overtime_periods,
            'game_type': 'regular',  # All current data is regular season
            'game_format': game_format,
            'home_shots': home_shots,
            'away_shots': away_shots,
        }

    @staticmethod
    def extract_officials(game_id: int, summary_data: Dict[Any, Any]) -> List[Official]:
        """Extract officials data from gamesummary response."""
        officials = []
        gc_data = summary_data.get('GC', {})
        summary = gc_data.get('Gamesummary', {})
        officials_on_ice = summary.get('officialsOnIce', [])

        for official_data in officials_on_ice:
            official = Official(
                game_id=game_id,
                official_id=official_data.get('person_id', ''),
                official_type_id=int(official_data.get('official_type_id', 0)),
                official_type=official_data.get('description', ''),
                first_name=official_data.get('first_name', ''),
                last_name=official_data.get('last_name', ''),
                jersey_number=official_data.get('jersey_number', ''),
            )
            officials.append(official)

        return officials


# =====================================================
# Main Scraper
# =====================================================

class APIGameScraper:
    """Main scraper using API endpoints."""

    def __init__(self, db_path: str = 'games_new.db'):
        """Initialize scraper."""
        self.api = HockeyTechAPI()
        self.db_path = db_path

    def scrape_game(self, game_id: int) -> Optional[GameData]:
        """Scrape complete game data from API."""
        print(f"\n{'='*70}")
        print(f"Scraping game {game_id}...")
        print(f"{'='*70}")

        # Fetch data from both endpoints
        pxp_data = self.api.fetch_pxpverbose(game_id)
        summary_data = self.api.fetch_gamesummary(game_id)

        if not pxp_data or not summary_data:
            print(f"✗ Failed to fetch API data for game {game_id}")
            return None

        # Parse game metadata
        game_dict = GameSummaryParser.extract_game_data(game_id, summary_data)
        if not game_dict:
            print("✗ Failed to parse game metadata")
            return None

        # Parse goals
        goals = PXPVerboseParser.extract_goals(game_id, pxp_data)
        print(f"  ✓ Found {len(goals)} goals")

        # Parse penalties
        penalties = PXPVerboseParser.extract_penalties(game_id, pxp_data)
        print(f"  ✓ Found {len(penalties)} penalties")

        # Parse officials
        officials = GameSummaryParser.extract_officials(game_id, summary_data)
        print(f"  ✓ Found {len(officials)} officials")

        # Create GameData object
        game_data = GameData(
            game_id=game_dict['game_id'],
            date_played=game_dict['date_played'],
            home_team_id=game_dict['home_team_id'],
            visiting_team_id=game_dict['visiting_team_id'],
            home_goals=game_dict['home_goals'],
            visiting_goals=game_dict['visiting_goals'],
            period=game_dict['period'],
            status=game_dict['status'],
            attendance=game_dict['attendance'],
            start_time=game_dict['start_time'],
            end_time=game_dict['end_time'],
            timezone=game_dict['timezone'],
            referee1=game_dict['referee1'],
            referee2=game_dict['referee2'],
            linesman1=game_dict['linesman1'],
            linesman2=game_dict['linesman2'],
            shootout=game_dict['shootout'],
            game_letter=game_dict['game_letter'],
            game_number=game_dict['game_number'],
            overtime_periods=game_dict['overtime_periods'],
            game_type=game_dict['game_type'],
            game_format=game_dict['game_format'],
            home_shots=game_dict['home_shots'],
            away_shots=game_dict['away_shots'],
            goals=goals,
            penalties=penalties,
            officials=officials,
        )

        print(f"\n{game_data.summary()}")
        return game_data

    def write_game_to_database(self, game_data: GameData) -> bool:
        """Write game data to database."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.isolation_level = None  # Autocommit mode
            cursor = conn.cursor()

            # Insert game (update if exists)
            cursor.execute('''
                INSERT OR REPLACE INTO games_extended (
                    game_id, game_date, home_team, away_team,
                    home_score, away_score, attendance, season_id,
                    game_status, overtime_periods, decided_by_shootout,
                    game_type, game_format, home_shots, away_shots
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_data.game_id,
                game_data.date_played,
                game_data.home_team_id,
                game_data.visiting_team_id,
                game_data.home_goals,
                game_data.visiting_goals,
                game_data.attendance,
                SEASON_ID,
                game_data.status,
                game_data.overtime_periods,
                game_data.shootout,
                game_data.game_type,
                game_data.game_format,
                game_data.home_shots,
                game_data.away_shots,
            ))

            # Insert goals
            for goal_number, goal in enumerate(game_data.goals, 1):
                assists_text = ''
                if goal.assist1_name:
                    assists_text = goal.assist1_name
                    if goal.assist2_name:
                        assists_text += f", {goal.assist2_name}"

                cursor.execute('''
                    INSERT INTO goals (
                        game_id, goal_number, player_name, player_number, team, assists,
                        period, time, power_play, empty_net, short_handed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_data.game_id,
                    goal_number,
                    goal.scorer_name,
                    goal.player_number,
                    goal.team_id,
                    assists_text,
                    goal.period,
                    goal.time,
                    int(goal.power_play),
                    int(goal.empty_net),
                    int(goal.short_handed),
                ))

            # Insert penalties
            for penalty in game_data.penalties:
                cursor.execute('''
                    INSERT INTO penalties (
                        game_id, player_name, team, penalty_type,
                        period, time, duration_minutes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_data.game_id,
                    penalty.player_name,
                    penalty.team_id,
                    penalty.offense_description,
                    penalty.period,
                    penalty.time,
                    int(penalty.minutes),
                ))

            # Insert officials
            for official in game_data.officials:
                full_name = f"{official.first_name} {official.last_name}".strip()
                cursor.execute('''
                    INSERT INTO officials (
                        game_id, official_type, name, number
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    game_data.game_id,
                    official.official_type,
                    full_name,
                    int(official.jersey_number) if official.jersey_number.isdigit() else 0,
                ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"  ✗ Database error: {e}")
            return False


# =====================================================
# Main Entry Point
# =====================================================

def main():
    """Main entry point for testing."""
    scraper = APIGameScraper()

    # Test with known game
    game_id = 1027888
    game_data = scraper.scrape_game(game_id)

    if game_data:
        # Optionally write to database
        # scraper.write_game_to_database(game_data)
        print("\n✓ Scraping successful!")
        print(f"  Goals: {len(game_data.goals)}")
        print(f"  Penalties: {len(game_data.penalties)}")
        print(f"  Officials: {len(game_data.officials)}")
    else:
        print("\n✗ Scraping failed!")


if __name__ == '__main__':
    main()
