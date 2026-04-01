# AHL Scraper - Claude Code Guidelines

## Project Overview
AHL game data scraper using HockeyTech APIs. Fetches games, players, officials, penalties, and rosters across 42 seasons (49-91).

## Technology Stack
- **Language**: Python 3.x
- **Package Manager**: uv
- **Type Checker**: ty (required, not mypy/pyright)
- **Database**: SQLite (`my_database.db`)
- **Dependencies**: httpx, pydantic, pydantic-sqlite, click, rich

## Development Workflow

### Before Committing
1. Run type checking: `uv run ty check`
2. Run linting: `uv run ruff check --fix`
3. Test commands: `uv run program.py --help` to verify CLI works

### Database Changes
- Always test schema changes on a copy of `my_database.db`
- Do NOT commit `my_database.db` - it's in .gitignore
- Document any schema changes in commit messages
- Test migrations with at least one full season scrape

### API Integration
- HockeyTech API key: `ccb91f29d6744675` (already in code, public from JS bundle)
- Base URL: `https://lscluster.hockeytech.com/feed/index.php`
- Available feeds: `modulekit`, `gc`, `statviewfeed`
- Rate limiting: No documented limits, but use reasonable delays for large scrapes

### Known Issues & Data Quirks
- **Empty strings in official data**: Some seasons (1, 47, 64, 76, 88) have games where API returns empty strings for official fields instead of omitting them. This causes `int('')` errors.
  - Fix: Check for empty strings before `int()` conversion
  - Affected: ~14 games out of 1,445 total (0.97%)

- **Playoff seasons**: Playoff season IDs = regular season ID + 2 to 8

- **Unplayed games**: Skip games with `None` team names (future/unscheduled games)

- **OT/Shootout detection**: Parse game status from HTML SCORING section, not inferred from goal periods

### Scraping Commands
```bash
# Load today's games
uv run program.py today

# Load entire season
uv run program.py season --season-id 90

# Load single game
uv run program.py game 1027888

# List available seasons
uv run program.py list_seasons

# Initialize database
uv run program.py init
```

### File Organization
- `program.py`: Main CLI application and database logic
- `my_database.db`: SQLite database (DO NOT COMMIT)
- `player_scrapper.py`: Legacy player scraper (separate from main CLI)
- `scraper_api.py`: API-based scraper (alternative to HTML scraping)

### Commit Messages
- Start with emoji (✨ feature, 🐛 fix, 🔧 chore, etc.)
- Reference issue number if applicable
- Keep first line under 70 characters

### Testing
- Test with smaller datasets first (`--limit 5`)
- Verify database consistency after scrapes: Check game count, player count, etc.
- Run `program.py season --season-id 90 --limit 10` before full scrapes

### Logging
The application uses Python's `logging` module with both file and console output:
- **Log files**: Located in `logs/ahl_scraper.log` (rotating file handler, max 10MB per file, 5 backups)
- **Console and file output**: Both respect the `--log-level` flag (default: ERROR)
- **Coverage**: API requests/responses, database operations, scraping progress, errors with full tracebacks

**Configure logging level** (applies only to console output):
```bash
# Default (ERROR level - only errors shown)
uv run program.py season --season-id 90

# Show informational messages
uv run program.py --log-level INFO season --season-id 90

# Show debug messages (verbose)
uv run program.py --log-level DEBUG season --season-id 90

# Show only warnings and errors
uv run program.py --log-level WARNING season --season-id 90
```

To access logs:
```bash
# View live logs (tail)
tail -f logs/ahl_scraper.log

# View recent logs
cat logs/ahl_scraper.log | head -100
```

Logged events include:
- API calls (URLs, response codes, timeouts, retries)
- Database operations (player loads, venue inserts, game saves)
- Command execution (start, completion, success/error counts)
- Data validation and edge cases
- **Exceptions**: Full error details and stack traces (logged at ERROR level with `exc_info=True`)

When errors occur:
- Console shows brief error message (in red)
- Log file captures full exception details including traceback
- Use `--log-level DEBUG` to see detailed operation logs for troubleshooting

## Resolved Issues
1. ✅ `save_officials()` empty string handling (FIXED)
   - API sometimes returns empty strings for official fields instead of omitting them
   - Solution: Check for empty strings before `int()` conversion, convert to 0
   - Location: `save_officials()` at line 1075-1087
   - Status: All exceptions logged with full traceback at ERROR level

## Performance Notes
- Full season scrape (~1,150 games) takes ~2-3 minutes per season
- Parallel scraping of multiple seasons not yet implemented
- Consider caching season data to avoid repeated API calls in `get_seasons_with_names()`
