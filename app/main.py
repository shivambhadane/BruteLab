import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Form, Response, status, HTTPException, Query, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
from app.auth import (
    process_login,
    get_or_create_student_challenge,
    get_leaderboard,
    reset_all_challenges,
    get_recent_logs
)
from app.models import (
    HealthResponse,
    StartChallengeRequest,
    StartChallengeResponse,
    LoginRequest,
    LoginResponse,
    AdminResetRequest
)

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema and seed 70 Level 2 challenge accounts
    init_db()
    yield

app = FastAPI(
    title="AuthForge Level 2: Controlled Live Authentication Challenge",
    description="Live classroom security challenge with Argon2id hashing, rate limiting, and challenge isolation.",
    version="2.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def get_landing_page(request: Request):
    """Renders the AuthForge Level 2 challenge landing page & dashboard."""
    username = request.cookies.get("authforge_user")
    if username:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/challenge/start")
async def start_challenge(req: StartChallengeRequest):
    """
    Assigns or retrieves a student's isolated challenge account (e.g. STU-037 -> AF-037).
    """
    challenge_data = get_or_create_student_challenge(req.student_code)
    if not challenge_data:
        raise HTTPException(status_code=404, detail="Student challenge ID not found. Use STU-001 through STU-070.")
    return challenge_data

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    challenge_id: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None)
):
    """
    Authenticates a candidate password against an assigned challenge account.
    Enforces rate limiting, progressive delay, account lockout, and Argon2id verification.
    """
    is_json = False
    
    if request.headers.get("content-type") == "application/json":
        is_json = True
        try:
            body = await request.json()
            challenge_id = body.get("challenge_id")
            username = body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not challenge_id or not username or not password:
        err_msg = "challenge_id, username, and password are required."
        if is_json:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "failed", "message": err_msg})
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": err_msg},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    status_code, result_data = process_login(challenge_id, username, password, client_ip)

    if is_json:
        json_resp = JSONResponse(status_code=status_code, content=result_data)
        if status_code == 200:
            json_resp.set_cookie(key="authforge_user", value=username)
        return json_resp

    if status_code == 200:
        redirect_resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        redirect_resp.set_cookie(key="authforge_user", value=username)
        return redirect_resp

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": result_data.get("message")},
        status_code=status_code
    )

@app.get("/challenge/status")
async def get_challenge_status(challenge_id: str = Query(...)):
    """Returns status and attempt budget for a given challenge account."""
    conn = get_or_create_student_challenge(challenge_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Challenge ID not found")
    return conn

@app.get("/leaderboard")
async def get_anonymized_leaderboard():
    """Returns anonymized rankings of completed challenges."""
    return get_leaderboard()

@app.post("/api/admin/reset")
async def admin_reset(req: AdminResetRequest):
    """Protected admin endpoint to reset classroom challenges and start a new round."""
    success = reset_all_challenges(req.admin_secret)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid admin secret key")
    return {"status": "success", "message": "Classroom challenge environment successfully reset."}

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Dashboard page for authenticated users."""
    username = request.cookies.get("authforge_user")
    if not username:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"username": username})

@app.get("/logout")
async def logout():
    """Logs out user by clearing session cookie."""
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("authforge_user")
    return resp

@app.get("/api/logs")
async def get_logs():
    """Returns recent log entries for the live audit stream."""
    return {"logs": get_recent_logs(limit=100)}
