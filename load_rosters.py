#!/usr/bin/env python
"""
Load game rosters into the game_rosters table.

Usage:
    python load_rosters.py [options]

Options:
    --season SEASON_ID    Season to load rosters for (default: 90)
    --limit LIMIT         Maximum number of games to load (default: all)
    --delay DELAY         Delay between API requests in seconds (default: 0.5)
"""

import sqlite3
import time
import argparse
import sys
from typing import Optional

from player_scrapper import scrape_game_roster


def get_missing_rosters(season_id: int, limit: Optional[int] = None) -> list:
    """Get games that don't have rosters loaded yet."""
    conn = sqlite3.connect("games_new.db")
    cursor = conn.cursor()

    # Get games without rosters that have been played
    cursor.execute("""
        SELECT game_id FROM games_extended
        WHERE season_id = ?
        AND home_team IS NOT NULL
        AND game_id NOT IN (SELECT DISTINCT game_id FROM game_rosters)
        ORDER BY game_id
    """, (season_id,))

    games = [row[0] for row in cursor.fetchall()]
    conn.close()

    if limit:
        games = games[:limit]

    return games


def load_rosters(season_id: int = 90, limit: Optional[int] = None, delay: float = 0.5) -> None:
    """Load game rosters for a season."""
    games = get_missing_rosters(season_id, limit)

    if not games:
        print(f"✓ No missing rosters for season {season_id}")
        return

    print(f"Loading rosters for {len(games)} games (season {season_id})...")
    print()

    loaded = 0
    skipped = 0

    for i, game_id in enumerate(games, 1):
        try:
            entries = scrape_game_roster(game_id, "games_new.db")

            if entries:
                loaded += len(entries)
                pct = (i / len(games)) * 100
                print(f"[{i}/{len(games)} ({pct:.0f}%)] Game {game_id}: {len(entries):3d} players ({loaded:5d} total)")
            else:
                skipped += 1
                pct = (i / len(games)) * 100
                print(f"[{i}/{len(games)} ({pct:.0f}%)] Game {game_id}: (skip or no data)")

            time.sleep(delay)

        except Exception as e:
            skipped += 1
            print(f"[{i}/{len(games)}] Game {game_id}: ERROR - {e}")
            time.sleep(delay)

    print()
    print("=" * 70)
    print(f"✓ Complete!")
    print(f"  Loaded: {loaded} player rosters")
    print(f"  Skipped: {skipped} games")
    print(f"  Total games processed: {len(games)}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Load game rosters into game_rosters table")
    parser.add_argument("--season", type=int, default=90, help="Season ID to load rosters for (default: 90)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of games to load")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API requests in seconds (default: 0.5)")

    args = parser.parse_args()

    try:
        load_rosters(season_id=args.season, limit=args.limit, delay=args.delay)
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
