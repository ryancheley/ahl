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
from pydantic import BaseModel, Field
from pydantic_sqlite import DataBase
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

console = Console()

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
    penalty: str = Field(validation_alias="lang_penalty_description")
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
                game_id INTEGER,
                player_id INTEGER,
                starter BOOLEAN,
                PRIMARY KEY (game_id, player_id)
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
                penalty TEXT,
                time_of_penalty_seconds INTEGER,
                player_penalized INTEGER,
                player_server INTEGER,
                PRIMARY KEY (game_id, home, period_id, player_penalized)
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
        console.print(f"[red]✗ Timeout: API request took too long[/red]")
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


def get_game_data(game_id: int) -> dict:
    url: str = f'https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=gamesummary&game_id={game_id}&key=ccb91f29d6744675&client_code=ahl'
    game_data = httpx.get(url).json()
    return game_data


def _get_game_meta_data(game_id: int, item: str):
    json_data = get_game_data(game_id)
    meta_data = json_data.get("GC").get("Gamesummary").get("meta")
    meta_data_item = meta_data.get(item)
    return meta_data_item


def _get_game_game_summary_data(game_id: int, item: str):
    json_data = get_game_data(game_id)
    data_item = json_data.get("GC").get("Gamesummary").get(item)
    return data_item


def get_penalties(game_id):
    penalties = []
    keys_to_use = ["home", "period_id", "pp", "bench", "penalty_shot", "minutes", "lang_penalty_description", "s", "player_penalized_info", "player_served_info"]

    penalty_data_list = _get_game_game_summary_data(game_id, 'penalties')
    if not penalty_data_list:
        return penalties

    for penalty_data in penalty_data_list:
        try:
            filtered_penalty_data = {k: penalty_data[k] for k in keys_to_use if k in penalty_data}
            filtered_penalty_data = {"game_id": game_id} | filtered_penalty_data

            # Safely extract player IDs with fallback to 0
            player_penalized_info = filtered_penalty_data.get('player_penalized_info')
            player_served_info = filtered_penalty_data.get('player_served_info')

            player_penalized_id = 0
            player_served_id = 0

            if player_penalized_info and isinstance(player_penalized_info, dict):
                player_penalized_id = player_penalized_info.get('player_id', 0)
            elif isinstance(player_penalized_info, int):
                player_penalized_id = player_penalized_info

            if player_served_info and isinstance(player_served_info, dict):
                player_served_id = player_served_info.get('player_id', 0)
            elif isinstance(player_served_info, int):
                player_served_id = player_served_info

            filtered_penalty_data['player_penalized_info'] = player_penalized_id
            filtered_penalty_data['player_served_info'] = player_served_id

            penalties.append(GamePenalties(**filtered_penalty_data))
        except Exception as e:
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
    home_shots = total_shots.get("home", 0) if total_shots else 0
    away_shots = total_shots.get("visitor", 0) if total_shots else 0

    game_dictionary = {
        "game_id": game_id,
        "season_id": int(_get_game_meta_data(game_id, "season_id") or 0),
        "away_team_id": away_team.team_id,
        "away_team_score": int(_get_game_meta_data(game_id, "visiting_goal_count") or 0),
        "home_team_id": home_team.team_id,
        "home_team_score": int(_get_game_meta_data(game_id, "home_goal_count") or 0),
        "game_status": str(_get_game_game_summary_data(game_id, "status_value") or "unknown"),
        "game_date": _get_game_meta_data(game_id, "date_played"),
        "game_attendance": int(_get_game_meta_data(game_id, "attendance") or 0),
        "home_team_shots": int(home_shots or 0),
        "away_team_shots": int(away_shots or 0),
        "game_number": int(_get_game_meta_data(game_id, "game_number") or 0),
        "venue_id": int(_get_game_meta_data(game_id, 'location') or 0)
    }
    return GameData(**game_dictionary)


# ============================================================================
# Data Saving Functions
# ============================================================================

