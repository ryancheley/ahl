# StatViewFeed API Investigation - Complete Technical Report

## Executive Summary

Investigation into the HockeyTech `statviewfeed` API endpoint to determine if it can provide game details (goals, penalties, officials) alongside the player data it currently supplies.

**Result:** The endpoint **does not support game details via JSON API**. Only player and roster data are available through this endpoint.

---

## Investigation Methodology

### Phase 1: Systematic Parameter Testing
- Tested 52+ endpoint variations with different `view` parameters
- Tested different `statsType` values
- Tested minimal vs. full parameter combinations
- Tested season_id variations

### Phase 2: Alternative Parameter Names
- Tested replacing `game_id` with `match_id`
- Tested adding `team_id` parameters
- Tested alternative feed names (`gameviewfeed`, `game`)

### Phase 3: Alternative API Patterns
- Tested REST-style endpoints (`/api/v1/games/{id}`)
- Tested direct statviewfeed paths (`/statviewfeed/game/{id}`)
- Tested theahl.com and external APIs
- Tested alternative domain names

### Phase 4: HTML Scraping Verification
- Confirmed HTML reports contain game details
- Tested official and text game report endpoints
- Verified public website access

---

## Test Results

### Working Endpoints

#### 1. Player Data (Confirmed Working)
```
Endpoint: https://lscluster.hockeytech.com/feed/index.php
Feed: statviewfeed
View: player
Parameter: player_id (required)
Response: JSON/JSONP
Status: ✓ 200 OK
Data: Player biographical information
```

**Example Request:**
```
https://lscluster.hockeytech.com/feed/index.php
  ?feed=statviewfeed
  &view=player
  &player_id=988
  &season_id=90
  &site_id=3
  &key=ccb91f29d6744675
  &client_code=ahl
  &league_id=4
  &lang=1
  &statsType=skaters
```

**Example Response:**
```json
(
  {
    "info": {
      "firstName": "Grant",
      "lastName": "McNeill",
      "position": "D",
      "height": "6-2",
      "weight": "214",
      "shoots": "L",
      "birthDate": "1983-06-08",
      "birthPlace": "Vermilion, AB"
    }
  }
)
```

---

#### 2. Game Rosters (Newly Discovered)
```
Endpoint: https://lscluster.hockeytech.com/feed/index.php
Feed: statviewfeed
View: roster
Parameter: game_id (required)
Response: JSON/JSONP
Status: ✓ 200 OK
Data: Team rosters for both teams
```

**Example Request:**
```
https://lscluster.hockeytech.com/feed/index.php
  ?feed=statviewfeed
  &view=roster
  &game_id=1027888
  &season_id=90
  &site_id=3
  &key=ccb91f29d6744675
  &client_code=ahl
  &league_id=4
  &lang=1
```

**Example Response Structure:**
```json
(
  {
    "teamName": null,
    "teamLogo": "https://lscluster.hockeytech.com/download.php?file_path=img/logos/...",
    "seasonName": "2025-26 Regular Season",
    "divisionName": "",
    "roster": [
      {
        "sections": [
          {
            "title": "Forwards",
            "headers": { ... },
            "rows": [ ... ]
          },
          {
            "title": "Defenders",
            "rows": [ ... ]
          }
        ]
      }
    ]
  }
)
```

---

### Failed Endpoints (All Tested)

The following `view` parameters were tested with `game_id` parameter and all returned `{"error": "InvalidView error: {view_name}"}`:

| View Parameter | Status | HTTP Code | Response |
|---|---|---|---|
| game | ✗ | 200 | InvalidView error: game |
| gamestats | ✗ | 200 | InvalidView error: gamestats |
| gamedetails | ✗ | 200 | InvalidView error: gamedetails |
| gamescore | ✗ | 200 | InvalidView error: gamescore |
| gamereport | ✗ | 200 | InvalidView error: gamereport |
| boxscore | ✗ | 200 | InvalidView error: boxscore |
| summary | ✗ | 200 | InvalidView error: summary |
| goals | ✗ | 200 | InvalidView error: goals |
| penalties | ✗ | 200 | InvalidView error: penalties |
| officials | ✗ | 200 | InvalidView error: officials |
| scoresheet | ✗ | 200 | InvalidView error: scoresheet |
| officialsummary | ✗ | 200 | InvalidView error: officialsummary |
| goalssummary | ✗ | 200 | InvalidView error: goalssummary |
| penaltiesummary | ✗ | 200 | InvalidView error: penaltiesummary |

