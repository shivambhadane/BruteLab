from typing import Optional, List
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

class StartChallengeRequest(BaseModel):
    student_code: str

class ChallengeTierInfo(BaseModel):
    challenge_id: str
    tier: str
    hash_type: str
    status: str
    password_hint: Optional[str] = None

class StartChallengeResponse(BaseModel):
    student_code: str
    challenges: List[ChallengeTierInfo]

class SubmitPasswordRequest(BaseModel):
    challenge_id: str
    password: str

class SubmitPasswordResponse(BaseModel):
    status: str
    message: str
    challenge_id: str
    time_taken_seconds: Optional[float] = None

class LeaderboardEntry(BaseModel):
    rank: int
    student_code: str
    solved_count: int
    total_time: str

class AdminResetRequest(BaseModel):
    admin_secret: str
