import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import (
    HealthResponse, StartChallengeRequest, StartChallengeResponse,
    SubmitPasswordRequest, SubmitPasswordResponse, LeaderboardEntry, AdminResetRequest, ChallengeTierInfo
)
from app.database import init_db
from app.auth import (
    format_student_code, get_student_challenges, get_challenge_file_content,
    verify_submission, get_leaderboard, get_recent_logs
)

app = FastAPI(
    title="AuthForge Level 2 — John the Ripper Offline Cracking Laboratory",
    description="Educational offline password-hash cracking lab",
    version="2.1.0"
)

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", context={"username": "student37"})


@app.post("/challenge/start", response_model=StartChallengeResponse)
def start_challenge(payload: StartChallengeRequest):
    code = format_student_code(payload.student_code)
    challenges = get_student_challenges(code)
    
    if not challenges:
        raise HTTPException(status_code=404, detail=f"Student identifier {payload.student_code} not found.")
        
    tier_infos = [
        ChallengeTierInfo(
            challenge_id=c["challenge_id"],
            tier=c["tier"],
            hash_type=c["hash_type"],
            status=c["status"],
            password_hint=c["password_hint"]
        )
        for c in challenges
    ]
    
    return StartChallengeResponse(student_code=code, challenges=tier_infos)

@app.get("/challenge/download/{challenge_id}")
def download_hash_file(challenge_id: str):
    res = get_challenge_file_content(challenge_id)
    if not res:
        raise HTTPException(status_code=404, detail="Challenge ID not found.")
        
    filename, content = res
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/challenge/submit", response_model=SubmitPasswordResponse)
def submit_password(payload: SubmitPasswordRequest):
    is_correct, message, time_taken = verify_submission(payload.challenge_id, payload.password)
    
    if is_correct:
        return SubmitPasswordResponse(
            status="success",
            message=message,
            challenge_id=payload.challenge_id,
            time_taken_seconds=time_taken
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=message
        )

@app.get("/leaderboard")
def leaderboard():
    return get_leaderboard()

@app.get("/api/logs")
def get_logs():
    return {"logs": get_recent_logs(50)}

@app.post("/api/admin/reset")
def admin_reset(payload: AdminResetRequest):
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "cyberlab-admin-key")
    if payload.admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized admin key.")
    
    init_db(force_reseed=True)
    return {"status": "success", "message": "Classroom challenges reset."}
