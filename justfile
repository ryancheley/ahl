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
    docker compose build

@up:
    docker compose up -d

@down:
    docker compose down

@logs:
    docker compose logs -f

@docker-test:
    docker compose up --build -d && sleep 2 && curl http://localhost:8000/admin/ && curl http://localhost:8001/