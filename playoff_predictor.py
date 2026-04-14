"""AHL Playoff Bracket Prediction Engine.

Monte Carlo-based predictions for AHL playoff outcomes with historical backtesting support.
Run 'playoff_predictor.py --help' for available commands.
"""

import click
import math
import sqlite3
import json
import os
from datetime import datetime, UTC, date
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from playoff_simulations import get_series_win_probability

# Load environment variables from .env file
load_dotenv()


# Database setup
_docker_db = Path("/data/my_database.db")
DB_PATH = (
    _docker_db if _docker_db.exists() else Path(__file__).parent / "my_database.db"
)


def _load_season_pairs() -> dict[int, Optional[int]]:
    """Load season pairings from environment variable or use defaults.

    Environment variable: AHL_SEASON_PAIRS
    Format: JSON string mapping regular_season_id -> playoff_season_id
    Example: {"77": 80, "81": 84, "86": 88, "90": null}

    Returns:
        Dictionary of {regular_season_id: playoff_season_id}
    """
    env_pairs = os.getenv("AHL_SEASON_PAIRS")

    if env_pairs:
        try:
            # Convert string keys from JSON to integers
            pairs = json.loads(env_pairs)
            return {int(k): v for k, v in pairs.items()}
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠ Warning: Failed to parse AHL_SEASON_PAIRS: {e}")
            print("  Falling back to defaults")

    # Default season pairings
    return {
        77: 80,  # 2022-23
        81: 84,  # 2023-24
        86: 88,  # 2024-25
        90: None,  # 2025-26 (TBD)
    }


SEASON_PAIRS = _load_season_pairs()

# Teams that qualify from each division
DIVISION_QUALIFY_COUNT = {
    "Central Division": 5,
    "North Division": 5,
    "Atlantic Division": 6,
    "Pacific Division": 7,
}

# Divisional conference mappings
DIVISION_CONFERENCE = {
    "Central Division": "West",
    "Pacific Division": "West",
    "North Division": "East",
    "Atlantic Division": "East",
}

# Distance threshold for home ice format (miles)
DISTANCE_THRESHOLD_MILES = 300

