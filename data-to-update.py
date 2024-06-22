import sqlite3
import time

from program import get_game_details, get_shots_on_goal

import requests

SQL = """
select game_id from games where home_team_shots is NULL or away_team_shots is null order by game_id desc
"""

"""
When a new data element needs to be added to the games table in games.db this starter script is a useful starting point.
It will NOT do the work for you though. 
"""


def get_game_ids_to_be_updated():
    """This method returns a list of game ids that need to be updated.

    Returns:
        List: List of Game IDs
    """
    # Connect to the database
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()

    # Execute a SELECT query of the Game IDs that you need to update
    cursor.execute(SQL)

    # Fetch all rows returned by the query
    rows = cursor.fetchall()

    # Close the cursor and the connection
    cursor.close()
    conn.close()
    game_ids = []
    for i in rows:
        game_ids.append(i[0])
    return game_ids


def update_game_data(game_id, *args):
    """This method updates the game data in the

    Args:
        game_id (integer): The Game ID to be updated
        args (tuple): The arguments to be updated in the database
    """
    # Connect to the database
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()

    # Execute an UPDATE query; this query will need to be updated to account for the number of arguments
    cursor.execute(
        "UPDATE games SET home_team_shots = ?, away_team_shots = ? WHERE game_id = ?", (home_team_shots, away_team_shots, game_id)
    )

    # Commit the changes
    conn.commit()

    # Close the cursor and the connection
    cursor.close()
    conn.close()


if __name__ == "__main__":
    """
    This is the main method that will be executed when the script is run. It will get the game IDs that need to be updated and then update the data for each game.
    The data that is updated is dependent on what changes have been implemented above
    """

    game_ids = get_game_ids_to_be_updated()
    for game_id in game_ids:
        url = f"https://lscluster.hockeytech.com/game_reports/text-game-report.php?client_code=ahl&game_id={game_id}"
        response = requests.get(url)
        if int(game_id) % 50 == 0:
            print("Waiting 2 seconds ...")
            time.sleep(2)
        game_details = get_game_details(response)
        home_team_shots = get_shots_on_goal(game_details, "home")
        away_team_shots = get_shots_on_goal(game_details, "away")
        # print(f"Game {game_id} has {home_team_shots} shots for the home team and {away_team_shots} shots for the away team")
        update_game_data(game_id, home_team_shots, away_team_shots)
        print(f"Updated game {game_id} with shots on goal")
