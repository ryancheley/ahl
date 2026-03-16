URLs that actually do something usefel

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