# Home ice schedules: {format_key: {game_number: is_higher_seed_home}}
HOME_ICE_SCHEDULES = {
    "R1_close": {1: True, 2: False, 3: True},  # 1-1-1
    "R1_far": {1: True, 2: True, 3: True},  # 3-0
    "R23_close": {1: True, 2: True, 3: False, 4: False, 5: True},  # 2-2-1
    "R23_far_A": {1: True, 2: True, 3: False, 4: False, 5: False},  # 2-3 option A
    "R23_far_B": {1: False, 2: False, 3: True, 4: True, 5: True},  # 2-3 option B
    "finals": {
        1: True,
        2: True,
        3: False,
        4: False,
        5: False,
        6: True,
        7: True,
    },  # 2-3-2
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class PlayoffSeeding(BaseModel):
    """Team seeding for a playoff bracket."""

    seeding_id: Optional[int] = None
    reg_season_id: int
    team_id: int
    division_name: str
    conference_name: str
    seed: int
    points: int
    wins: int
    reg_wins: int
    row_wins: int
    gp: int
    computed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class SeriesState(BaseModel):
    """State of a playoff series."""

    series_id: Optional[int] = None
    playoff_season_id: int
    reg_season_id: int
    round_number: int
    division_name: Optional[str] = None
    conference_name: Optional[str] = None
    series_label: str
    higher_seed_team_id: Optional[int] = None
    lower_seed_team_id: Optional[int] = None
    higher_seed_wins: int = 0
    lower_seed_wins: int = 0
    series_winner_team_id: Optional[int] = None
    series_complete: bool = False
    source_series_a_id: Optional[int] = None
    source_series_b_id: Optional[int] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class SeriesPrediction(BaseModel):
    """Win probability prediction for a series."""

    prediction_id: Optional[int] = None
    series_id: int
    snapshot_date: str
    home_team_id: int
    away_team_id: int
    home_series_win_pct: float
    away_series_win_pct: float
    expected_games: float
    games_dist_json: str
    n_simulations: int
    computed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class BracketSnapshot(BaseModel):
    """Daily snapshot of full bracket predictions."""

    snapshot_id: Optional[int] = None
    playoff_season_id: int
    snapshot_date: str
    snapshot_type: str  # 'pre', 'live', 'mid', 'final'
    bracket_json: str
    champion_probs_json: str
    n_simulations: int
    computed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_tables(conn: sqlite3.Connection) -> None:
    """Create playoff tables if they don't exist."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playoff_seedings (
            seeding_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_season_id INTEGER NOT NULL,
            team_id       INTEGER NOT NULL,
            division_name TEXT NOT NULL,
            conference_name TEXT NOT NULL,
            seed          INTEGER NOT NULL,
            points        INTEGER NOT NULL,
            wins          INTEGER NOT NULL,
            reg_wins      INTEGER NOT NULL,
            row_wins      INTEGER NOT NULL,
            gp            INTEGER NOT NULL,
            computed_at   TEXT NOT NULL,
            UNIQUE(reg_season_id, team_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playoff_brackets (
            series_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            playoff_season_id     INTEGER NOT NULL,
            reg_season_id         INTEGER NOT NULL,
            round_number          INTEGER NOT NULL,
            division_name         TEXT,
            conference_name       TEXT,
            series_label          TEXT NOT NULL,
            higher_seed_team_id   INTEGER,
            lower_seed_team_id    INTEGER,
            higher_seed_wins      INTEGER NOT NULL DEFAULT 0,
            lower_seed_wins       INTEGER NOT NULL DEFAULT 0,
            series_winner_team_id INTEGER,
            series_complete       INTEGER NOT NULL DEFAULT 0,
            source_series_a_id    INTEGER,
            source_series_b_id    INTEGER,
            updated_at            TEXT NOT NULL,
            UNIQUE(playoff_season_id, series_label)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playoff_series_predictions (
            prediction_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id            INTEGER NOT NULL REFERENCES playoff_brackets(series_id),
            snapshot_date        TEXT NOT NULL,
            home_team_id         INTEGER NOT NULL,
            away_team_id         INTEGER NOT NULL,
            home_series_win_pct  REAL NOT NULL,
            away_series_win_pct  REAL NOT NULL,
            expected_games       REAL NOT NULL,
            games_dist_json      TEXT NOT NULL,
            n_simulations        INTEGER NOT NULL,
            computed_at          TEXT NOT NULL,
            UNIQUE(series_id, snapshot_date)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playoff_prediction_snapshots (
            snapshot_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            playoff_season_id    INTEGER NOT NULL,
            snapshot_date        TEXT NOT NULL,
            snapshot_type        TEXT NOT NULL,
            bracket_json         TEXT NOT NULL,
            champion_probs_json  TEXT NOT NULL,
            n_simulations        INTEGER NOT NULL,
            computed_at          TEXT NOT NULL,
            UNIQUE(playoff_season_id, snapshot_date)
        )
        """
    )

    conn.commit()
    print("✓ Playoff tables initialized")


# ============================================================================
# STANDINGS COMPUTATION
# ============================================================================


