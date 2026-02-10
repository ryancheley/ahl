import sqlite3
from datetime import date, timedelta

season_dictionary = {
    "2005-06": {
        "regular": {"start_date": "2005-10-05", "end_date": "2006-04-16"},
        "post": {"start_date": "2006-04-18", "end_date": "2006-06-15"},
    },
    "2006-07": {
        "regular": {"start_date": "2006-10-04", "end_date": "2007-04-15"},
        "post": {"start_date": "2007-04-18", "end_date": "2007-06-07"},
    },
    "2007-08": {
        "regular": {"start_date": "2007-10-03", "end_date": "2008-04-13"},
        "post": {"start_date": "2008-04-16", "end_date": "2008-06-10"},
    },
    "2008-09": {
        "regular": {"start_date": "2008-10-08", "end_date": "2009-04-12"},
        "post": {"start_date": "2009-04-15", "end_date": "2009-06-12"},
    },
    "2009-10": {
        "regular": {"start_date": "2009-10-02", "end_date": "2010-04-11"},
        "post": {"start_date": "2010-04-14", "end_date": "2010-06-16"},
    },
    "2010-11": {
        "regular": {"start_date": "2010-10-08", "end_date": "2011-04-10"},
        "post": {"start_date": "2011-04-13", "end_date": "2011-06-16"},
    },
    "2011-12": {
        "regular": {"start_date": "2011-10-07", "end_date": "2012-04-15"},
        "post": {"start_date": "2012-04-19", "end_date": "2012-06-16"},
    },
    "2012-13": {
        "regular": {"start_date": "2012-10-12", "end_date": "2013-04-21"},
        "post": {"start_date": "2013-04-26", "end_date": "2013-06-18"},
    },
    "2013-14": {
        "regular": {"start_date": "2013-10-04", "end_date": "2014-04-19"},
        "post": {"start_date": "2014-04-23", "end_date": "2014-06-17"},
    },
    "2014-15": {
        "regular": {"start_date": "2014-10-10", "end_date": "2015-04-19"},
        "post": {"start_date": "2015-04-22", "end_date": "2015-06-13"},
    },
    "2015-16": {
        "regular": {"start_date": "2015-10-09", "end_date": "2016-04-17"},
        "post": {"start_date": "2016-04-20", "end_date": "2016-06-16"},
    },
    "2016-17": {
        "regular": {"start_date": "2016-10-14", "end_date": "2017-04-15"},
        "post": {"start_date": "2017-04-20", "end_date": "2017-06-13"},
    },
    "2017-18": {
        "regular": {"start_date": "2017-10-06", "end_date": "2018-04-15"},
        "post": {"start_date": "2018-04-19", "end_date": "2018-06-16"},
    },
    "2018-19": {
        "regular": {"start_date": "2018-10-05", "end_date": "2019-04-15"},
        "post": {"start_date": "2019-04-17", "end_date": "2019-06-08"},
    },
    "2019-20": {
        "regular": {"start_date": "2019-10-04", "end_date": "2020-03-12"},
        "post": {},
    },
    "2020-21": {
        "regular": {"start_date": "2021-02-05", "end_date": "2021-05-20"},
        "post": {},
    },
    "2021-22": {
        "regular": {"start_date": "2021-10-15", "end_date": "2022-04-30"},
        "post": {"start_date": "2022-05-02", "end_date": "2022-06-25"},
    },
    "2022-23": {
        "regular": {"start_date": "2022-10-14", "end_date": "2023-04-16"},
        "post": {"start_date": "2023-04-18", "end_date": "2023-06-21"},
    },
    "2023-24": {
        "regular": {"start_date": "2023-10-13", "end_date": "2024-04-21"},
        "post": {"start_date": "2024-04-22", "end_date": "2024-06-30"},
    },
    "2024-25": {
        "regular": {"start_date": "2024-10-11", "end_date": "2025-04-20"},
        "post": {"start_date": "2025-04-21", "end_date": "2025-06-30"},
    },
}

# Connect to your SQLite database
conn = sqlite3.connect("games.db")
cur = conn.cursor()

# Create the dim_date table if it doesn't exist
cur.execute("""
CREATE TABLE IF NOT EXISTS dim_date (
    date TEXT PRIMARY KEY,
    season TEXT,
    season_phase TEXT,
    day_of_season INTEGER)
""")

# Add day_of_season column if it doesn't exist (for existing tables)
try:
    cur.execute("ALTER TABLE dim_date ADD COLUMN day_of_season INTEGER")
except sqlite3.OperationalError as e:
    if "duplicate column name" not in str(e):
        raise


# Function to determine the season for a given date
def find_season(given_date):
    """
    Determine the season and phase (regular or post) for a given date.

    Parameters:
    - given_date (date): The date for which to find the season and phase.

    Returns:
    - tuple: (season, phase) where season is the season string (e.g., "2020-21")
             and phase is either 'regular' or 'post'. Returns (None, None) if the
             date does not fall within any defined season or phase.
    """
    for season, periods in season_dictionary.items():
        # Check the regular season period
        regular_start = date.fromisoformat(periods["regular"]["start_date"])
        regular_end = date.fromisoformat(periods["regular"]["end_date"])
        if regular_start <= given_date <= regular_end:
            return (season, "regular")

        # Check the post-season period, if it exists
        if "post" in periods and periods["post"]:  # Ensure 'post' exists and is not empty
            post_start = date.fromisoformat(periods["post"]["start_date"])
            post_end = date.fromisoformat(periods["post"]["end_date"])
            if post_start <= given_date <= post_end:
                return (season, "post")

    # If the date does not fall within any defined season or phase
    return (None, None)


# Generate dates and insert into the database
# Start from the beginning of the first season in the season_dictionary
start_date = date(2005, 10, 5)
end_date = date(2026, 4, 19)
# Assuming start_date and end_date are already defined
current_date = start_date
season_day_counter = {}  # Track day count per season

while current_date <= end_date:
    # Use the updated find_season function to get the season and phase (regular/post)
    season, phase = find_season(current_date)
    if season:
        # Format the date as "YYYY-MM-DD 00:00:00" for insertion
        date_str = current_date.strftime("%Y-%m-%d 00:00:00")
        # Prepare the season_phase string to include whether it's regular or post-season
        season_phase = f"{phase}" if phase else "Out of season"  # Append phase if it exists or mark as out of season

        # Calculate day_of_season
        if season not in season_day_counter:
            season_day_counter[season] = 1
        else:
            season_day_counter[season] += 1
        day_of_season = season_day_counter[season]

        # Insert or replace date (formatted with time), season, phase, and day_of_season into the table
        cur.execute("INSERT OR REPLACE INTO dim_date (date, season, season_phase, day_of_season) VALUES (?, ?, ?, ?)", (date_str, season, season_phase, day_of_season))
    # Move to the next day
    current_date += timedelta(days=1)

# Don't forget to commit the changes and close the connection after the loop
conn.commit()
conn.close()
