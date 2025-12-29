# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Using Just (Recommended)
- `just run` - Start Django development server
- `just load` - Execute main scraping script (program.py)
- `just game <game_id>` - Get specific game data via Django management command
- `just recent` - Show most recent game ID
- `just django` - Compile Django requirements

### Direct Python Commands
- `python manage.py runserver` - Start Django dev server
- `python program.py` - Run scraping script (update games.db)
- `python manage.py get_game --game_id=<id>` - Get specific game data
- `python manage.py most_recent` - Show most recent game ID
- `pytest` - Run all tests
- `pytest tests/test_utils.py` - Run specific test file
- `black .` - Format code (line length: 130)
- `pip-compile requirements.in` - Update dependencies

## Architecture Overview

### Project Type
AHL Scraper is a Python web scraping + Django web application that collects game data from the American Hockey League (AHL) website and serves it through a Django admin interface with datasette for data visualization.

### Multi-Database Architecture
- **games.db** - SQLite database for scraped game data (managed directly by scraper)
- **db.sqlite3** - Django default database for application data

Database operations are routed by `core.dbrouters.GamesRouter` - models in the `games` app read/write to `games.db`, while all other operations use the default database.

### Key Applications
- **games** - Main Django app with models for scraped data (Conference, Division, Team, Arena, Season, DimDate, TeamDatePoint, Game)
- **core** - Project configuration with multi-database router and settings

### Data Flow
1. `program.py` scrapes AHL website (lscluster.hockeytech.com) directly
2. Updates `games.db` using SQLite (not Django migrations)
3. Django models provide ORM access to existing tables
4. Data served via datasette at ahl-data.ryancheley.com

## Development Workflow

### Scraping Development
- Tables in `games.db` must be created via direct SQLite commands
- Django models added after table creation (not the other way around)
- Use `just load` to run scraper and update database

### Testing
- pytest-based test suite in `tests/` directory
- Tests use mocked responses for scraping functions
- Run tests with `pytest` before committing changes

### Code Quality
- Black formatter enforces 130-character line length
- Pre-commit hooks validate:
  - Commit messages must start with emoji (`^[\p{Emoji}]:.{0,65}$`)
  - Code formatting with Black
  - Requirements compilation

### Deployment
- Automated via GitHub Actions (runs daily at 12:13 UTC)
- Updates games.db and commits with timestamp
- After PR merges, switch back to main and pull changes

## Important Conventions

### Database Schema
The `games.db` schema includes:
- Games (scores, attendance, teams, dates)
- Teams, Arenas, Conferences, Divisions
- DimDate (dimension table with seasons and phases)
- TeamDatePoint (team performance over time)

### Environment Configuration
- Uses `django-environ` for environment variables
- `.env` file contains SECRET_KEY and DEBUG settings
- WhiteNoise middleware serves static files in production

### Data Access
- Primary data access via datasette SQL queries
- Pre-built queries in `metadata.yaml` for common analyses
- Django admin interface available for browsing data
- API endpoints provided by datasette

## Testing Specific Games
To test a specific game:
1. Get the game ID: `python manage.py most_recent`
2. Fetch game data: `python manage.py get_game --game_id=<id>`
3. Verify in datasette or Django admin

## File Structure Notes
- `program.py` - Main scraper (imports directly from games.models)
- `dim_date.py` - Season date definitions loaded via Django management command
- `data-to-update.py` - Database update utilities
- `games/management/` - Custom management commands for data access