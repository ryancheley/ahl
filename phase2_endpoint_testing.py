#!/usr/bin/env python3
"""
Phase 2: Deep-Dive Endpoint Testing
Tests newly discovered API endpoints from Phase 1 investigation

Tests the gc (game clock) and modulekit feeds which could provide
structured data to replace or supplement HTML scraping.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Configuration
API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"
SEASON_ID = 90
SITE_ID = 3
LEAGUE_ID = 4
LANG = 1

# Test with known good game
TEST_GAME_ID = 1027888

BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def parse_jsonp(text: str) -> Optional[Dict[Any, Any]]:
    """Strip JSONP wrapper and parse JSON."""
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def test_endpoint(
    name: str,
    params: Dict[str, str],
    description: str = ""
) -> Optional[Dict[Any, Any]]:
    """Test an API endpoint and return parsed response."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}Testing: {name}{RESET}")
    if description:
        print(f"Description: {description}")
    print(f"Endpoint: {BASE_URL}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print(f"{BLUE}{'='*70}{RESET}")

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"{RED}Error: HTTP {response.status_code}{RESET}")
            return None

        # Try to parse as JSONP
        data = parse_jsonp(response.text)

        if data is None:
            print(f"{RED}Error: Could not parse JSON response{RESET}")
            print(f"Response preview: {response.text[:200]}")
            return None

        # Check for API errors
        if "error" in data:
            print(f"{RED}API Error: {data['error']}{RESET}")
            return None

        print(f"{GREEN}✓ Success!{RESET}")

        # Show data structure
        if isinstance(data, dict):
            keys = list(data.keys())
            print(f"Response keys: {keys}")

            # Show sample of data
            for key in keys[:3]:  # First 3 keys
                value = data[key]
                if isinstance(value, dict):
                    sub_keys = list(value.keys())[:5]
                    print(f"  {key}: dict with keys {sub_keys}")
                elif isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                    if len(value) > 0 and isinstance(value[0], dict):
                        print(f"    First item keys: {list(value[0].keys())}")
                else:
                    print(f"  {key}: {type(value).__name__}")

        return data

    except requests.RequestException as e:
        print(f"{RED}Request Error: {e}{RESET}")
        return None

