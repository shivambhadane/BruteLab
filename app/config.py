import os
from pydantic import BaseModel

class Settings(BaseModel):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "authforge-level2-secret-2026")
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "admin-super-secret-key")
    
    # Challenge Security Limits
    MAX_ATTEMPTS: int = int(os.getenv("MAX_ATTEMPTS", "50"))
    MAX_ATTEMPTS_PER_WINDOW: int = int(os.getenv("MAX_ATTEMPTS_PER_WINDOW", "5"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    LOCKOUT_DURATION: int = int(os.getenv("LOCKOUT_DURATION", "120"))
    PROGRESSIVE_DELAY_BASE: float = float(os.getenv("PROGRESSIVE_DELAY_BASE", "0.1"))

settings = Settings()
