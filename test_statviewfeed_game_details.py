"""
Systematic test of statviewfeed endpoint for game details.

We know statviewfeed works with:
- feed=statviewfeed
- view=player
- player_id parameter
- season_id=90, site_id=3, key=ccb91f29d6744675, client_code=ahl, league_id=4, lang=1
- statsType=skaters

Now we test variations for game data by replacing view and parameters.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

TEST_GAME_ID = 1027888
API_KEY = "ccb91f29d6744675"
BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def build_url(
    view: str,
    game_id: int = TEST_GAME_ID,
    stats_type: Optional[str] = None,
    extra_params: Optional[Dict[str, str]] = None,
) -> str:
    """Build a test URL with standard parameters."""
    params = {
        "feed": "statviewfeed",
        "view": view,
        "game_id": str(game_id),
        "season_id": "90",
        "site_id": "3",
        "key": API_KEY,
        "client_code": "ahl",
        "league_id": "4",
        "lang": "1",
    }

    if stats_type:
        params["statsType"] = stats_type

    if extra_params:
        params.update(extra_params)

    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{BASE_URL}?{query_string}"


def test_endpoint(url: str, description: str = "") -> Dict[str, Any]:
    """Test a single endpoint and return findings."""
    result = {
        "url": url,
        "description": description,
        "status": None,
        "content_type": None,
        "is_json": False,
        "is_jsonp": False,
        "has_data": False,
        "data_keys": [],
        "response_length": 0,
        "response_preview": None,
        "error": None,
    }

    try:
        print(f"  Testing: {description}...", end=" ", flush=True)
        response = requests.get(url, headers=HEADERS, timeout=10)
        result["status"] = response.status_code
        result["response_length"] = len(response.text)

        if response.status_code == 200:
            result["content_type"] = response.headers.get("content-type", "unknown")

            text = response.text.strip()

            # Check for JSONP
            if text.startswith("(") and text.endswith(")"):
                result["is_jsonp"] = True
                text = text[1:-1]

            # Try JSON parsing
            try:
                data = json.loads(text)
                result["is_json"] = True
                result["has_data"] = bool(data)
                if isinstance(data, dict):
                    result["data_keys"] = list(data.keys())[:10]
                result["response_preview"] = json.dumps(data, indent=2)[:300]
                print("✓ JSON")
            except:
                # Not JSON, show text preview
                result["response_preview"] = text[:300]
                print("✓ (non-JSON)")
        else:
            print(f"✗ {response.status_code}")

        time.sleep(0.3)

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ ERROR: {str(e)[:50]}")

    return result


def main():
    """Test statviewfeed endpoint with various game-related parameters."""

    print("=" * 100)
    print("STATVIEWFEED ENDPOINT - GAME DETAILS INVESTIGATION")
    print(f"Test Game ID: {TEST_GAME_ID}")
    print(f"API Key: {API_KEY[:10]}...")
    print("=" * 100)

    results = []

    # ===== PATTERN 1: Different views (replacing "player" with game-related names) =====
    print("\n[PATTERN 1] Different view parameters")
    print("-" * 100)

    view_tests = [
        ("game", None),
        ("gamestats", None),
        ("gamedetails", None),
        ("gamescore", None),
        ("gamereport", None),
        ("boxscore", None),
        ("summary", None),
        ("goals", None),
        ("penalties", None),
        ("officials", None),
        ("scoresheet", None),
        ("roster", None),
        ("officialsummary", None),
        ("goalssummary", None),
        ("penaltiesummary", None),
    ]

    for view, _ in view_tests:
        url = build_url(view)
        result = test_endpoint(url, f"view={view}")
        results.append(result)
        if result["has_data"]:
            print(f"       Keys: {', '.join(result['data_keys'][:5])}")

    # ===== PATTERN 2: Different statsType values =====
    print("\n[PATTERN 2] Different statsType values with various views")
    print("-" * 100)

    stats_types = ["goals", "penalties", "officials", "boxscore", "detailed", "summary", "gamedetails"]
    views_to_test = ["game", "gamestats", "gamedetails"]

    for view in views_to_test:
        for stats_type in stats_types:
            url = build_url(view, stats_type=stats_type)
            result = test_endpoint(url, f"view={view} + statsType={stats_type}")
            results.append(result)
            if result["has_data"]:
                print(f"       Keys: {', '.join(result['data_keys'][:5])}")

    # ===== PATTERN 3: Minimal parameters (testing what's required) =====
    print("\n[PATTERN 3] Minimal parameter tests")
    print("-" * 100)

    minimal_tests = [
        # Just the essentials
        (
            {
                "feed": "statviewfeed",
                "view": "game",
                "game_id": str(TEST_GAME_ID),
                "key": API_KEY,
                "client_code": "ahl",
            },
            "Minimal params (no season/site/league/lang)",
        ),
        (
            {
                "feed": "statviewfeed",
                "view": "game",
                "game_id": str(TEST_GAME_ID),
                "key": API_KEY,
                "league_id": "4",
            },
            "League ID only",
        ),
        (
            {
                "feed": "statviewfeed",
                "view": "game",
                "game_id": str(TEST_GAME_ID),
                "key": API_KEY,
                "site_id": "3",
            },
            "Site ID only",
        ),
    ]

    for params, desc in minimal_tests:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{BASE_URL}?{query_string}"
        result = test_endpoint(url, desc)
        results.append(result)
        if result["has_data"]:
            print(f"       Keys: {', '.join(result['data_keys'][:5])}")

    # ===== PATTERN 4: Alternative API key scenarios =====
    print("\n[PATTERN 4] Testing without API key (checking if required)")
    print("-" * 100)

    url_no_key = (
        f"{BASE_URL}?feed=statviewfeed&view=game&game_id={TEST_GAME_ID}"
        "&season_id=90&site_id=3&client_code=ahl&league_id=4&lang=1"
    )
    result = test_endpoint(url_no_key, "Without API key")
    results.append(result)

    # ===== PATTERN 5: Different season_id values =====
    print("\n[PATTERN 5] Different season_id values")
    print("-" * 100)

    season_ids = ["90", "89", "88", None]  # None means no season_id

    for season_id in season_ids:
        params = {
            "feed": "statviewfeed",
            "view": "game",
            "game_id": str(TEST_GAME_ID),
            "site_id": "3",
            "key": API_KEY,
            "client_code": "ahl",
            "league_id": "4",
            "lang": "1",
        }
        if season_id:
            params["season_id"] = season_id

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{BASE_URL}?{query_string}"
        desc = f"season_id={season_id}" if season_id else "No season_id"
        result = test_endpoint(url, desc)
        results.append(result)
        if result["has_data"]:
            print(f"       Keys: {', '.join(result['data_keys'][:5])}")

    # ===== PATTERN 6: View parameters specifically for game components =====
    print("\n[PATTERN 6] Specific game component views")
    print("-" * 100)

    component_views = [
        "boxscore",
        "roster",
        "goals",
        "penalties",
        "officials",
        "shots",
        "teamstats",
        "playerstats",
    ]

    for view in component_views:
        url = build_url(view)
        result = test_endpoint(url, f"Component: view={view}")
        results.append(result)
        if result["has_data"]:
            print(f"       Keys: {', '.join(result['data_keys'][:5])}")

    # ===== GENERATE SUMMARY =====
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    successful = [r for r in results if r["status"] == 200]
    json_responses = [r for r in successful if r["is_json"]]
    with_data = [r for r in json_responses if r["has_data"]]

    print(f"\nTotal endpoints tested: {len(results)}")
    print(f"Successful (200 OK): {len(successful)}")
    print(f"JSON responses: {len(json_responses)}")
    print(f"With data: {len(with_data)}")

    # Save all results to JSON
    output_file = "/Users/ryan/Documents/github/ahl/statviewfeed_game_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nFull results saved to {output_file}")

    # Print successful endpoints with data
    if with_data:
        print("\n✓ ENDPOINTS WITH DATA:")
        for r in sorted(with_data, key=lambda x: x["response_length"], reverse=True)[:15]:
            print(f"\n  {r['description']}")
            if r["data_keys"]:
                print(f"  Keys: {', '.join(r['data_keys'])}")
            print(f"  Response length: {r['response_length']} bytes")


if __name__ == "__main__":
    main()
