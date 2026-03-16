# Pydantic SQLite Integration Guide

## Overview

`program.py` now uses **pydantic_sqlite** to automatically create and populate SQLite tables from Pydantic models. This replaces manual SQL and provides type-safe data validation.

## Key Architecture Decisions

### 1. Flattened Models
Nested Pydantic objects don't work well with pydantic_sqlite. Instead:
- **Removed**: Nested objects (e.g., `GameData` containing `Team`)
- **Added**: ID references (e.g., `GameData` has `away_team_id` and `home_team_id`)
- **Result**: Cleaner database schema matching relational design

**Example**:
```python
# Before
class GameData(BaseModel):
    away_team: Team  # ❌ Nested object

# After
class GameData(BaseModel):
    away_team_id: int  # ✅ Just the ID
```

### 2. Separate Table Per Entity
Each Pydantic model → One SQLite table:
- `Person` → `person` table
- `Team` → `team` table
- `GameData` → `gamedata` table
- `GamePenalties` → `gamepenalties` table
- etc.

## How pydantic_sqlite Works

### Database Initialization
```python
from pydantic_sqlite import DataBase

db = DataBase('my_database.db')
db.create(Team, if_not_exists=True)
db.create(GameData, if_not_exists=True)
```

This:
1. Creates `my_database.db` if it doesn't exist
2. Creates tables for each model (auto-derives SQL schema from fields)
3. Uses `if_not_exists=True` to skip if table already exists

### Inserting Data
```python
team = Team(team_id=1, team_code="LAK", active=True, name="LA Kings", city="LA", nickname="Kings")
db.insert(team)

# Or with replace (upsert)
db.insert(team, replace=True)
```

## Current Implementation

### Models (Lines 13-105)
All 12 Pydantic models defined:
- Core: `Person`, `Team`, `Venue`, `Season`
- Game: `GameData`, `GameOfficial`, `Player`
- Relationships: `GameRoster`, `Official`
- Penalties: `PenaltyClass`, `Penalty`, `GamePenalties`

All use **flat structure** with ID references instead of nested objects.

### Functions

#### `init_database()` → `DataBase`
Creates all tables. Call once at startup.
```python
db = init_database()  # Creates my_database.db with all 12 tables
```

#### `get_season_ids()` → `list[int]`
Fetches available season IDs from API.

#### `get_season_game_ids(season_id: int)` → `list[int]`
Fetches all game IDs for a season.

#### `save_game_data(db: DataBase, game_id: int)` → `bool`
Fetches and saves ONE game's data:
1. Fetches game metadata → creates `GameData` instance
2. Fetches team data → creates `Team` instances (with `replace=True`)
3. Fetches penalties → creates `GamePenalties` instances
4. Inserts all into database
5. Returns `True` on success, `False` on error

#### `save_season_games(db: DataBase, season_id: int, limit: int = None)` → `int`
Fetches and saves all games in a season (with optional limit).

```python
# Save first 5 games of season 90
saved = save_season_games(db, season_id=90, limit=5)
```

#### `main()`
Default entry point:
1. Initializes database
2. Fetches season IDs
3. Processes first season (limited to 5 games for testing)
4. Prints summary

## Usage Examples

### Example 1: Load All Games from One Season
```python
db = init_database()
saved = save_season_games(db, season_id=90)
print(f"Saved {saved} games")
```

### Example 2: Load Specific Games
```python
db = init_database()
game_ids = [1027888, 1027889, 1027890]

for game_id in game_ids:
    save_game_data(db, game_id)
```

### Example 3: Query Data After Loading
```python
from pydantic_sqlite import DataBase

db = DataBase('my_database.db')

# Fetch all teams
teams = db.select(Team)
for team in teams:
    print(team.name)

# Fetch all penalties
penalties = db.select(GamePenalties)
for penalty in penalties:
    print(f"Game {penalty.game_id}: {penalty.minutes} min penalty")
```

## Database Schema

After running, `my_database.db` contains:

```
person
  ├─ person_id (PRIMARY KEY)
  ├─ first_name
  ├─ last_name
  └─ birth

team
  ├─ team_id (PRIMARY KEY)
  ├─ team_code
  ├─ active
  ├─ name
  ├─ city
  └─ nickname

gamedata
  ├─ game_id (PRIMARY KEY)
  ├─ season_id
  ├─ away_team_id (FK → team.team_id)
  ├─ away_team_score
  ├─ home_team_id (FK → team.team_id)
  ├─ home_team_score
  ├─ game_status
  ├─ game_date
  ├─ game_attendance
  ├─ home_team_shots
  ├─ away_team_shots
  ├─ game_number
  └─ venue_id

gamepenalties
  ├─ game_id (FK → gamedata.game_id)
  ├─ home
  ├─ period_id
  ├─ powerplay
  ├─ bench
  ├─ penalty_shot
  ├─ minutes
  ├─ penalty
  ├─ time_of_penalty_seconds
  ├─ player_penalized
  └─ player_server

... (and 6 more tables)
```

## Running the Script

```bash
# Run with defaults (first 5 games of first available season)
python program.py

# Or customize in code:
if __name__ == "__main__":
    db = init_database()
    season_ids = get_season_ids()
    saved = save_season_games(db, season_ids[0], limit=100)
```

## Next Steps

### To expand:
1. **Add more data extraction** - Extract officials, game rosters, etc.
2. **Populate remaining models** - Fill `Player`, `GameRoster`, `GameOfficial` tables
3. **Add error handling** - Handle missing API fields gracefully
4. **Optimize** - Batch inserts for better performance on large datasets
5. **Add validation** - Use Pydantic validators to clean/validate data before insertion

### To query:
```python
from pydantic_sqlite import DataBase

db = DataBase('my_database.db')

# Get all games for a team
games = db.select(GameData, where={"home_team_id": 415})

# Custom queries
import sqlite3
conn = sqlite3.connect('my_database.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM gamedata WHERE season_id = 90")
rows = cursor.fetchall()
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `ProgrammingError: table already exists` | Use `if_not_exists=True` when creating |
| Fields not matching API response | Use Pydantic `Field(validation_alias="api_field_name")` |
| Nested objects in model | Flatten to ID references instead |
| `None` values in database | Add `Optional[type]` to model fields |

## References

- [pydantic_sqlite docs](https://github.com/reclaimworks/pydantic-sqlite)
- [Pydantic docs](https://docs.pydantic.dev/)
- [SQLite docs](https://www.sqlite.org/docs.html)
