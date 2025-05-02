import sqlite3

# Connect to the database
conn = sqlite3.connect('games.db')
cursor = conn.cursor()

print("Adding day_of_season column to dim_date table...")

try:
    # Add the day_of_season column to the dim_date table
    cursor.execute('ALTER TABLE dim_date ADD COLUMN day_of_season INTEGER')
    conn.commit()
    print("Column added successfully!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("Column already exists.")
    else:
        print(f"Error: {e}")
finally:
    # Close the connection
    conn.close()