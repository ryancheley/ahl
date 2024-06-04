from django.core.management.base import BaseCommand

from bs4 import BeautifulSoup
import httpx

from games.models import Arena


def convert_to_float(value):
    try:
        degrees = value.split("°")
    except AttributeError:
        return value
    try:
        minutes = degrees[1].split("′")
    except:
        return value
    try:
        seconds = minutes[1].split("″")
    except:
        return value

    return float(degrees[0]) + float(minutes[0]) / 60 + float(seconds[0]) / 3600


class Command(BaseCommand):
    help = """
    This command will load the ltitidude and longitude of arenas with missing data
    """

    def handle(self, *args, **options):
        missing_arena_data = Arena.objects.filter(latitude=0, longitude=0)
        for i in missing_arena_data:
            wiki_link = "https://en.wikipedia.org/wiki/"
            clean_name = i.arena.replace(" ", "_")
            link = wiki_link + clean_name
            response = httpx.get(link)
            soup = BeautifulSoup(response.text, "html.parser")
            try:
                latitude = soup.find("span", class_="latitude").text
                longitude = soup.find("span", class_="longitude").text
            except AttributeError:
                latitude = 0
                longitude = 0
            latitude = convert_to_float(latitude)
            longitude = convert_to_float(longitude)
            i.latitude = latitude
            i.longitude = longitude
            print(f"Updating {i.arena} with latitude {latitude} and longitude {longitude}")
            i.save()
            print(f"Updated {i.arena} with latitude {latitude} and longitude {longitude}")
