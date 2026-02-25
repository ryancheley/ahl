#!/usr/bin/env python3
"""
Phase 3 Validation: Compare API-based vs HTML-based scraping

Compares results from scraper_api.py (new API approach)
with data already in the database (HTML scraping results)
to validate accuracy and completeness.
"""

import sqlite3
from scraper_api import APIGameScraper

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def fetch_database_goals(game_id: int, db_path: str = 'games_new.db') -> int:
    """Get number of goals from database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM goals WHERE game_id = ?', (game_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except sqlite3.OperationalError:
        return 0

def fetch_database_penalties(game_id: int, db_path: str = 'games_new.db') -> int:
    """Get number of penalties from database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM penalties WHERE game_id = ?', (game_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except sqlite3.OperationalError:
        return 0

def fetch_database_officials(game_id: int, db_path: str = 'games_new.db') -> int:
    """Get number of officials from database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM officials WHERE game_id = ?', (game_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except sqlite3.OperationalError:
        return 0

def compare_game(game_id: int):
    """Compare API scraping results with database."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}Comparing Game {game_id}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    # Scrape using API
    scraper = APIGameScraper()
    api_data = scraper.scrape_game(game_id)

    if not api_data:
        print(f"{RED}✗ Failed to scrape via API{RESET}")
        return False

    # Get data from database
    db_goals = fetch_database_goals(game_id)
    db_penalties = fetch_database_penalties(game_id)
    db_officials = fetch_database_officials(game_id)

    # Compare
    print(f"\n{BOLD}Comparison Results:{RESET}\n")

    results = []

    # Goals
    api_goal_count = len(api_data.goals)
    print(f"{BOLD}Goals:{RESET}")
    print(f"  API:      {GREEN}{api_goal_count}{RESET}")
    print(f"  Database: {db_goals}")
    if api_goal_count == db_goals:
        print(f"  {GREEN}✓ MATCH{RESET}")
        results.append(True)
    else:
        print(f"  {YELLOW}⚠ Mismatch{RESET}")
        results.append(False)

    # Penalties
    api_penalty_count = len(api_data.penalties)
    print(f"\n{BOLD}Penalties:{RESET}")
    print(f"  API:      {GREEN}{api_penalty_count}{RESET}")
    print(f"  Database: {db_penalties}")
    if api_penalty_count == db_penalties:
        print(f"  {GREEN}✓ MATCH{RESET}")
        results.append(True)
    else:
        print(f"  {YELLOW}⚠ Mismatch{RESET}")
        results.append(False)

    # Officials
    api_official_count = len(api_data.officials)
    print(f"\n{BOLD}Officials:{RESET}")
    print(f"  API:      {GREEN}{api_official_count}{RESET}")
    print(f"  Database: {db_officials}")
    if api_official_count == db_officials:
        print(f"  {GREEN}✓ MATCH{RESET}")
        results.append(True)
    else:
        print(f"  {YELLOW}⚠ Mismatch (may be expected - officials might not be in old DB){RESET}")
        results.append(False)

    # Summary
    print(f"\n{BOLD}Summary:{RESET}")
    if all(results):
        print(f"  {GREEN}✓ All checks passed!{RESET}")
    else:
        print(f"  {YELLOW}⚠ Some mismatches found{RESET}")

    return all(results)

def main():
    """Run validation tests."""
    print(f"\n{BOLD}{YELLOW}PHASE 3: VALIDATION TEST{RESET}")
    print(f"{YELLOW}Comparing API vs HTML scraping results{RESET}")

    # Test with multiple games
    test_games = [
        1027888,  # Known good game with complete data
        1027887,  # Another game for variety
        1027886,  # Third game for confidence
    ]

    results = []
    for game_id in test_games:
        result = compare_game(game_id)
        results.append((game_id, result))

    # Overall summary
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}VALIDATION SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for game_id, result in results:
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"Game {game_id}: {status}")

    print(f"\nTotal: {passed}/{total} games passed")

    if passed == total:
        print(f"\n{GREEN}✓ All validation tests passed!{RESET}")
        print(f"{GREEN}API-based scraper is ready for production.{RESET}")
    else:
        print(f"\n{YELLOW}⚠ Some tests failed - review mismatches above{RESET}")

if __name__ == '__main__':
    main()
