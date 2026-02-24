"""
Brute force test of /feed endpoint with all possible view and feed combinations.
"""

import requests
import time
from typing import List, Tuple

TEST_GAME_ID = 1027888

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# Common view names from sports API documentation
VIEWS = [
    # Box score related
    "BoxScore", "boxscore", "box", "box_score",
    # Game summary
    "GameSummary", "gamesummary", "game_summary", "Summary",
    # Details
    "GameDetail", "gamedetail", "game_detail", "Detail",
    "GameReport", "gamereport", "game_report", "Report",
    # Roster
    "Roster", "RosterCompare", "rostercompare", "roster_compare",
    # Stats
    "Stats", "TeamStats", "teamstats", "team_stats", "PlayerStats", "playerstats",
    # Goals
    "Goals", "GoalSummary", "goalsummary", "goal_summary", "GoalDetail", "goaldetail",
    # Penalties
    "Penalties", "PenaltySummary", "penaltysummary", "penalty_summary",
    # Officials
    "Officials", "OfficialSummary", "officialsummary", "official_summary",
    "Referees", "RefereeSummary", "refereesummary",
    # Shots
    "Shots", "ShotMap", "shotmap", "shot_map",
    # Events
    "Events", "EventSummary", "eventsummary", "event_summary",
    # Other
    "PlayByPlay", "playbyplay", "play_by_play",
    "Scoring", "scoring",
    "Discipline", "discipline",
    "Shifts", "shifts",
]

# Feed types
FEEDS = [
    None,  # No feed specified
    "statviewfeed",
    "boxscore",
    "gamescore",
    "detail",
    "summary",
    "goals",
    "penalties",
    "officials",
    "JSON",
    "JSON2",
]


def test_view_feed_combinations():
    """Test various combinations of views and feeds."""
    print("="*80)
    print("TESTING /FEED ENDPOINT COMBINATIONS")
    print(f"Test Game ID: {TEST_GAME_ID}")
    print("="*80 + "\n")

    session = requests.Session()
    session.headers.update(HEADERS)

    # Visit main site first to get cookies
    session.get("https://theahl.com/stats/", timeout=10)

    successful_endpoints = []
    errors_found = set()

    # Test combinations
    tested = 0
    for view in VIEWS:
        for feed in FEEDS:
            tested += 1
            if tested % 20 == 0:
                print(f"Tested {tested} combinations...", end="\r")

            # Build URL
            if feed:
                url = f"https://lscluster.hockeytech.com/feed?view={view}&feed={feed}&client_code=ahl&game_id={TEST_GAME_ID}"
            else:
                url = f"https://lscluster.hockeytech.com/feed?view={view}&client_code=ahl&game_id={TEST_GAME_ID}"

            try:
                response = session.get(url, timeout=5)

                # Extract response message
                error_msg = response.text.strip()[:100] if response.text else "no response"

                # Track unique error messages
                if response.status_code == 200:
                    if "Unsupported feed" in error_msg:
                        errors_found.add("Unsupported feed")
                    elif "Client access denied" in error_msg:
                        errors_found.add("Client access denied")
                    elif "Invalid key" in error_msg:
                        errors_found.add("Invalid key")
                    else:
                        # We found something different!
                        successful_endpoints.append({
                            "view": view,
                            "feed": feed,
                            "url": url,
                            "response": error_msg,
                        })
                        print(f"\n✓ INTERESTING RESPONSE: {view}/{feed}")
                        print(f"  Response: {error_msg}\n")

            except Exception as e:
                pass

            time.sleep(0.05)

    print(f"\n\nTested {tested} combinations")
    print(f"Unique errors found: {', '.join(errors_found)}")

    if successful_endpoints:
        print(f"\n✓ Found {len(successful_endpoints)} interesting endpoints:")
        for ep in successful_endpoints[:10]:
            print(f"\n  View: {ep['view']}, Feed: {ep['feed']}")
            print(f"  URL: {ep['url']}")
            print(f"  Response: {ep['response']}")


def test_json_endpoints():
    """Test if /feed supports JSON responses."""
    print("\n" + "="*80)
    print("TESTING FOR JSON SUPPORT")
    print("="*80 + "\n")

    session = requests.Session()
    session.headers.update({
        **HEADERS,
        "Accept": "application/json",
    })

    # Try with Accept header for JSON
    tests = [
        f"https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}&fmt=json",
        f"https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}&format=json",
        f"https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}&type=json",
    ]

    for url in tests:
        try:
            response = session.get(url, timeout=10)
            print(f"URL: {url.split('?')[1]}")
            print(f"  Content-Type: {response.headers.get('content-type')}")
            print(f"  Response: {response.text[:100]}")
            print()
        except Exception as e:
            print(f"  Error: {e}\n")


def test_alternative_paths():
    """Test alternative paths that might expose feed data."""
    print("\n" + "="*80)
    print("TESTING ALTERNATIVE PATHS")
    print("="*80 + "\n")

    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://theahl.com/stats/", timeout=10)

    paths = [
        f"https://lscluster.hockeytech.com/feeds/statviewfeed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed/statviewfeed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed/BoxScore?client_code=ahl&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/data/games/{TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/data/game?id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/statview?view=BoxScore&game_id={TEST_GAME_ID}",
    ]

    for url in paths:
        try:
            response = session.get(url, timeout=5)
            print(f"Status: {response.status_code} - {url.split('/')[-1]}")
            if response.status_code == 200:
                print(f"  Content: {response.text[:100]}")
        except:
            pass


if __name__ == "__main__":
    test_view_feed_combinations()
    test_json_endpoints()
    test_alternative_paths()
