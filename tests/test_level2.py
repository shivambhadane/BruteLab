import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, hash_sha256, hash_argon2id

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_level2_db():
    init_db(force_reseed=True)

def test_hash_generation():
    raw_pass = "cyberlab2026"
    sha_hash = hash_sha256(raw_pass)
    assert len(sha_hash) == 64
    
    argon_hash = hash_argon2id(raw_pass)
    assert argon_hash.startswith("$argon2id$")

def test_start_challenge_assignment():
    response = client.post("/challenge/start", json={"student_code": "STU-010"})
    assert response.status_code == 200
    data = response.json()
    assert data["student_code"] == "STU-010"
    assert len(data["challenges"]) == 3

def test_download_hash_file_format():
    response = client.get("/challenge/download/JR-010-EASY")
    assert response.status_code == 200
    content = response.text
    assert content.startswith("student10:")

def test_invalid_password_submission():
    response = client.post("/challenge/submit", json={
        "challenge_id": "JR-010-EASY",
        "password": "incorrect_guess"
    })
    assert response.status_code == 400

def test_valid_password_submissions_all_tiers():
    # Easy Tier for STU-010 ((10-1)%10 = 9 -> 'forge2026')
    res_easy = client.post("/challenge/submit", json={"challenge_id": "JR-010-EASY", "password": "forge2026"})
    assert res_easy.status_code == 200
    
    # Medium Tier for STU-010 ((10-1)%9 = 0 -> 'CyberLab2026!')
    res_med = client.post("/challenge/submit", json={"challenge_id": "JR-010-MEDIUM", "password": "CyberLab2026!"})
    assert res_med.status_code == 200
    
    # Hard Tier for STU-010 ((10-1)%4 = 1 -> 'argon_shadow88')
    res_hard = client.post("/challenge/submit", json={"challenge_id": "JR-010-HARD", "password": "argon_shadow88"})
    assert res_hard.status_code == 200


def test_admin_reset_endpoint():
    response = client.post("/api/admin/reset", json={"admin_secret": "cyberlab-admin-key"})
    assert response.status_code == 200
