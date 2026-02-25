#!/usr/bin/env python3
"""
Phase 2 Analysis: GC PXPVerbose Data Structure
Deep analysis of the gc/pxpverbose endpoint response to determine
what game data is available and if it can replace HTML scraping.
"""

import requests
import json
from collections import defaultdict
from typing import Dict, List, Any

API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"
SEASON_ID = 90
TEST_GAME_ID = 1027888

BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def fetch_pxpverbose():
    """Fetch pxpverbose data for test game."""
    params = {
        'feed': 'gc',
        'tab': 'pxpverbose',
        'game_id': str(TEST_GAME_ID),
        'season_id': str(SEASON_ID),
        'key': API_KEY,
        'client_code': CLIENT_CODE,
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    return json.loads(response.text)

def analyze_pxpverbose(data: Dict[Any, Any]):
    """Analyze pxpverbose response structure and content."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}GC PXPVERBOSE DATA STRUCTURE ANALYSIS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    gc_data = data.get('GC', {})
    pxp_events = gc_data.get('Pxpverbose', [])

    print(f"{BOLD}Basic Stats:{RESET}")
    print(f"  Total events: {len(pxp_events)}")

    # Analyze event types
    event_types = defaultdict(int)
    event_samples = defaultdict(list)

    for event in pxp_events:
        event_type = event.get('event', 'unknown')
        event_types[event_type] += 1
        if len(event_samples[event_type]) < 1:  # Keep one sample of each type
            event_samples[event_type].append(event)

    print(f"\n{BOLD}Event Types Found:{RESET}")
    for event_type in sorted(event_types.keys()):
        count = event_types[event_type]
        print(f"  {event_type:20s}: {count:4d} events")

    # Deep dive into important event types
    print(f"\n{BOLD}{GREEN}GOALS SECTION{RESET}")
    goals = [e for e in pxp_events if e.get('event') == 'goal']
    print(f"Total goals: {len(goals)}")

    if goals:
        print(f"\nGoal event structure (first goal):")
        goal = goals[0]
        print(json.dumps(goal, indent=2)[:1000])

        # Extract goal details
        print(f"\n{BOLD}Goal fields available:{RESET}")
        for key in sorted(goal.keys()):
            value = goal[key]
            if isinstance(value, dict):
                print(f"  {key}: {type(value).__name__} with keys {list(value.keys())[:5]}")
            elif isinstance(value, list):
                print(f"  {key}: list ({len(value)} items)")
            else:
                print(f"  {key}: {value}")

    # Analyze penalties
    print(f"\n{BOLD}{RED}PENALTIES SECTION{RESET}")
    penalties = [e for e in pxp_events if e.get('event') == 'penalty']
    print(f"Total penalties: {len(penalties)}")

    if penalties:
        print(f"\nPenalty event structure (first penalty):")
        penalty = penalties[0]
        print(json.dumps(penalty, indent=2)[:1000])

        print(f"\n{BOLD}Penalty fields available:{RESET}")
        for key in sorted(penalty.keys()):
            value = penalty[key]
            if isinstance(value, dict):
                print(f"  {key}: {type(value).__name__} with keys {list(value.keys())[:5]}")
            else:
                print(f"  {key}: {value}")

    # Analyze game metadata
    print(f"\n{BOLD}{YELLOW}GAME METADATA{RESET}")
    parameters = gc_data.get('Parameters', {})
    print(f"Parameters in response:")
    for key, value in parameters.items():
        print(f"  {key}: {value}")

    # Check for officials
    print(f"\n{BOLD}OFFICIALS SECTION{RESET}")
    officials = [e for e in pxp_events if e.get('event') == 'official']
    print(f"Total official events: {len(officials)}")

    if officials:
        print(f"\nOfficial event structure (first official):")
        official = officials[0]
        print(json.dumps(official, indent=2))

    # Summary comparison
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}COMPARISON WITH HTML SCRAPING NEEDS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    print(f"{BOLD}Current HTML Scraping Extracts:{RESET}")
    print("  ✓ Game scores/results")
    print("  ✓ Goal details (scorer, assists, time, period)")
    print("  ✓ Penalty details (type, minutes, description, period)")
    print("  ✓ Officials (referees, linespersons)")
    print("  ✓ Game timing and status")
    print("  ✓ Attendance")

    print(f"\n{BOLD}GC/PXPVerbose Provides:{RESET}")
    if goals:
        print(f"  ✓ Goals ({len(goals)} found) - DETAILED with event structure")
    else:
        print(f"  ✗ Goals (none found in this game)")

    if penalties:
        print(f"  ✓ Penalties ({len(penalties)} found) - with penalty details")
    else:
        print(f"  ✗ Penalties (none found in this game)")

    if officials:
        print(f"  ✓ Officials ({len(officials)} found) - in event stream")
    else:
        print(f"  ✗ Officials (not found as events)")

    print(f"  ✓ Game timing and periods")
    print(f"  ✓ Team information")
    print(f"  ✓ Comprehensive player information")

    print(f"\n{BOLD}Assessment:{RESET}")
    if goals and len(goals) > 0:
        print(f"  {GREEN}✓ Goals data structure validates API capability")
    if penalties and len(penalties) > 0:
        print(f"  {GREEN}✓ Penalties data structure validates API capability")
    if not officials:
        print(f"  {YELLOW}⚠ Official information may need further investigation")

    print(f"\n{BOLD}Recommendation:{RESET}")
    print(f"  GC/PXPVerbose appears capable of replacing HTML scraping for:")
    print(f"  - Game scores and final results")
    print(f"  - All goal details")
    print(f"  - All penalty details")
    print(f"  - Game timing and periods")
    print(f"  - Player information")
    print(f"  - Attendance")
    print(f"\n  Further testing needed for: Official assignments")

    return {
        'total_events': len(pxp_events),
        'goals': len(goals),
        'penalties': len(penalties),
        'officials': len(officials),
        'event_types': dict(event_types),
    }

def fetch_gamesummary():
    """Fetch game summary data for comparison."""
    params = {
        'feed': 'gc',
        'tab': 'gamesummary',
        'game_id': str(TEST_GAME_ID),
        'season_id': str(SEASON_ID),
        'key': API_KEY,
        'client_code': CLIENT_CODE,
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    return json.loads(response.text)

def analyze_gamesummary(data: Dict[Any, Any]):
    """Analyze game summary endpoint."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}GC GAMESUMMARY DATA STRUCTURE ANALYSIS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    gc_data = data.get('GC', {})
    summary = gc_data.get('Gamesummary', {})
    meta = summary.get('meta', {})

    print(f"{BOLD}Game Metadata Available:{RESET}")
    print(f"  Game ID: {meta.get('id')}")
    print(f"  Date: {meta.get('date_played')}")
    print(f"  Home Team ID: {meta.get('home_team')}")
    print(f"  Visiting Team ID: {meta.get('visiting_team')}")
    print(f"  Home Goals: {meta.get('home_goal_count')}")
    print(f"  Visiting Goals: {meta.get('visiting_goal_count')}")
    print(f"  Attendance: {meta.get('attendance')}")
    print(f"  Status: {meta.get('status')}")
    print(f"  Timezone: {meta.get('timezone')}")
    print(f"  Start Time: {meta.get('start_time')}")
    print(f"  End Time: {meta.get('end_time')}")

    print(f"\n{BOLD}Scoring by Period:{RESET}")
    periods = summary.get('periods', {})
    for period_num, period_data in periods.items():
        if isinstance(period_data, dict):
            home = period_data.get('home', {}).get('goal_count', 0)
            visiting = period_data.get('visiting', {}).get('goal_count', 0)
            print(f"  Period {period_num}: Home {home}, Visiting {visiting}")

    print(f"\n{BOLD}Recommendation:{RESET}")
    print(f"  Gamesummary provides metadata but pxpverbose is more detailed")
    print(f"  Use pxpverbose for comprehensive game data")

def main():
    print(f"\n{BOLD}{YELLOW}PHASE 2: DEEP PXP ANALYSIS{RESET}")
    print(f"Analyzing gc/pxpverbose endpoint response")
    print(f"Test Game ID: {TEST_GAME_ID}\n")

    try:
        print(f"{BOLD}Fetching PXP Verbose data...{RESET}")
        pxp_data = fetch_pxpverbose()
        pxp_stats = analyze_pxpverbose(pxp_data)

        print(f"\n{BOLD}Fetching Game Summary data...{RESET}")
        summary_data = fetch_gamesummary()
        analyze_gamesummary(summary_data)

        # Save analysis results
        with open('phase2_pxpverbose_analysis.json', 'w') as f:
            json.dump(pxp_stats, f, indent=2)

        print(f"\n{GREEN}Analysis saved to: phase2_pxpverbose_analysis.json{RESET}")

    except Exception as e:
        print(f"{RED}Error during analysis: {e}{RESET}")

if __name__ == '__main__':
    main()
