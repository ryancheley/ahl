"""Migration script to add latitude/longitude to venue table and populate AHL arena coordinates."""

import sqlite3
from pathlib import Path

# Current AHL arenas (2025-26 season) with coordinates in decimal degrees
# Using both database names and common aliases for matching
AHL_ARENAS = {
    # Eastern Conference - Atlantic Division
    "Amica Mutual Pavilion": (
        41.8231,
        -71.4107,
    ),  # Providence & Bridgeport (using Providence coords)
    "Bojangles Coliseum": (35.2252, -80.8384),  # Charlotte Checkers
    "XL Center": (41.7658, -72.6734),  # Hartford Wolf Pack
    "Giant Center": (40.3356, -76.6745),  # Hershey Bears
    "PPL Center": (40.6084, -75.3744),  # Lehigh Valley Phantoms
    "Providence Civic Center": (41.8231, -71.4107),  # Providence Bruins (alt name)
    "Springfield Civic Center": (
        42.1015,
        -72.5898,
    ),  # Springfield Thunderbirds (alt name)
    "MHG Ice Centre": (42.1015, -72.5898),  # Springfield Thunderbirds
    "Mohegan Sun Arena at Casey Plaza": (
        41.2107,
        -75.9067,
    ),  # Wilkes-Barre/Scranton Penguins
    # Eastern Conference - North Division
    "Canadian Tire Centre": (45.2968, -75.6465),  # Belleville Senators
    "Quicken Loans Arena": (41.4965, -81.6882),  # Cleveland Monsters
    "Place Bell": (45.5017, -73.4994),  # Laval Rocket
    "Blue Cross Arena": (43.8853, -77.6003),  # Rochester Americans
    "Onondaga County War Memorial Arena": (43.0346, -76.0922),  # Syracuse Crunch
    "Coca-Cola Coliseum": (43.6629, -79.3957),  # Toronto Marlies
    "Scotiabank Arena": (43.6426, -79.3957),  # Toronto (alt name)
    "Utica Memorial Auditorium": (43.1015, -75.2323),  # Utica Comets
    # Western Conference - Central Division
    "Allstate Arena": (42.0049, -87.9850),  # Rockford IceHogs
    "Van Andel Arena": (42.9689, -85.6805),  # Grand Rapids Griffins
    "Wells Fargo Arena": (41.5868, -93.6285),  # Iowa Wild
    "Canada Life Centre": (49.8951, -97.1434),  # Manitoba Moose
    "Fiserv Forum": (43.0045, -87.9167),  # Milwaukee Admirals
    "BMO Harris Bradley Center": (43.0045, -87.9167),  # Milwaukee (old name)
    "H-E-B Center at Cedar Park": (30.2743, -97.7954),  # Texas Stars
    # Western Conference - Pacific Division
    "Abbotsford Entertainment & Sports Centre": (
        49.0504,
        -122.3045,
    ),  # Abbotsford Canucks
    "Rabobank Arena": (35.2698, -119.0187),  # Bakersfield Condors
    "Scotiabank Saddledome": (51.0382, -114.0720),  # Calgary Wranglers
    "Acrisure Arena": (33.8133, -116.4260),  # Coachella Valley Firebirds
    "Dignity Health Arena": (39.7487, -104.9947),  # Colorado Eagles
    "The Dollar Loan Center": (35.9720, -115.1370),  # Henderson Silver Knights
    "Toyota Arena": (34.0622, -117.6007),  # Ontario Reign (Ontario, CA)
    "Pechanga Arena San Diego": (32.6057, -117.0327),  # San Diego Gulls
    "SAP Center at San Jose": (37.3330, -121.9010),  # San Jose Barracuda
    "Climate Pledge Arena": (47.6205, -122.3493),  # Seattle (future WHL/AHL)
    "Tucson Convention Center Arena": (32.2313, -110.9265),  # Tucson Roadrunners
}


def migrate():
    """Add latitude/longitude columns and populate coordinates."""
    db_path = Path(__file__).parent / "my_database.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(venue)")
        columns = {row[1] for row in cursor.fetchall()}

        if "latitude" not in columns:
            print("Adding latitude column...")
            cursor.execute("ALTER TABLE venue ADD COLUMN latitude REAL")

        if "longitude" not in columns:
            print("Adding longitude column...")
            cursor.execute("ALTER TABLE venue ADD COLUMN longitude REAL")

        # Update coordinates for known arenas
        print(f"Populating coordinates for {len(AHL_ARENAS)} arenas...")
        for arena_name, (lat, lon) in AHL_ARENAS.items():
            cursor.execute(
                "UPDATE venue SET latitude = ?, longitude = ? WHERE name = ?",
                (lat, lon, arena_name),
            )

        conn.commit()

        # Check how many arenas got coordinates
        cursor.execute("SELECT COUNT(*) FROM venue WHERE latitude IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"✓ Successfully populated coordinates for {count} venues")

        return True

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)