def compute_standings(
    conn: sqlite3.Connection, reg_season_id: int
) -> list[PlayoffSeeding]:
    """Compute final regular-season standings with AHL tiebreakers.

    Tiebreakers: (1) most points, (2) most regulation wins, (3) most reg+OT wins.

    Args:
        conn: Database connection.
        reg_season_id: Regular season ID (e.g. 90).

    Returns:
        List of PlayoffSeeding objects, one per team.
    """
    cursor = conn.cursor()

    # Get standings from gamedata
    cursor.execute(
        """
        WITH all_games AS (
            SELECT
                home_team_id as team_id,
                away_team_id as opp_team_id,
                home_team_score as team_score,
                away_team_score as opp_score,
                game_status,
                season_id
            FROM gamedata
            WHERE season_id = ?
            UNION ALL
            SELECT
                away_team_id as team_id,
                home_team_id as opp_team_id,
                away_team_score as team_score,
                home_team_score as opp_score,
                game_status,
                season_id
            FROM gamedata
            WHERE season_id = ?
        ),
        team_records AS (
            SELECT
                ag.team_id,
                tsd.division_name,
                tsd.conference_name,
                COUNT(*) as gp,
                SUM(CASE WHEN ag.team_score > ag.opp_score THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN ag.team_score < ag.opp_score AND ag.game_status = 'Final' THEN 1 ELSE 0 END) as reg_losses,
                SUM(CASE WHEN ag.team_score < ag.opp_score AND ag.game_status IN ('Final OT', 'Final SO') THEN 1 ELSE 0 END) as ot_losses
            FROM all_games ag
            LEFT JOIN team_season_division tsd ON ag.team_id = tsd.team_id AND tsd.season_id = ?
            GROUP BY ag.team_id
        )
        SELECT
            team_id,
            division_name,
            conference_name,
            gp,
            wins,
            reg_losses,
            ot_losses,
            wins * 2 + ot_losses as points,
            wins as reg_wins,
            wins + ot_losses as row_wins
        FROM team_records
        WHERE division_name IS NOT NULL
        ORDER BY division_name, points DESC, reg_wins DESC, row_wins DESC
        """,
        [reg_season_id, reg_season_id, reg_season_id],
    )

    rows = cursor.fetchall()
    seedings = []
    now = datetime.now(UTC).isoformat()

    # Assign seeds by division
    division_seeds = {}
    for row in rows:
        div = row["division_name"]
        if div not in division_seeds:
            division_seeds[div] = []
        division_seeds[div].append(row)

    for div, teams in division_seeds.items():
        for i, row in enumerate(teams, start=1):
            seeding = PlayoffSeeding(
                reg_season_id=reg_season_id,
                team_id=row["team_id"],
                division_name=row["division_name"],
                conference_name=row["conference_name"],
                seed=i,
                points=row["points"],
                wins=row["wins"],
                reg_wins=row["reg_wins"],
                row_wins=row["row_wins"],
                gp=row["gp"],
                computed_at=now,
            )
            seedings.append(seeding)

    return seedings


