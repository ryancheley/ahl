#!/usr/bin/env python
"""
Game scraper CLI - Scrape AHL game data from hockeytech

Usage:
    python scrape_games.py single <game_id>
    python scrape_games.py range <start_id> <num_games>
    python scrape_games.py list <game_id1> <game_id2> ...
    python scrape_games.py season <season_id>
"""

import sys
import argparse
from scrapper import scrape_game_id_range
import sqlite3
from typing import List


def scrape_single(game_id: int, db_path: str = "games_new.db", delay: float = 0.5) -> None:
    """Scrape a single game."""
    print(f"Scraping game {game_id}...")
    print()

    results = scrape_game_id_range(
        start_game_id=game_id,
        num_games=1,
        db_path=db_path,
        delay=delay
    )

    if results and results[0]:
        game = results[0]
        print()
        print("=" * 70)
        print(f"✓ Game {game.game_id}: {game.away_team} @ {game.home_team}")
        print(f"  Score: {game.away_score}-{game.home_score}")
        print(f"  Status: {game.game_status}")
        print(f"  Date: {game.game_date}")
        print(f"  Goals: {len(game.goals)}")
        print(f"  Penalties: {len(game.penalties)}")
        print("=" * 70)
    else:
        print("✗ Failed to scrape game")


def scrape_range(start_id: int, num_games: int, db_path: str = "games_new.db", delay: float = 0.5) -> None:
    """Scrape a range of consecutive games."""
    print(f"Scraping {num_games} games starting from {start_id}...")
    print()

    results = scrape_game_id_range(
        start_game_id=start_id,
        num_games=num_games,
        db_path=db_path,
        delay=delay
    )

    successful = [r for r in results if r]
    print()
    print("=" * 70)
    print(f"✓ Scraped {len(successful)}/{num_games} games")
    for game in successful:
        print(f"  {game.away_team:20s} @ {game.home_team:20s} {game.away_score}-{game.home_score}")
    print("=" * 70)


def scrape_list(game_ids: List[int], db_path: str = "games_new.db", delay: float = 0.5) -> None:
    """Scrape a list of specific (non-consecutive) games."""
    print(f"Scraping {len(game_ids)} specific games...")
    print()

    successful = 0
    failed = 0

    for game_id in game_ids:
        print(f"  Game {game_id}...", end=" ", flush=True)

        results = scrape_game_id_range(
            start_game_id=game_id,
            num_games=1,
            db_path=db_path,
            delay=delay
        )

        if results and results[0]:
            game = results[0]
            print(f"✓ {game.away_team} @ {game.home_team}")
            successful += 1
        else:
            print("✗ Failed")
            failed += 1

    print()
    print("=" * 70)
    print(f"✓ Successful: {successful}/{len(game_ids)}")
    if failed > 0:
        print(f"✗ Failed: {failed}")
    print("=" * 70)


def scrape_season_missing(season_id: int, db_path: str = "games_new.db", delay: float = 0.5) -> None:
    """Scrape all missing games from a specific season."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get games in this season that need scraping
    cursor.execute(
        "SELECT game_id FROM games_extended WHERE season_id = ? AND home_team IS NULL ORDER BY game_id",
        (season_id,)
    )
    games_to_scrape = [int(row[0]) for row in cursor.fetchall()]

    cursor.execute(
        "SELECT COUNT(*) FROM games_extended WHERE season_id = ?",
        (season_id,)
    )
    total_in_season = cursor.fetchone()[0]

    conn.close()

    if not games_to_scrape:
        print(f"Season {season_id}: All {total_in_season} games already scraped ✓")
        return

    print(f"Season {season_id}: Scraping {len(games_to_scrape)} missing games (out of {total_in_season})")
    print()

    # Process in batches
    batch_size = 30
    total_batches = (len(games_to_scrape) + batch_size - 1) // batch_size
    total_success = 0

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(games_to_scrape))

        start_id = games_to_scrape[start_idx]
        num_games = end_idx - start_idx

        print(f"  [{batch_idx+1}/{total_batches}] Batch of {num_games} from {start_id}...", end=" ", flush=True)

        try:
            results = scrape_game_id_range(
                start_game_id=start_id,
                num_games=num_games,
                db_path=db_path,
                delay=delay
            )

            success = len([r for r in results if r])
            total_success += success
            print(f"✓ {success} new")
        except Exception as e:
            print(f"✗ Error: {e}")

    print()
    print("=" * 70)
    print(f"✓ Season {season_id}: Scraped {total_success} games")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape AHL game data from hockeytech",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_games.py single 1026640
  python scrape_games.py range 1028550 10
  python scrape_games.py list 1026640 1026641 1028550
  python scrape_games.py season 70
        """
    )

    parser.add_argument("--db", default="games_new.db", help="Database path (default: games_new.db)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Single game
    single_parser = subparsers.add_parser("single", help="Scrape a single game")
    single_parser.add_argument("game_id", type=int, help="Game ID to scrape")

    # Range
    range_parser = subparsers.add_parser("range", help="Scrape a range of consecutive games")
    range_parser.add_argument("start_id", type=int, help="Starting game ID")
    range_parser.add_argument("num_games", type=int, help="Number of consecutive games to scrape")

    # List
    list_parser = subparsers.add_parser("list", help="Scrape a list of specific games")
    list_parser.add_argument("game_ids", type=int, nargs="+", help="Game IDs to scrape")

    # Season
    season_parser = subparsers.add_parser("season", help="Scrape all missing games from a season")
    season_parser.add_argument("season_id", type=int, help="Season ID to scrape")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "single":
            scrape_single(args.game_id, args.db, args.delay)
        elif args.command == "range":
            scrape_range(args.start_id, args.num_games, args.db, args.delay)
        elif args.command == "list":
            scrape_list(args.game_ids, args.db, args.delay)
        elif args.command == "season":
            scrape_season_missing(args.season_id, args.db, args.delay)
    except KeyboardInterrupt:
        print("\n\n✗ Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
