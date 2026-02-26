#!/usr/bin/env python3
"""
Create and populate teams table using HockeyTech API.

Fetches team data from the gc/gamesummary endpoint which contains complete
team information (id, name, code, city, division, conference).
"""

import sqlite3
import requests
import json
from typing import Dict, Optional

# Configuration
DB_PATH = 'games_new.db'
BASE_URL = "https://lscluster.hockeytech.com/feed/index.php"
API_KEY = "ccb91f29d6744675"
CLIENT_CODE = "ahl"

class TeamPopulator:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.teams = {}  # team_id -> team_data
    
    def create_teams_table(self) -> bool:
        """Create the teams table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    team_id INTEGER PRIMARY KEY,
                    team_name TEXT NOT NULL,
                    short_code TEXT,
                    city TEXT,
                    nickname TEXT,
                    conference TEXT,
                    division TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            print("✓ Teams table created/verified")
            return True
        except Exception as e:
            print(f"✗ Error creating teams table: {e}")
            return False
    
    def get_unique_game_ids(self, limit: int = None) -> list:
        """Get game IDs from database to fetch team data from."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT DISTINCT game_id FROM games_extended ORDER BY game_id"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            games = [row[0] for row in cursor.fetchall()]
            conn.close()
            return games
        except Exception as e:
            print(f"✗ Error fetching game IDs: {e}")
            return []
    
    def fetch_team_data_from_game(self, game_id: str) -> Dict:
        """Fetch team data from a specific game's gamesummary endpoint."""
        try:
            url = (
                f"{BASE_URL}?feed=gc&tab=gamesummary"
                f"&game_id={game_id}&season_id=90"
                f"&key={API_KEY}&client_code={CLIENT_CODE}"
            )
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            teams_found = {}
            
            # Extract from GC/Gamesummary
            if 'GC' in data and 'Gamesummary' in data['GC']:
                gs = data['GC']['Gamesummary']
                
                # Extract home team
                if 'home' in gs and gs['home']:
                    home = gs['home']
                    team_id = int(home['id'])
                    teams_found[team_id] = {
                        'id': team_id,
                        'name': home.get('name', f'Team {team_id}'),
                        'code': home.get('code', ''),
                        'city': home.get('city', ''),
                        'nickname': home.get('nickname', ''),
                        'division': gs.get('home_division', ''),
                    }
                
                # Extract visiting/away team
                if 'visitor' in gs and gs['visitor']:
                    visitor = gs['visitor']
                    team_id = int(visitor['id'])
                    teams_found[team_id] = {
                        'id': team_id,
                        'name': visitor.get('name', f'Team {team_id}'),
                        'code': visitor.get('code', ''),
                        'city': visitor.get('city', ''),
                        'nickname': visitor.get('nickname', ''),
                        'division': gs.get('visitor_division', ''),
                    }
            
            return teams_found
        except Exception as e:
            return {}
    
    def populate_teams(self):
        """Populate the teams table from game data."""
        print("\nFetching game IDs...")
        game_ids = self.get_unique_game_ids()
        print(f"Found {len(game_ids)} games")
        
        print("\nExtracting team data from games...")
        for i, game_id in enumerate(game_ids):
            if (i + 1) % 100 == 0 or i == 0:
                print(f"  [{i+1}/{len(game_ids)}] Processing game {game_id}...")
            
            game_teams = self.fetch_team_data_from_game(game_id)
            self.teams.update(game_teams)
            
            # Stop early if we have all teams
            unique_db_teams = set()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT CAST(home_team AS INTEGER) FROM games_extended WHERE home_team IS NOT NULL")
            unique_db_teams.update([row[0] for row in cursor.fetchall()])
            cursor.execute("SELECT DISTINCT CAST(away_team AS INTEGER) FROM games_extended WHERE away_team IS NOT NULL")
            unique_db_teams.update([row[0] for row in cursor.fetchall()])
            conn.close()
            
            if len(self.teams) >= len(unique_db_teams):
                print(f"  Found all {len(self.teams)} teams")
                break
        
        print(f"\nExtracted {len(self.teams)} unique teams")
        
        # Insert into database
        print("Populating teams table...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        inserted = 0
        for team_id, team_data in sorted(self.teams.items()):
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO teams 
                    (team_id, team_name, short_code, city, nickname, division) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    team_data['id'],
                    team_data['name'],
                    team_data['code'],
                    team_data['city'],
                    team_data['nickname'],
                    team_data['division'],
                ))
                inserted += 1
            except Exception as e:
                print(f"  ✗ Error inserting team {team_id}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✓ Inserted {inserted} teams into database")
        
        # Show results
        print("\nTeams table contents:")
        print("-" * 100)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT team_id, team_name, short_code, city, division FROM teams ORDER BY team_id")
        
        count = 0
        for row in cursor.fetchall():
            team_id, name, code, city, division = row
            print(f"  {team_id:3d} | {name:35s} | {code:>4s} | {city:20s} | {division}")
            count += 1
        
        print(f"\nTotal teams: {count}")
        conn.close()

def main():
    populator = TeamPopulator()
    
    # Create table
    if not populator.create_teams_table():
        return
    
    # Populate with data
    populator.populate_teams()

if __name__ == '__main__':
    main()

