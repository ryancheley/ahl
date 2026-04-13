# AHL Scraper

A Python web scraping application that collects comprehensive game data from the American Hockey League (AHL) and serves it through an interactive datasette interface.

## Features

- **42 Seasons of Historical Data** — Complete game records from Season 49 through Season 91 (12,799+ games)
- **Current Season Coverage** — Season 90 (2025-26) with 798 played games, including scores, attendance, goals, and penalties
- **Player Database** — 9,013+ players with biographical information
- **Game Rosters** — Complete roster data linking players to games (21,060+ entries)
- **Automated Updates** — Daily scheduled scraping to keep data current
- **Interactive Analytics** — Powered by [datasette](https://datasette.io/) for SQL-based data exploration

## Helpful Links

### Season 90 (2025-26) Analytics
- [Average Home Attendance by Team](https://ahl-data.ryancheley.com/games?sql=select+home_team%0A%2C+sum%28game_attendance%29+as+total_attendance%0A%2C+round%28avg%28game_attendance%29%2C0%29+as+avg_attendance%0A%2C+count%28%2A%29+as+games_played%0Afrom+games%0Awhere+strftime%28%27%25Y%27%2C+game_date%29+%3D+%272025%27%0Agroup+by+home_team%0Aorder+by+avg_attendance+desc)

- [Season 90 Game Statistics](https://ahl-data.ryancheley.com/games?sql=select+sum%28home_team_score%29+as+total_home_goals%0A%2C+sum%28away_team_score%29+as+total_away_goals%0A%2C+round%28avg%28home_team_score%29%2C2%29+as+avg_home_goals%0A%2C+round%28avg%28away_team_score%29%2C2%29+as+avg_away_goals%0A%2C+count%28%2A%29+as+total_games%0A%2C+round%28sum%28home_team_score%29+*+1.0+%2F+count%28%2A%29%2C2%29+as+goals_per_game%0Afrom+games%0Awhere+strftime%28%27%25Y%27%2C+game_date%29+%3D+%272025%27)

- [Browse All Games](https://ahl-data.ryancheley.com/games) — Filter by team, date, season, and more

- [Player Database](https://ahl-data.ryancheley.com/players) — 9,000+ player records with biographical information

## Getting Started

### Prerequisites
- Python 3.14+
- Just (recommended for command running)
- Docker (optional, for containerized deployment)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ryancheley/ahl.git
   cd ahl
   ```

2. **Install dependencies**
   ```bash
   just compile-all     # Compile all requirement files
   ```

3. **Run the scraper**
   ```bash
   just load            # Execute the main scraping script
   ```

### Common Commands

**Scraping & Data**
- `just load` — Execute the main scraping script
- `just game <game_id>` — Get specific game data
- `just recent` — Show most recent game ID

**Datasette**
- `just datasette` — Install datasette dependencies and serve data locally

**Testing**
- `pytest` — Run test suite

**Docker (Deployment)**
- `just build` — Build Docker images
- `just up` — Start Docker services
- `just down` — Stop Docker services
- `just logs` — View Docker service logs
- `just docker-test` — Build, start, and test both endpoints

See [CLAUDE.md](CLAUDE.md) for comprehensive development documentation.

## Architecture

The project uses SQLite for data storage:

- **my_database.db** — SQLite database with all scraped game data (games, goals, penalties, officials, players, game rosters, teams, arenas, conferences, divisions, seasons, dates)

### Data Flow

1. `program.py` scrapes the AHL website (lscluster.hockeytech.com)
2. Updates `my_database.db` with raw game data
3. Datasette provides interactive SQL interface at ahl-data.ryancheley.com

## Code Quality

- **Formatter**: ruff
- **Type Checker**: ty
- **Testing**: pytest-based test suite
- **Pre-commit Hooks**: prek validates commit messages (emoji prefix), formatting, and requirements compilation
