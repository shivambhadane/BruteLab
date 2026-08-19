import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, Response, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.auth import verify_credentials, log_login_attempt, get_recent_logs
from app.models import LoginRequest, LoginResponse, HealthResponse

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema and seed default users
    init_db()
    yield

app = FastAPI(
    title="AuthForge Level 1: Vulnerable Login Lab",
    description="Intentionally vulnerable local authentication system for cybersecurity education.",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files & setup templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def get_login_page(request: Request):
    """Returns the AuthForge Level 1 login page."""
    # Check session cookie
    username = request.cookies.get("authforge_user")
    if username:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(None),
    password: str = Form(None)
):
    """
    Authenticates a user against local database.
    Accepts both HTML form submit and JSON payload.
    """
    is_json = False
    
    # Handle JSON content-type if sent by API client/tool
    if request.headers.get("content-type") == "application/json":
        is_json = True
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not username or not password:
        if is_json:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"status": "failed", "message": "Invalid username or password."}
            )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid username or password."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Verify credentials in database
    is_valid = verify_credentials(username, password)

    if is_valid:
        log_login_attempt(username, "SUCCESS")
        
        if is_json:
            json_resp = JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "success", "message": "Authentication successful.", "username": username}
            )
            json_resp.set_cookie(key="authforge_user", value=username)
            return json_resp

        redirect_resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        redirect_resp.set_cookie(key="authforge_user", value=username)
        return redirect_resp

    else:
        log_login_attempt(username, "FAILED")
        
        if is_json:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"status": "failed", "message": "Invalid username or password."}
            )
        
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid username or password."},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Dashboard page accessible after authentication."""
    username = request.cookies.get("authforge_user")
    if not username:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"username": username})


@app.get("/logout")
async def logout():
    """Logs out the user by clearing the session cookie."""
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("authforge_user")
    return resp

@app.get("/api/logs")
async def get_logs():
    """API endpoint for live log stream in lab dashboard."""
    logs = get_recent_logs(limit=100)
    return {"logs": logs}
