"""
Script to populate the dim_team_date_point dimension table.

This dimension tracks cumulative team statistics (wins, losses, OTL, SOL, total_points)
for each team on each date, enabling year-over-year trend analysis.
"""

import sqlite3
from datetime import datetime


def populate_dim_team_date_point():
    """
    Populate the dim_team_date_point dimension table with cumulative team statistics by date.

    The dimension is built by:
    1. Getting all unique teams and dates from games
    2. Calculating cumulative wins, losses, OTL, SOL, and points for each team on each date
    3. Points are calculated as: wins * 2 + OTL * 1
    """
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()

    # Create the dim_team_date_point table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_team_date_point (
            team_id INTEGER,
            pk_date TEXT,
            wins INTEGER,
            loses INTEGER,
            otl INTEGER,
            sol INTEGER,
            total_points INTEGER,
            PRIMARY KEY (team_id, pk_date)
        )
    """)

    # Get all unique teams
    cursor.execute("""
        SELECT DISTINCT away_team FROM games
        UNION
        SELECT DISTINCT home_team FROM games
    """)
    teams = [row[0] for row in cursor.fetchall()]

    print(f"Found {len(teams)} unique teams")

    # For each team, calculate cumulative statistics by date
    for team in teams:
        print(f"Processing team: {team}")

        # Get all games for this team (both home and away), ordered by date
        cursor.execute("""
            SELECT game_date, home_team, away_team, home_team_score, away_team_score
            FROM games
            WHERE home_team = ? OR away_team = ?
            ORDER BY game_date ASC
        """, (team, team))

        games = cursor.fetchall()

        # Initialize counters
        wins = 0
        loses = 0
        otl = 0
        sol = 0
        total_points = 0

        for game_date, home_team, away_team, home_score, away_score in games:
            is_home = home_team == team
            team_score = home_score if is_home else away_score
            opponent_score = away_score if is_home else home_score

            # Determine result
            if team_score > opponent_score:
                wins += 1
                total_points += 2
            elif team_score < opponent_score:
                # Check if overtime/shootout (determined by game_status, but we'll use score difference logic)
                loses += 1
            else:
                # Tie - shouldn't happen in modern AHL but handle it
                loses += 1

            # Note: OTL and SOL distinction requires game_status which isn't reliably available
            # For now, we'll set all losses as regular losses
            # TODO: Update once game_status parsing is improved

            # Format date as TEXT for database
            date_str = game_date if isinstance(game_date, str) else datetime.fromisoformat(game_date).strftime("%Y-%m-%d %H:%M:%S")

            # Insert or update the record
            cursor.execute("""
                INSERT OR REPLACE INTO dim_team_date_point
                (team_id, pk_date, wins, loses, otl, sol, total_points)
                VALUES ((SELECT id FROM team WHERE name = ?), ?, ?, ?, ?, ?, ?)
            """, (team, date_str, wins, loses, otl, sol, total_points))

    conn.commit()
    conn.close()
    print("dim_team_date_point population complete!")


if __name__ == "__main__":
    populate_dim_team_date_point()
