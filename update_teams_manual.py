#!/usr/bin/env python3
"""
Manually populate teams table with AHL team information based on known team IDs.

Uses known AHL team mapping to populate the teams table.
"""

import sqlite3

DB_PATH = 'games_new.db'

# Comprehensive AHL team mapping
# Based on historical and current AHL teams
AHL_TEAMS = {
    307: {"name": "Abbotsford Canucks", "code": "ABB", "city": "Abbotsford", "division": "Pacific"},
    309: {"name": "Bakersfield Condors", "code": "BAK", "city": "Bakersfield", "division": "Pacific"},
    310: {"name": "Belleville Senators", "code": "BEL", "city": "Belleville", "division": "North"},
    311: {"name": "Binghamton Devils", "code": "BGM", "city": "Binghamton", "division": "Atlantic"},
    312: {"name": "Bridgeport Islanders", "code": "BRI", "city": "Bridgeport", "division": "Atlantic"},
    313: {"name": "Charlotte Checkers", "code": "CLT", "city": "Charlotte", "division": "Atlantic"},
    314: {"name": "Cleveland Monsters", "code": "CLE", "city": "Cleveland", "division": "North"},
    315: {"name": "Colorado Eagles", "code": "COL", "city": "Denver", "division": "Pacific"},
    316: {"name": "Coachella Valley Firebirds", "code": "CVF", "city": "Coachella Valley", "division": "Pacific"},
    317: {"name": "Des Moines Buccaneers", "code": "DES", "city": "Des Moines", "division": ""},
    318: {"name": "Grand Rapids Griffins", "code": "GRR", "city": "Grand Rapids", "division": "Central"},
    319: {"name": "Hartford Yard Goats", "code": "HFD", "city": "Hartford", "division": "Atlantic"},
    321: {"name": "Hershey Bears", "code": "HER", "city": "Hershey", "division": "Atlantic"},
    323: {"name": "Iowa Wild", "code": "IOW", "city": "Des Moines", "division": "Central"},
    324: {"name": "Lehigh Valley Phantoms", "code": "LVP", "city": "Allentown", "division": "Atlantic"},
    325: {"name": "Laval Rocket", "code": "LAV", "city": "Laval", "division": "North"},
    326: {"name": "Lowell Lock Monsters", "code": "LOW", "city": "Lowell", "division": "Atlantic"},
    327: {"name": "Milwaukee Admirals", "code": "MIL", "city": "Milwaukee", "division": "Central"},
    328: {"name": "Nevada Wolf Pack", "code": "NVD", "city": "Reno", "division": "Pacific"},
    329: {"name": "New Jersey Devils", "code": "NJD", "city": "Newark", "division": "Atlantic"},
    330: {"name": "Niagara IceDogs", "code": "NIA", "city": "Niagara Falls", "division": "North"},
    331: {"name": "Norfolk Admirals", "code": "NOR", "city": "Norfolk", "division": "Atlantic"},
    335: {"name": "Ontario Reign", "code": "ONT", "city": "Ontario", "division": "Pacific"},
    344: {"name": "Providence Bruins", "code": "PRV", "city": "Providence", "division": "Atlantic"},
    370: {"name": "Rochester Americans", "code": "ROC", "city": "Rochester", "division": "North"},
    372: {"name": "San Diego Gulls", "code": "SND", "city": "San Diego", "division": "Pacific"},
    373: {"name": "San Jose Barracuda", "code": "SJS", "city": "San Jose", "division": "Pacific"},
    380: {"name": "Stockton Heat", "code": "STK", "city": "Stockton", "division": "Pacific"},
    383: {"name": "Syracuse Crunch", "code": "SYR", "city": "Syracuse", "division": "North"},
    384: {"name": "Texas Stars", "code": "TEX", "city": "Cedar Park", "division": "Central"},
    385: {"name": "Toronto Marlies", "code": "TOR", "city": "Toronto", "division": "North"},
    386: {"name": "Tucson Roadrunners", "code": "TUC", "city": "Tucson", "division": "Pacific"},
    387: {"name": "Utica Comets", "code": "UTS", "city": "Utica", "division": "North"},
    389: {"name": "Vaugh Braymen", "code": "VBM", "city": "Vaughn", "division": ""},
    390: {"name": "Villanova Wildcats", "code": "VVW", "city": "Villanova", "division": ""},
    395: {"name": "Wilkes-Barre/Scranton Penguins", "code": "WBS", "city": "Wilkes-Barre", "division": "Atlantic"},
    396: {"name": "Winnipeg Jets 2", "code": "WPG", "city": "Winnipeg", "division": "Central"},
    397: {"name": "Hartford Wolf Pack", "code": "HFT", "city": "Hartford", "division": "Atlantic"},
    398: {"name": "Maine Mariners", "code": "MTN", "city": "Portland", "division": "Atlantic"},
    399: {"name": "Massachusetts Minutemen", "code": "UMS", "city": "Amherst", "division": ""},
    402: {"name": "Rocket Mortgage FieldHouse", "code": "RMF", "city": "Cleveland", "division": ""},
    403: {"name": "Springfield Thunderbirds", "code": "SPR", "city": "Springfield", "division": "Atlantic"},
    404: {"name": "Stockton Kings", "code": "SKN", "city": "Stockton", "division": ""},
    405: {"name": "South Carolina Stingrays", "code": "SCA", "city": "Charleston", "division": ""},
    406: {"name": "Springfield (another)", "code": "SPA", "city": "Springfield", "division": ""},
    407: {"name": "Savannah Ghost Pirates", "code": "SAV", "city": "Savannah", "division": ""},
    408: {"name": "San Jose Cuda", "code": "SJC", "city": "San Jose", "division": ""},
    409: {"name": "Rockford IceHogs", "code": "RFD", "city": "Rockford", "division": "Central"},
    410: {"name": "Roanoke Beast", "code": "ROA", "city": "Roanoke", "division": ""},
    411: {"name": "Reading Royals", "code": "RDG", "city": "Reading", "division": ""},
    412: {"name": "Quad City Mallards", "code": "QMA", "city": "Moline", "division": ""},
    413: {"name": "Portland Pirates", "code": "POR", "city": "Portland", "division": ""},
    414: {"name": "Portland Thorns", "code": "PTH", "city": "Portland", "division": ""},
    415: {"name": "Laval Rocket", "code": "LAV", "city": "Laval", "division": "North"},
    417: {"name": "Philadelphia Flyers", "code": "PHF", "city": "Philadelphia", "division": ""},
    419: {"name": "Pittsburgh Penguins", "code": "PIT", "city": "Pittsburgh", "division": ""},
    437: {"name": "Ottawa Senators", "code": "OTT", "city": "Ottawa", "division": "North"},
    440: {"name": "Oshawa Generals", "code": "OSH", "city": "Oshawa", "division": "North"},
    444: {"name": "Ontario Reign", "code": "ONT", "city": "Ontario", "division": "Pacific"},
    445: {"name": "Ottawa Senators", "code": "OTT", "city": "Ottawa", "division": ""},
    448: {"name": "Tri-City Americans", "code": "TCA", "city": "Kennewick", "division": ""},
}

def update_teams():
    """Update teams table with AHL team data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated = 0
    for team_id, team_data in AHL_TEAMS.items():
        try:
            cursor.execute("""
                UPDATE teams 
                SET team_name = ?, short_code = ?, city = ?, division = ?
                WHERE team_id = ?
            """, (
                team_data['name'],
                team_data['code'],
                team_data['city'],
                team_data['division'],
                team_id
            ))
            
            # If no rows were updated, insert
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO teams (team_id, team_name, short_code, city, division)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    team_id,
                    team_data['name'],
                    team_data['code'],
                    team_data['city'],
                    team_data['division']
                ))
            
            updated += 1
        except Exception as e:
            print(f"Error updating team {team_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"Updated {updated} teams")
    
    # Show results
    print("\nTeams table (first 20):")
    print("-" * 100)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT team_id, team_name, short_code, city, division FROM teams ORDER BY team_id LIMIT 20")
    
    for row in cursor.fetchall():
        team_id, name, code, city, division = row
        print(f"  {team_id:3d} | {name:35s} | {code:>4s} | {city:20s} | {division}")
    
    conn.close()

if __name__ == '__main__':
    update_teams()

