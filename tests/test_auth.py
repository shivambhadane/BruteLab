import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.auth import LOG_PATH

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_login_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "AuthForge" in response.text
    assert "Level 1 • Vulnerable" in response.text

def test_successful_login_json():
    payload = {"username": "testuser", "password": "password123"}
    response = client.post("/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["username"] == "testuser"

def test_successful_login_form():
    form_data = {"username": "labuser", "password": "cyberlab2026"}
    response = client.post("/login", data=form_data, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

def test_failed_login_invalid_password():
    payload = {"username": "testuser", "password": "wrongpassword"}
    response = client.post("/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "failed"

def test_failed_login_unknown_user():
    payload = {"username": "unknown_hacker", "password": "password123"}
    response = client.post("/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "failed"

def test_auth_logging_records_attempts():
    username = "student"
    client.post("/login", json={"username": username, "password": "wrongpass"})
    client.post("/login", json={"username": username, "password": "studentpass"})

    assert LOG_PATH.exists()
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        logs = f.read()
    
    assert f"username={username} | result=FAILED" in logs
    assert f"username={username} | result=SUCCESS" in logs

def test_unrestricted_rapid_login_attempts():
    """Verify Level 1 behavior: No rate limiting (V1) - all requests are processed."""
    for i in range(15):
        res = client.post("/login", json={"username": "testuser", "password": f"attempt_{i}"})
        assert res.status_code == 401
