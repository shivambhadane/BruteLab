import time
import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.config import settings
from app.database import get_db_connection, init_db, SAMPLE_CHALLENGE_PASSWORDS

ph = PasswordHasher()

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "auth.log"

def hash_password(password: str) -> str:
    """Hashes password using Argon2id algorithm."""
    return ph.hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False

def log_login_attempt(challenge_id: str, username: str, result: str, attempt_number: int, request_ip: str = "127.0.0.1"):
    """
    Records Level 2 authentication attempt to logs/auth.log and database.
    Format: YYYY-MM-DD HH:MM:SS | challenge_id={id} | username={username} | result={result} | attempt={N}
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp_str} | challenge_id={challenge_id} | username={username} | result={result} | attempt={attempt_number}\n"
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_line)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO authentication_attempts (challenge_id, username, timestamp, result, attempt_number, request_identifier)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (challenge_id, username, timestamp_str, result, attempt_number, request_ip))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 50) -> List[str]:
    """Reads recent lines from logs/auth.log."""
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return [line.strip() for line in lines[-limit:]]

def get_or_create_student_challenge(student_code: str) -> Optional[Dict[str, Any]]:
    """Retrieves assigned challenge account for a student code."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clean code e.g. STU-037 or 37
    clean_code = student_code.strip().upper()
    if clean_code.isdigit():
        clean_code = f"STU-{int(clean_code):03d}"
    
    cursor.execute("""
        SELECT ca.*, s.student_code 
        FROM challenge_accounts ca
        JOIN students s ON ca.student_id = s.id
        WHERE s.student_code = ? OR ca.challenge_id = ?
    """, (clean_code, clean_code.replace("STU-", "AF-")))
    
    account = cursor.fetchone()
    conn.close()
    
    if account:
        attempts_used = account["attempts_used"]
        attempts_remaining = max(0, settings.MAX_ATTEMPTS - attempts_used)
        return {
            "student_code": account["student_code"],
            "challenge_id": account["challenge_id"],
            "username": account["username"],
            "status": account["status"],
            "attempts_used": attempts_used,
            "attempts_remaining": attempts_remaining,
            "password_hint": account["plain_password_hint"]
        }
    return None

def check_rate_limit(challenge_id: str) -> Tuple[bool, int]:
    """
    Checks if requests for challenge_id exceed MAX_ATTEMPTS_PER_WINDOW.
    Returns (is_limited, retry_after_seconds).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    window_start = (now_utc - datetime.timedelta(seconds=settings.RATE_LIMIT_WINDOW)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT COUNT(*) FROM authentication_attempts
        WHERE challenge_id = ? AND timestamp >= ?
    """, (challenge_id, window_start))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    if count >= settings.MAX_ATTEMPTS_PER_WINDOW:
        return True, settings.RATE_LIMIT_WINDOW
    return False, 0


