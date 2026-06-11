import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "token" in data["data"]


def test_login_failure():
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_auth_status_unauthorized():
    response = client.get("/api/v1/auth/status")
    assert response.status_code == 401  # no token


def test_auth_status_with_token():
    # Login first to get token
    login_resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    token = login_resp.json()["data"]["token"]
    response = client.get("/api/v1/auth/status", headers={
        "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "logged_in" in data["data"]
    assert "username" in data["data"]
