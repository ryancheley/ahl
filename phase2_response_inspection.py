#!/usr/bin/env python3
"""
Phase 2 Investigation - Response Inspection
The gc and modulekit endpoints ARE responding with JSON,
but the responses are being truncated. Let's examine the full responses.
"""

import requests
import json
from typing import Optional

API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"
SEASON_ID = 90
SITE_ID = 3
LEAGUE_ID = 4
LANG = 1
TEST_GAME_ID = 1027888

BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"

BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"

def inspect_endpoint(name: str, params: dict):
    """Fetch and inspect full response from endpoint."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}Inspecting: {name}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.text)} bytes")
        print(f"Content-Type: {response.headers.get('content-type', 'not specified')}")

        # Try to parse as JSON
        text = response.text.strip()
        is_jsonp = text.startswith("(") and text.endswith(")")

        if is_jsonp:
            text = text[1:-1]

        try:
            data = json.loads(text)
            print(f"\n{GREEN}✓ Valid JSON{RESET}")
            print(f"Top-level keys: {list(data.keys())}")

            # Pretty print first 50 lines
            pretty = json.dumps(data, indent=2)
            lines = pretty.split('\n')[:100]
            print("\nResponse preview (first 100 lines):")
            print('\n'.join(lines))

            if len(pretty.split('\n')) > 100:
                print(f"\n... ({len(pretty.split(chr(10))) - 100} more lines)")

        except json.JSONDecodeError as e:
            print(f"{RED}✗ JSON Parse Error: {e}{RESET}")
            print(f"Raw preview: {response.text[:500]}")

    except Exception as e:
        print(f"Error: {e}")

def main():
    print(f"\n{BOLD}{YELLOW}PHASE 2 INVESTIGATION - RESPONSE INSPECTION{RESET}")
    print(f"{YELLOW}Examining full responses from endpoints{RESET}\n")

    # Test 1: GC PXP Verbose with API key
    inspect_endpoint(
        "GC Feed - PXPVerbose with API Key",
        {
            'feed': 'gc',
            'tab': 'pxpverbose',
            'game_id': str(TEST_GAME_ID),
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
        }
    )

    # Test 2: GC Game Summary
    inspect_endpoint(
        "GC Feed - GameSummary with API Key",
        {
            'feed': 'gc',
            'tab': 'gamesummary',
            'game_id': str(TEST_GAME_ID),
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
        }
    )

    # Test 3: ModuleKit Schedule
    inspect_endpoint(
        "ModuleKit - Schedule with Full Params",
        {
            'feed': 'modulekit',
            'view': 'schedule',
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
            'site_id': str(SITE_ID),
            'league_id': str(LEAGUE_ID),
            'lang': str(LANG),
        }
    )

    # Test 4: ModuleKit Standings
    inspect_endpoint(
        "ModuleKit - Standings with Full Params",
        {
            'feed': 'modulekit',
            'view': 'statviewtype',
            'type': 'standings',
            'season_id': str(SEASON_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
            'site_id': str(SITE_ID),
            'league_id': str(LEAGUE_ID),
            'lang': str(LANG),
        }
    )

    # Test 5: Verify known working endpoint for comparison
    inspect_endpoint(
        "StatViewFeed - Roster (Known Working)",
        {
            'feed': 'statviewfeed',
            'view': 'roster',
            'game_id': str(TEST_GAME_ID),
            'season_id': str(SEASON_ID),
            'site_id': str(SITE_ID),
            'key': API_KEY,
            'client_code': CLIENT_CODE,
            'league_id': str(LEAGUE_ID),
            'lang': str(LANG),
        }
    )

if __name__ == '__main__':
    main()
