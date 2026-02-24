"""
Deep investigation of the /feed endpoint and theahl.com data loading
"""

import requests
import json
import re
from typing import Dict, Any

TEST_GAME_ID = 1027888

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://theahl.com/",
}

def test_feed_endpoint():
    """Test the /feed endpoint with various parameters."""
    print("="*80)
    print("INVESTIGATING /FEED ENDPOINT")
    print("="*80 + "\n")

    # The /feed endpoint might require a 'key' parameter
    # Try different approaches
    tests = [
        # Without key
        f"https://lscluster.hockeytech.com/feed?view=BoxScore&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}",

        # With potential key values
        f"https://lscluster.hockeytech.com/feed?key=ahlstats&view=BoxScore&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed?key=ahl&view=BoxScore&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed?key=86&view=BoxScore&game_id={TEST_GAME_ID}",

        # Different feed types/parameters
        f"https://lscluster.hockeytech.com/feed?feed=boxscore&game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/feed?type=boxscore&game_id={TEST_GAME_ID}",

        # Test statviewfeed with game_id
        f"https://lscluster.hockeytech.com/statviewfeed?game_id={TEST_GAME_ID}",
        f"https://lscluster.hockeytech.com/statviewfeed?game_id={TEST_GAME_ID}&client_code=ahl",
    ]

    for url in tests:
        try:
            print(f"Testing: {url}")
            response = requests.get(url, headers=HEADERS, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            preview = response.text[:200] if response.text else "NO CONTENT"
            print(f"  Response: {preview}\n")
        except Exception as e:
            print(f"  Error: {e}\n")


def analyze_theahl_page():
    """Analyze the theahl.com page to see how it loads game data."""
    print("\n" + "="*80)
    print("ANALYZING THEAHL.COM GAME PAGE")
    print("="*80 + "\n")

    url = f"https://theahl.com/stats/game-center/{TEST_GAME_ID}"
    try:
        print(f"Fetching: {url}\n")
        response = requests.get(url, headers=HEADERS, timeout=10)
        html = response.text

        # Look for API calls in the page
        print("Searching for API endpoints in page source...")

        # Common patterns for API calls
        patterns = [
            r'https://[^"\s\']+api[^"\s\']*',
            r'/api/[^"\s\']*',
            r'fetch\(["\']([^"\']+)',
            r'xhr\.open\(["\'][A-Z]+["\'],\s*["\']([^"\']+)',
            r'"url"\s*:\s*["\']([^"\']+)',
            r'endpoint["\']?\s*:\s*["\']([^"\']+)',
        ]

        found_apis = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if 'api' in match.lower() or 'feed' in match.lower():
                    found_apis.add(match)

        if found_apis:
            print(f"\n✓ Found {len(found_apis)} potential API references:")
            for api in sorted(found_apis)[:20]:
                print(f"  - {api}")
        else:
            print("  No obvious API calls found in initial scan")

        # Look for data attributes or specific markers
        print("\nSearching for data loading scripts...")
        if 'ng-' in html or 'angular' in html.lower():
            print("  ✓ Found AngularJS directives (ng-app, ng-controller, etc.)")
        if 'react' in html.lower():
            print("  ✓ Found React references")
        if 'vue' in html.lower():
            print("  ✓ Found Vue references")

        # Look for hardcoded data or script blocks
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"\n  Found {len(script_blocks)} script blocks")

        # Check for window.gameData or similar
        if 'window.' in html:
            window_refs = re.findall(r'window\.(\w+)\s*=', html)
            if window_refs:
                print(f"\n✓ Found window object assignments:")
                for ref in set(window_refs)[:10]:
                    print(f"  - window.{ref}")

    except Exception as e:
        print(f"Error: {e}")


def test_direct_statviewfeed():
    """Test if statviewfeed works with different configurations."""
    print("\n" + "="*80)
    print("TESTING STATVIEWFEED DIRECTLY")
    print("="*80 + "\n")

    # Extract the game_id from our test and try different views
    views_to_test = [
        "BoxScore",
        "RosterCompare",
        "ShotMap",
        "EventSummary",
        "GameSummary",
        "TeamStats",
        "PlayerStats",
        "GoalSummary",
        "PenaltySummary",
    ]

    # Try both with and without client_code
    configs = [
        {"client_code": "ahl"},
        {"league_id": 86},
        {"site_id": 4629},
        {},
    ]

    for config in configs:
        print(f"\nTesting with config: {config}")
        for view in views_to_test[:3]:  # Test subset to avoid too many requests
            params = {"view": view, "game_id": TEST_GAME_ID, **config}
            url = "https://lscluster.hockeytech.com/statviewfeed?" + "&".join(f"{k}={v}" for k, v in params.items())

            try:
                response = requests.get(url, headers=HEADERS, timeout=5)
                status = "✓" if response.status_code == 200 else "✗"
                print(f"  {status} {view}: {response.status_code}")
            except Exception as e:
                print(f"  ✗ {view}: {str(e)[:50]}")


def test_browser_like_requests():
    """Test with headers that look more like a browser."""
    print("\n" + "="*80)
    print("TESTING WITH ENHANCED BROWSER HEADERS")
    print("="*80 + "\n")

    # More complete browser headers
    enhanced_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://theahl.com/stats/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    url = f"https://lscluster.hockeytech.com/statviewfeed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}"

    try:
        print(f"Testing: {url}")
        response = requests.get(url, headers=enhanced_headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Response preview: {response.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")


def test_with_session_cookie():
    """Test with session management."""
    print("\n" + "="*80)
    print("TESTING WITH SESSION/COOKIE HANDLING")
    print("="*80 + "\n")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    # First, visit the main site to get cookies
    print("1. Visiting main site...")
    try:
        resp1 = session.get("https://theahl.com/stats/", timeout=10)
        print(f"   Status: {resp1.status_code}")
        print(f"   Cookies: {session.cookies.get_dict()}")
    except Exception as e:
        print(f"   Error: {e}")

    # Now try the feed endpoint
    print("\n2. Trying feed endpoint with session...")
    url = f"https://lscluster.hockeytech.com/feed?view=BoxScore&client_code=ahl&game_id={TEST_GAME_ID}"
    try:
        resp2 = session.get(url, timeout=10)
        print(f"   Status: {resp2.status_code}")
        print(f"   Response: {resp2.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    test_feed_endpoint()
    test_direct_statviewfeed()
    test_browser_like_requests()
    test_with_session_cookie()
    analyze_theahl_page()
