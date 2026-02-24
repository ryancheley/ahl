"""
Comprehensive HockeyTech API Investigation Script

This script systematically tests various API endpoints and parameter combinations
to identify if detailed game data (goals, penalties, officials) is available via API.
"""

import requests
import json
from typing import List, Dict, Any, Tuple
from itertools import product
import time

# Test game ID - use a known game with data
TEST_GAME_ID = 1027888
SEASON_ID = 20252026  # Current season
LEAGUE_ID = 86  # AHL
SITE_ID = 4629  # AHL site

# Request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
}

# Base domains to test
BASE_DOMAINS = [
    "https://lscluster.hockeytech.com",
    "https://theahl.com",
    "https://api.theahl.com",
    "https://statsapi.nhl.com",  # Just in case AHL uses NHL's system
]

# Common path patterns to test
PATH_PATTERNS = [
    # feed patterns
    "/statviewfeed",
    "/statviewfeeds",
    "/feed",
    "/feeds",
    "/api/v1",
    "/api/v2",
    "/api",

    # game-specific paths
    "/game",
    "/games",
    "/game-detail",
    "/game-report",
    "/game_reports",

    # detail types
    "/goal",
    "/goals",
    "/penalty",
    "/penalties",
    "/official",
    "/officials",
    "/stats",
]

# View/feed combinations to test
VIEW_COMBINATIONS = [
    # Basic views
    ("BoxScore", None),
    ("GameSummary", None),
    ("GameDetail", None),
    ("GameReport", None),
    ("OfficialReport", None),

    # Detail-specific views
    ("GoalSummary", None),
    ("GoalDetail", None),
    ("Goals", None),
    ("PenaltySummary", None),
    ("PenaltyDetail", None),
    ("Penalties", None),
    ("OfficialDetail", None),
    ("Officials", None),
    ("RefereeSummary", None),
    ("Referees", None),

    # Combo views
    ("GameSummary", "Goals"),
    ("GameSummary", "Penalties"),
    ("GameSummary", "Officials"),
    ("BoxScore", "Goals"),
    ("BoxScore", "Penalties"),
    ("BoxScore", "Officials"),
    ("OfficialReport", "Goals"),
    ("OfficialReport", "Penalties"),
]

# Parameter variations to test
def get_parameter_sets() -> List[Dict[str, Any]]:
    """Generate different parameter combinations to test."""
    return [
        # Basic game_id only
        {"game_id": TEST_GAME_ID},

        # game_id with season/league
        {"game_id": TEST_GAME_ID, "season_id": SEASON_ID},
        {"game_id": TEST_GAME_ID, "league_id": LEAGUE_ID},
        {"game_id": TEST_GAME_ID, "site_id": SITE_ID},

        # Multiple parameters
        {"game_id": TEST_GAME_ID, "season_id": SEASON_ID, "league_id": LEAGUE_ID},
        {"game_id": TEST_GAME_ID, "season_id": SEASON_ID, "site_id": SITE_ID},
        {"game_id": TEST_GAME_ID, "league_id": LEAGUE_ID, "site_id": SITE_ID},

        # Different parameter names
        {"gameId": TEST_GAME_ID},
        {"id": TEST_GAME_ID},
        {"game": TEST_GAME_ID},

        # Format specifications
        {"game_id": TEST_GAME_ID, "fmt": "json"},
        {"game_id": TEST_GAME_ID, "format": "json"},

        # Client code variations
        {"client_code": "ahl", "game_id": TEST_GAME_ID},

        # Language parameter
        {"game_id": TEST_GAME_ID, "lang_id": 1},
        {"game_id": TEST_GAME_ID, "lang": "en"},
    ]


