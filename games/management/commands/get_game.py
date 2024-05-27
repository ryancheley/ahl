from django.core.management.base import BaseCommand
from program import write_game_data


class Command(BaseCommand):
    help = """
    This command will load game data from the specified game_id.
    """

    def add_arguments(self, parser):
        parser.add_argument("--game_id", type=int, help="The ID of the game to load")

    def handle(self, *args, **options):
        game_id = options["game_id"]
        write_game_data(game_id=game_id)
