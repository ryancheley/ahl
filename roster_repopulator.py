#!/usr/bin/env python3
"""
Game Roster Repopulator

Repopulates game_rosters table with roster data from the API scraper.
This ensures we have complete team rosters for all games.

Features:
- Batch processing with progress tracking
- Database backup before starting
- Error handling and recovery
- Transaction management
- Performance metrics

Usage:
    python roster_repopulator.py              # Repopulate all rosters
    python roster_repopulator.py --limit 100  # Repopulate first 100 games
"""

import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from player_scrapper import scrape_game_roster

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


class RosterRepopulator:
    """Repopulates game roster database with fresh API data."""

    def __init__(self, db_path: str = DB_PATH):
        """Initialize repopulator."""
        self.db_path = db_path
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
            import shutil
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

    def get_game_ids(self) -> list:
        """Get list of game IDs to repopulate."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all game IDs from games_extended
            cursor.execute(
                'SELECT DISTINCT game_id FROM games_extended ORDER BY game_id'
            )

            game_ids = [str(row[0]) for row in cursor.fetchall()]
            conn.close()

            return game_ids

        except Exception as e:
            print(f"{RED}Error fetching game IDs: {e}{RESET}")
            return []

    def repopulate_rosters(self, game_ids: list) -> None:
        """Repopulate all game rosters with fresh API data."""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}Starting Roster Repopulation{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        self.stats['total'] = len(game_ids)
        self.stats['start_time'] = datetime.now()

        print(f"Total games to process: {self.stats['total']}")
        print(f"Processing rosters for each game...\n")

        for idx, game_id in enumerate(game_ids, start=1):
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
                # Scrape roster data
                entries = scrape_game_roster(game_id, self.db_path)

                if entries:
                    self.stats['successful'] += 1
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
            print(f"\n{GREEN}✓ ALL ROSTERS SUCCESSFULLY REPOPULATED!{RESET}")
        else:
            completion = (self.stats['successful'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
            print(f"\n{YELLOW}⚠ Completion: {completion:.1f}%{RESET}")

    def run(self, limit: int = None) -> None:
        """Run the complete repopulation process."""
        print(f"\n{CYAN}{BOLD}{'='*70}")
        print("AHL GAME ROSTER REPOPULATOR")
        print(f"{'='*70}{RESET}\n")

        # Backup database
        if not self.backup_database():
            print(f"{RED}Backup failed. Aborting.{RESET}")
            return

        # Get game IDs
        print(f"Fetching game IDs from database...")
        game_ids = self.get_game_ids()

        if not game_ids:
            print(f"{RED}No games found to repopulate.{RESET}")
            return

        print(f"{GREEN}✓ Found {len(game_ids)} games to process{RESET}\n")

        # Apply limit if specified
        if limit:
            game_ids = game_ids[:limit]
            print(f"Limited to first {limit} games\n")

        # Repopulate
        try:
            self.repopulate_rosters(game_ids)
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Repopulation interrupted by user.{RESET}")
            self.print_summary()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Repopulate game_rosters table with fresh roster data'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit to first N games'
    )

    args = parser.parse_args()

    repopulator = RosterRepopulator()
    repopulator.run(limit=args.limit)


if __name__ == '__main__':
    main()
