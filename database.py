import sqlite3
import os
from datetime import datetime

DB_FILE = "couple_app.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # helper function to add column if it doesn't exist
    def add_column_if_missing(table, column, definition):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            print(f"Adding column {column} to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        couple_id TEXT NOT NULL
    )
    ''')
    
    # Places table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS places (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')
    add_column_if_missing("places", "couple_id", "TEXT NOT NULL DEFAULT 'default_couple'")
    
    # Schedules table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schedules (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        title TEXT NOT NULL,
        time TEXT,
        place_id TEXT
    )
    ''')
    add_column_if_missing("schedules", "couple_id", "TEXT NOT NULL DEFAULT 'default_couple'")
    
    # Tracking Sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_lat REAL NOT NULL,
        start_lng REAL NOT NULL,
        start_time TEXT NOT NULL,
        last_update_time TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    ''')
    add_column_if_missing("tracking_sessions", "couple_id", "TEXT NOT NULL DEFAULT 'default_couple'")
    
    # Couple Info table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS couple_info (
        couple_id TEXT PRIMARY KEY,
        start_date TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Seed users after table creation
    seed_users()

def seed_users():
    conn = get_db()
    cursor = conn.cursor()
    
    import uuid
    
    # Check if user1 exists
    cursor.execute("SELECT * FROM users WHERE username = 'user1'")
    if not cursor.fetchone():
        couple_id = str(uuid.uuid4())
        # Create user1
        cursor.execute('''
            INSERT INTO users (id, username, password, couple_id)
            VALUES (?, ?, ?, ?)
        ''', (str(uuid.uuid4()), 'user1', '20240206', couple_id))
        
        # Create user2
        cursor.execute('''
            INSERT INTO users (id, username, password, couple_id)
            VALUES (?, ?, ?, ?)
        ''', (str(uuid.uuid4()), 'user2', '20240206', couple_id))
        
        # Update existing data to this couple_id
        cursor.execute("UPDATE places SET couple_id = ? WHERE couple_id = 'default_couple'", (couple_id,))
        cursor.execute("UPDATE schedules SET couple_id = ? WHERE couple_id = 'default_couple'", (couple_id,))
        cursor.execute("UPDATE tracking_sessions SET couple_id = ? WHERE couple_id = 'default_couple'", (couple_id,))
        
        print("Seeded user1, user2 and updated existing data.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
