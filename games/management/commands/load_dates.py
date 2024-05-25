from django.core.management.base import BaseCommand
from games.models import DimDate
from datetime import datetime, timedelta, timezone


class Command(BaseCommand):
    help = """
    This command will load the dim_date table with dates for a specified season.
    If the dates already exist, they will be ignored.
    """

    def add_arguments(self, parser):
        parser.add_argument("--start_date", type=str, help="The start date for the season (YYYY-MM-DD)")
        parser.add_argument("--end_date", type=str, help="The end date for the season (YYYY-MM-DD)")
        parser.add_argument("--phase", type=str, choices=["regular", "post"], help="The phase of the season (regular/post)")

    def handle(self, *args, **options):
        print("Loading dates...")
        naive_start_date = options["start_date"]
        naive_end_date = options["end_date"]
        aware_start_date = datetime.strptime(naive_start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        aware_end_date = datetime.strptime(naive_end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        phase = options["phase"]
        for i in range((aware_end_date - aware_start_date).days + 1):
            current_date = aware_start_date + timedelta(days=i)
            print(f"Processing date: {current_date}")
            DimDate.objects.get_or_create(date=current_date, season=current_date.year, season_phase=phase)
