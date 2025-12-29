# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AHL (American Hockey League) web scraper that collects game data and publishes it via Datasette. The project uses Django for organization but is primarily a data collection/processing application with minimal web interface.

## Key Commands

### Development
- `just run` - Start Django development server (port 8000)
- `just dev` or `just docker-simple` - Start Docker development environment (without nginx)
- `just dev-with-nginx` - Start Docker environment with nginx reverse proxy (production-like)
- `just dev-up` - Start Docker services in background
- `just dev-down` - Stop Docker services
- `just dev-logs` - Show all Docker logs
- `just dev-logs-django` - Show Django container logs
- `just dev-logs-datasette` - Show Datasette container logs

### Coolify Deployment
- `just coolify-build` - Build Coolify Docker images
- `just coolify-up` - Start Coolify services
- `just coolify-down` - Stop Coolify services
- `just coolify-logs` - Show all Coolify logs
- `just coolify-logs-django` - Show Django logs in Coolify
- `just coolify-logs-datasette` - Show Datasette logs in Coolify

### Database Operations
- `just django-admin <command>` - Run Django management commands in Docker
- `just django-shell` - Open Django shell in Docker
- `just django-migrate` - Run migrations in Docker
- `just django-load-dates` - Load date dimensions in Docker
- `just createsuperuser` - Create Django admin user in Docker
- `just createsuperuser-local` - Create Django admin user locally
- `just db-console` - Access Django database console in Docker
- `just db-games` - Access games database directly via sqlite3 in Docker

### Data Collection
- `just load` - Run the main scraper program.py to update game data
- `just recent` - Get most recent games data
- `just game <game_id>` - Retrieve specific game by ID

### Code Quality
- `just format` or `just lint` - Format code with Black
- `just type-check` - Run type checking with ty
- `just test` - Run pytest tests
- `just django` - Update Django dependencies

### Testing
- `just test-watch` - Run pytest with watch mode for development

## Database Architecture

### Multi-Database Setup
- **default**: Django's primary database (db.sqlite3) - minimal use
- **games**: Main database for all hockey data (games.db) - contains all models

### Database Router
The `GamesRouter` in `core/dbrouters.py` routes all `games` app operations to the games database. Models in the games app always use games.db.

### Key Models (games app)
- `Conference`, `Division`, `Season` - League structure
- `Team`, `Arena`, `Franchise` - Team/Arena information
- `DimDate` - Date dimension for analytics
- `TeamDatePoint` - Team statistics over time
- Games stored directly in games table

## Core Architecture

### Main Components
1. **Scraper (`program.py`)**:
   - Scrapes lscluster.hockeytech.com
   - Processes game details, attendance, teams
   - Updates SQLite database via Django models

2. **Django Structure**:
   - Minimal Django web interface
   - Management commands for specific operations
   - Datasette integration for publishing data

3. **Data Publishing**:
   - Data published to Vercel via Datasette
   - Live queries available at https://ahl-data.ryancheley.com/
   - SQL examples in README.md

### Testing
- Tests are in `tests/` directory
- Focus on scraper utility functions in `program.py`
- Use test data in `tests/parameters.py`
- Run with `pytest`

## Package Management

- Uses `uv` for package installation
- Dependencies managed via `requirements.in` and `requirements.txt`
- `pip-compile` used to generate requirements (via `just django`)

## Environment

- Environment variables in `.env`
- Django settings use `environ` for configuration
- Proxy headers configured for Coolify/Caddy deployment