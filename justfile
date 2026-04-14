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

# Docker Compose Tasks

@up *ARGS:
    docker compose up {{ ARGS }}

@down:
    docker compose down

@logs:
    docker compose logs -f

@shell:
    docker compose exec datasette /bin/bash

@rebuild *ARGS:
    docker compose up --build {{ ARGS }}

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

# Local Datasette (without Docker)

@datasette:
    uv run datasette serve my_database.db \
        --metadata metadata.yaml \
        --plugins-dir plugins \
        --template-dir plugins/templates \
        --host 127.0.0.1 --port 8001

# Monte Carlo Game Predictor

@mc-init:
    uv run retrain.py init

@mc-train season_id="90":
    uv run retrain.py train --season-id {{season_id}}

@mc-status:
    uv run retrain.py status

@divisions season_id="90":
    uv run program.py divisions --season-id {{season_id}}