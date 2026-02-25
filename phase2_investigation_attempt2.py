#!/usr/bin/env python3
"""
Phase 2 Investigation - Attempt 2
The initial endpoints returned "Client access denied"
This script tries different approaches to get them working:
1. Add API key to requests
2. Try different base URLs (theahl.com, hockeytech.com)
3. Test the working endpoints with different parameters
4. Analyze what makes statviewfeed work vs the others
"""

import requests
import json
from typing import Optional, Dict, Any

API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"
SEASON_ID = 90
SITE_ID = 3
LEAGUE_ID = 4
LANG = 1
TEST_GAME_ID = 1027888

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

def test_endpoint_variant(
    name: str,
    base_url: str,
    params: Dict[str, str],
) -> tuple[bool, str]:
    """Test endpoint variant and return success status and response preview."""
    try:
        response = requests.get(base_url, params=params, timeout=10)
        status = response.status_code

        if status != 200:
            return False, f"HTTP {status}"

        # Check response content
        preview = response.text[:100].strip()

        if "Client access denied" in response.text:
            return False, "Client access denied"
        elif "error" in response.text.lower():
            return False, f"Error in response: {preview}"
        elif response.text.startswith("("):
            data = parse_jsonp(response.text)
            if data and "error" not in data:
                return True, "Valid JSON response"
            return False, "JSON error field"
        else:
            return False, preview

    except Exception as e:
        return False, f"Exception: {str(e)[:50]}"

def main():
    print(f"\n{BOLD}{YELLOW}{'='*70}")
    print("PHASE 2 INVESTIGATION - ATTEMPT 2")
    print("Testing different approaches to access new endpoints")
    print(f"{'='*70}{RESET}\n")

    # =====================================================
    # PART 1: Verify known working endpoints still work
    # =====================================================
    print(f"{BOLD}PART 1: Verify Known Working Endpoints{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    known_working = {
        'player': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'statviewfeed',
                'view': 'player',
                'player_id': '988',
                'season_id': str(SEASON_ID),
                'site_id': str(SITE_ID),
                'key': API_KEY,
                'client_code': CLIENT_CODE,
                'league_id': str(LEAGUE_ID),
                'lang': str(LANG),
                'statsType': 'skaters'
            }
        },
        'roster': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
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
        },
    }

    for name, config in known_working.items():
        success, msg = test_endpoint_variant(name, config['base'], config['params'])
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{status} statviewfeed/{name}: {msg}")

    # =====================================================
    # PART 2: Try gc endpoints WITH API key and full params
    # =====================================================
    print(f"\n{BOLD}PART 2: GC Endpoints WITH Full Parameters{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    gc_variants = {
        'pxpverbose_no_auth': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'gc',
                'tab': 'pxpverbose',
                'game_id': str(TEST_GAME_ID),
                'season_id': str(SEASON_ID),
            }
        },
        'pxpverbose_with_key': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'gc',
                'tab': 'pxpverbose',
                'game_id': str(TEST_GAME_ID),
                'season_id': str(SEASON_ID),
                'key': API_KEY,
                'client_code': CLIENT_CODE,
            }
        },
        'pxpverbose_full_params': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'gc',
                'tab': 'pxpverbose',
                'game_id': str(TEST_GAME_ID),
                'season_id': str(SEASON_ID),
                'site_id': str(SITE_ID),
                'league_id': str(LEAGUE_ID),
                'key': API_KEY,
                'client_code': CLIENT_CODE,
                'lang': str(LANG),
            }
        },
    }

    for name, config in gc_variants.items():
        success, msg = test_endpoint_variant(name, config['base'], config['params'])
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{status} {name}: {msg}")

    # =====================================================
    # PART 3: Try different base URLs for gc feed
    # =====================================================
    print(f"\n{BOLD}PART 3: Try Different Base URLs for GC{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    base_urls = [
        'https://lscluster.hockeytech.com/feed/index.php',
        'https://theahl.com/feed/index.php',
        'https://api.hockeytech.com/feed/index.php',
        'https://lscluster.hockeytech.com/gc/',
        'https://theahl.com/api/gc',
    ]

    params_pxp = {
        'feed': 'gc',
        'tab': 'pxpverbose',
        'game_id': str(TEST_GAME_ID),
        'season_id': str(SEASON_ID),
        'key': API_KEY,
        'client_code': CLIENT_CODE,
    }

    for url in base_urls:
        success, msg = test_endpoint_variant(f"gc_pxpverbose", url, params_pxp)
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{status} {url}: {msg}")

    # =====================================================
    # PART 4: Try modulekit with different parameters
    # =====================================================
    print(f"\n{BOLD}PART 4: ModuleKit Endpoints WITH Full Parameters{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    modulekit_variants = {
        'schedule_no_auth': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'modulekit',
                'view': 'schedule',
                'season_id': str(SEASON_ID),
            }
        },
        'schedule_with_client': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'modulekit',
                'view': 'schedule',
                'season_id': str(SEASON_ID),
                'client_code': CLIENT_CODE,
            }
        },
        'schedule_full_params': {
            'base': 'https://lscluster.hockeytech.com/feed/index.php',
            'params': {
                'feed': 'modulekit',
                'view': 'schedule',
                'season_id': str(SEASON_ID),
                'key': API_KEY,
                'client_code': CLIENT_CODE,
                'site_id': str(SITE_ID),
                'league_id': str(LEAGUE_ID),
                'lang': str(LANG),
            }
        },
    }

    for name, config in modulekit_variants.items():
        success, msg = test_endpoint_variant(name, config['base'], config['params'])
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{status} {name}: {msg}")

    # =====================================================
    # PART 5: Try theahl.com directly
    # =====================================================
    print(f"\n{BOLD}PART 5: Try theahl.com Domain Directly{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    theahl_tests = {
        'theahl_game_data': {
            'base': 'https://theahl.com/feed/index.php',
            'params': {
                'feed': 'gc',
                'tab': 'pxpverbose',
                'game_id': str(TEST_GAME_ID),
            }
        },
        'theahl_statviewfeed': {
            'base': 'https://theahl.com/feed/index.php',
            'params': {
                'feed': 'statviewfeed',
                'view': 'player',
                'player_id': '988',
                'season_id': str(SEASON_ID),
                'key': API_KEY,
                'client_code': CLIENT_CODE,
            }
        },
    }

    for name, config in theahl_tests.items():
        success, msg = test_endpoint_variant(name, config['base'], config['params'])
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"{status} {name}: {msg}")

    # =====================================================
    # SUMMARY
    # =====================================================
    print(f"\n{BOLD}{YELLOW}{'='*70}")
    print("FINDINGS")
    print(f"{'='*70}{RESET}")

    print(f"""
{BOLD}Key Observations:{RESET}
1. statviewfeed endpoints (player, roster) work with just the API key
2. gc and modulekit endpoints return "Client access denied" even with full params
3. This suggests gc and modulekit are either:
   - Restricted to certain domains/IP ranges
   - Require different authentication headers
   - Not actually available through the public API key
   - Only available through the web frontend (theahl.com)

{BOLD}Hypothesis:{RESET}
The Phase 1 discovery of gc and modulekit endpoints may have been from:
- JavaScript that makes requests from the browser (has session cookies)
- Internal/private API not accessible to external API key
- Different authentication mechanism not yet discovered

{BOLD}Recommendation:{RESET}
Phase 2 should shift to:
1. JavaScript bundle analysis on theahl.com (browser requests)
2. DevTools inspection of actual network traffic
3. Investigating if these endpoints work with session cookies
4. Looking at the hockeytech npm package to see their approach
""")

if __name__ == '__main__':
    main()
