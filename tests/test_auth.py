import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

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
    assert "BruteLab" in response.text
    assert "Level 2" in response.text


def test_start_missing_student_code():
    response = client.post("/challenge/start", json={"student_code": "STU-999"})
    assert response.status_code == 404
