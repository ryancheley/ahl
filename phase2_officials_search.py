#!/usr/bin/env python3
"""
Phase 2: Officials Data Search
Searching for officials information in all available API endpoints
"""

import requests
import json
from typing import Dict, Any

API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"
SEASON_ID = 90
TEST_GAME_ID = 1027888

BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def find_officials_in_data(data: Dict[Any, Any], path: str = "") -> list:
    """Recursively search data structure for officials-related fields."""
    officials_fields = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # Check if key mentions officials, referee, linesman, etc.
            key_lower = key.lower()
            if any(term in key_lower for term in ['official', 'referee', 'linesman', 'ref', 'lines']):
                officials_fields.append((current_path, value))

            # Recurse if value is dict or list
            if isinstance(value, dict):
                officials_fields.extend(find_officials_in_data(value, current_path))
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                officials_fields.extend(find_officials_in_data(value[0], current_path))

    return officials_fields

def search_endpoint(name: str, params: dict) -> None:
    """Search endpoint for officials data."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}Searching: {name}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = json.loads(response.text)

        officials = find_officials_in_data(data)

        if officials:
            print(f"{GREEN}✓ Found {len(officials)} official-related field(s):{RESET}\n")
            for path, value in officials:
                print(f"  Path: {path}")
                if isinstance(value, dict):
                    print(f"  Value type: dict with keys {list(value.keys())[:10]}")
                    print(f"  Sample: {json.dumps(value, indent=4)[:500]}")
                elif isinstance(value, list):
                    print(f"  Value type: list with {len(value)} items")
                    if len(value) > 0 and isinstance(value[0], dict):
                        print(f"  First item: {json.dumps(value[0], indent=4)[:500]}")
                else:
                    print(f"  Value: {value}")
                print()
        else:
            print(f"{RED}✗ No official-related fields found{RESET}\n")

        # Show available top-level keys for reference
        top_level = list(data.keys())
        print(f"{BOLD}Top-level keys in response: {top_level}{RESET}\n")

    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

def main():
    print(f"\n{BOLD}{YELLOW}PHASE 2: OFFICIALS DATA SEARCH{RESET}")
    print(f"Searching all endpoints for officials information\n")

    # Test 1: GC Game Summary
    search_endpoint(
        "GC Feed - GameSummary",
        {
            'feed': 'gc',
            'tab': 'gamesummary',
            'game_id': str(TEST_GAME_ID),
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
        }
    )

    # Test 2: GC PXP (non-verbose)
    search_endpoint(
        "GC Feed - PXP (non-verbose)",
        {
            'feed': 'gc',
            'tab': 'pxp',
            'game_id': str(TEST_GAME_ID),
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
        }
    )

    # Test 3: GC Preview (for pre-game officials)
    search_endpoint(
        "GC Feed - Preview",
        {
            'feed': 'gc',
            'tab': 'preview',
            'game_id': str(TEST_GAME_ID),
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
        }
    )

    # Test 4: StatViewFeed - Schedule (game-level data)
    search_endpoint(
        "StatViewFeed - Schedule",
        {
            'feed': 'statviewfeed',
            'view': 'schedule',
            'team': 'all',
            'season': str(SEASON_ID),
            'month': '-1',
            'key': API_KEY,
            'client_code': CLIENT_CODE,
        }
    )

    print(f"\n{BOLD}{YELLOW}{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}{RESET}")
    print(f"""
If officials data is NOT found in any endpoint:
- May need to keep HTML scraping ONLY for officials
- Or find alternative endpoint/view combination
- Consider hybrid approach: API for 95% + HTML for officials only

If officials data IS found:
- Can implement 100% API-based solution
- No HTML scraping needed
- All data from clean, structured API
""")

if __name__ == '__main__':
    main()
