import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.auth import LOG_PATH

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db(force_reseed=True)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_login_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "AuthForge" in response.text
    assert "Level 2" in response.text



def test_login_missing_parameters_returns_400():
    payload = {"username": "student01", "password": "password123"}
    response = client.post("/login", json=payload)
    assert response.status_code == 400

def test_failed_login_invalid_password():
    payload = {"challenge_id": "AF-001", "username": "student01", "password": "wrongpassword"}
    response = client.post("/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "failed"

def test_failed_login_unknown_challenge_id():
    payload = {"challenge_id": "AF-999", "username": "student999", "password": "password123"}
    response = client.post("/login", json=payload)
    assert response.status_code == 404
