"""Tests for subscription-related endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authenticated headers."""
    resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    token = resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_subscriptions(auth_headers):
    response = client.get("/api/v1/subscriptions/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_subscriptions_with_status(auth_headers):
    response = client.get("/api/v1/subscriptions/?status=active", headers=auth_headers)
    assert response.status_code == 200


def test_tmdb_search_for_subscription(auth_headers):
    """Test the new /subscriptions/tmdb/search endpoint."""
    response = client.get("/api/v1/subscriptions/tmdb/search?q=Inception", headers=auth_headers)
    # May 200 (success) or 502 (TMDB unavailable) — both valid
    assert response.status_code in (200, 502)
    if response.status_code == 200:
        data = response.json()
        assert "data" in data
        items = data["data"]
        assert isinstance(items, list)
        if items:
            assert "tmdb_id" in items[0]
            assert "title" in items[0]


def test_create_subscription_missing_tmdb_id(auth_headers):
    response = client.post("/api/v1/subscriptions/", json={
        "media_name": "Test Movie",
        "media_type": "movie",
        "quality": "1080p",
    }, headers=auth_headers)
    # Should fail — tmdb_id is required
    assert response.status_code in (400, 422)


def test_subscription_count(auth_headers):
    response = client.get("/api/v1/subscriptions/stats/count", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data["data"]
    assert "active" in data["data"]
