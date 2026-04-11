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

@docker-cp-db:
    docker cp my_database.db $(docker ps -q --filter ancestor=ahl):/data/my_database.db

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

# Monte Carlo Game Predictor

@datasette:
    uv run datasette serve my_database.db \
        --metadata metadata.yaml \
        --plugins-dir plugins \
        --template-dir plugins/templates \
        --host 127.0.0.1 --port 8001

@mc-init:
    uv run retrain.py init

@mc-train season_id="90":
    uv run retrain.py train --season-id {{season_id}}

@mc-status:
    uv run retrain.py status