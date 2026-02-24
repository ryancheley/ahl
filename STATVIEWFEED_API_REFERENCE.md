# StatViewFeed API Reference - Complete Specification

## API Overview

Base URL: `https://lscluster.hockeytech.com/feed/index.php`

The statviewfeed API provides access to AHL player and roster data through a simple HTTP GET interface returning JSON/JSONP responses.

---

## Authentication

### API Key
```
Parameter: key
Value: ccb91f29d6744675
Required: Yes
Type: Static (appears to not expire)
Usage: All requests require this key
Failure: Returns "Invalid key." (plain text) if missing
```

---

## Endpoints

### 1. Player Data Endpoint

**Purpose:** Retrieve biographical and statistical information about a specific player.

**URL Pattern:**
```
https://lscluster.hockeytech.com/feed/index.php?
  feed=statviewfeed
  &view=player
  &player_id={player_id}
  &season_id=90
  &site_id=3
  &key=ccb91f29d6744675
  &client_code=ahl
  &league_id=4
  &lang=1
  &statsType=skaters
```

**Parameters:**

| Parameter | Type | Required | Example | Notes |
|-----------|------|----------|---------|-------|
| feed | string | Yes | statviewfeed | Only supported feed |
| view | string | Yes | player | Only valid view for player data |
| player_id | integer | Yes | 988 | Unique player identifier |
| season_id | integer | Yes | 90 | Appears to be constant (90 = current) |
| site_id | integer | Yes | 3 | Appears to be constant (3 = AHL) |
| key | string | Yes | ccb91f29d6744675 | API authentication key |
| client_code | string | Yes | ahl | League identifier |
| league_id | integer | Yes | 4 | League code (4 = AHL) |
| lang | integer | Yes | 1 | Language (1 = English) |
| statsType | string | Yes | skaters | Type of player data (skaters vs. goaltenders) |

**Response Format:** JSON/JSONP