def save_seedings(conn: sqlite3.Connection, seedings: list[PlayoffSeeding]) -> int:
    """Save seedings to database. Returns count saved."""
    cursor = conn.cursor()
    count = 0

    for seeding in seedings:
        cursor.execute(
            """
            INSERT OR REPLACE INTO playoff_seedings
            (reg_season_id, team_id, division_name, conference_name, seed, points, wins, reg_wins, row_wins, gp, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seeding.reg_season_id,
                seeding.team_id,
                seeding.division_name,
                seeding.conference_name,
                seeding.seed,
                seeding.points,
                seeding.wins,
                seeding.reg_wins,
                seeding.row_wins,
                seeding.gp,
                seeding.computed_at,
            ),
        )
        count += 1

    conn.commit()
    return count


# ============================================================================
# BRACKET STRUCTURE
# ============================================================================


def build_bracket_structure(
    seedings: list[PlayoffSeeding],
    playoff_season_id: int,
    reg_season_id: int,
) -> list[SeriesState]:
    """Build complete playoff bracket structure from seedings.

    Implements AHL playoff rules for each division.

    Args:
        seedings: List of teams with seeds.
        playoff_season_id: The playoff season ID.
        reg_season_id: The regular season ID.

    Returns:
        List of SeriesState objects representing all series.
    """
    series_list = []
    series_counter = {}
    series_id_map = {}  # Maps (div, round, slot) -> series_id
    series_idx = 0

    # Group seedings by division
    by_division = {}
    for seeding in seedings:
        div = seeding.division_name
        if div not in by_division:
            by_division[div] = []
        by_division[div].append(seeding)

    # Build Round 1 series per division
    for div in sorted(by_division.keys()):
        teams = sorted(by_division[div], key=lambda s: s.seed)
        conf = teams[0].conference_name
        series_counter[div] = 0

        if div == "Central Division" or div == "North Division":
            # 5-team format: #4v#5, #2v#3, winners play #1
            # R1 series
            s1 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-A",
                higher_seed_team_id=teams[3].team_id,  # #4
                lower_seed_team_id=teams[4].team_id,  # #5
            )
            series_list.append(s1)
            series_id_map[(div, 1, "A")] = series_idx
            series_idx += 1

            s2 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-B",
                higher_seed_team_id=teams[1].team_id,  # #2
                lower_seed_team_id=teams[2].team_id,  # #3
            )
            series_list.append(s2)
            series_id_map[(div, 1, "B")] = series_idx
            series_idx += 1

            # R2 series (winners play #1 and each other)
            s3 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=2,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R2-A",
                higher_seed_team_id=teams[0].team_id,  # #1
                lower_seed_team_id=None,  # TBD: winner of R1-A
                source_series_a_id=None,  # Will be filled in after R1 series are saved
                source_series_b_id=None,
            )
            series_list.append(s3)
            series_id_map[(div, 2, "A")] = series_idx
            series_idx += 1

            s4 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=2,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R2-B",
                higher_seed_team_id=None,  # TBD
                lower_seed_team_id=None,  # TBD
                source_series_a_id=None,  # Will be filled in after R1 series are saved
                source_series_b_id=None,
            )
            series_list.append(s4)
            series_id_map[(div, 2, "B")] = series_idx
            series_idx += 1

            # R3 (division final)
            s5 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=3,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} Final",
                higher_seed_team_id=None,  # TBD
                lower_seed_team_id=None,  # TBD
                source_series_a_id=series_id_map[(div, 2, "A")],
                source_series_b_id=series_id_map[(div, 2, "B")],
            )
            series_list.append(s5)
            series_id_map[(div, 3, "A")] = series_idx
            series_idx += 1

        elif div == "Atlantic Division":
            # 6-team format: #3v#6, #4v#5, then lowest seed vs #1, other vs #2
            s1 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-A",
                higher_seed_team_id=teams[2].team_id,  # #3
                lower_seed_team_id=teams[5].team_id,  # #6
            )
            series_list.append(s1)
            series_id_map[(div, 1, "A")] = series_idx
            series_idx += 1

            s2 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-B",
                higher_seed_team_id=teams[3].team_id,  # #4
                lower_seed_team_id=teams[4].team_id,  # #5
            )
            series_list.append(s2)
            series_id_map[(div, 1, "B")] = series_idx
            series_idx += 1

            # R2: lowest seed from R1 plays #1; other plays #2
            s3 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=2,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R2-A",
                higher_seed_team_id=teams[0].team_id,  # #1
                lower_seed_team_id=None,  # TBD
                source_series_a_id=None,  # Will be filled in after R1 series are saved
                source_series_b_id=None,
            )
            series_list.append(s3)
            series_id_map[(div, 2, "A")] = series_idx
            series_idx += 1

            s4 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=2,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R2-B",
                higher_seed_team_id=teams[1].team_id,  # #2
                lower_seed_team_id=None,  # TBD
                source_series_a_id=None,  # Will be filled in after R1 series are saved
                source_series_b_id=None,
            )
            series_list.append(s4)
            series_id_map[(div, 2, "B")] = series_idx
            series_idx += 1

            # R3 (division final)
            s5 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=3,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} Final",
                higher_seed_team_id=None,  # TBD
                lower_seed_team_id=None,  # TBD
                source_series_a_id=None,  # Will be filled in after R2 series are saved
                source_series_b_id=None,
            )
            series_list.append(s5)
            series_id_map[(div, 3, "A")] = series_idx
            series_idx += 1

        elif div == "Pacific Division":
            # 7-team format: #1 bye; #2v#7, #3v#6, #4v#5
            s1 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-A",
                higher_seed_team_id=teams[1].team_id,  # #2
                lower_seed_team_id=teams[6].team_id,  # #7
            )
            series_list.append(s1)
            series_id_map[(div, 1, "A")] = series_idx
            series_idx += 1

            s2 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-B",
                higher_seed_team_id=teams[2].team_id,  # #3
                lower_seed_team_id=teams[5].team_id,  # #6
            )
            series_list.append(s2)
            series_id_map[(div, 1, "B")] = series_idx
            series_idx += 1

            s3 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=1,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R1-C",
                higher_seed_team_id=teams[3].team_id,  # #4
                lower_seed_team_id=teams[4].team_id,  # #5
            )
            series_list.append(s3)
            series_id_map[(div, 1, "C")] = series_idx
            series_idx += 1

            # R2: #1 plays lowest seed from R1; two other R1 winners play each other
            s4 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=2,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R2-A",
                higher_seed_team_id=teams[0].team_id,  # #1
                lower_seed_team_id=None,  # TBD: lowest seed
                source_series_a_id=None,  # Will be filled in after R1 series are saved
                source_series_b_id=None,
            )
            series_list.append(s4)
            series_id_map[(div, 2, "A")] = series_idx
            series_idx += 1

            s5 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=2,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} R2-B",
                higher_seed_team_id=None,  # TBD
                lower_seed_team_id=None,  # TBD
                source_series_a_id=None,  # Will be filled in after R1 series are saved
                source_series_b_id=None,
            )
            series_list.append(s5)
            series_id_map[(div, 2, "B")] = series_idx
            series_idx += 1

            # R3 (division final)
            s6 = SeriesState(
                playoff_season_id=playoff_season_id,
                reg_season_id=reg_season_id,
                round_number=3,
                division_name=div,
                conference_name=conf,
                series_label=f"{div} Final",
                higher_seed_team_id=None,  # TBD
                lower_seed_team_id=None,  # TBD
                source_series_a_id=None,  # Will be filled in after R2 series are saved
                source_series_b_id=None,
            )
            series_list.append(s6)
            series_id_map[(div, 3, "A")] = series_idx
            series_idx += 1

    # Conference finals and Calder Cup final
    # West: Central winner vs Pacific winner

    s_west = SeriesState(
        playoff_season_id=playoff_season_id,
        reg_season_id=reg_season_id,
        round_number=4,
        division_name=None,
        conference_name="West",
        series_label="Western Conference Final",
        higher_seed_team_id=None,  # TBD
        lower_seed_team_id=None,  # TBD
        source_series_a_id=None,  # Will be filled in after R3 series are saved
        source_series_b_id=None,
    )
    series_list.append(s_west)
    series_id_map[("Conference", 4, "W")] = series_idx
    series_idx += 1

    # East: North winner vs Atlantic winner

    s_east = SeriesState(
        playoff_season_id=playoff_season_id,
        reg_season_id=reg_season_id,
        round_number=4,
        division_name=None,
        conference_name="East",
        series_label="Eastern Conference Final",
        higher_seed_team_id=None,  # TBD
        lower_seed_team_id=None,  # TBD
        source_series_a_id=None,  # Will be filled in after R3 series are saved
        source_series_b_id=None,
    )
    series_list.append(s_east)
    series_id_map[("Conference", 4, "E")] = series_idx
    series_idx += 1

    # Calder Cup Final
    s_finals = SeriesState(
        playoff_season_id=playoff_season_id,
        reg_season_id=reg_season_id,
        round_number=5,
        division_name=None,
        conference_name=None,
        series_label="Calder Cup Final",
        higher_seed_team_id=None,  # TBD
        lower_seed_team_id=None,  # TBD
        source_series_a_id=None,  # Will be filled in after conference finals are saved
        source_series_b_id=None,
    )
    series_list.append(s_finals)

    return series_list


def save_bracket(conn: sqlite3.Connection, series_list: list[SeriesState]) -> int:
    """Save bracket series to database. Returns count saved."""
    cursor = conn.cursor()
    count = 0

    for series in series_list:
        cursor.execute(
            """
            INSERT OR REPLACE INTO playoff_brackets
            (playoff_season_id, reg_season_id, round_number, division_name, conference_name,
             series_label, higher_seed_team_id, lower_seed_team_id, higher_seed_wins, lower_seed_wins,
             series_winner_team_id, series_complete, source_series_a_id, source_series_b_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                series.playoff_season_id,
                series.reg_season_id,
                series.round_number,
                series.division_name,
                series.conference_name,
                series.series_label,
                series.higher_seed_team_id,
                series.lower_seed_team_id,
                series.higher_seed_wins,
                series.lower_seed_wins,
                series.series_winner_team_id,
                1 if series.series_complete else 0,
                None,  # source_series_a_id - will be filled in after Round 1 complete
                None,  # source_series_b_id - will be filled in after Round 1 complete
                series.updated_at,
            ),
        )
        count += 1

    conn.commit()
    return count


