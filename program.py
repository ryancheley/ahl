"""
HTML parsing utilities for AHL game data.

This module provides utility functions for parsing HTML game reports
from the hockeytech API and extracting game details.

Used by: scrapper.py (main game scraper)
"""

from datetime import datetime
import re

import requests

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Agent": "Ryan",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Cookie": "PHPSESSID=7po31mvdjpu7mj978ft8hssqod",
    "Host": "lscluster.hockeytech.com",
    "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def get_team(game_details, home_or_away):
    if home_or_away == "home":
        team_details = re.split(" at | - ", game_details[0])[1]
    else:
        team_details = re.split(" at | - ", game_details[0])[0]
    match = re.search(r"\d+", team_details)
    if match is None:
        return ""
    team_score_position = match.span()
    team_score_start = team_score_position[0]
    return team_details[:team_score_start].strip()


def get_away_team(game_details):
    return get_team(game_details, "away")


def get_home_team(game_details):
    return get_team(game_details, "home")


def get_score(game_details, home_or_away):
    if home_or_away == "home":
        team_details = re.split(" at | - ", game_details[0])[1]
    else:
        team_details = re.split(" at | - ", game_details[0])[0]
    match = re.search(r"\d+", team_details)
    if match is None:
        return ""
    team_score_position = match.span()
    team_score_start = team_score_position[0]
    team_score_end = team_score_position[1]
    return team_details[team_score_start:team_score_end]


def get_away_team_score(game_details):
    return get_score(game_details, "away")


def get_home_team_score(game_details):
    return get_score(game_details, "home")


def get_game_status(game_details):
    return re.split(" at | - ", game_details[0])[2].replace("Status: ", "")


def get_date(game_details):
    date_format = "%A, %B %d, %Y"
    date_details = re.split(" - ", game_details[1])[0]
    return datetime.strptime(date_details, date_format)


def get_attendance(game_details):
    try:
        attendance = int(game_details[-3].replace("A-", "").replace(",", ""))
    except ValueError:
        attendance = 0
    return attendance


def get_shots_on_goal(game_details, home_or_away):
    shots = game_details[-6].replace("Shots on Goal-", "").split(".")
    if home_or_away == "home":
        team_details = shots[1].split("-")[-1]
    else:
        team_details = shots[0].split("-")[-1]
    return team_details


def get_game_details(response: requests.Response):
    for i in response.text.split("\n"):
        line_item = i.strip()
        try:
            start_item = line_item[0]
            if start_item != "<" and start_item != "(":
                game_details = []
                page_details = line_item.split("<br />")
                for item in page_details:
                    if item != "":
                        game_details.append(item)
                return game_details
        except IndexError:
            game_details = ['{"error": "No such game"}']


