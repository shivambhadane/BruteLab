import os
import hashlib
import sqlite3
import random
from pathlib import Path
from argon2 import PasswordHasher

ph = PasswordHasher()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "brutelab.db"


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

# Password dictionary pools for John the Ripper challenge generation
EASY_PASSWORDS = [
    "cyberlab2026", "pass123", "shadow88", "alpha2026", "matrix99",
    "dragon123", "secops2026", "shield44", "phoenix77", "forge2026"
]

MEDIUM_PASSWORDS = [
    "CyberLab2026!", "Shadow88#", "Alpha2026!", "Matrix99$", "Dragon123!",
    "SecOps2026#", "Shield44!", "Phoenix77$", "Forge2026!"
]

HARD_PASSWORDS = [
    "argon_cyber2026", "argon_shadow88", "argon_matrix99", "argon_secops2026"
]

def hash_sha256(password: str) -> str:
    """Generates SHA-256 hex digest for fast hash cracking (EASY/MEDIUM)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def hash_argon2id(password: str) -> str:
    """Generates Argon2id hash for memory-hard defense comparison (HARD)."""
    return ph.hash(password)

def init_db(force_reseed: bool = False):
    """Initializes John the Ripper Offline Cracking Lab database schema."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenge_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT NOT NULL,
            challenge_id TEXT UNIQUE NOT NULL,
            tier TEXT NOT NULL,
            hash_type TEXT NOT NULL,
            username TEXT NOT NULL,
            hash_value TEXT NOT NULL,
            plain_password TEXT NOT NULL,
            password_hint TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            time_taken_seconds REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            challenge_id TEXT NOT NULL,
            student_code TEXT NOT NULL,
            result TEXT NOT NULL,
            submission TEXT
        )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM challenge_hashes")
    count = cursor.fetchone()[0]

    if count == 0 or force_reseed:
        if force_reseed:
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM challenge_hashes")
            conn.commit()

        # Seed 70 students with 3 challenge tiers each (Total 210 challenges)
        for i in range(1, 71):
            student_code = f"STU-{i:03d}"
            username = f"student{i:02d}"

            # 1. EASY Tier (SHA-256)
            easy_pass = EASY_PASSWORDS[(i - 1) % len(EASY_PASSWORDS)]
            easy_id = f"JR-{i:03d}-EASY"
            easy_hash = hash_sha256(easy_pass)
            cursor.execute("""
                INSERT INTO challenge_hashes
                (student_code, challenge_id, tier, hash_type, username, hash_value, plain_password, password_hint, status)
                VALUES (?, ?, 'EASY', 'SHA-256', ?, ?, ?, 'Weak dictionary word', 'ACTIVE')
            """, (student_code, easy_id, username, easy_hash, easy_pass))

            # 2. MEDIUM Tier (SHA-256 + Rule mutation)
            med_pass = MEDIUM_PASSWORDS[(i - 1) % len(MEDIUM_PASSWORDS)]
            med_id = f"JR-{i:03d}-MEDIUM"
            med_hash = hash_sha256(med_pass)
            cursor.execute("""
                INSERT INTO challenge_hashes
                (student_code, challenge_id, tier, hash_type, username, hash_value, plain_password, password_hint, status)
                VALUES (?, ?, 'MEDIUM', 'SHA-256', ?, ?, ?, 'Capitalized + special symbol mutation', 'ACTIVE')
            """, (student_code, med_id, username, med_hash, med_pass))

            # 3. HARD Tier (Argon2id Defense comparison)
            hard_pass = HARD_PASSWORDS[(i - 1) % len(HARD_PASSWORDS)]
            hard_id = f"JR-{i:03d}-HARD"
            hard_hash = hash_argon2id(hard_pass)
            cursor.execute("""
                INSERT INTO challenge_hashes
                (student_code, challenge_id, tier, hash_type, username, hash_value, plain_password, password_hint, status)
                VALUES (?, ?, 'HARD', 'Argon2id', ?, ?, ?, 'Memory-hard Argon2id hash', 'ACTIVE')
            """, (student_code, hard_id, username, hard_hash, hard_pass))

        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("John the Ripper Offline Lab Database Initialized.")