**Total failed attempts:** 14+ different view names

---

## HTML Scraping Alternative

Since no JSON API exists for game details, the following HTML endpoints provide the necessary data:

### Official Game Report
```
https://lscluster.hockeytech.com/game_reports/official-game-report.php
  ?client_code=ahl&game_id=1027888
```

- **Status:** 200 OK
- **Size:** ~20KB
- **Format:** HTML
- **Contains:**
  - Game summary and scores
  - All goals with scorers, assists, time, period
  - All penalties with player, type, duration, period
  - Officials (referees and linesmen)
  - Team rosters
  - Game statistics

---

## API Key Analysis

### Key Information
- **Key:** `ccb91f29d6744675` (static, non-expiring)
- **Location:** Currently in `player_scrapper.py` and `program.py`
- **Required:** YES - requests without key return "Invalid key."
- **Scope:** Works for both `player` and `roster` views

### Additional Parameters
All requests require these parameters (appear to be constants):
- `season_id=90`
- `site_id=3`
- `league_id=4`
- `lang=1`
- `client_code=ahl`

---

## Conclusion

### What This Means

1. **The statviewfeed API is NOT suitable for game details**
   - Only supports player and roster views
   - No game events (goals, penalties, officials) available via JSON

2. **Current implementation is correct**
   - `program.py` correctly uses HTML scraping for game details
   - `player_scrapper.py` correctly uses JSON API for player data
   - No changes needed to existing code

3. **Opportunity: Game Rosters**
   - The newly discovered `view=roster` parameter can provide structured JSON roster data
   - Could complement HTML-scraped game details
   - Provides both team information and rosters in standard JSON format

### Recommendations

**For game details (goals, penalties, officials):**
- Continue using HTML scraping from `/game_reports/official-game-report.php`
- This is reliable and provides all necessary data

**For team rosters:**
- Can optionally use `statviewfeed?view=roster&game_id={id}`
- Returns structured JSON instead of HTML parsing
- Provides consistent data format for API consumers

**For player data:**
- Continue using existing `player_scrapper.py` implementation
- `statviewfeed?view=player&player_id={id}` is fully functional

---

## Testing Scripts

Three comprehensive test scripts were created and validated:

1. **test_statviewfeed_game_details.py**
   - Systematic testing of all view parameters
   - Tests 52 different endpoint combinations
   - Identifies which views work vs. fail

2. **test_game_api_discovery.py**
   - Comprehensive API discovery across multiple domains
   - Tests JSON and HTML endpoints
   - Searches for embedded data in HTML

3. **validate_statviewfeed_endpoints.py**
   - Final validation of working endpoints
   - Demonstrates functionality with real data
   - Confirms absence of game details API

---

## Technical Appendix

### Supported Feeds
- ✓ `statviewfeed` - Works
- ✗ `gameviewfeed` - Not supported
- ✗ `game` - Not supported

### Supported Views (by feed type)
- **statviewfeed:**
  - ✓ `player` (with `player_id`)
  - ✓ `roster` (with `game_id`)
  - ✗ All other views tested

### Response Format
- Both endpoints return JSONP-formatted JSON
- Response is wrapped in parentheses: `({...})`
- Must strip wrapper before JSON parsing

### Rate Limiting
- No rate limiting observed
- ~0.3 second delays recommended between requests
- All 100+ test requests completed without throttling

---

## References

- **Working Player API:** `player_scrapper.py` lines 20-25
- **HTML Scraping:** `program.py` line 152
- **Test Results:** `statviewfeed_game_results.json` (52 endpoints tested)
