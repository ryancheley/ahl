from datetime import datetime
import re
import sqlite3
import time
import argparse
import sys

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


def get_shots_on_goal(game_details, home_or_away):
    shots = game_details[-6].replace("Shots on Goal-", "").split(".")
    if home_or_away == "home":
        team_details = shots[1].split("-")[-1]
    else:
        team_details = shots[0].split("-")[-1]
    return team_details


def get_game_details(response: str):
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


def get_most_recent_game_id_to_check_for_data(lookback=0):
    """
    Get the most recent game ID from the database.
    
    Args:
        lookback (int): Number of games to look back from the most recent game ID.
                        Default is 0, which returns the most recent game ID.
    
    Returns:
        int: The most recent game ID minus the lookback value. If the database is empty,
             returns None and prints an error message.
    """
    # Connect to the database
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()

    # Execute a SELECT query
    cursor.execute("SELECT game_id FROM games")

    # Fetch all rows returned by the query
    rows = cursor.fetchall()
    
    # Close the cursor and the connection
    cursor.close()
    conn.close()
    
    if not rows:
        print("Error: No games found in the database. Please add at least one game first.")
        return None
        
    # Get the most recent id with data and then go back by the specified lookback amount
    most_recent_game_id = int(max(rows)[0])
    return most_recent_game_id - lookback


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
        conn = sqlite3.connect("games.db")
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
                    get_shots_on_goal(game_details, "home"),
                    get_shots_on_goal(game_details, "away"),
                ]

                conn = sqlite3.connect("games.db")
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
                        game_attendance INTEGER,
                        home_team_shots INTEGER,
                        away_team_shots INTEGER
                    )
                """
                )
                try:
                    cursor.execute(
                        """
                        INSERT INTO games (game_id, away_team, away_team_score, home_team, home_team_score, game_status, game_date, game_attendance, home_team_shots, away_team_shots)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        data,
                    )
                except sqlite3.IntegrityError:
                    print(f"Game {game_id} has already been added")

                conn.commit()
                conn.close()
        except IndexError:
            print(f"There is an issue getting game id {game_id}")


def process_game_range(start_game_id, range_count):
    """
    Process a range of game IDs starting from start_game_id.
    
    Args:
        start_game_id (int): The starting game ID
        range_count (int): Number of games to process from the starting ID
    """
    if start_game_id is None:
        return
        
    end_game_id = start_game_id + range_count
    print(f"Processing game range from {start_game_id} to {end_game_id-1}")
    
    for i in range(start_game_id, end_game_id):
        time.sleep(1)
        write_game_data(i)


def process_single_game(game_id):
    """
    Process a single game ID.
    
    Args:
        game_id (int): The game ID to process
    """
    print(f"Processing single game ID: {game_id}")
    write_game_data(game_id)


def main():
    parser = argparse.ArgumentParser(description='Retrieve and process hockey game data.')
    
    # Create a group for mutually exclusive options
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--game_id', type=int, help='Specific game ID to retrieve')
    group.add_argument('--start_id', type=int, help='Starting game ID for range processing')
    
    # Parameters for range-based processing
    parser.add_argument('--lookback', type=int, default=16, 
                        help='Number of games to look back from most recent (default: 16)')
    parser.add_argument('--range', type=int, default=32, 
                        help='Number of games to process in a range (default: 32)')
    
    args = parser.parse_args()

    if args.game_id:
        # Process a single specified game ID
        process_single_game(args.game_id)
    else:
        # Process a range of games
        if args.start_id:
            # Use specified start ID
            start_game_id = args.start_id
        else:
            # Use most recent ID minus lookback
            start_game_id = get_most_recent_game_id_to_check_for_data(args.lookback)
            
        process_game_range(start_game_id, args.range)


if __name__ == "__main__":
    main()