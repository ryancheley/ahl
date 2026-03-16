# HockeyTech API URLs - Data Scraping Documentation

This document catalogues all API endpoints and URLs used for data scraping in the AHL Scraper project.

**API Provider**: HockeyTech (lscluster)  
**Base Domain**: `https://lscluster.hockeytech.com/feed/index.php`  
**API Key**: `ccb91f29d6744675`  
**Client Code**: `ahl`  
**League ID**: `4` (AHL)  

---

## 1. Player Data API

### Endpoint: StatViewFeed - Player View

**Purpose**: Fetch individual player biographical and draft information

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=player&player_id={player_id}&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1&statsType=skaters
```

**Parameters**:
- `feed`: `statviewfeed` - Specifies the data feed type
- `view`: `player` - Requests player-specific data
- `player_id`: Integer ID of the player to fetch
- `season_id`: `90` (2025-26 AHL Season)
- `site_id`: `3` (AHL site)
- `key`: API authentication key
- `client_code`: `ahl` - Client identifier
- `league_id`: `4` (AHL league)
- `lang`: `1` (English)
- `statsType`: `skaters` - Type of player statistics

**Response Format**: JSONP (wrapped JSON)

**Data Returned**:
- Player name and ID
- Position, height, weight
- Shoots (L/R)
- Birth date and birthplace
- Draft information (team, year, round, pick)

**Example Request**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=player&player_id=988&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1&statsType=skaters
```

---

## 2. Game Roster APIs

### 2.1 Endpoint: StatViewFeed - Roster View (Generic)

**Purpose**: Fetch game roster data (default team only)

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id={game_id}&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1
```

**Parameters**:
- `feed`: `statviewfeed`
- `view`: `roster` - Requests roster/game player data
- `game_id`: Integer ID of the game
- `season_id`: `90`
- `site_id`: `3`
- `key`: API key
- `client_code`: `ahl`
- `league_id`: `4`
- `lang`: `1`

**Response Format**: JSONP

**Data Returned**: Roster for single team (usually home team)

### 2.2 Endpoint: StatViewFeed - Roster View (Team-Specific)

**Purpose**: Fetch roster data for a specific team in a game

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id={game_id}&team_id={team_id}&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1
```

**Parameters** (in addition to above):
- `team_id`: Integer ID of the specific team (required for team-specific roster)

**Response Format**: JSONP

**Data Returned**:
- Team name and ID
- Players by section (Forwards, Defenders, Goalies)
- Jersey numbers
- Positions

**Example Requests**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id=1027888&team_id=415&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1
```

---

## 3. Game Center APIs (GC Feed)

### 3.1 Endpoint: GC - Play-by-Play Verbose

**Purpose**: Fetch complete game play-by-play data including all events, goals, and penalties

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=pxpverbose&game_id={game_id}&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl
```

**Parameters**:
- `feed`: `gc` - Game Center feed
- `tab`: `pxpverbose` - Play-by-play verbose data
- `game_id`: Integer game ID
- `season_id`: AHL season ID (e.g., 90 for 2025-26)
- `key`: API key
- `client_code`: `ahl`

**Response Format**: JSON (wrapped in GC object)

**Data Returned**:
- Complete play-by-play events
- All goals with scorer, assists, flags (power play, empty net, short-handed, penalty shot, game-winning, game-tying)
- All penalties with type, classification, and minutes
- Period information
- Event details including team ID and player information

**Example Request**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=pxpverbose&game_id=1027888&season_id=90&key=ccb91f29d6744675&client_code=ahl
```

### 3.2 Endpoint: GC - Game Summary

**Purpose**: Fetch complete game summary including metadata, officials, and final statistics

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=gamesummary&game_id={game_id}&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl
```

**Parameters**:
- `feed`: `gc`
- `tab`: `gamesummary` - Game summary data
- `game_id`: Integer game ID
- `season_id`: AHL season ID
- `key`: API key
- `client_code`: `ahl`

**Response Format**: JSON (wrapped in GC object)

**Data Returned**:
- Game metadata (date, time, status)
- Home and away team information (ID, name, code, city, division, conference)
- Final scores and shot counts
- Officials (referees, linesmen) with names and numbers
- Home and away team lineups with player stats
- Game status and timing information
- Attendance

**Example Request**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=gamesummary&game_id=1027888&season_id=90&key=ccb91f29d6744675&client_code=ahl
```

--- 

## 4. ModuleKit APIs

### 4.1 Endpoint: ModuleKit - Schedule

**Purpose**: Fetch season schedule with all games

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&tab=schedule&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl
```

**Parameters**:
- `feed`: `modulekit` - Module Kit feed
- `tab`: `schedule` - Season schedule
- `season_id`: AHL season ID
- `key`: API key
- `client_code`: `ahl`

**Response Format**: JSON

**Data Returned**:
- All games in season (including unplayed games)
- Game IDs, dates, times
- Home and away teams (ID, name, code)
- Current status and scores

**Example Request**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&tab=schedule&season_id=90&key=ccb91f29d6744675&client_code=ahl
```

### 4.2 Endpoint: ModuleKit - Standings

**Purpose**: Fetch season standings by division/conference

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&tab=standings&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl
```

**Parameters**:
- `feed`: `modulekit`
- `tab`: `standings` - League standings
- `season_id`: AHL season ID
- `key`: API key
- `client_code`: `ahl`

**Response Format**: JSON

**Data Returned**:
- Team standings organized by division/conference
- Wins, losses, overtime losses
- Points, games played
- Team rankings

### 4.3 Endpoint: ModuleKit - Teams

