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