import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db_connection
from app.auth import hash_password, verify_password
from app.config import settings

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_level2_db():
    init_db(force_reseed=True)


def test_argon2id_password_hashing():
    raw_pass = "cyberlab2026"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(hashed, raw_pass) is True
    assert verify_password(hashed, "wrongpassword") is False

def test_start_challenge_assignment():
    res = client.post("/challenge/start", json={"student_code": "STU-037"})
    assert res.status_code == 200
    data = res.json()
    assert data["challenge_id"] == "AF-037"
    assert data["username"] == "student37"
    assert data["attempts_remaining"] == 50

def test_challenge_isolation_prevents_unauthorized_targeting():
    """Verify Section 8 Requirement: Students cannot target another student's account."""
    # Attempting to log into student01 using AF-037 challenge ID
    res = client.post("/login", json={
        "challenge_id": "AF-037",
        "username": "student01",
        "password": "pass"
    })
    assert res.status_code == 403
    assert "Access denied" in res.json()["message"]

def test_rate_limiting_triggers_429():
    """Verify Section 10.1 Requirement: Exceeding 5 attempts per minute triggers HTTP 429."""
    for i in range(5):
        client.post("/login", json={"challenge_id": "AF-010", "username": "student10", "password": f"pass_{i}"})
    
    # 6th attempt should be rate limited
    res = client.post("/login", json={"challenge_id": "AF-010", "username": "student10", "password": "pass_6"})
    assert res.status_code == 429
    assert "Rate limit" in res.json()["message"]

def test_account_lockout_triggers_423():
    """Verify Section 12 Requirement: 10 failed attempts trigger account lockout (HTTP 423)."""
    # Disable rate limit window check for lockout test or use separate attempts
    conn = get_db_connection()
    conn.execute("UPDATE challenge_accounts SET failed_attempts = 9 WHERE challenge_id = 'AF-015'")
    conn.commit()
    conn.close()


    res = client.post("/login", json={"challenge_id": "AF-015", "username": "student15", "password": "wrong_pass"})
    assert res.status_code == 423
    assert "locked" in res.json()["message"]

def test_successful_challenge_completion():
    """Verify successful authentication completes challenge and adds entry to leaderboard."""
    # Retrieve plain password hint/password for AF-001
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM challenge_accounts WHERE challenge_id = 'AF-001'")
    h = cursor.fetchone()["password_hash"]
    conn.close()

    # Find matching raw password from wordlist
    from app.database import SAMPLE_CHALLENGE_PASSWORDS
    correct_pass = None
    for p in SAMPLE_CHALLENGE_PASSWORDS:
        if verify_password(h, p):
            correct_pass = p
            break
    
    assert correct_pass is not None

    res = client.post("/login", json={
        "challenge_id": "AF-001",
        "username": "student01",
        "password": correct_pass
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Check leaderboard
    lb_res = client.get("/leaderboard")
    assert lb_res.status_code == 200
    entries = lb_res.json()
    assert len(entries) >= 1
    assert entries[0]["challenge_id"] == "AF-001"

def test_admin_reset_endpoint():
    """Verify Section 36 Reset System."""
    # Invalid secret fails
    res_bad = client.post("/api/admin/reset", json={"admin_secret": "wrong-secret"})
    assert res_bad.status_code == 403

    # Valid secret succeeds
    res_good = client.post("/api/admin/reset", json={"admin_secret": settings.ADMIN_SECRET})
    assert res_good.status_code == 200
    assert res_good.json()["status"] == "success"
