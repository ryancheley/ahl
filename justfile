@run:
    python manage.py runserver

@game game_id:
    python manage.py get_game --game_id={{game_id}}

@load:
    python program.py

@recent:
    python manage.py most_recent

@django:
    pip-compile requirements-django.in -o requirements-django.txt
    pip install -r requirements-django.txt

@datasette:
    pip-compile requirements-datasette.in -o requirements-datasette.txt

@compile-all:
    pip-compile requirements.in -o requirements.txt
    pip-compile requirements-django.in -o requirements-django.txt
    pip-compile requirements-datasette.in -o requirements-datasette.txt

@build:
    docker build -t ahl .

@up:
    docker run -p 8001:8001 ahl

@lint:
    uv run ruff check .
    uv run ty check