# ============================================================================
# CLI COMMANDS
# ============================================================================


@click.group()
def cli():
    """AHL Playoff Bracket Prediction Engine."""
    pass


@cli.command()
def init():
    """Initialize playoff tables."""
    conn = get_db_connection()
    try:
        init_tables(conn)
    finally:
        conn.close()


@cli.command()
@click.option("--season-id", type=int, default=90, help="Regular season ID")
def status(season_id: int):
    """Show playoff system status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='playoff_seedings'"
        )
        if not cursor.fetchone():
            print(
                "❌ Playoff tables not initialized. Run 'playoff_predictor.py init' first."
            )
            return

        # Check seedings
        cursor.execute(
            "SELECT COUNT(*) FROM playoff_seedings WHERE reg_season_id = ?",
            [season_id],
        )
        seeding_count = cursor.fetchone()[0]

        # Check bracket
        playoff_season_id = SEASON_PAIRS.get(season_id)
        if playoff_season_id:
            cursor.execute(
                "SELECT COUNT(*) FROM playoff_brackets WHERE playoff_season_id = ?",
                [playoff_season_id],
            )
            bracket_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT MAX(snapshot_date) FROM playoff_prediction_snapshots WHERE playoff_season_id = ?",
                [playoff_season_id],
            )
            last_update = cursor.fetchone()[0]

            print(f"Season {season_id} → Playoff {playoff_season_id}")
            print(f"  Seedings: {seeding_count} teams")
            print(f"  Bracket series: {bracket_count}")
            print(f"  Last update: {last_update or 'Never'}")
        else:
            print(f"Season {season_id}: No paired playoff season")

    finally:
        conn.close()


# ============================================================================
# SIMULATION LAYER
# ============================================================================


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in miles between two lat/lon points."""
    R = 3958.8  # Earth radius in miles
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def get_series_format(
    conn: sqlite3.Connection,
    team_a_id: int,
    team_b_id: int,
    round_number: int,
) -> str:
    """Determine home ice schedule format based on distance between teams.

    Args:
        conn: Database connection.
        team_a_id: Higher seeded team.
        team_b_id: Lower seeded team.
        round_number: 1, 2, or 3 (3+ = finals).

    Returns:
        Format key like 'R1_close', 'R23_far_A', 'finals'.
    """
    cursor = conn.cursor()

    # Get arena coordinates for both teams
    cursor.execute(
        """
        SELECT v.latitude, v.longitude
        FROM venue v
        JOIN gamedata g ON v.venue_id = g.venue_id
        WHERE g.home_team_id = ?
        LIMIT 1
        """,
        [team_a_id],
    )
    result_a = cursor.fetchone()
    if not result_a or result_a[0] is None:
        return "R1_close" if round_number == 1 else "R23_close"

    lat_a, lon_a = result_a[0], result_a[1]

    cursor.execute(
        """
        SELECT v.latitude, v.longitude
        FROM venue v
        JOIN gamedata g ON v.venue_id = g.venue_id
        WHERE g.home_team_id = ?
        LIMIT 1
        """,
        [team_b_id],
    )
    result_b = cursor.fetchone()
    if not result_b or result_b[0] is None:
        return "R1_close" if round_number == 1 else "R23_close"

    lat_b, lon_b = result_b[0], result_b[1]

    distance = haversine_miles(lat_a, lon_a, lat_b, lon_b)

    if round_number == 1:
        return "R1_far" if distance > DISTANCE_THRESHOLD_MILES else "R1_close"
    elif round_number in (2, 3):
        return "R23_far_A" if distance > DISTANCE_THRESHOLD_MILES else "R23_close"
    else:  # Conference finals, Calder Cup finals
        return "finals"


