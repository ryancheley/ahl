# StatViewFeed API - Quick Reference Card

## What Works

### Player Data
```
https://lscluster.hockeytech.com/feed/index.php?
feed=statviewfeed&view=player&player_id=988&
season_id=90&site_id=3&key=ccb91f29d6744675&
client_code=ahl&league_id=4&lang=1&statsType=skaters
```
✓ Returns player info (name, position, height, weight, draft info)

### Game Rosters
```
https://lscluster.hockeytech.com/feed/index.php?
feed=statviewfeed&view=roster&game_id=1027888&
season_id=90&site_id=3&key=ccb91f29d6744675&
client_code=ahl&league_id=4&lang=1
```
✓ Returns team rosters (forwards, defensemen, goaltenders)

---

## What DOESN'T Work

### Game Details (Goals, Penalties, Officials)
All views below return `{"error": "InvalidView error: {view}"}`
- ✗ view=game
- ✗ view=boxscore
- ✗ view=goals
- ✗ view=penalties
- ✗ view=officials
- ✗ view=gamedetails
- ✗ All other game-related views

**No JSON API exists for game details.**

---

## Alternative: HTML Scraping

For game details, use:
```
https://lscluster.hockeytech.com/game_reports/official-game-report.php?
client_code=ahl&game_id=1027888
```
✓ HTML page containing all game data (what program.py uses)

---

## Key Parameters

| Parameter | Value | Required | Notes |
|-----------|-------|----------|-------|
| feed | statviewfeed | Yes | Only supported feed |
| view | player OR roster | Yes | Only these two work |
| player_id | {id} | For player view | Required for player data |
| game_id | {id} | For roster view | Required for rosters |
| key | ccb91f29d6744675 | Yes | Static API key |
| client_code | ahl | Yes | League code |
| season_id | 90 | Yes | Current season |
| site_id | 3 | Yes | AHL site code |
| league_id | 4 | Yes | AHL league code |
| lang | 1 | Yes | English |
| statsType | skaters | For player | Type of player data |

---

## Implementation

### Python
```python
import requests
import json

API_KEY = "ccb91f29d6744675"

# Player data
url = f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=player&player_id=988&season_id=90&site_id=3&key={API_KEY}&client_code=ahl&league_id=4&lang=1&statsType=skaters"
resp = requests.get(url)
text = resp.text.strip()
if text.startswith('(') and text.endswith(')'):
    text = text[1:-1]
data = json.loads(text)
```

---

## Response Format

Responses are JSONP (JSON wrapped in parentheses):
```
({"info": {...}})
```

**Must strip parentheses before JSON parsing.**

---

## Success Indicators
- ✓ HTTP 200
- ✓ Response starts with `(`
- ✓ Contains expected data key (`info` or `roster`)
- ✓ No `error` field

## Failure Indicators
- ✗ Plain text: "Invalid key."
- ✗ Plain text: "Client access denied."
- ✗ JSON: `{"error": "InvalidView error: ..."}`

---

## Files for Reference

| File | Purpose |
|------|---------|
| `player_scrapper.py` | Working implementation of player endpoint |
| `program.py` | Working HTML scraping for game details |
| `validate_statviewfeed_endpoints.py` | Validation test script |
| `STATVIEWFEED_API_REFERENCE.md` | Complete API specification |
| `STATVIEWFEED_INVESTIGATION_SUMMARY.md` | Full investigation report |
| `TEST_RESULTS_SUMMARY.txt` | Detailed test results |

---

## Bottom Line

1. **Statviewfeed = Player & Roster data only**
2. **No JSON API for game details exists**
3. **HTML scraping is the correct approach**
4. **Current implementation is correct**