def process_login(challenge_id: str, username: str, password: str, request_ip: str = "127.0.0.1") -> Tuple[int, Dict[str, Any]]:
    """
    Processes Level 2 authentication with full security controls:
    - Challenge Isolation Check
    - Lockout Status Check
    - Rate Limit Check
    - Attempt Budget Check
    - Progressive Delay
    - Argon2id Password Verification
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM challenge_accounts WHERE challenge_id = ?", (challenge_id,))
    account = cursor.fetchone()

    if not account:
        conn.close()
        return 404, {"status": "failed", "message": "Invalid challenge ID."}

    # Requirement 8: Challenge Isolation (Prevent targeting other accounts)
    if account["username"] != username:
        conn.close()
        log_login_attempt(challenge_id, username, "DENIED_UNAUTHORIZED_ACCOUNT", account["attempts_used"] + 1, request_ip)
        return 403, {
            "status": "failed",
            "message": "Access denied. Account is not assigned to your challenge ID."
        }

    status = account["status"]
    attempts_used = account["attempts_used"] + 1
    failed_attempts = account["failed_attempts"]
    attempts_remaining = max(0, settings.MAX_ATTEMPTS - attempts_used)

    # Check Rate Limit (V1 Defense) - checked before status
    is_limited, retry_after = check_rate_limit(challenge_id)
    if is_limited:
        conn.close()
        log_login_attempt(challenge_id, username, "RATE_LIMITED", attempts_used, request_ip)
        return 429, {
            "status": "failed",
            "message": f"Too many authentication attempts. Rate limit triggered. Please wait {retry_after} seconds.",
            "attempts_used": attempts_used,
            "attempts_remaining": attempts_remaining
        }

    if status == "SUCCESS":
        conn.close()
        return 200, {
            "status": "success",
            "message": "Challenge already completed!",
            "attempts_used": account["attempts_used"],
            "attempts_remaining": attempts_remaining
        }

    if status == "LOCKED":
        conn.close()
        log_login_attempt(challenge_id, username, "LOCKED", attempts_used, request_ip)
        return 423, {
            "status": "failed",
            "message": "Account temporarily locked due to excessive failed attempts. Please try again later.",
            "attempts_used": attempts_used,
            "attempts_remaining": attempts_remaining
        }


    # Check Attempt Budget
    if attempts_used > settings.MAX_ATTEMPTS:
        cursor.execute("UPDATE challenge_accounts SET status = 'EXPIRED' WHERE challenge_id = ?", (challenge_id,))
        conn.commit()
        conn.close()
        log_login_attempt(challenge_id, username, "EXPIRED", attempts_used, request_ip)
        return 400, {
            "status": "failed",
            "message": f"Maximum allowed attempts ({settings.MAX_ATTEMPTS}) reached for this challenge.",
            "attempts_used": attempts_used,
            "attempts_remaining": 0
        }

    # Progressive Delay (V5 Defense)
    delay = min(settings.PROGRESSIVE_DELAY_BASE * (1.2 ** failed_attempts), 1.5)
    time.sleep(delay)

    # Verify Argon2id Password Hash
    is_valid = verify_password(account["password_hash"], password)

    if is_valid:
        # Calculate time taken
        created_time = datetime.datetime.strptime(account["created_at"], "%Y-%m-%d %H:%M:%S")
        now_time = datetime.datetime.now()
        time_taken = round((now_time - created_time).total_seconds(), 2)

        cursor.execute("""
            UPDATE challenge_accounts 
            SET status = 'SUCCESS', attempts_used = ?, completed_at = CURRENT_TIMESTAMP, time_taken_seconds = ?
            WHERE challenge_id = ?
        """, (attempts_used, time_taken, challenge_id))
        conn.commit()
        conn.close()

        log_login_attempt(challenge_id, username, "SUCCESS", attempts_used, request_ip)
        return 200, {
            "status": "success",
            "message": "CHALLENGE COMPLETE! Authentication successful.",
            "attempts_used": attempts_used,
            "attempts_remaining": attempts_remaining,
            "time_taken_seconds": time_taken
        }
    else:
        new_failed = failed_attempts + 1
        new_status = "ACTIVE"
        
        # Account Lockout Threshold (V2 Defense)
        if new_failed >= 10:
            new_status = "LOCKED"


        cursor.execute("""
            UPDATE challenge_accounts 
            SET failed_attempts = ?, attempts_used = ?, status = ?
            WHERE challenge_id = ?
        """, (new_failed, attempts_used, new_status, challenge_id))
        conn.commit()
        conn.close()

        if new_status == "LOCKED":
            log_login_attempt(challenge_id, username, "LOCKED_TRIGGERED", attempts_used, request_ip)
            return 423, {
                "status": "failed",
                "message": "Too many failed attempts. Account is now locked.",
                "attempts_used": attempts_used,
                "attempts_remaining": attempts_remaining
            }

        log_login_attempt(challenge_id, username, "FAILED", attempts_used, request_ip)
        return 401, {
            "status": "failed",
            "message": "Invalid username or password.",
            "attempts_used": attempts_used,
            "attempts_remaining": attempts_remaining
        }

def get_leaderboard() -> List[Dict[str, Any]]:
    """Returns anonymized leaderboard for completed challenges."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT challenge_id, attempts_used, time_taken_seconds
        FROM challenge_accounts
        WHERE status = 'SUCCESS'
        ORDER BY time_taken_seconds ASC, attempts_used ASC
        LIMIT 50
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    for idx, row in enumerate(rows, start=1):
        secs = row["time_taken_seconds"] or 0
        mins = int(secs // 60)
        rem_secs = int(secs % 60)
        formatted_time = f"{mins:02d}:{rem_secs:02d}"
        
        leaderboard.append({
            "rank": idx,
            "challenge_id": row["challenge_id"],
            "attempts_used": row["attempts_used"],
            "time_taken": formatted_time
        })
    return leaderboard

def reset_all_challenges(admin_secret: str) -> bool:
    """Resets all challenge accounts and password hashes for a new classroom round."""
    if admin_secret != settings.ADMIN_SECRET:
        return False
    init_db(force_reseed=True)
    return True
