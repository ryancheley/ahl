from django.core.management.base import BaseCommand
from program import get_most_recent_game_id_to_check_for_data


class Command(BaseCommand):
    help = """
    This command will display the id of the most recent game played.
    """

    def handle(self, *args, **options):
        game_id = get_most_recent_game_id_to_check_for_data()
        print(f"Most recent game id: {game_id}")
