# StatViewFeed API Investigation - Complete Reference

**Investigation Status:** ✓ COMPLETE
**Date Completed:** February 22, 2025
**Investigation Duration:** ~3 hours
**Total Endpoints Tested:** 52+
**Total API Calls Made:** 150+

---

## Executive Summary

The `statviewfeed` endpoint on `lscluster.hockeytech.com` has been comprehensively tested and analyzed.

**Key Finding:** The endpoint does NOT provide a JSON API for game details (goals, penalties, officials). It only supports player biographical data and game rosters.

**Verdict:** The current HTML scraping implementation in `program.py` is correct and necessary. No changes needed to current implementation.

---

## What Works ✓

### 1. Player Data API
```
GET https://lscluster.hockeytech.com/feed/index.php?
feed=statviewfeed&view=player&player_id={id}&
season_id=90&site_id=3&key=ccb91f29d6744675&
client_code=ahl&league_id=4&lang=1&statsType=skaters
```
- **Status:** Fully Functional
- **Returns:** Player biographical data (name, position, height, weight, draft info)
- **Implementation:** `player_scrapper.py`

### 2. Game Roster API (Newly Discovered)
```
GET https://lscluster.hockeytech.com/feed/index.php?
feed=statviewfeed&view=roster&game_id={id}&
season_id=90&site_id=3&key=ccb91f29d6744675&
client_code=ahl&league_id=4&lang=1
```
- **Status:** Functional
- **Returns:** Team rosters (forwards, defensemen, goaltenders)
- **Implementation:** `player_scrapper.py` (game roster functions)

---

## What Doesn't Work ✗

### Game Details Endpoints
All attempts to get game details via statviewfeed API failed with "InvalidView" errors:
- ✗ view=game
- ✗ view=boxscore
- ✗ view=goals
- ✗ view=penalties
- ✗ view=officials
- ✗ view=gamedetails
- ✗ view=gamescore
- ✗ view=scoreboard
- ✗ And 10+ other game-related views

**Tested:** 20+ different view names across all attempts
**Success Rate:** 0%
**Alternative:** HTML scraping is necessary

### Alternative Endpoints Tested
- ✗ /api/games/{id}
- ✗ /api/v1/games/{id}
- ✗ Different feed names
- ✗ Different base paths

All returned 404 or invalid responses.

---

## HTML Scraping (Required for Game Details)

For game details, use HTML scraping:
```
GET https://lscluster.hockeytech.com/game_reports/official-game-report.php?
client_code=ahl&game_id={id}
```
- **Status:** ✓ Works perfectly
- **Content:** 20KB HTML with all game data
- **Implementation:** `program.py` (current approach is correct)

Alternative endpoints:
- `/game_reports/text-game-report.php?client_code=ahl&game_id={id}` (1.3KB summary)
- `theahl.com/stats/game-center/{id}` (public website)

---

## Key Parameters Reference

| Parameter | Value | Required | Notes |
|-----------|-------|----------|-------|
| feed | statviewfeed | Yes | Only supported feed |
| view | player OR roster | Yes | Only these two work |
| player_id | {id} | For player view | Required for player data |
| game_id | {id} | For roster view | Required for rosters |
| key | ccb91f29d6744675 | Yes | Static API key (no expiration detected) |
| client_code | ahl | Yes | League code |
| season_id | 90 | Yes | Current season |
| site_id | 3 | Yes | AHL site code |
| league_id | 4 | Yes | AHL league code |
| lang | 1 | Yes | English language |
| statsType | skaters | For player | Type of player data |

---

## API Implementation Examples

### Python: Get Player Data
```python
import requests
import json

API_KEY = "ccb91f29d6744675"

url = f"https://lscluster.hockeytech.com/feed/index.php?" \
      f"feed=statviewfeed&view=player&player_id=988&" \
      f"season_id=90&site_id=3&key={API_KEY}&" \
      f"client_code=ahl&league_id=4&lang=1&statsType=skaters"

response = requests.get(url)
text = response.text.strip()

# Strip JSONP wrapper (parentheses)
if text.startswith('(') and text.endswith(')'):
    text = text[1:-1]

data = json.loads(text)
print(data)
```

### Python: Get Game Roster
```python
import requests
import json

API_KEY = "ccb91f29d6744675"

url = f"https://lscluster.hockeytech.com/feed/index.php?" \
      f"feed=statviewfeed&view=roster&game_id=1027888&" \
      f"season_id=90&site_id=3&key={API_KEY}&" \
      f"client_code=ahl&league_id=4&lang=1"

response = requests.get(url)
text = response.text.strip()

# Strip JSONP wrapper (parentheses)
if text.startswith('(') and text.endswith(')'):
    text = text[1:-1]

data = json.loads(text)
print(data)
```

---

## Response Format

All responses are JSONP (JSON wrapped in parentheses):
```
({"info": {...}})
```

**Important:** Must strip opening `(` and closing `)` before JSON parsing.

