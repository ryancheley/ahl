@run:
    python manage.py runserver

@game game_id:
    python manage.py get_game --game_id={{game_id}}

@load:
    python program.py

@recent:
    python manage.py most_recent

@django:
    pip-compile django-requirements.in
    pip install -r django-requirements.txt

# Docker Development Recipes

@dev:
    @docker-simple

@docker-simple:
    docker-compose -f docker-compose.simple.yml up --build

@up:
    docker-compose -f docker-compose.simple.yml up -d

@down:
    docker-compose -f docker-compose.simple.yml down

@logs:
    docker-compose -f docker-compose.simple.yml logs -f

@logs-django:
    docker-compose -f docker-compose.simple.yml logs -f django

@logs-datasette:
    docker-compose -f docker-compose.simple.yml logs -f datasette

@ps:
    docker-compose -f docker-compose.simple.yml ps

@restart:
    docker-compose -f docker-compose.simple.yml restart

@clean:
    docker-compose -f docker-compose.simple.yml down -v --remove-orphans

@nginx:
    docker-compose -f docker-compose.dev.yml up --build

# Coolify Deployment

@coolify-build:
    docker-compose -f docker-compose.yaml build

@coolify-up:
    docker-compose -f docker-compose.yaml up -d

@coolify-down:
    docker-compose -f docker-compose.yaml down

@coolify-logs:
    docker-compose -f docker-compose.yaml logs -f

@coolify-logs-django:
    docker-compose -f docker-compose.yaml logs -f django

@coolify-logs-datasette:
    docker-compose -f docker-compose.yaml logs -f datasette

# Django Management Commands in Docker

@django-admin:
    docker-compose -f docker-compose.simple.yml exec django python manage.py

@django-shell:
    docker-compose -f docker-compose.simple.yml exec django python manage.py shell

@django-migrate:
    docker-compose -f docker-compose.simple.yml exec django python manage.py migrate

@django-collectstatic:
    docker-compose -f docker-compose.simple.yml exec django python manage.py collectstatic --noinput

@django-load-dates:
    docker-compose -f docker-compose.simple.yml exec django python manage.py load_dates

# Database Management

@db-console:
    docker-compose -f docker-compose.simple.yml exec django python manage.py dbshell

@db-games:
    docker-compose -f docker-compose.simple.yml exec datasette sqlite3 /app/games.db

# Superuser Management

@createsuperuser:
    docker-compose -f docker-compose.simple.yml exec django python manage.py createsuperuser

@createsuperuser-local:
    python manage.py createsuperuser

# Testing

@test:
    pytest

@test-watch:
    pytest --watch

# Code Quality

@lint:
    black .

@type-check:
    ty

@format:
    black .