class APIInvestigator:
    """Systematically test HockeyTech API endpoints."""

    def __init__(self):
        self.results = {
            "successful_endpoints": [],
            "endpoints_with_data": [],
            "parameter_findings": {},
            "domain_findings": {},
            "view_findings": {},
        }
        self.tested_urls = set()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def test_url(self, url: str, description: str = "") -> Tuple[bool, str, Any]:
        """Test a single URL and return (success, content_type, data/error)."""
        if url in self.tested_urls:
            return False, "cached", None

        self.tested_urls.add(url)

        try:
            response = self.session.get(url, timeout=10)

            # Record the response
            content_type = response.headers.get("content-type", "unknown")
            success = response.status_code == 200

            if success:
                # Try to parse as JSON
                if "json" in content_type or response.text.startswith("{") or response.text.startswith("["):
                    try:
                        data = response.json()
                        return True, "json", data
                    except:
                        return True, content_type, response.text[:500]
                else:
                    return True, content_type, response.text[:500]
            else:
                return False, f"HTTP {response.status_code}", response.text[:200]

        except requests.exceptions.Timeout:
            return False, "timeout", None
        except requests.exceptions.ConnectionError:
            return False, "connection_error", None
        except Exception as e:
            return False, type(e).__name__, str(e)

    def test_feed_endpoints(self):
        """Test feed/view style endpoints."""
        print("\n" + "="*80)
        print("TESTING FEED/VIEW ENDPOINTS")
        print("="*80)

        for domain in BASE_DOMAINS:
            self.results["domain_findings"][domain] = []

            for path in PATH_PATTERNS:
                for view, feed in VIEW_COMBINATIONS:
                    # Build URL variations
                    urls_to_test = [
                        # Basic path + view
                        f"{domain}{path}?view={view}&game_id={TEST_GAME_ID}",
                        f"{domain}{path}/{view}?game_id={TEST_GAME_ID}",

                        # With feed
                        f"{domain}{path}?view={view}&feed={feed}&game_id={TEST_GAME_ID}" if feed else None,
                        f"{domain}{path}/{view}/{feed}?game_id={TEST_GAME_ID}" if feed else None,

                        # Extended path patterns
                        f"{domain}{path}/stats?view={view}&game_id={TEST_GAME_ID}",
                        f"{domain}{path}/games/{TEST_GAME_ID}?view={view}",
                        f"{domain}{path}/game/{TEST_GAME_ID}?view={view}",
                    ]

                    for url in filter(None, urls_to_test):
                        success, content_type, data = self.test_url(url)

                        if success and data:
                            finding = {
                                "url": url,
                                "view": view,
                                "feed": feed,
                                "path": path,
                                "domain": domain,
                                "content_type": content_type,
                            }

                            self.results["domain_findings"][domain].append(finding)
                            self.results["successful_endpoints"].append(finding)

                            # Check if it has goal/penalty/official data
                            data_str = str(data).lower() if data else ""
                            if any(x in data_str for x in ["goal", "penalty", "official", "referee"]):
                                self.results["endpoints_with_data"].append(finding)
                                print(f"✓ FOUND DATA: {url}")

                        time.sleep(0.1)  # Rate limiting

    def test_rest_endpoints(self):
        """Test REST-style endpoints."""
        print("\n" + "="*80)
        print("TESTING REST-STYLE ENDPOINTS")
        print("="*80)

        rest_patterns = [
            f"/api/v1/games/{TEST_GAME_ID}",
            f"/api/v1/games/{TEST_GAME_ID}/goals",
            f"/api/v1/games/{TEST_GAME_ID}/penalties",
            f"/api/v1/games/{TEST_GAME_ID}/officials",
            f"/api/v2/games/{TEST_GAME_ID}",
            f"/api/games/{TEST_GAME_ID}",
            f"/api/game/{TEST_GAME_ID}",
            f"/api/game-detail/{TEST_GAME_ID}",
            f"/stats/game/{TEST_GAME_ID}",
            f"/stats/game-detail/{TEST_GAME_ID}",
            f"/data/games/{TEST_GAME_ID}",
            f"/data/game/{TEST_GAME_ID}",
        ]

        for domain in BASE_DOMAINS:
            for pattern in rest_patterns:
                url = domain + pattern
                success, content_type, data = self.test_url(url)

                if success and data:
                    finding = {
                        "url": url,
                        "pattern": pattern,
                        "domain": domain,
                        "content_type": content_type,
                    }
                    self.results["successful_endpoints"].append(finding)

                    # Check for detailed data
                    data_str = str(data).lower()
                    if any(x in data_str for x in ["goal", "penalty", "official"]):
                        self.results["endpoints_with_data"].append(finding)
                        print(f"✓ FOUND DATA: {url}")

                time.sleep(0.1)

    def test_parameter_variations(self):
        """Test different parameter combinations with known working endpoints."""
        print("\n" + "="*80)
        print("TESTING PARAMETER VARIATIONS")
        print("="*80)

        # Test against statviewfeed (if it exists) and other known paths
        base_endpoints = [
            "https://lscluster.hockeytech.com/feed",
            "https://lscluster.hockeytech.com/statviewfeed",
            "https://lscluster.hockeytech.com/api/v1",
        ]

        for endpoint in base_endpoints:
            for params in get_parameter_sets():
                url = endpoint + "?" + "&".join(f"{k}={v}" for k, v in params.items())
                success, content_type, data = self.test_url(url)

                if success and data:
                    self.results["parameter_findings"][str(params)] = {
                        "url": url,
                        "success": True,
                        "content_type": content_type,
                    }
                    print(f"✓ VALID PARAMS: {params} -> {content_type}")

                time.sleep(0.1)

    def test_theahl_endpoints(self):
        """Test endpoints specific to theahl.com."""
        print("\n" + "="*80)
        print("TESTING THEAHL.COM SPECIFIC ENDPOINTS")
        print("="*80)

        theahl_patterns = [
            f"/stats/game-center/{TEST_GAME_ID}",
            f"/stats/game/{TEST_GAME_ID}",
            f"/api/stats/game/{TEST_GAME_ID}",
            f"/api/game-center/{TEST_GAME_ID}",
            f"/game-center/{TEST_GAME_ID}",
            f"/games/{TEST_GAME_ID}",
            f"/stats/games/{TEST_GAME_ID}",
        ]

        for pattern in theahl_patterns:
            urls = [
                f"https://theahl.com{pattern}",
                f"https://api.theahl.com{pattern}",
            ]

            for url in urls:
                success, content_type, data = self.test_url(url)

                if success and data:
                    finding = {
                        "url": url,
                        "pattern": pattern,
                        "content_type": content_type,
                    }
                    self.results["successful_endpoints"].append(finding)
                    print(f"✓ FOUND ENDPOINT: {url}")

                time.sleep(0.1)

    def test_query_parameters(self):
        """Test common query parameters on known working endpoints."""
        print("\n" + "="*80)
        print("TESTING QUERY PARAMETERS ON KNOWN ENDPOINTS")
        print("="*80)

        base_url = "https://lscluster.hockeytech.com/game_reports/official-game-report.php"

        # Known working endpoint - test different parameters
        params_to_test = [
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "lang_id": 1},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "format": "json"},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "view": "goals"},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "view": "penalties"},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "view": "officials"},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "details": "true"},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "full": "true"},
            {"client_code": "ahl", "game_id": TEST_GAME_ID, "extended": "true"},
        ]

        for params in params_to_test:
            url = base_url + "?" + "&".join(f"{k}={v}" for k, v in params.items())
            success, content_type, data = self.test_url(url)

            if success:
                self.results["parameter_findings"][str(params)] = {
                    "url": url,
                    "success": True,
                    "content_type": content_type,
                    "data_preview": str(data)[:100] if data else "no data",
                }
                print(f"✓ VALID: {params}")
                print(f"  Content-Type: {content_type}")
                print(f"  Preview: {str(data)[:100]}")

            time.sleep(0.1)

    def generate_report(self):
        """Generate a summary report of findings."""
        print("\n" + "="*80)
        print("INVESTIGATION REPORT")
        print("="*80)

        print(f"\nTotal URLs tested: {len(self.tested_urls)}")
        print(f"Successful endpoints: {len(self.results['successful_endpoints'])}")
        print(f"Endpoints with goal/penalty/official data: {len(self.results['endpoints_with_data'])}")

        if self.results["successful_endpoints"]:
            print("\n--- SUCCESSFUL ENDPOINTS ---")
            for finding in self.results["successful_endpoints"][:10]:
                print(f"\n{finding['url']}")
                if "content_type" in finding:
                    print(f"  Content-Type: {finding['content_type']}")

        if self.results["endpoints_with_data"]:
            print("\n--- ENDPOINTS WITH DETAILED DATA ---")
            for finding in self.results["endpoints_with_data"][:10]:
                print(f"\n{finding['url']}")
                if "content_type" in finding:
                    print(f"  Content-Type: {finding['content_type']}")

        if self.results["parameter_findings"]:
            print("\n--- VALID PARAMETER COMBINATIONS ---")
            for params, result in list(self.results["parameter_findings"].items())[:10]:
                print(f"\n{params}")
                print(f"  URL: {result['url']}")

        # Save detailed results to JSON
        with open("/Users/ryan/Documents/github/ahl/api_investigation_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\n✓ Detailed results saved to api_investigation_results.json")


def main():
    """Run the API investigation."""
    investigator = APIInvestigator()

    print("HockeyTech API Investigation")
    print(f"Testing game ID: {TEST_GAME_ID}")
    print(f"Season: {SEASON_ID}")

    # Run investigations
    investigator.test_feed_endpoints()
    investigator.test_rest_endpoints()
    investigator.test_theahl_endpoints()
    investigator.test_parameter_variations()
    investigator.test_query_parameters()

    # Generate report
    investigator.generate_report()


if __name__ == "__main__":
    main()