def main():
    """Run all Phase 2 endpoint tests."""

    print(f"\n{BOLD}{'='*70}")
    print("PHASE 2: DEEP-DIVE ENDPOINT TESTING")
    print(f"{'='*70}{RESET}")
    print(f"Test Game ID: {TEST_GAME_ID}")
    print(f"Season: {SEASON_ID}")
    print(f"Testing API endpoints discovered in Phase 1")

    results = {}

    # =====================================================
    # SECTION 1: GC FEED TESTING (HIGHEST PRIORITY)
    # =====================================================
    print(f"\n{BOLD}{YELLOW}SECTION 1: GC (GAME CLOCK) FEED TESTING{RESET}")
    print(f"{YELLOW}These endpoints could replace HTML scraping!{RESET}")

    # 1.1 GC PXP Verbose (detailed play-by-play)
    results['gc_pxpverbose'] = test_endpoint(
        "GC Feed - PXP Verbose (Detailed Play-by-Play)",
        {
            'feed': 'gc',
            'tab': 'pxpverbose',
            'game_id': TEST_GAME_ID,
            'season_id': SEASON_ID,
        },
        "Most detailed play-by-play. Should include all game events."
    )

    # 1.2 GC PXP (play-by-play)
    results['gc_pxp'] = test_endpoint(
        "GC Feed - PXP (Play-by-Play)",
        {
            'feed': 'gc',
            'tab': 'pxp',
            'game_id': TEST_GAME_ID,
            'season_id': SEASON_ID,
        },
        "Play-by-play data (might be similar to pxpverbose)"
    )

    # 1.3 GC Game Summary
    results['gc_gamesummary'] = test_endpoint(
        "GC Feed - Game Summary",
        {
            'feed': 'gc',
            'tab': 'gamesummary',
            'game_id': TEST_GAME_ID,
            'season_id': SEASON_ID,
        },
        "Final game summary with scores and stats"
    )

    # 1.4 GC Clock (live game clock)
    results['gc_clock'] = test_endpoint(
        "GC Feed - Clock (Live Game Clock)",
        {
            'feed': 'gc',
            'tab': 'clock',
            'game_id': TEST_GAME_ID,
            'season_id': SEASON_ID,
        },
        "Live game clock data (may only work for in-progress games)"
    )

    # 1.5 GC Preview
    results['gc_preview'] = test_endpoint(
        "GC Feed - Preview",
        {
            'feed': 'gc',
            'tab': 'preview',
            'game_id': TEST_GAME_ID,
            'season_id': SEASON_ID,
        },
        "Pre-game preview (may only work for future games)"
    )

    # =====================================================
    # SECTION 2: MODULEKIT FEED TESTING
    # =====================================================
    print(f"\n{BOLD}{YELLOW}SECTION 2: MODULEKIT FEED TESTING{RESET}")

    # 2.1 ModuleKit Schedule
    results['modulekit_schedule'] = test_endpoint(
        "ModuleKit Feed - Schedule",
        {
            'feed': 'modulekit',
            'view': 'schedule',
            'season_id': SEASON_ID,
        },
        "Complete season schedule"
    )

    # 2.2 ModuleKit Games Per Day
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    results['modulekit_gamesperday'] = test_endpoint(
        "ModuleKit Feed - Games Per Day",
        {
            'feed': 'modulekit',
            'view': 'gamesperday',
            'start_date': yesterday,
            'end_date': tomorrow,
        },
        f"Games between {yesterday} and {tomorrow}"
    )

    # 2.3 ModuleKit Standings
    results['modulekit_standings'] = test_endpoint(
        "ModuleKit Feed - Standings",
        {
            'feed': 'modulekit',
            'view': 'statviewtype',
            'type': 'standings',
            'season_id': SEASON_ID,
        },
        "League standings"
    )

    # 2.4 ModuleKit Top Scorers
    results['modulekit_topscorers'] = test_endpoint(
        "ModuleKit Feed - Top Scorers",
        {
            'feed': 'modulekit',
            'view': 'statviewtype',
            'type': 'topscorers',
            'season_id': SEASON_ID,
        },
        "Top goal scorers"
    )

    # 2.5 ModuleKit Seasons
    results['modulekit_seasons'] = test_endpoint(
        "ModuleKit Feed - Seasons",
        {
            'feed': 'modulekit',
            'view': 'seasons',
        },
        "All available seasons"
    )

    # =====================================================
    # SECTION 3: DOMAIN STRUCTURE ENUMERATION
    # =====================================================
    print(f"\n{BOLD}{YELLOW}SECTION 3: DOMAIN STRUCTURE ENUMERATION{RESET}")

    domain_tests = [
        ('robots.txt', 'https://lscluster.hockeytech.com/robots.txt'),
        ('sitemap.xml', 'https://lscluster.hockeytech.com/sitemap.xml'),
        ('/api/docs', 'https://lscluster.hockeytech.com/api/docs'),
        ('/swagger', 'https://lscluster.hockeytech.com/swagger'),
        ('/.well-known/', 'https://lscluster.hockeytech.com/.well-known/'),
    ]

    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}Testing Domain Structure{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    for name, url in domain_tests:
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            status = response.status_code
            if status == 200:
                print(f"{GREEN}✓{RESET} {name}: {status}")
            else:
                print(f"{RED}✗{RESET} {name}: {status}")
        except requests.RequestException as e:
            print(f"{RED}✗{RESET} {name}: Error ({type(e).__name__})")

    # =====================================================
    # SUMMARY
    # =====================================================
    print(f"\n{BOLD}{YELLOW}{'='*70}")
    print("PHASE 2 RESULTS SUMMARY")
    print(f"{'='*70}{RESET}")

    successful = sum(1 for v in results.values() if v is not None)
    total = len(results)

    print(f"\nEndpoints Tested: {total}")
    print(f"Successful: {GREEN}{successful}{RESET}")
    print(f"Failed: {RED}{total - successful}{RESET}")

    print(f"\n{BOLD}Successful Endpoints:{RESET}")
    for name, data in results.items():
        if data is not None:
            print(f"  {GREEN}✓{RESET} {name}")

    print(f"\n{BOLD}Failed Endpoints:{RESET}")
    for name, data in results.items():
        if data is None:
            print(f"  {RED}✗{RESET} {name}")

    # =====================================================
    # KEY FINDINGS
    # =====================================================
    print(f"\n{BOLD}{YELLOW}{'='*70}")
    print("KEY FINDINGS")
    print(f"{'='*70}{RESET}")

    if results['gc_pxpverbose']:
        print(f"{GREEN}✓ GC/PXPVerbose Works!{RESET} - Play-by-play data available")
        print("  This could potentially replace HTML scraping!")

    if results['gc_gamesummary']:
        print(f"{GREEN}✓ GC/GameSummary Works!{RESET} - Final game data available")

    if results['modulekit_schedule']:
        print(f"{GREEN}✓ ModuleKit/Schedule Works!{RESET} - Season schedule available")

    if results['modulekit_seasons']:
        print(f"{GREEN}✓ ModuleKit/Seasons Works!{RESET} - All seasons available")

    # Save results to JSON
    output_file = 'phase2_results.json'
    with open(output_file, 'w') as f:
        # Convert any dict results to string representation for JSON serialization
        json_results = {}
        for key, data in results.items():
            if data is not None:
                json_results[key] = {
                    'status': 'success',
                    'keys': list(data.keys()) if isinstance(data, dict) else 'unknown'
                }
            else:
                json_results[key] = {'status': 'failed'}

        json.dump(json_results, f, indent=2)

    print(f"\n{BLUE}Results saved to: {output_file}{RESET}")
    print(f"\n{BOLD}Next Steps:{RESET}")
    print("1. Review results in phase2_results.json")
    print("2. If gc/pxpverbose works, analyze the complete data structure")
    print("3. Compare against HTML-scraped data to assess completeness")
    print("4. Decide if implementation should switch to API for game details")

if __name__ == '__main__':
    main()