**Purpose**: Fetch team information for season

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&tab=teams&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl
```

**Parameters**:
- `feed`: `modulekit`
- `tab`: `teams` - Team data
- `season_id`: AHL season ID
- `key`: API key
- `client_code`: `ahl`

**Response Format**: JSON

**Data Returned**: Team roster and season information

### 4.4 Endpoint: ModuleKit - Roster (Team-Specific)

**Purpose**: Fetch full team roster for a season

**URL Template**:
```
https://lscluster.hockeytech.com/feed/index.php?feed=modulekit&tab=roster&team_id={team_id}&season_id={season_id}&key=ccb91f29d6744675&client_code=ahl&league_id=4
```

**Parameters**:
- `feed`: `modulekit`
- `tab`: `roster` - Team roster
- `team_id`: Team ID
- `season_id`: AHL season ID
- `key`: API key
- `client_code`: `ahl`
- `league_id`: `4`

**Response Format**: JSON

**Data Returned**: Full team roster with player details

---

## 5. API Authentication & Parameters

### Common Parameters Across All Endpoints

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `key` | `ccb91f29d6744675` | API authentication key (found in hockeytech JS bundle) |
| `client_code` | `ahl` | Client identifier for AHL |
| `league_id` | `4` | AHL league identifier |
| `site_id` | `3` | AHL site identifier |
| `lang` | `1` | Language (1 = English) |
| `season_id` | `90` | 2025-26 AHL season (primary focus) |

### Response Format Notes

- **JSONP responses** from StatViewFeed API are wrapped in parentheses: `(...)`
  - Must strip outer parentheses before parsing JSON
- **JSON responses** from GC and ModuleKit feeds are standard JSON
  - May be wrapped in objects like `{ "GC": {...} }` or `{ "SiteKit": {...} }`

---

## 6. Seasons Available via API

The following AHL seasons are available via the API:

| Season ID | Year(s) | Season Name |
|-----------|---------|-------------|
| 49 | 2014 | AHL Season 49 |
| 50 | 2014-15 | AHL Season 50 |
| 51 | 2015 | AHL Season 51 |
| 53 | 2016 | AHL Season 53 |
| 54 | 2016 | AHL Season 54 |
| 56 | 2016-17 | AHL Season 56 |
| 57 | 2017 | AHL Season 57 |
| 60 | 2017-18 | AHL Season 60 |
| 61 | 2018 | AHL Season 61 |
| 62-69 | 2018-2020 | Seasons 62-69 |
| 70 | 2003 | AHL Season 70 |
| 71-72 | 2020-21 | AHL Seasons 71-72 |
| 73 | 2021 | AHL Season 73 |
| 75-76 | 2021-22 | AHL Seasons 75-76 |
| 77 | 2022 | AHL Season 77 |
| 78-80 | 2022-23 | AHL Seasons 78-80 |
| 81 | 2023 | AHL Season 81 |
| 82-85 | 2023-24 | AHL Seasons 82-85 |
| 86 | 2024 | AHL Season 86 |
| 87-89 | 2024-25 | AHL Seasons 87-89 |
| 90 | 2025-26 | AHL Season 90 (Current) |
| 91 | Future | AHL Season 91 |

---

## 7. Usage Examples

### Fetch a Specific Player
```
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=player&player_id=988&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1&statsType=skaters
```

### Fetch Game Roster for Both Teams
```
# Home team (team_id=415)
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id=1027888&team_id=415&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1

# Away team (team_id=396)
https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=roster&game_id=1027888&team_id=396&season_id=90&site_id=3&key=ccb91f29d6744675&client_code=ahl&league_id=4&lang=1
```

### Fetch Complete Game Data
```
# Play-by-play
https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=pxpverbose&game_id=1027888&season_id=90&key=ccb91f29d6744675&client_code=ahl

# Game summary with officials
https://lscluster.hockeytech.com/feed/index.php?feed=gc&tab=gamesummary&game_id=1027888&season_id=90&key=ccb91f29d6744675&client_code=ahl
```

---

## 8. API Implementation Status

### Currently Implemented
- ✅ **Player Data Scraper**: `player_scrapper.py` (StatViewFeed player view)
- ✅ **Game Roster Scraper**: `player_scrapper.py` (StatViewFeed roster view with team_id)
- ✅ **Game Scraper (API-based)**: `scraper_api.py` (GC pxpverbose & gamesummary)
- ✅ **Schedule Fetcher**: Multiple scripts (ModuleKit schedule)

### Data Captured
- ✅ Player biographical information (9,000+ players)
- ✅ Game rosters (616,017 entries across 13,122 games)
- ✅ Game play-by-play (goals, penalties, events)
- ✅ Game metadata (scores, officials, attendance)
- ✅ Team information (32 unique teams)
- ✅ Season schedules (all 42 seasons)

---

## 9. Notes on API Behavior

### Important Findings

1. **Play-by-Play Completeness**: The GC pxpverbose endpoint captures all goals including overtime goals that HTML scraping missed.

2. **Officials Data**: Complete officials information (referees, linesmen) available exclusively through GC gamesummary endpoint.

3. **Team-Specific Rosters**: The StatViewFeed roster endpoint requires `team_id` parameter to fetch specific team rosters; without it, returns default (home) team.

4. **JSONP Parsing**: StatViewFeed endpoints return JSONP format requiring parentheses stripping before JSON parsing.

5. **Rate Limiting**: No explicit rate limiting observed; recommend reasonable request intervals for respectful API usage.

6. **Season ID Gaps**: Not all season IDs between 49-91 are available; follow documented season list.

---

## 10. References

- **Base API Documentation**: HockeyTech API (reverse-engineered from JS bundle)
- **Implementation Files**:
  - `player_scrapper.py` - Player and roster scraping
  - `scraper_api.py` - Game-centric API scraping
  - `roster_repopulator_both_teams.py` - Batch roster repopulation

**Last Updated**: February 26, 2026
