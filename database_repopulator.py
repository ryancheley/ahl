#!/usr/bin/env python3
"""
Database Repopulator

Repopulates games_new.db with fresh data from the API scraper.
This ensures complete and accurate game data including overtime goals.

Features:
- Batch processing with progress tracking
- Database backup before starting
- Error handling and recovery
- Transaction management
- Performance metrics

Usage:
    python database_repopulator.py              # Refresh all games
    python database_repopulator.py --season 90  # Refresh season 90 only
    python database_repopulator.py --limit 100  # Refresh first 100 games
"""

import sqlite3
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path
from scraper_api import APIGameScraper

# Configuration
DB_PATH = 'games_new.db'
BATCH_SIZE = 50  # Process this many games before committing
PROGRESS_INTERVAL = 10  # Print progress every N games

# Colors for terminal output
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


class DatabaseRepopulator:
    """Repopulates game database with fresh API data."""

    def __init__(self, db_path: str = DB_PATH):
        """Initialize repopulator."""
        self.db_path = db_path
        self.scraper = APIGameScraper(db_path)
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None,
        }

    def backup_database(self) -> bool:
        """Create backup of database before repopulation."""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}Creating Database Backup{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.db_path}.backup_{timestamp}"

            print(f"Backing up to: {backup_path}")
            shutil.copy2(self.db_path, backup_path)

            # Verify backup
            if Path(backup_path).exists():
                print(f"{GREEN}✓ Backup created successfully{RESET}\n")
                return True
            else:
                print(f"{RED}✗ Backup failed{RESET}\n")
                return False

        except Exception as e:
            print(f"{RED}✗ Error creating backup: {e}{RESET}\n")
            return False

    def get_game_ids(self, season_id: int = None) -> list:
        """Get list of game IDs to repopulate."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if season_id:
                cursor.execute(
                    'SELECT DISTINCT game_id FROM games_extended WHERE season_id = ? ORDER BY game_id',
                    (season_id,)
                )
            else:
                cursor.execute(
                    'SELECT DISTINCT game_id FROM games_extended ORDER BY game_id'
                )

            game_ids = [row[0] for row in cursor.fetchall()]
            conn.close()

            return game_ids

        except Exception as e:
            print(f"{RED}Error fetching game IDs: {e}{RESET}")
            return []

    def clear_game_data(self, game_id: int) -> bool:
        """Clear existing data for a game before refreshing."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            # Delete existing data
            cursor.execute('DELETE FROM goals WHERE game_id = ?', (game_id,))
            cursor.execute('DELETE FROM penalties WHERE game_id = ?', (game_id,))
            cursor.execute('DELETE FROM officials WHERE game_id = ?', (game_id,))

            conn.commit()
            conn.close()
            return True

        except Exception:
            return False

    def repopulate_games(self, game_ids: list, start_index: int = 0) -> None:
        """Repopulate all games with fresh API data."""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}Starting Database Repopulation{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        self.stats['total'] = len(game_ids)
        self.stats['start_time'] = datetime.now()

        print(f"Total games to process: {self.stats['total']}")
        print(f"Starting from index: {start_index}\n")

        for idx, game_id in enumerate(game_ids[start_index:], start=start_index + 1):
            # Print progress
            if idx % PROGRESS_INTERVAL == 0 or idx == 1:
                elapsed = datetime.now() - self.stats['start_time']
                rate = idx / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
                remaining = (self.stats['total'] - idx) / rate if rate > 0 else 0
                print(
                    f"[{idx:5d}/{self.stats['total']}] "
                    f"Processing game {game_id}... "
                    f"(Rate: {rate:.1f} games/sec, ETA: {remaining/60:.1f} min)"
                )

            try:
                # Clear existing data
                self.clear_game_data(game_id)

                # Scrape fresh data
                game_data = self.scraper.scrape_game(game_id)

                if game_data:
                    # Write to database
                    if self.scraper.write_game_to_database(game_data):
                        self.stats['successful'] += 1
                    else:
                        self.stats['failed'] += 1
                        print(f"  {RED}✗ Failed to write game {game_id}{RESET}")
                else:
                    self.stats['skipped'] += 1

            except Exception as e:
                self.stats['failed'] += 1
                print(f"  {RED}✗ Error processing game {game_id}: {e}{RESET}")

        # Final summary
        self.stats['end_time'] = datetime.now()
        self.print_summary()

    def print_summary(self) -> None:
        """Print repopulation summary."""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}Repopulation Summary{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        elapsed = self.stats['end_time'] - self.stats['start_time']
        hours = elapsed.total_seconds() / 3600
        rate = self.stats['successful'] / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0

        print(f"Total Games Processed: {self.stats['total']}")
        print(f"  {GREEN}✓ Successful: {self.stats['successful']}{RESET}")
        print(f"  {RED}✗ Failed: {self.stats['failed']}{RESET}")
        print(f"  {YELLOW}⊘ Skipped: {self.stats['skipped']}{RESET}")

        print(f"\nTime Elapsed: {hours:.2f} hours ({elapsed.total_seconds():.0f} seconds)")
        print(f"Processing Rate: {rate:.2f} games/second")

        if self.stats['successful'] == self.stats['total']:
            print(f"\n{GREEN}✓ ALL GAMES SUCCESSFULLY REPOPULATED!{RESET}")
        else:
            completion = (self.stats['successful'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
            print(f"\n{YELLOW}⚠ Completion: {completion:.1f}%{RESET}")

    def run(self, season_id: int = None, limit: int = None, resume_from: int = 0) -> None:
        """Run the complete repopulation process."""
        print(f"\n{CYAN}{BOLD}{'='*70}")
        print("AHL GAME DATABASE REPOPULATOR")
        print(f"{'='*70}{RESET}\n")

        # Backup database
        if not self.backup_database():
            print(f"{RED}Backup failed. Aborting.{RESET}")
            return

        # Get game IDs
        print(f"Fetching game IDs from database...")
        game_ids = self.get_game_ids(season_id)

        if not game_ids:
            print(f"{RED}No games found to repopulate.{RESET}")
            return

        print(f"{GREEN}✓ Found {len(game_ids)} games to repopulate{RESET}\n")

        # Apply limit if specified
        if limit:
            game_ids = game_ids[:limit]
            print(f"Limited to first {limit} games\n")

        # Repopulate
        try:
            self.repopulate_games(game_ids, start_index=resume_from)
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Repopulation interrupted by user.{RESET}")
            print(f"Resume from game index {self.stats['successful']} with:")
            print(f"  python database_repopulator.py --resume {self.stats['successful']}\n")
            self.print_summary()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Repopulate games_new.db with fresh API data'
    )
    parser.add_argument(
        '--season',
        type=int,
        help='Only repopulate specific season (e.g., 90)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit to first N games'
    )
    parser.add_argument(
        '--resume',
        type=int,
        default=0,
        help='Resume from game index'
    )

    args = parser.parse_args()

    repopulator = DatabaseRepopulator()
    repopulator.run(
        season_id=args.season,
        limit=args.limit,
        resume_from=args.resume
    )


if __name__ == '__main__':
    main()
