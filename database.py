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
    
    # Tracking Sessions table (to track dwell time)
    # We only need the latest session per user (or device), 
    # but for MVP, assuming 1 user device is tracking.
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
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
