"""
Game Details API Discovery - Testing both JSON APIs and alternative approaches.

Key Finding: statviewfeed endpoint only supports 'roster' view for games (returns team rosters).
Now testing if:
1. There's an alternative JSON API for game details
2. If we need to scrape HTML game reports
3. If the game details are accessible through a different API endpoint
"""

import requests
import json
import re
from typing import Dict, Any, Optional
import time

TEST_GAME_ID = 1027888
API_KEY = "ccb91f29d6744675"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}


def test_json_endpoints():
    """Test various JSON endpoints"""
    print("\n" + "=" * 100)
    print("SECTION 1: JSON ENDPOINTS")
    print("=" * 100)

    endpoints = [
        # Statviewfeed with different paths
        f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id={TEST_GAME_ID}&season_id=90&site_id=3&key={API_KEY}&client_code=ahl&league_id=4&lang=1",

        # Try with older/alternative API URLs
        f"https://lscluster.hockeytech.com/statviewfeed?view=game&game_id={TEST_GAME_ID}",

        # Direct statviewfeed
        f"https://lscluster.hockeytech.com/statviewfeed/game/{TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/statviewfeed/game/{TEST_GAME_ID}.json",

        # Alternative API patterns
        f"https://lscluster.hockeytech.com/api/games/{TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/api/games/{TEST_GAME_ID}/details",
        f"https://lscluster.hockeytech.com/api/game/{TEST_GAME_ID}",

        # Try theahl.com (actual public site)
        f"https://theahl.com/api/games/{TEST_GAME_ID}",
        f"https://theahl.com/api/v1/games/{TEST_GAME_ID}",

        # Try more specific game data URLs
        f"https://lscluster.hockeytech.com/game_reports/data.json?game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/game_reports/game_data.json?game_id={TEST_GAME_ID}",
    ]

    print("\nTesting JSON endpoints:\n")

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=HEADERS, timeout=5)
            status = response.status_code
            content = response.text[:150]

            # Determine if it's likely JSON
            is_json = content.strip().startswith(('{', '['))
            indicator = "✓ JSON" if is_json else "  HTML/Text"

            endpoint_short = endpoint.split('?')[0].split('/')[-1] or endpoint.split('/')[-2]
            print(f"[{status:3}] {endpoint_short:35} {indicator}")

            if status == 200 and is_json:
                try:
                    data = json.loads(response.text)
                    if isinstance(data, dict):
                        keys = list(data.keys())[:3]
                        print(f"      Keys: {keys}")
                except:
                    pass
        except Exception as e:
            print(f"[ERR] {endpoint.split('?')[0].split('/')[-1]:35} {str(e)[:50]}")

        time.sleep(0.2)


def test_html_endpoints():
    """Test HTML endpoints that we can scrape"""
    print("\n" + "=" * 100)
    print("SECTION 2: HTML ENDPOINTS (Scrapeable)")
    print("=" * 100)

    endpoints = [
        (f"https://lscluster.hockeytech.com/game_reports/official-game-report.php?client_code=ahl&game_id={TEST_GAME_ID}", "Official Game Report"),
        (f"https://lscluster.hockeytech.com/game_reports/text-game-report.php?client_code=ahl&game_id={TEST_GAME_ID}", "Text Game Report"),
        (f"https://theahl.com/stats/game-center/{TEST_GAME_ID}", "AHL Game Center"),
    ]

    print("\nTesting HTML endpoints:\n")

    for endpoint, name in endpoints:
        try:
            response = requests.get(endpoint, headers=HEADERS, timeout=5)
            status = response.status_code
            length = len(response.text)

            # Look for key data patterns in HTML
            has_goals = "goal" in response.text.lower()
            has_penalties = "penalty" in response.text.lower()
            has_officials = "official" in response.text.lower()

            indicators = []
            if has_goals:
                indicators.append("goals")
            if has_penalties:
                indicators.append("penalties")
            if has_officials:
                indicators.append("officials")

            ind_str = f"({', '.join(indicators)})" if indicators else "(no key data)"

            print(f"[{status:3}] {name:30} {length:6} bytes {ind_str}")

        except Exception as e:
            print(f"[ERR] {name:30} {str(e)[:50]}")

        time.sleep(0.3)


def test_direct_scraping():
    """Test if we can extract game details from official game report"""
    print("\n" + "=" * 100)
    print("SECTION 3: DIRECT HTML SCRAPING TEST")
    print("=" * 100)

    url = f"https://lscluster.hockeytech.com/game_reports/official-game-report.php?client_code=ahl&game_id={TEST_GAME_ID}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            html = response.text

            # Look for common HTML patterns in game reports
            patterns = {
                "Goals": r"<[^>]*>Goal[s]?<[^>]*>|goal_id|scorer|period.*time",
                "Penalties": r"<[^>]*>Penalt[y|ies]<[^>]*>|penalty|minor|major",
                "Officials": r"<[^>]*>Official[s]?<[^>]*>|referee|linesman",
                "Teams": r"<[^>]*>Team[s]?<[^>]*>|home.*away|final.*score",
            }

            print("\nSearching for data patterns in HTML:\n")

            for category, pattern in patterns.items():
                matches = len(re.findall(pattern, html, re.IGNORECASE))
                print(f"{category:15}: {matches:3} matches")

                # Show sample match if found
                if matches > 0:
                    sample = re.search(pattern, html, re.IGNORECASE)
                    if sample:
                        preview = sample.group(0)[:60]
                        print(f"                Sample: {preview}")

            # Look for JSON data embedded in HTML
            print("\nSearching for embedded JSON in HTML:")

            json_patterns = [
                r'<script[^>]*>var\s+(\w+)\s*=\s*(\{[^<]+\})',
                r'<script[^>]*type="application/json"[^>]*>([^<]+)</script>',
                r'data-.*?=\'(.*?)\'',
            ]

            found_json = False
            for pattern in json_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    print(f"  Found {len(matches)} potential JSON data blocks")
                    found_json = True

            if not found_json:
                print("  No embedded JSON found")

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all tests"""
    print("GAME DETAILS API DISCOVERY")
    print("Testing game ID:", TEST_GAME_ID)
    print("=" * 100)

    test_json_endpoints()
    test_html_endpoints()
    test_direct_scraping()

    print("\n" + "=" * 100)
    print("CONCLUSIONS")
    print("=" * 100)
    print("""
Current findings:
1. statviewfeed endpoint ONLY supports 'roster' view for games
   - Returns team rosters with player information
   - Does NOT include goals, penalties, or officials

2. No dedicated JSON API found for detailed game data
   - Official game reports are HTML pages
   - Data may need to be extracted via HTML scraping

3. Options for getting game details:
   a) HTML scraping from /game_reports/official-game-report.php
   b) Check if theahl.com has a public JSON API
   c) Use program.py's existing HTML parsing approach
    """)


if __name__ == "__main__":
    main()
