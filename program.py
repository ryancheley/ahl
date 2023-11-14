from datetime import datetime
import re
import sqlite3
import time

import requests


def get_team(game_details, home_or_away):
    if home_or_away == "home":
        team_details = re.split(" at | - ", game_details[0])[1]
    else:
        team_details = re.split(" at | - ", game_details[0])[0]
    team_score_position = re.search(r"\d+", team_details).span()
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
    team_score_position = re.search(r"\d+", team_details).span()
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


def get_game_details(response: str):
    for i in response.text.split("\n"):
        line_item = i.strip()
        try:
            start_item = line_item[0]
            if start_item != "<":
                game_details = []
                page_details = line_item.split("<br />")
                for item in page_details:
                    if item != "":
                        game_details.append(item)
                return game_details
        except IndexError:
            game_details = ['{"error": "No such game"}']


def get_most_recent_game_id_to_check_for_data():
    # Connect to the database
    conn = sqlite3.connect("/Users/ryan/Documents/testbed/ahl/games.db")
    cursor = conn.cursor()

    # Execute a SELECT query
    cursor.execute("SELECT game_id FROM games")

    # Fetch all rows returned by the query
    rows = cursor.fetchall()

    # Close the cursor and the connection
    cursor.close()
    conn.close()

    # We get the most recent id with data and then go back 16 game to catch any games that were played
    # since the last time. This is done to account for the way that Playoff Series work
    most_recent_game_id_to_check_for_data = int(max(rows)[0]) - 16
    return most_recent_game_id_to_check_for_data


def write_game_data(game_id: int, full_load: bool = False):
    url = f"https://lscluster.hockeytech.com/game_reports/text-game-report.php?client_code=ahl&game_id={game_id}"
    response = requests.get(url)
    game_details = get_game_details(response)
    if game_id % 10 == 0 and full_load:
        print("Waiting 1 second ... ")
        time.sleep(1)
        print("Starting again ... ")
    else:
        print(f"Getting data for game {game_id}")

    if game_details == ['{"error": "No such game"}']:
        conn = sqlite3.connect("/Users/ryan/Documents/testbed/ahl/games.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS unplayed_games (
                game_id TEXT PRIMARY KEY
            )
        """
        )
        try:
            cursor.execute(
                """
                INSERT INTO unplayed_games (game_id)
                VALUES (?)
            """,
                [game_id],
            )
        except sqlite3.IntegrityError:
            print(f"Game {game_id} has already been added")

        conn.commit()
        conn.close()
    elif game_details == ["This game is not available."]:
        print(f"Game id {game_id} is potentially scheduled to be played but hasn't been played yet!")

    else:
        try:
            if get_game_status(game_details).startswith("Final"):
                data = [
                    game_id,
                    get_away_team(game_details),
                    get_away_team_score(game_details),
                    get_home_team(game_details),
                    get_home_team_score(game_details),
                    get_game_status(game_details),
                    get_date(game_details),
                    get_attendance(game_details),
                ]

                conn = sqlite3.connect("/Users/ryan/Documents/testbed/ahl/games.db")
                cursor = conn.cursor()

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS games (
                        game_id TEXT PRIMARY KEY,
                        away_team TEXT,
                        away_team_score INTEGER,
                        home_team TEXT,
                        home_team_score INTEGER,
                        game_status TEXT,
                        game_date TEXT,
                        game_attendance INTEGER
                    )
                """
                )
                try:
                    cursor.execute(
                        """
                        INSERT INTO games (game_id, away_team, away_team_score, home_team, home_team_score, game_status, game_date, game_attendance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        data,
                    )
                except sqlite3.IntegrityError:
                    print(f"Game {game_id} has already been added")

                conn.commit()
                conn.close()
        except IndexError:
            print(f"There is an issue getting game id {game_id}")


if __name__ == "__main__":
    start_game_id = get_most_recent_game_id_to_check_for_data()
    # start_game_id = 1025316
    end_game_id = start_game_id + 32
    # end_game_id = 1025179
    for i in range(start_game_id, end_game_id):
        time.sleep(1)
        write_game_data(i)