def save_venue(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save venue data from game."""
    try:
        venue_id = int(_get_game_meta_data(game_id, 'location') or 0)
        if venue_id == 0:
            return True

        location = _get_game_game_summary_data(game_id, 'location')
        venue_name = location if isinstance(location, str) else f"Venue {venue_id}"

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

        cursor.execute(
            'INSERT OR IGNORE INTO season (season_id, season_name, shortname, career, playoff, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (season_id, f"Season {season_id}", f"S{season_id}", False, False, None, None)
        )
        conn.commit()
        return True
    except Exception as e:
        console.print(f"[red]Error saving season: {e}[/red]")
        return False


def save_penalty_classes(conn: sqlite3.Connection, game_id: int) -> bool:
    """Extract and save penalty class data from game penalties."""
    try:
        penalty_data_list = _get_game_game_summary_data(game_id, 'penalties')
        if not penalty_data_list:
            return True

        cursor = conn.cursor()
        saved_classes = set()

        for penalty_data in penalty_data_list:
            if isinstance(penalty_data, dict):
                penalty_class_id = int(penalty_data.get('penalty_class_id', 0))
                penalty_class_desc = penalty_data.get('penalty_class', '')

                if penalty_class_id > 0 and penalty_class_id not in saved_classes:
                    cursor.execute(
                        'INSERT OR IGNORE INTO penaltyclass (penalty_class_id, penalty_class_description) VALUES (?, ?)',
                        (penalty_class_id, penalty_class_desc)
                    )
                    saved_classes.add(penalty_class_id)

                    # Also save the specific penalty type
                    penalty_description = penalty_data.get('lang_penalty_description', '')
                    if penalty_description:
                        # Use hash of description as penalty_id since API doesn't provide one
                        penalty_id = abs(hash(penalty_description)) % 10000
                        cursor.execute(
                            'INSERT OR IGNORE INTO penalty (penalty_id, penalty_class_id, penalty_description) VALUES (?, ?, ?)',
                            (penalty_id, penalty_class_id, penalty_description)
                        )

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
        insert_model(conn, game, 'gamedata')

        away_team = get_game_team_instance(game_id, "visitor")
        home_team = get_game_team_instance(game_id, "home")
        insert_model(conn, away_team, 'team', replace=True)
        insert_model(conn, home_team, 'team', replace=True)

        penalties = get_penalties(game_id)
        for penalty in penalties:
            insert_model(conn, penalty, 'gamepenalties', replace=True)

        # Save venue, season, officials, and penalty classes
        save_venue(conn, game_id)
        save_season(conn, game_id)
        save_officials(conn, game_id)
        save_penalty_classes(conn, game_id)

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
    """Load all games played today."""
    console.print(Panel.fit("[bold cyan]Loading Today's Games[/bold cyan]", border_style="cyan"))

    conn = init_database()
    today_date = datetime.now().date()
    console.print(f"[yellow]Date:[/yellow] {today_date}\n")

    saved_count = 0
    error_count = 0
    games_data = []

    season_ids = get_season_ids()
    if not season_ids:
        console.print("[red]✗ No seasons found[/red]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scanning all seasons...", total=None)

        for season_id in season_ids:
            game_ids = get_season_game_ids(season_id)

            for game_id in game_ids:
                try:
                    game = get_game_instance(game_id)
                    game_check_date = game.game_date if isinstance(game.game_date, date) else game.game_date.date()

                    if game_check_date == today_date:
                        away_team = get_game_team_instance(game_id, "visitor")
                        home_team = get_game_team_instance(game_id, "home")

                        insert_model(conn, game, 'gamedata')
                        insert_model(conn, away_team, 'team', replace=True)
                        insert_model(conn, home_team, 'team', replace=True)

                        penalties = get_penalties(game_id)
                        for penalty in penalties:
                            insert_model(conn, penalty, 'gamepenalties', replace=True)

                        games_data.append({
                            "Game ID": game_id,
                            "Away": away_team.name,
                            "Home": home_team.name,
                            "Score": f"{game.away_team_score}-{game.home_team_score}",
                            "Status": game.game_status,
                        })
                        saved_count += 1
                except Exception:
                    error_count += 1
                    continue

        progress.stop()

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
    else:
        console.print("[yellow]⊘ No games found for today[/yellow]")

    if error_count > 0:
        console.print(f"[yellow]⚠ {error_count} games skipped due to errors[/yellow]")


@cli.command()
@click.option('--season-id', type=int, required=True, help='Season ID (e.g., 90 for 2025-26)')
@click.option('--limit', type=int, default=None, help='Maximum number of games to load')
def season(season_id: int, limit: int):
    """Load all games for a specific season."""
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

    console.print(f"[yellow]Found {len(game_ids)} games[/yellow]\n")

    saved_count = 0
    error_count = 0
    games_data = []

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Loading games...",
            total=len(game_ids)
        )

        for game_id in game_ids:
            success, message = save_game_data(conn, game_id)

            if success:
                games_data.append({"ID": game_id, "Result": message})
                saved_count += 1
            else:
                error_count += 1

            progress.advance(task)

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
        task = progress.add_task("Fetching game data...", total=None)
        success, message = save_game_data(conn, game_id)
        progress.stop()

    if success:
        console.print(f"\n[green]✓ Game saved successfully[/green]")
        console.print(f"[cyan]{message}[/cyan]")
    else:
        console.print(f"\n[red]✗ Failed to load game[/red]")
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
        task = progress.add_task("Registering models...", total=None)
        init_database()
        progress.stop()

    console.print("[green]✓ Database initialized[/green]")
    console.print("[cyan]Models: Person, Team, Venue, Season, GameData, GameOfficial, Official, Player, GameRoster, PenaltyClass, Penalty, GamePenalties[/cyan]")
    console.print("[dim]Tables will be created automatically on first data insert[/dim]")


if __name__ == "__main__":
    cli()
