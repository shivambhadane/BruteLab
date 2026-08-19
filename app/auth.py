import datetime
from pathlib import Path
from app.database import get_db_connection

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "auth.log"

def verify_credentials(username: str, password: str) -> bool:
    """
    Level 1 Authentication Verification.
    
    VULNERABILITY NOTE:
    - Plain-text password verification (V3)
    - No rate limiting or delay (V1, V5)
    - No account lockout (V2)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    user = cursor.fetchone()
    conn.close()
    
    return user is not None

def log_login_attempt(username: str, result: str):
    """
    Records login attempt to logs/auth.log for observability.
    Format: YYYY-MM-DD HH:MM:SS | username={username} | result={result}
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | username={username} | result={result}\n"
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_line)

def get_recent_logs(limit: int = 50) -> list[str]:
    """Reads the last N lines from the authentication log."""
    if not LOG_PATH.exists():
        return []
    
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return [line.strip() for line in lines[-limit:]]
