from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    message: str
    username: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
