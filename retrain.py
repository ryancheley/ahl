#!/usr/bin/env python3
"""Monte Carlo team and official stats retrainer.

Computes cached Poisson parameters and official home-win bias for the
Monte Carlo game outcome predictor. Runs daily via Coolify after data scrape.
"""

import sqlite3
from datetime import datetime, UTC
from pathlib import Path

import click
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()
DB_PATH = Path(__file__).parent / "my_database.db"
LEAGUE_HOME_WIN_PCT = 0.5361  # Empirical from historical data
MIN_OFFICIAL_GAMES = 20  # Minimum sample size for official stats


def get_db_connection() -> sqlite3.Connection:
    """Get database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


class TeamStats(BaseModel):
    """Cached team attack/defense rates for Monte Carlo."""

    team_id: int
    season_id: int
    attack_rate: float
    defense_rate: float
    so_win_rate: float
    games_used: int
    computed_at: str


class OfficialStats(BaseModel):
    """Cached official home-win bias for Monte Carlo."""

    person_id: int
    home_win_pct: float
    games_officiated: int
    computed_at: str


def init_tables(conn: sqlite3.Connection) -> None:
    """Create the three MC prediction tables if they don't exist."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mc_team_stats (
            team_id       INTEGER NOT NULL,
            season_id     INTEGER NOT NULL,
            attack_rate   REAL NOT NULL,
            defense_rate  REAL NOT NULL,
            so_win_rate   REAL NOT NULL,
            games_used    INTEGER NOT NULL,
            computed_at   TEXT NOT NULL,
            PRIMARY KEY (team_id, season_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mc_official_stats (
            person_id         INTEGER PRIMARY KEY,
            home_win_pct      REAL NOT NULL,
            games_officiated  INTEGER NOT NULL,
            computed_at       TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mc_predictions (
            prediction_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id          INTEGER NOT NULL,
            n_simulations    INTEGER NOT NULL,
            decay_rate       REAL NOT NULL,
            lookback_games   INTEGER NOT NULL,
            home_win_pct     REAL NOT NULL,
            away_win_pct     REAL NOT NULL,
            ot_pct           REAL NOT NULL,
            so_pct           REAL NOT NULL,
            avg_home_goals   REAL NOT NULL,
            avg_away_goals   REAL NOT NULL,
            score_dist_json  TEXT NOT NULL,
            computed_at      TEXT NOT NULL,
            UNIQUE(game_id, n_simulations, decay_rate, lookback_games)
        )
        """
    )

    conn.commit()
    console.print(
        Panel(
            "[green]✓ MC prediction tables created successfully[/green]",
            title="Init",
        )
    )


def compute_team_stats(
    conn: sqlite3.Connection, season_id: int, lookback: int, decay_rate: float
) -> list[TeamStats]:
    """Compute attack/defense rates for all teams in a season using exponential decay."""
    import math

    cursor = conn.cursor()

    # Get league average goals for this season (regulation scoring)
    cursor.execute(
        """
        SELECT AVG((home_team_score + away_team_score) / 2.0) as league_avg_goals
        FROM gamedata
        WHERE season_id = ? AND game_status = 'Final'
        """,
        (season_id,),
    )
    result = cursor.fetchone()
    league_avg_goals = float(result["league_avg_goals"]) if result["league_avg_goals"] else 2.94

    # Get all teams in this season
    cursor.execute(
        """
        SELECT DISTINCT team_id FROM (
            SELECT home_team_id as team_id FROM gamedata WHERE season_id = ?
            UNION
            SELECT away_team_id as team_id FROM gamedata WHERE season_id = ?
        )
        """,
        (season_id, season_id),
    )
    teams = [row["team_id"] for row in cursor.fetchall()]

    stats = []
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    for team_id in teams:
        # Fetch recent games for this team (both home and away)
        cursor.execute(
            """
            SELECT
                g.game_date,
                g.home_team_id,
                g.away_team_id,
                g.home_team_score,
                g.away_team_score,
                g.game_status
            FROM gamedata g
            WHERE g.season_id = ?
              AND (g.home_team_id = ? OR g.away_team_id = ?)
              AND g.game_status = 'Final'
            ORDER BY g.game_date DESC
            LIMIT ?
            """,
            (season_id, team_id, team_id, lookback),
        )
        games = cursor.fetchall()

        if not games:
            continue

        # Compute weighted attack and defense rates with exponential decay
        total_weight = 0.0
        weighted_goals_for = 0.0
        weighted_goals_against = 0.0

        for i, game in enumerate(games):
            weight = math.exp(-decay_rate * i)
            total_weight += weight

            if game["home_team_id"] == team_id:
                gf = game["home_team_score"]
                ga = game["away_team_score"]
            else:
                gf = game["away_team_score"]
                ga = game["home_team_score"]

            weighted_goals_for += weight * gf
            weighted_goals_against += weight * ga

        avg_gf = weighted_goals_for / total_weight if total_weight > 0 else 0
        avg_ga = weighted_goals_against / total_weight if total_weight > 0 else 0

        attack_rate = avg_gf / league_avg_goals if league_avg_goals > 0 else 1.0
        defense_rate = avg_ga / league_avg_goals if league_avg_goals > 0 else 1.0

        # Compute SO win rate for this team
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN g.game_status = 'Final SO' AND
                    ((g.home_team_id = ? AND g.home_team_score > g.away_team_score) OR
                     (g.away_team_id = ? AND g.away_team_score > g.home_team_score))
                    THEN 1 ELSE 0 END) as so_wins,
                SUM(CASE WHEN g.game_status = 'Final SO' AND
                    (g.home_team_id = ? OR g.away_team_id = ?)
                    THEN 1 ELSE 0 END) as so_total
            FROM gamedata g
            WHERE g.season_id = ?
              AND (g.home_team_id = ? OR g.away_team_id = ?)
            """,
            (team_id, team_id, team_id, team_id, season_id, team_id, team_id),
        )
        so_result = cursor.fetchone()
        so_wins = so_result["so_wins"] or 0
        so_total = so_result["so_total"] or 0
        so_win_rate = (so_wins / so_total) if so_total > 0 else 0.5

        stats.append(
            TeamStats(
                team_id=team_id,
                season_id=season_id,
                attack_rate=attack_rate,
                defense_rate=defense_rate,
                so_win_rate=so_win_rate,
                games_used=len(games),
                computed_at=timestamp,
            )
        )

    return stats


def compute_official_stats(conn: sqlite3.Connection) -> list[OfficialStats]:
    """Compute home-win bias for all officials across all seasons."""
    cursor = conn.cursor()

    # Get all officials with enough games (all types: referees and linesmen)
    cursor.execute(
        """
        SELECT
            go.person_id,
            COUNT(*) as games_count,
            SUM(CASE WHEN g.home_team_score > g.away_team_score THEN 1 ELSE 0 END) as home_wins
        FROM gameofficial go
        JOIN gamedata g ON go.game_id = g.game_id
        WHERE g.game_status LIKE 'Final%'
        GROUP BY go.person_id
        HAVING COUNT(*) >= ?
        """,
        (MIN_OFFICIAL_GAMES,),
    )

    results = cursor.fetchall()
    stats = []
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    for row in results:
        person_id = row["person_id"]
        games_count = row["games_count"]
        home_wins = row["home_wins"]
        home_win_pct = (home_wins / games_count) if games_count > 0 else 0.5

        stats.append(
            OfficialStats(
                person_id=person_id,
                home_win_pct=home_win_pct,
                games_officiated=games_count,
                computed_at=timestamp,
            )
        )

    return stats


def save_team_stats(conn: sqlite3.Connection, stats: list[TeamStats]) -> int:
    """Save team stats to database, replacing old stats for the same (team, season)."""
    cursor = conn.cursor()
    count = 0

    for stat in stats:
        cursor.execute(
            """
            INSERT OR REPLACE INTO mc_team_stats
            (team_id, season_id, attack_rate, defense_rate, so_win_rate, games_used, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stat.team_id,
                stat.season_id,
                stat.attack_rate,
                stat.defense_rate,
                stat.so_win_rate,
                stat.games_used,
                stat.computed_at,
            ),
        )
        count += 1

    conn.commit()
    return count


def save_official_stats(conn: sqlite3.Connection, stats: list[OfficialStats]) -> int:
    """Save official stats to database, replacing old stats."""
    cursor = conn.cursor()
    count = 0

    for stat in stats:
        cursor.execute(
            """
            INSERT OR REPLACE INTO mc_official_stats
            (person_id, home_win_pct, games_officiated, computed_at)
            VALUES (?, ?, ?, ?)
            """,
            (stat.person_id, stat.home_win_pct, stat.games_officiated, stat.computed_at),
        )
        count += 1

    conn.commit()
    return count


@click.group()
def cli():
    """Monte Carlo prediction stats trainer."""
    pass


@cli.command()
def init():
    """Initialize MC prediction tables."""
    conn = get_db_connection()
    try:
        init_tables(conn)
    finally:
        conn.close()


@cli.command()
@click.option(
    "--season-id",
    type=int,
    default=90,
    help="Season ID to train (default: 90)",
)
@click.option(
    "--lookback",
    type=int,
    default=20,
    help="Number of recent games to consider (default: 20)",
)
@click.option(
    "--decay-rate",
    type=float,
    default=0.1,
    help="Exponential decay rate for recency weighting (default: 0.1)",
)
def train(season_id: int, lookback: int, decay_rate: float):
    """Train team and official stats."""
    conn = get_db_connection()
    try:
        # Compute team stats
        console.print(f"\n[cyan]Computing team stats for season {season_id}...[/cyan]")
        team_stats = compute_team_stats(conn, season_id, lookback, decay_rate)
        team_count = save_team_stats(conn, team_stats)
        console.print(f"[green]✓ Saved {team_count} team stats[/green]")

        # Compute official stats
        console.print("\n[cyan]Computing official stats (all seasons)...[/cyan]")
        official_stats = compute_official_stats(conn)
        official_count = save_official_stats(conn, official_stats)
        console.print(f"[green]✓ Saved {official_count} official stats[/green]")

        console.print(
            Panel(
                f"[green]Training complete[/green]\n"
                f"Teams: {team_count}\n"
                f"Officials: {official_count}",
                title="Summary",
            )
        )
    finally:
        conn.close()


@cli.command()
def status():
    """Show stats retraining status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check team stats
        cursor.execute(
            """
            SELECT season_id, COUNT(*) as team_count, MAX(computed_at) as latest
            FROM mc_team_stats
            GROUP BY season_id
            ORDER BY season_id DESC
            LIMIT 5
            """
        )
        team_results = cursor.fetchall()

        # Check official stats
        cursor.execute(
            """
            SELECT COUNT(*) as official_count, MAX(computed_at) as latest
            FROM mc_official_stats
            """
        )
        official_result = cursor.fetchone()

        # Display
        if team_results:
            table = Table(title="Team Stats by Season")
            table.add_column("Season", style="cyan")
            table.add_column("Teams", style="magenta")
            table.add_column("Latest Update", style="green")

            for row in team_results:
                latest = row["latest"]
                # Parse ISO datetime with Z suffix as UTC
                age = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                # Compare with timezone-aware UTC now
                now = datetime.now(UTC)
                hours_ago = (now - age).total_seconds() / 3600
                age_str = f"{hours_ago:.1f}h ago" if hours_ago < 24 else f"{hours_ago/24:.1f}d ago"

                table.add_row(str(row["season_id"]), str(row["team_count"]), age_str)

            console.print(table)
        else:
            console.print("[yellow]No team stats found. Run 'retrain train' first.[/yellow]")

        if official_result and official_result["official_count"]:
            console.print("\n[cyan]Official Stats:[/cyan]")
            console.print(f"  Officials: {official_result['official_count']}")
            latest = official_result["latest"]
            # Parse ISO datetime with Z suffix as UTC
            age = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            # Compare with timezone-aware UTC now
            now = datetime.now(UTC)
            hours_ago = (now - age).total_seconds() / 3600
            age_str = f"{hours_ago:.1f}h ago" if hours_ago < 24 else f"{hours_ago/24:.1f}d ago"
            console.print(f"  Latest Update: {age_str}")
        else:
            console.print("[yellow]No official stats found.[/yellow]")

    finally:
        conn.close()


if __name__ == "__main__":
    cli()
