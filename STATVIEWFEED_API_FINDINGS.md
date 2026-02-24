# StatViewFeed API Investigation - Final Findings

## Summary

After systematic testing of the HockeyTech `statviewfeed` endpoint, we have identified its capabilities and limitations for accessing AHL game data.

## Key Finding: Limited Game Details Support

**The `statviewfeed` endpoint does NOT provide a JSON API for game details (goals, penalties, officials).**

### What Works

#### 1. Player Data (Confirmed Working)
```
https://lscluster.hockeytech.com/feed/index.php
  ?feed=statviewfeed
  &view=player
  &player_id={id}
  &season_id=90
  &site_id=3
  &key=ccb91f29d6744675
  &client_code=ahl
  &league_id=4
  &lang=1
  &statsType=skaters
```

**Response:** JSON (JSONP) with player information including:
- Player name, position, height, weight, shoots
- Birth date and birthplace
- Draft information (team, year, round, pick)

**Status:** ✓ Fully functional and already implemented in `player_scrapper.py`

---

#### 2. Team Rosters (Working with Game ID)
```
https://lscluster.hockeytech.com/feed/index.php
  ?feed=statviewfeed
  &view=roster
  &game_id={id}
  &season_id=90
  &site_id=3
  &key=ccb91f29d6744675
  &client_code=ahl
  &league_id=4
  &lang=1
```

**Response:** JSON (JSONP) with team roster including:
- Team name and logo
- Season name
- Division name
- Player rosters organized by position (Forwards, Defensemen, Goaltenders)

**Status:** ✓ Works but only returns roster data, NOT game event data

---

### What Does NOT Work

The following `view` parameters were tested with `game_id` parameter:
- `game`, `gamestats`, `gamedetails`, `gamescore`, `gamereport`
- `boxscore`, `summary`, `goals`, `penalties`, `officials`
- `scoresheet`, `officialsummary`, `goalssummary`, `penaltiesummary`
- All returned: `{"error": "InvalidView error: {view_name}"}`

**Conclusion:** The `statviewfeed` feed **only accepts `player` and `roster` views**. Game-specific views are not supported.

---

## Alternative Data Sources

### 1. HTML Game Reports (Scrapeable)

#### Official Game Report
```
https://lscluster.hockeytech.com/game_reports/official-game-report.php
  ?client_code=ahl&game_id={id}
```

**Status:** 200 OK - Returns 20KB HTML page with complete game data

**Contains:**
- Game summary and final score
- Goals (with scorers, assists, time, period)
- Penalties (with player, type, duration, period)
- Officials (referees and linesmen)
- Team rosters for both teams
- Game statistics

**Note:** This is the HTML page that `program.py` parses

---

#### Text Game Report
```
https://lscluster.hockeytech.com/game_reports/text-game-report.php
  ?client_code=ahl&game_id={id}
```

**Status:** 200 OK - Returns 1.3KB text-based report

**Contains:**
- Lightweight text summary with goals and officials
- Smaller payload than HTML version

---

#### AHL Game Center (Public Website)
```
https://theahl.com/stats/game-center/{id}
```

**Status:** 200 OK - Returns 120KB public web page

**Contains:**
- Complete game details
- Interactive game center interface
- Player and team statistics

**Note:** Uses AngularJS frontend, no direct JSON API endpoint

---

## API Testing Summary

| Endpoint Type | URL | Result | Game ID Param | Data Type |
|---|---|---|---|---|
| statviewfeed player | /feed/index.php?feed=statviewfeed&view=player | ✓ Works | player_id | JSON/JSONP |
| statviewfeed roster | /feed/index.php?feed=statviewfeed&view=roster | ✓ Works | game_id | JSON/JSONP |
| statviewfeed game | /feed/index.php?feed=statviewfeed&view=game | ✗ Invalid | game_id | Error |
| statviewfeed boxscore | /feed/index.php?feed=statviewfeed&view=boxscore | ✗ Invalid | game_id | Error |
| Official Game Report | /game_reports/official-game-report.php | ✓ Works | game_id | HTML |
| Text Game Report | /game_reports/text-game-report.php | ✓ Works | game_id | HTML |

---

## Recommendations

### For Accessing Detailed Game Data:

**Option A: Continue with HTML Scraping (Current Approach)**
- Use existing `program.py` HTML parsing from `/game_reports/official-game-report.php`
- Reliable and provides all necessary data
- No additional API keys needed beyond what's already available

**Option B: Use Roster View for Team Information**
- Use `statviewfeed` with `view=roster` and `game_id` to get team rosters
- Complements the goals/penalties/officials from HTML scraping
- Returns structured JSON data for consistency

**Option C: Hybrid Approach**
1. Get game summary and events from `official-game-report.php` (HTML scraping)
2. Get team rosters from `statviewfeed?view=roster` (JSON API)
3. Get player details on demand from `statviewfeed?view=player` (JSON API)

---

## API Key Requirements

The working endpoints require:
- `key=ccb91f29d6744675` (static, already in player_scrapper.py)
- `client_code=ahl`
- `season_id=90` (appears to be constant)
- `site_id=3` (appears to be constant)
- `league_id=4` (appears to be constant)
- `lang=1` (appears to be constant)

All these parameters are already defined in `player_scrapper.py`.

---

## Testing Scripts

1. **test_statviewfeed_game_details.py** - Systematic testing of statviewfeed views
   - Tests 52 different endpoint combinations
   - Identifies which views support game_id parameter

2. **test_game_api_discovery.py** - Comprehensive API discovery
   - Tests JSON endpoints
   - Tests HTML endpoints
   - Searches for embedded data in pages

3. **api_focused_test.py** - Tests various base paths and parameter patterns

---

## Conclusion

The statviewfeed API is **limited to player and roster data only**. For detailed game information (goals, penalties, officials), we must either:
1. Continue using HTML scraping from official game reports
2. Switch to the public website (theahl.com) which doesn't have a direct JSON API

The current `program.py` approach using HTML scraping is the correct and necessary method for this data.
