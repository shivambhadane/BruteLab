import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_john_db():
    init_db(force_reseed=True)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_login_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "AuthForge" in response.text
    assert "John the Ripper" in response.text

def test_start_challenge_assignment():
    response = client.post("/challenge/start", json={"student_code": "STU-037"})
    assert response.status_code == 200
    data = response.json()
    assert data["student_code"] == "STU-037"
    assert len(data["challenges"]) == 3
    
    tiers = [c["tier"] for c in data["challenges"]]
    assert tiers == ["EASY", "MEDIUM", "HARD"]
    assert data["challenges"][0]["challenge_id"] == "JR-037-EASY"
    assert data["challenges"][0]["hash_type"] == "SHA-256"

def test_download_hash_file():
    response = client.get("/challenge/download/JR-037-EASY")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert 'attachment; filename="challenge_JR-037-EASY.txt"' in response.headers["content-disposition"]
    
    content = response.text
    assert content.startswith("student37:")
    hash_part = content.strip().split(":")[1]
    assert len(hash_part) == 64  # SHA-256 hex length

def test_submit_incorrect_password():
    response = client.post("/challenge/submit", json={
        "challenge_id": "JR-037-EASY",
        "password": "wrong_password_123"
    })
    assert response.status_code == 400
    assert "INCORRECT" in response.json()["detail"]

def test_submit_correct_password_easy():
    # Student STU-001 Easy password is 'cyberlab2026'
    response = client.post("/challenge/submit", json={
        "challenge_id": "JR-001-EASY",
        "password": "cyberlab2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["challenge_id"] == "JR-001-EASY"

def test_submit_correct_password_medium():
    # Student STU-001 Medium password is 'CyberLab2026!'
    response = client.post("/challenge/submit", json={
        "challenge_id": "JR-001-MEDIUM",
        "password": "CyberLab2026!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

def test_submit_correct_password_hard():
    # Student STU-001 Hard password is 'argon_cyber2026'
    response = client.post("/challenge/submit", json={
        "challenge_id": "JR-001-HARD",
        "password": "argon_cyber2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

def test_leaderboard():
    response = client.get("/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["student_code"] == "STU-001"
    assert data[0]["solved_count"] == 3

def test_admin_reset_endpoint():
    response = client.post("/api/admin/reset", json={"admin_secret": "cyberlab-admin-key"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
