import os
import sqlite3
import random
from pathlib import Path
from argon2 import PasswordHasher

ph = PasswordHasher()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "authforge.db"

def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

# Sample password dictionary for educational challenge generation
SAMPLE_CHALLENGE_PASSWORDS = [
    "cyberlab2026", "pass123", "shadow88", "alpha2026", "matrix99",
    "dragon123", "secops2026", "shield44", "phoenix77", "forge2026",
    "starlight00", "nexus55", "quantum88", "horizon123", "beacon99"
]

def hash_password(password: str) -> str:
    """Hashes password using Argon2id algorithm."""
    return ph.hash(password)

def init_db(force_reseed: bool = False):
    """Initializes Level 2 database schema and seeds challenge accounts."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table 1: students
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table 2: challenge_accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenge_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            challenge_id TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plain_password_hint TEXT,
            status TEXT DEFAULT 'ACTIVE',
            failed_attempts INTEGER DEFAULT 0,
            attempts_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            completed_at TIMESTAMP,
            time_taken_seconds REAL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)

    # Table 3: authentication_attempts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authentication_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id TEXT NOT NULL,
            username TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            request_identifier TEXT
        )
    """)

    # Table 4: challenges
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'ACTIVE',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)

    conn.commit()

    # Seed 70 classroom challenge accounts if empty or force_reseed
    cursor.execute("SELECT COUNT(*) FROM challenge_accounts")
    count = cursor.fetchone()[0]

    if count == 0 or force_reseed:
        if force_reseed:
            cursor.execute("PRAGMA foreign_keys = OFF")
            cursor.execute("DELETE FROM authentication_attempts")
            cursor.execute("DELETE FROM challenge_accounts")
            cursor.execute("DELETE FROM students")
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()


        # Seed student accounts 1 to 70
        for i in range(1, 71):
            student_code = f"STU-{i:03d}"
            challenge_id = f"AF-{i:03d}"
            username = f"student{i:02d}"
            
            # Select random password from challenge wordlist
            raw_password = random.choice(SAMPLE_CHALLENGE_PASSWORDS)
            hashed_pass = hash_password(raw_password)
            hint = f"Dictionary word (Length: {len(raw_password)})"

            cursor.execute(
                "INSERT INTO students (student_code) VALUES (?)",
                (student_code,)
            )
            student_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO challenge_accounts 
                (student_id, challenge_id, username, password_hash, plain_password_hint, status)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            """, (student_id, challenge_id, username, hashed_pass, hint))

        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Level 2 Database initialized with Argon2id password hashes.")
