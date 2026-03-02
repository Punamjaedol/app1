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
    add_column_if_missing("users", "name", "TEXT DEFAULT ''")
    add_column_if_missing("users", "birthday", "TEXT DEFAULT ''")
    
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
    add_column_if_missing("schedules", "description", "TEXT DEFAULT ''")
    add_column_if_missing("schedules", "is_annual", "INTEGER DEFAULT 0")
    
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
            INSERT INTO users (id, username, password, couple_id, name, birthday)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), 'user1', '20240206', couple_id, 'USER1', '1997-02-25'))
        
        # Create user2
        cursor.execute('''
            INSERT INTO users (id, username, password, couple_id, name, birthday)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), 'user2', '20240206', couple_id, 'USER2', '1997-02-18'))
        
        # Seed couple_info
        cursor.execute('''
            INSERT INTO couple_info (couple_id, start_date)
            VALUES (?, ?)
        ''', (couple_id, '2024-02-06'))
        
        print("Seeded user1, user2, couple_info and updated existing data.")
    else:
        # Update existing users with names/birthdays if missing
        cursor.execute("UPDATE users SET name = 'USER2', birthday = '1997-02-18' WHERE username = 'user2' AND (name IS NULL OR name = '')")
        
        # Ensure couple_info exists for existing test couple
        cursor.execute("SELECT couple_id FROM users WHERE username = 'user1'")
        row = cursor.fetchone()
        if row:
            cursor.execute("INSERT OR IGNORE INTO couple_info (couple_id, start_date) VALUES (?, ?)", (row["couple_id"], '2024-02-06'))
    
    # Cleanup redundant data (now calculated dynamically)
    # 1. Delete old birthday schedules
    cursor.execute("DELETE FROM schedules WHERE title LIKE '%생일 🎂'")
    # 2. Delete old anniversary schedules (e.g., 1주년, 2주년)
    cursor.execute("DELETE FROM schedules WHERE title LIKE '%주년!'")
    
    # Unify "All Day" to "종일" (already handled by dynamic injection but good for existing custom ones)
    cursor.execute("UPDATE schedules SET time = '종일' WHERE time = 'All Day'")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