@cli.command()
@click.option("--season-id", type=int, default=90)
@click.option("--n-simulations", type=int, default=1000)
@click.option(
    "--projected",
    is_flag=True,
    help="Use projected playoff predictions (if actual playoff season not started)",
)
def update(season_id: int, n_simulations: int, projected: bool):
    """Update playoff predictions (full pipeline).

    For seasons where the playoff season hasn't been created yet, use --projected
    to generate predictions based on current regular season standings.
    """
    conn = get_db_connection()
    try:
        print(f"Updating season {season_id}...")

        # Step 1: Compute standings
        print("  Computing standings...")
        seedings = compute_standings(conn, season_id)
        saved = save_seedings(conn, seedings)
        print(f"    ✓ {saved} seedings")

        # Step 2: Determine playoff season ID
        playoff_season_id = SEASON_PAIRS.get(season_id)

        if not playoff_season_id:
            if projected:
                # Use special ID 999 for projected/simulated playoffs
                playoff_season_id = 999
                print(
                    f"  📊 Using PROJECTED playoff mode (season_id={playoff_season_id})"
                )
                print(
                    f"     Predictions based on current standings for season {season_id}"
                )
            else:
                print(f"    ⚠ No playoff season paired with season {season_id}")
                print(
                    "    💡 Use --projected flag to generate predictions based on current standings"
                )
                return

        print(f"  Building bracket for playoff season {playoff_season_id}...")
        bracket = build_bracket_structure(seedings, playoff_season_id, season_id)
        saved = save_bracket(conn, bracket)
        print(f"    ✓ {saved} series")

        # Step 3: Run predictions for all series with known teams
        print(f"  Running simulations ({n_simulations} per series)...")
        cursor = conn.cursor()
        snapshot_date = str(date.today())
        saved_count = 0

        for series in bracket:
            if series.higher_seed_team_id and series.lower_seed_team_id:
                # Get series format
                schedule_key = get_series_format(
                    conn,
                    series.higher_seed_team_id,
                    series.lower_seed_team_id,
                    series.round_number,
                )

                # Run simulation
                h_pct, l_pct, games_dist, exp_games = get_series_win_probability(
                    conn,
                    series.higher_seed_team_id,
                    series.lower_seed_team_id,
                    schedule_key,
                    n_simulations,
                )

                # Get series_id from database
                cursor.execute(
                    "SELECT series_id FROM playoff_brackets WHERE playoff_season_id = ? AND higher_seed_team_id = ? AND lower_seed_team_id = ?",
                    [
                        playoff_season_id,
                        series.higher_seed_team_id,
                        series.lower_seed_team_id,
                    ],
                )
                row = cursor.fetchone()
                if row:
                    series_id = row[0]
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO playoff_series_predictions
                        (series_id, snapshot_date, home_team_id, away_team_id, home_series_win_pct, away_series_win_pct,
                         expected_games, games_dist_json, n_simulations, computed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            series_id,
                            snapshot_date,
                            series.higher_seed_team_id,
                            series.lower_seed_team_id,
                            h_pct,
                            l_pct,
                            exp_games,
                            json.dumps(games_dist),
                            n_simulations,
                            datetime.now(UTC).isoformat(),
                        ),
                    )
                    saved_count += 1

        conn.commit()
        print(f"    ✓ {saved_count} predictions generated and saved")

        print("✓ Update complete")

    finally:
        conn.close()


if __name__ == "__main__":
    cli()