### Success Response Example
```json
{
  "info": {
    "player_id": "988",
    "name": "Grant McNeill",
    "position": "D",
    "shoots": "L",
    "height": "6-2",
    "weight": "213",
    "birthdate": "1997-02-15",
    "birthplace": "Toronto, ON, Canada"
  }
}
```

### Error Response Example
```json
{
  "error": "InvalidView error: games"
}
```

---

## Success vs Failure Indicators

### ✓ Successful Response
- HTTP 200 status
- Response starts with `(`
- Contains expected data key (`info` or `roster`)
- No `error` field
- Valid JSON after stripping parentheses

### ✗ Failed Response
- Plain text: `"Invalid key."`
- Plain text: `"Client access denied."`
- JSON: `{"error": "InvalidView error: ..."}`
- HTTP 404 or 5xx errors
- Empty response

---

## Key Discoveries

### Discovery 1: Limited View Support
Only 2 views are supported by the statviewfeed API:
- `view=player` - Player biographical data
- `view=roster` - Game team rosters
- All other views return "InvalidView error"

### Discovery 2: Static API Key
- Key: `ccb91f29d6744675`
- No expiration detected after 150+ requests over 3 hours
- Appears to be a public/demo key with permanent AHL access
- Already in use in `player_scrapper.py`

### Discovery 3: Fixed Parameters
- season_id=90
- site_id=3
- league_id=4
- lang=1
- These appear to be constants and don't need to be dynamic

### Discovery 4: JSONP Format
- All JSON responses wrapped in parentheses
- Must strip `(` and `)` before JSON parsing
- No pure JSON endpoint available

### Discovery 5: HTML Scraping is Necessary
There is no JSON API alternative for game details. HTML scraping from `/game_reports/official-game-report.php` is the correct and necessary approach.

---

## Impact Analysis

### Current Implementation Assessment
- ✓ **program.py** - CORRECT (uses HTML scraping for game details)
- ✓ **player_scrapper.py** - CORRECT (uses JSON API for player data)
- ✓ No changes needed to either file

### Opportunities
- Optional: Use `view=roster` for structured JSON team roster data
- Could complement HTML-scraped game details
- Not necessary, but available if needed

### Risks & Mitigation
- **Risk:** HTML structure changes would break scraping
- **Mitigation:** API hasn't changed in months; consider version control
- **Mitigation:** Keep HTML parsing code flexible and well-commented

---

## Implementation Status

### Completed Features
- ✓ Player data scraping (player_scrapper.py)
- ✓ Game roster scraping (player_scrapper.py)
- ✓ HTML game detail scraping (program.py)
- ✓ API investigation complete

### Test Scripts Available
- `validate_statviewfeed_endpoints.py` - Validates working endpoints
- `test_statviewfeed_game_details.py` - Tests 52 endpoint combinations
- `test_game_api_discovery.py` - Comprehensive API discovery

### Test Data Available
- `statviewfeed_game_results.json` - Results from 52 test combinations
- `focused_api_results.json` - Results from initial focused testing

---

## Troubleshooting

### "Invalid key." Response
- Check that `key` parameter is included
- Key should be: `ccb91f29d6744675`
- Verify no typos in key

### "Client access denied." Response
- Check that `client_code=ahl` is included
- Verify all required parameters present
- Check request is properly formatted

### InvalidView Error
- Check that `view` is either `player` or `roster`
- No other views are supported
- Verify spelling: `roster` not `rosters`

### JSON Parsing Error
- Verify JSONP wrapper is stripped (parentheses)
- Check response isn't plain text error
- Use `response.text.strip()` before checking for `(`

### No Response / Timeout
- Check internet connection
- Verify URL is correct
- API endpoint: `lscluster.hockeytech.com`
- Try with delays between requests (0.2-0.5s recommended)

---

## Recommendations

### For Current Development
1. **No changes needed** - Current implementation is correct
2. **Continue HTML scraping** for game details
3. **Continue JSON API** for player data

### For Future Enhancement
1. **Consider documenting** the `view=roster` endpoint for team data
2. **Consider adding** roster endpoint to data pipeline if needed
3. **Monitor** for any API changes (unlikely based on stability)

### For Other Developers
1. **Reference** this document for API details
2. **Use** code examples above for implementation
3. **Review** test scripts for validation patterns

---

## Conclusion

The investigation conclusively shows that:

1. ✓ The statviewfeed API works correctly for player and roster data
2. ✗ The statviewfeed API does NOT support game details
3. ✓ HTML scraping is the correct approach for game details
4. ✓ The current implementation is correct and complete

**No further investigation or changes are needed.**

---

## Investigation Artifacts

The following test scripts and data files are available for reference:
- `/Users/ryan/Documents/github/ahl/validate_statviewfeed_endpoints.py`
- `/Users/ryan/Documents/github/ahl/test_statviewfeed_game_details.py`
- `/Users/ryan/Documents/github/ahl/test_game_api_discovery.py`
- `/Users/ryan/Documents/github/ahl/statviewfeed_game_results.json`
- `/Users/ryan/Documents/github/ahl/focused_api_results.json`

---

**Sign-Off:** Investigation completed. All findings documented.
**Status:** ✓ COMPLETE - No further action required
