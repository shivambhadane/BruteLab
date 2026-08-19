from typing import Optional, List
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

class StartChallengeRequest(BaseModel):
    student_code: str

class StartChallengeResponse(BaseModel):
    student_code: str
    challenge_id: str
    username: str
    status: str
    attempts_used: int
    attempts_remaining: int
    password_hint: Optional[str] = None

class LoginRequest(BaseModel):
    challenge_id: str
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    message: str
    attempts_used: int
    attempts_remaining: int
    time_taken_seconds: Optional[float] = None

class ChallengeStatusResponse(BaseModel):
    challenge_id: str
    username: str
    status: str
    attempts_used: int
    attempts_remaining: int
    lockout_remaining_seconds: int = 0

class LeaderboardEntry(BaseModel):
    rank: int
    challenge_id: str
    attempts_used: int
    time_taken: str

class AdminResetRequest(BaseModel):
    admin_secret: str
    difficulty: Optional[str] = "EASY"
