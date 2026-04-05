# Development Tasks

@lint:
    uv run ruff check . --fix
    uv run ty check

@test:
    uv run pytest

# Scraper CLI Commands

@today:
    uv run program.py today

@season season_id="90":
    uv run program.py season --season-id {{season_id}}

@game game_id:
    uv run program.py game {{game_id}}

@list-seasons:
    uv run program.py list_seasons

@init:
    uv run program.py init

# Docker Tasks

@docker-build:
    docker build -t ahl .

@docker-up:
    docker run --rm -p 8001:8001 ahl

@docker-logs:
    docker logs -f $(docker ps -q --filter ancestor=ahl)

@docker-shell:
    docker run --rm -it -p 8001:8001 --entrypoint /bin/bash ahl

# Docker Development (mount local code)

@docker-dev:
    docker run --rm -it -p 8001:8001 -v {{justfile_directory()}}:/app -w /app python:3.14-slim /bin/bash

# Cleanup

@clean:
    rm -rf .pytest_cache __pycache__ *.pyc logs/*.log
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Database sync

@db-push:
    scp my_database.db root@h-web-p-002:/data/my_database.db

@db-pull:
    cp my_database.db my_database.db.orig
    scp root@h-web-p-002:/data/my_database.db my_database.db