**Response Structure:**
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
      "birthPlace": "Vermilion, AB",
      "drafts": [
        {
          "draft_team": "Colorado",
          "draft_year": "2002",
          "draft_round": "2",
          "draft_rank": "34"
        }
      ]
    }
  }
)
```

**HTTP Status Codes:**
- 200 - Success
- 400 - Invalid parameters

**Success Indicators:**
- Response starts with `(`
- Contains `"info"` key with player data
- No `"error"` key

**Failure Indicators:**
- Plain text response "Invalid key." (no API key)
- Plain text response "Client access denied." (missing client_code)
- JSON with `"error"` key (no other failure modes observed for valid view)

**Notes:**
- Response is JSONP-wrapped (parentheses must be stripped)
- Player must exist in database; non-existent players return empty list `[]`
- No rate limiting observed

---

### 2. Game Roster Endpoint

**Purpose:** Retrieve team rosters for a specific game.

**URL Pattern:**
```
https://lscluster.hockeytech.com/feed/index.php?
  feed=statviewfeed
  &view=roster
  &game_id={game_id}
  &season_id=90
  &site_id=3
  &key=ccb91f29d6744675
  &client_code=ahl
  &league_id=4
  &lang=1
```

**Parameters:**

| Parameter | Type | Required | Example | Notes |
|-----------|------|----------|---------|-------|
| feed | string | Yes | statviewfeed | Only supported feed |
| view | string | Yes | roster | Only valid view for game rosters |
| game_id | integer | Yes | 1027888 | Unique game identifier |
| season_id | integer | Yes | 90 | Appears to be constant |
| site_id | integer | Yes | 3 | Appears to be constant |
| key | string | Yes | ccb91f29d6744675 | API authentication key |
| client_code | string | Yes | ahl | League identifier |
| league_id | integer | Yes | 4 | League code (4 = AHL) |
| lang | integer | Yes | 1 | Language (1 = English) |

**Response Format:** JSON/JSONP

**Response Structure:**
```json
(
  {
    "teamName": null,
    "teamLogo": "https://lscluster.hockeytech.com/download.php?file_path=img/logos/0_90.jpg&liaf=1&client_code=ahl",
    "seasonName": "2025-26 Regular Season",
    "divisionName": "",
    "roster": [
      {
        "sections": [
          {
            "title": "Forwards",
            "headers": {
              "tp_jersey_number": { "properties": { ... } },
              "name": { "properties": { ... } },
              "position": { "properties": { ... } },
              "shoots": { "properties": { ... } }
            },
            "rows": [
              {
                "tp_jersey_number": "23",
                "name": "Player Name",
                "position": "C",
                "shoots": "R",
                "height_hyphenated": "5-11",
                "weight": "185"
              }
            ]
          },
          {
            "title": "Defensemen",
            "rows": [ ... ]
          },
          {
            "title": "Goaltenders",
            "rows": [ ... ]
          }
        ]
      }
    ]
  }
)
```

**HTTP Status Codes:**
- 200 - Success

**Success Indicators:**
- Response starts with `(`
- Contains `"roster"` key with array of rosters
- Contains team sections with player data

**Notes:**
- Response is JSONP-wrapped (parentheses must be stripped)
- Only returns one team's roster in the current example
- Player rows contain standardized fields with consistent structure

---

## Data Fields Reference

### Player Info Fields
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| firstName | string | "Grant" | First name |
| lastName | string | "McNeill" | Last name |
| position | string | "D" | Playing position (C, RW, LW, D, G) |
| height | string | "6-2" | Height in feet-inches format |
| weight | string | "214" | Weight in pounds |
| shoots | string | "L" | Shooting hand (L or R) |
| birthDate | string | "1983-06-08" | ISO 8601 format |
| birthPlace | string | "Vermilion, AB" | City and province/state |
| drafts | array | [ ... ] | Draft history (array of draft objects) |

### Draft Object Fields
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| draft_team | string | "Colorado" | Team that drafted |
| draft_year | string | "2002" | Year of draft |
| draft_round | string | "2" | Draft round |
| draft_rank | string | "34" | Pick number in round |

### Roster Row Fields
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| tp_jersey_number | string | "23" | Jersey number |
| name | string | "John Smith" | Player name |
| position | string | "C" | Position |
| shoots | string | "R" | Shooting hand |
| height_hyphenated | string | "5-11" | Height in feet-inches |
| weight | string | "185" | Weight in pounds |

---

## Error Handling

### Possible Error Responses

| Error | HTTP Code | Cause | Solution |
|-------|-----------|-------|----------|
| "Invalid key." | 200 | API key missing or invalid | Add valid key parameter |
| "Client access denied." | 200 | client_code missing | Add client_code=ahl |
| `{"error": "InvalidView error: {view}"}` | 200 | Unsupported view parameter | Use only "player" or "roster" |
| No response / Timeout | N/A | Rate limiting or server issue | Add delay between requests |

---

## Rate Limiting & Best Practices

### Observed Behavior
- No explicit rate limiting detected
- 100+ consecutive requests completed without throttling
- Recommend 0.2-0.5 second delays between requests for courtesy

### Best Practices
1. Always include all required parameters
2. Strip JSONP wrapper before JSON parsing
3. Handle missing/empty fields gracefully
4. Cache player data locally when possible
5. Use connection pooling for multiple requests
6. Set request timeout to 10 seconds minimum

---

## Implementation Examples

### Python Implementation

```python
import requests
import json

API_KEY = "ccb91f29d6744675"

def fetch_player_data(player_id):
    """Fetch player data from statviewfeed API"""
    url = (
        "https://lscluster.hockeytech.com/feed/index.php"
        "?feed=statviewfeed&view=player"
        f"&player_id={player_id}&season_id=90&site_id=3"
        f"&key={API_KEY}&client_code=ahl&league_id=4&lang=1"
        "&statsType=skaters"
    )

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None

    # Strip JSONP wrapper
    text = response.text.strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]

    return json.loads(text)


def fetch_game_roster(game_id):
    """Fetch game roster from statviewfeed API"""
    url = (
        "https://lscluster.hockeytech.com/feed/index.php"
        "?feed=statviewfeed&view=roster"
        f"&game_id={game_id}&season_id=90&site_id=3"
        f"&key={API_KEY}&client_code=ahl&league_id=4&lang=1"
    )

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None

    # Strip JSONP wrapper
    text = response.text.strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]

    return json.loads(text)
```

---

## Limitations & Known Issues

1. **No Game Details API**
   - No endpoint exists for goals, penalties, officials via JSON
   - Must use HTML scraping for game event data

2. **Limited View Support**
   - Only "player" and "roster" views work
   - All other game-related views return InvalidView errors

3. **Static Parameters**
   - season_id, site_id, league_id appear to be fixed values
   - May need verification if used across different leagues/seasons

4. **No Documentation**
   - API is undocumented, discovered through testing
   - May change without notice

---

## Related Endpoints

For game details (goals, penalties, officials), use HTML scraping:
```
https://lscluster.hockeytech.com/game_reports/official-game-report.php
  ?client_code=ahl&game_id={game_id}
```

---

## Version History

| Date | Status | Notes |
|------|--------|-------|
| 2025-02-22 | Current | API specification created |
| 2025-02-21 | Investigation | Systematic testing of 52+ endpoints |
| 2025-02-20 | Discovery | Game roster endpoint identified |

---

## Contact / Support

For implementation details in the AHL project, see:
- `player_scrapper.py` - Working implementation of player endpoint
- `program.py` - Uses HTML scraping for game details
- `STATVIEWFEED_INVESTIGATION_SUMMARY.md` - Full investigation report
