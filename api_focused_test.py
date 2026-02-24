"""
Focused HockeyTech API testing targeting the most likely endpoints.
Tests specific patterns known to work in similar sports data APIs.
"""

import requests
import json
import time
from typing import Dict, Any

TEST_GAME_ID = 1027888

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

def test_endpoint(url: str, description: str = "") -> Dict[str, Any]:
    """Test a single endpoint and return findings."""
    result = {
        "url": url,
        "description": description,
        "status": None,
        "content_type": None,
        "is_json": False,
        "has_data": False,
        "data_keys": [],
        "response_preview": None,
        "error": None,
    }

    try:
        print(f"Testing: {description or url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        result["status"] = response.status_code

        if response.status_code == 200:
            result["content_type"] = response.headers.get("content-type", "unknown")

            # Try JSON parsing
            try:
                data = response.json()
                result["is_json"] = True
                result["has_data"] = bool(data)
                if isinstance(data, dict):
                    result["data_keys"] = list(data.keys())[:10]
                result["response_preview"] = json.dumps(data, indent=2)[:500]
            except:
                result["response_preview"] = response.text[:500]

        time.sleep(0.5)

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    """Test focused set of endpoints."""

    print("="*80)
    print("FOCUSED HOCKEYTECH API INVESTIGATION")
    print(f"Test Game ID: {TEST_GAME_ID}")
    print("="*80 + "\n")

    results = []

    # ===== PATTERN 1: Direct statviewfeed with different views =====
    print("\n[PATTERN 1] StatViewFeed with various views")
    print("-" * 80)

    statviewfeed_tests = [
        ("https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&client_code=ahl&game_id=1027888",
         "StatViewFeed BoxScore"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=RosterCompare&client_code=ahl&game_id=1027888",
         "StatViewFeed RosterCompare"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=GameSummary&client_code=ahl&game_id=1027888",
         "StatViewFeed GameSummary"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=GoalSummary&client_code=ahl&game_id=1027888",
         "StatViewFeed GoalSummary"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=PenaltySummary&client_code=ahl&game_id=1027888",
         "StatViewFeed PenaltySummary"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=OfficialSummary&client_code=ahl&game_id=1027888",
         "StatViewFeed OfficialSummary"),
    ]

    for url, desc in statviewfeed_tests:
        result = test_endpoint(url, desc)
        results.append(result)
        if result["status"] == 200:
            print(f"  ✓ {desc}: {result['content_type']}")
            if result["data_keys"]:
                print(f"    Keys: {', '.join(result['data_keys'][:5])}")
        else:
            print(f"  ✗ {desc}: {result['status']}")

    # ===== PATTERN 2: Different base paths with feed parameter =====
    print("\n[PATTERN 2] Different base paths with feed parameter")
    print("-" * 80)

    feed_tests = [
        ("https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id=1027888&feed=statviewfeed",
         "Feed: StatViewFeed"),
        ("https://lscluster.hockeytech.com/feed?view=goals&client_code=ahl&game_id=1027888",
         "Feed: goals view"),
        ("https://lscluster.hockeytech.com/feed?view=penalties&client_code=ahl&game_id=1027888",
         "Feed: penalties view"),
        ("https://lscluster.hockeytech.com/api?view=BoxScore&client_code=ahl&game_id=1027888",
         "API: BoxScore"),
        ("https://lscluster.hockeytech.com/api/game?client_code=ahl&game_id=1027888",
         "API: game endpoint"),
    ]

    for url, desc in feed_tests:
        result = test_endpoint(url, desc)
        results.append(result)
        if result["status"] == 200:
            print(f"  ✓ {desc}: {result['content_type']}")
        else:
            print(f"  ✗ {desc}: {result.get('status', 'error')}")

    # ===== PATTERN 3: REST-style endpoints =====
    print("\n[PATTERN 3] REST-style endpoints")
    print("-" * 80)

    rest_tests = [
        ("https://lscluster.hockeytech.com/api/v1/games/1027888",
         "API v1: /games/{id}"),
        ("https://lscluster.hockeytech.com/api/v1/games/1027888/goals",
         "API v1: /games/{id}/goals"),
        ("https://lscluster.hockeytech.com/api/v1/games/1027888/penalties",
         "API v1: /games/{id}/penalties"),
        ("https://lscluster.hockeytech.com/api/v1/games/1027888/officials",
         "API v1: /games/{id}/officials"),
        ("https://api.theahl.com/v1/games/1027888",
         "AHL API v1: /games/{id}"),
        ("https://api.theahl.com/v1/games/1027888/goals",
         "AHL API v1: /games/{id}/goals"),
    ]

    for url, desc in rest_tests:
        result = test_endpoint(url, desc)
        results.append(result)
        if result["status"] == 200:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc}: {result.get('status', 'error')}")

    # ===== PATTERN 4: Query parameter variations on known endpoint =====
    print("\n[PATTERN 4] Query parameter variations on known endpoint")
    print("-" * 80)

    base_url = "https://lscluster.hockeytech.com/game_reports/official-game-report.php"
    param_tests = [
        (f"{base_url}?client_code=ahl&game_id=1027888&lang_id=1&format=json",
         "Add format=json"),
        (f"{base_url}?client_code=ahl&game_id=1027888&lang_id=1&details=full",
         "Add details=full"),
        (f"{base_url}?client_code=ahl&game_id=1027888&lang_id=1&view=goals",
         "Add view=goals"),
        (f"{base_url}?client_code=ahl&game_id=1027888&lang_id=1&include=goals,penalties,officials",
         "Add include=goals,penalties,officials"),
        (f"{base_url}?client_code=ahl&game_id=1027888&lang_id=1&api=true",
         "Add api=true"),
    ]

    for url, desc in param_tests:
        result = test_endpoint(url, desc)
        results.append(result)
        if result["status"] == 200:
            print(f"  ✓ {desc}: {result['content_type']}")
            if result["is_json"]:
                print(f"    Keys: {', '.join(result['data_keys'][:5])}")
        else:
            print(f"  ✗ {desc}: {result.get('status', 'error')}")

    # ===== PATTERN 5: theahl.com specific endpoints =====
    print("\n[PATTERN 5] TheAHL.com specific endpoints")
    print("-" * 80)

    theahl_tests = [
        ("https://theahl.com/stats/game-center/1027888",
         "Game Center page"),
        ("https://theahl.com/api/stats/game-center/1027888",
         "API: game-center"),
        ("https://theahl.com/api/game/1027888",
         "API: game"),
        ("https://theahl.com/api/game/1027888/details",
         "API: game details"),
        ("https://theahl.com/api/game/1027888/goals",
         "API: game goals"),
    ]

    for url, desc in theahl_tests:
        result = test_endpoint(url, desc)
        results.append(result)
        if result["status"] == 200:
            print(f"  ✓ {desc}: {result['content_type']}")
        else:
            print(f"  ✗ {desc}: {result.get('status', 'error')}")

    # ===== PATTERN 6: Test with different client codes / leagues =====
    print("\n[PATTERN 6] Different client codes and league parameters")
    print("-" * 80)

    client_tests = [
        ("https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&client_code=nhl&game_id=1027888",
         "Client code: nhl"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&league_id=86&game_id=1027888",
         "League ID: 86"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&site_id=4629&game_id=1027888",
         "Site ID: 4629"),
        ("https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&client_code=ahl&league_id=86&game_id=1027888",
         "Client code + League ID"),
    ]

    for url, desc in client_tests:
        result = test_endpoint(url, desc)
        results.append(result)
        if result["status"] == 200:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc}: {result.get('status', 'error')}")

    # ===== GENERATE SUMMARY =====
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = [r for r in results if r["status"] == 200]
    json_responses = [r for r in successful if r["is_json"]]

    print(f"\nTotal endpoints tested: {len(results)}")
    print(f"Successful (200 OK): {len(successful)}")
    print(f"JSON responses: {len(json_responses)}")

    # Save all results to JSON
    with open("/Users/ryan/Documents/github/ahl/focused_api_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nFull results saved to focused_api_results.json")

    # Print successful endpoints with data
    if json_responses:
        print("\n✓ ENDPOINTS WITH JSON RESPONSES:")
        for r in json_responses[:10]:
            print(f"\n  {r['description']}")
            print(f"  URL: {r['url']}")
            if r['data_keys']:
                print(f"  Keys: {', '.join(r['data_keys'])}")


if __name__ == "__main__":
    main()
