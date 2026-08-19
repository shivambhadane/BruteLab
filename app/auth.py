import datetime
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.database import get_db_connection, hash_sha256

ph = PasswordHasher()

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "auth.log"

def log_event(challenge_id: str, student_code: str, result: str, submission: str):
    """Logs audit event to logs/auth.log and database audit table."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp_str} | challenge_id={challenge_id} | student={student_code} | result={result} | submission={submission}\n"
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_line)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (timestamp, challenge_id, student_code, result, submission)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp_str, challenge_id, student_code, result, submission))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 50) -> List[str]:
    """Reads recent lines from logs/auth.log."""
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return [line.strip() for line in lines[-limit:]]

def format_student_code(raw_code: str) -> str:
    """Formats STU-037 or 37 into STU-037."""
    clean = raw_code.strip().upper()
    if clean.isdigit():
        return f"STU-{int(clean):03d}"
    return clean

def get_student_challenges(student_code: str) -> List[Dict[str, Any]]:
    """Retrieves all 3 tier challenges (EASY, MEDIUM, HARD) for a student."""
    formatted_code = format_student_code(student_code)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT challenge_id, tier, hash_type, status, password_hint
        FROM challenge_hashes
        WHERE student_code = ?
        ORDER BY CASE tier WHEN 'EASY' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'HARD' THEN 3 END
    """, (formatted_code,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return []
        
    return [
        {
            "challenge_id": r["challenge_id"],
            "tier": r["tier"],
            "hash_type": r["hash_type"],
            "status": r["status"],
            "password_hint": r["password_hint"]
        }
        for r in rows
    ]

def get_challenge_file_content(challenge_id: str) -> Optional[Tuple[str, str]]:
    """
    Generates John the Ripper formatted challenge file content:
    username:hash_value\n
    Returns (filename, content).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, hash_value, challenge_id FROM challenge_hashes WHERE challenge_id = ?", (challenge_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    filename = f"challenge_{row['challenge_id']}.txt"
    content = f"{row['username']}:{row['hash_value']}\n"
    return filename, content

def verify_submission(challenge_id: str, candidate_password: str) -> Tuple[bool, str, Optional[float]]:
    """
    Verifies candidate password against stored challenge hash.
    Returns (is_correct, message, time_taken_seconds).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, student_code, tier, hash_type, hash_value, plain_password, status, created_at, completed_at, time_taken_seconds
        FROM challenge_hashes
        WHERE challenge_id = ?
    """, (challenge_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Invalid Challenge ID", None

    if row["status"] == "SOLVED":
        conn.close()
        return True, "Challenge already completed", row["time_taken_seconds"]

    candidate_clean = candidate_password.strip()
    is_match = False
    
    if row["hash_type"] == "SHA-256":
        candidate_hash = hash_sha256(candidate_clean)
        is_match = (candidate_hash.lower() == row["hash_value"].lower()) or (candidate_clean == row["plain_password"])
    elif row["hash_type"] == "Argon2id":
        if candidate_clean == row["plain_password"]:
            is_match = True
        else:
            try:
                is_match = ph.verify(row["hash_value"], candidate_clean)
            except Exception:
                is_match = False

    if is_match:
        # Calculate time taken
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        created_at_dt = None
        try:
            created_at_dt = datetime.datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        except Exception:
            created_at_dt = now_utc

        time_taken = (now_utc - created_at_dt).total_seconds()
        if time_taken < 1.0:
            time_taken = 1.0  # Floor for realistic educational presentation

        cursor.execute("""
            UPDATE challenge_hashes
            SET status = 'SOLVED', completed_at = ?, time_taken_seconds = ?
            WHERE challenge_id = ?
        """, (now_str, time_taken, challenge_id))
        conn.commit()
        conn.close()
        
        log_event(challenge_id, row["student_code"], "SUCCESS", candidate_clean)
        return True, "CORRECT! Password verified.", round(time_taken, 1)
    else:
        conn.close()
        log_event(challenge_id, row["student_code"], "FAILED", candidate_clean)
        return False, "INCORRECT! Password candidate does not match hash.", None

def get_leaderboard() -> List[Dict[str, Any]]:
    """Ranks students by number of tiers solved and minimum total time."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT student_code,
               COUNT(*) AS solved_count,
               SUM(time_taken_seconds) AS total_seconds
        FROM challenge_hashes
        WHERE status = 'SOLVED'
        GROUP BY student_code
        ORDER BY solved_count DESC, total_seconds ASC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    for idx, r in enumerate(rows, start=1):
        secs = r["total_seconds"] or 0
        mins = int(secs // 60)
        rem_secs = int(secs % 60)
        time_str = f"{mins:02d}:{rem_secs:02d}"
        leaderboard.append({
            "rank": idx,
            "student_code": r["student_code"],
            "solved_count": r["solved_count"],
            "total_time": time_str
        })
    return leaderboard
