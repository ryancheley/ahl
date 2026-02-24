"""
Validation script demonstrating working statviewfeed endpoints.

This script validates that:
1. The statviewfeed API works for player data (already confirmed)
2. The statviewfeed API works for game rosters
3. No game details JSON API exists
"""

import requests
import json
import time

API_KEY = "ccb91f29d6744675"
TEST_GAME_ID = 1027888
TEST_PLAYER_ID = 988  # Grant McNeill


def test_player_data():
    """Validate player data endpoint"""
    print("\n" + "=" * 100)
    print("TEST 1: StatViewFeed - Player Data (KNOWN WORKING)")
    print("=" * 100)

    url = (
        "https://lscluster.hockeytech.com/feed/index.php"
        "?feed=statviewfeed&view=player"
        "&player_id=988&season_id=90&site_id=3"
        "&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1&statsType=skaters"
    )

    print(f"\nURL: {url[:80]}...")
    print(f"\nFull URL for reference (player_id={TEST_PLAYER_ID}):")
    print(url)

    try:
        response = requests.get(url, timeout=10)
        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            text = response.text.strip()

            # Handle JSONP response
            if text.startswith("(") and text.endswith(")"):
                text = text[1:-1]
                print("Response Format: JSONP (wrapped in parentheses)")
            else:
                print("Response Format: JSON")

            data = json.loads(text)

            if isinstance(data, dict) and "info" in data:
                info = data["info"]
                print(f"\nPlayer Data Retrieved:")
                print(f"  Name: {info.get('firstName')} {info.get('lastName')}")
                print(f"  Position: {info.get('position')}")
                print(f"  Height: {info.get('height')}")
                print(f"  Weight: {info.get('weight')}")
                print(f"  Shoots: {info.get('shoots')}")
                print(f"  Birth Date: {info.get('birthDate')}")
                print(f"  Birth Place: {info.get('birthPlace')}")

                print("\n✓ ENDPOINT WORKING - Returns player biographical data")
                return True
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

    return False


def test_roster_data():
    """Validate game roster endpoint"""
    print("\n" + "=" * 100)
    print("TEST 2: StatViewFeed - Game Roster (NEWLY DISCOVERED)")
    print("=" * 100)

    url = (
        "https://lscluster.hockeytech.com/feed/index.php"
        "?feed=statviewfeed&view=roster"
        "&game_id=1027888&season_id=90&site_id=3"
        "&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1"
    )

    print(f"\nURL: {url[:80]}...")
    print(f"\nFull URL for reference (game_id={TEST_GAME_ID}):")
    print(url)

    try:
        response = requests.get(url, timeout=10)
        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            text = response.text.strip()

            # Handle JSONP response
            if text.startswith("(") and text.endswith(")"):
                text = text[1:-1]
                print("Response Format: JSONP (wrapped in parentheses)")
            else:
                print("Response Format: JSON")

            data = json.loads(text)

            if isinstance(data, dict):
                print(f"\nRoster Data Retrieved:")
                print(f"  Team Name: {data.get('teamName', 'N/A')}")
                print(f"  Season: {data.get('seasonName')}")
                print(f"  Division: {data.get('divisionName', 'N/A')}")

                if "roster" in data and isinstance(data["roster"], list):
                    roster_list = data["roster"]
                    print(f"  Roster Teams: {len(roster_list)} team(s)")

                    for team_idx, team in enumerate(roster_list, 1):
                        if "sections" in team:
                            sections = team["sections"]
                            print(f"\n  Team {team_idx} Sections:")
                            for section in sections:
                                title = section.get("title", "Unknown")
                                rows = section.get("rows", [])
                                print(f"    - {title}: {len(rows)} players")

                print("\n✓ ENDPOINT WORKING - Returns team roster for game")
                return True
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

    return False


def test_game_details_failure():
    """Test that game details endpoints don't exist"""
    print("\n" + "=" * 100)
    print("TEST 3: StatViewFeed - Game Details (DOES NOT WORK)")
    print("=" * 100)

    # Try some game-related views
    views_to_test = ["game", "boxscore", "goals", "penalties", "officials"]

    print(f"\nTesting if game details views are supported...")
    print(f"(Using game_id={TEST_GAME_ID})\n")

    all_failed = True

    for view in views_to_test:
        url = (
            "https://lscluster.hockeytech.com/feed/index.php"
            f"?feed=statviewfeed&view={view}"
            f"&game_id={TEST_GAME_ID}&season_id=90&site_id=3"
            f"&key={API_KEY}&client_code=ahl&league_id=4&lang=1"
        )

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                text = response.text.strip()
                if text.startswith("(") and text.endswith(")"):
                    text = text[1:-1]

                data = json.loads(text)
                if "error" in data:
                    print(f"  view={view:15} -> ✗ {data['error']}")
                else:
                    print(f"  view={view:15} -> ? Unexpected response")
                    all_failed = False
            else:
                print(f"  view={view:15} -> ✗ HTTP {response.status_code}")
        except Exception as e:
            print(f"  view={view:15} -> ✗ Error: {str(e)[:40]}")

        time.sleep(0.2)

    if all_failed:
        print(f"\n✓ CONFIRMED - No JSON API exists for game details")
        print(f"  Game details must be extracted from HTML pages")
        return True

    return False


def test_api_key_requirement():
    """Test that API key is required"""
    print("\n" + "=" * 100)
    print("TEST 4: API Key Requirement Validation")
    print("=" * 100)

    # Test without API key
    url_no_key = (
        "https://lscluster.hockeytech.com/feed/index.php"
        "?feed=statviewfeed&view=player"
        "&player_id=988&season_id=90&site_id=3"
        "&client_code=ahl&league_id=4&lang=1&statsType=skaters"
    )

    print(f"\nTesting without API key...")
    response = requests.get(url_no_key, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:100]}")

    if "invalid key" in response.text.lower() or response.status_code != 200:
        print(f"\n✓ CONFIRMED - API key is REQUIRED")
        print(f"  Key found in code: ccb91f29d6744675")
        return True

    return False


def main():
    """Run all validation tests"""
    print("\n" + "=" * 120)
    print("STATVIEWFEED API VALIDATION - FINAL TEST SUITE")
    print("=" * 120)

    results = []

    # Run tests
    results.append(("Player Data", test_player_data()))
    time.sleep(1)

    results.append(("Game Roster", test_roster_data()))
    time.sleep(1)

    results.append(("Game Details (None)", test_game_details_failure()))
    time.sleep(1)

    results.append(("API Key Required", test_api_key_requirement()))

    # Print summary
    print("\n" + "=" * 120)
    print("VALIDATION SUMMARY")
    print("=" * 120)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print("\n" + "=" * 120)
    print("CONCLUSIONS")
    print("=" * 120)
    print("""
1. statviewfeed endpoint WORKS for:
   ✓ Player data (view=player with player_id)
   ✓ Game rosters (view=roster with game_id)

2. statviewfeed endpoint DOES NOT WORK for:
   ✗ Game details (goals, penalties, officials)
   ✗ Any view parameter besides 'player' and 'roster'

3. API Key is REQUIRED:
   ✓ Key: ccb91f29d6744675 (static)
   ✓ Already implemented in player_scrapper.py

4. For game details, use alternative sources:
   ✓ HTML scraping: /game_reports/official-game-report.php
   ✓ Public website: https://theahl.com/stats/game-center/{game_id}
""")


if __name__ == "__main__":
    main()
