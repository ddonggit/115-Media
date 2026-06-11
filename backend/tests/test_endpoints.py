"""Tests for config, transfers, sources endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    token = resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


# ── Config Tests ──────────────────────────────────────────────

def test_get_115_config(auth_headers):
    response = client.get("/api/v1/config/115", headers=auth_headers)
    assert response.status_code in (200, 404)  # None or missing


def test_get_transfer_config(auth_headers):
    response = client.get("/api/v1/config/transfer", headers=auth_headers)
    assert response.status_code == 200


def test_put_transfer_config(auth_headers):
    response = client.put("/api/v1/config/transfer", json={
        "max_submit_retry": 5,
        "max_wait_days": 14,
    }, headers=auth_headers)
    assert response.status_code == 200


def test_get_subscription_config(auth_headers):
    response = client.get("/api/v1/config/subscription", headers=auth_headers)
    assert response.status_code == 200


def test_put_subscription_config(auth_headers):
    response = client.put("/api/v1/config/subscription", json={
        "rss_check_interval_minutes": 15,
    }, headers=auth_headers)
    assert response.status_code == 200


def test_put_strm_config(auth_headers):
    """Verify PUT is supported alongside POST for STRM config."""
    response = client.put("/api/v1/config/strm", json={
        "strm_base_url": "http://localhost:8095/115",
        "media_library_path": "/media/test",
        "auto_generate": False,
    }, headers=auth_headers)
    assert response.status_code == 200


def test_put_tmdb_config(auth_headers):
    """Verify PUT is supported alongside POST for TMDB config."""
    response = client.put("/api/v1/config/tmdb", json={
        "api_key": "test-key-123",
        "language": "zh-CN",
    }, headers=auth_headers)
    assert response.status_code == 200


# ── Transfers Tests ──────────────────────────────────────────

def test_list_transfers(auth_headers):
    response = client.get("/api/v1/transfers/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_transfer_errors(auth_headers):
    """Test the new GET /transfers/errors endpoint."""
    response = client.get("/api/v1/transfers/errors", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


# ── Sources Tests ────────────────────────────────────────────

def test_list_sources(auth_headers):
    response = client.get("/api/v1/sources/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_sources_rss_prefix(auth_headers):
    """Verify /rss-sources prefix works (SPEC-compliant)."""
    response = client.get("/api/v1/rss-sources/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_source_export(auth_headers):
    response = client.get("/api/v1/sources/export", headers=auth_headers)
    assert response.status_code == 200
    # Should return JSON array
    assert response.headers.get("content-type", "").startswith("application/json")


def test_source_nonexistent_scan(auth_headers):
    """Test scan on nonexistent source returns 404."""
    response = client.post("/api/v1/sources/99999/scan", headers=auth_headers)
    assert response.status_code == 404


def test_source_nonexistent_status(auth_headers):
    """Test status on nonexistent source returns 404."""
    response = client.get("/api/v1/sources/99999/status", headers=auth_headers)
    assert response.status_code == 404


# ── Sync Tests ───────────────────────────────────────────────

def test_sync_start(auth_headers):
    """Test the new /sync/start endpoint."""
    response = client.post("/api/v1/sync/start?sync_type=full", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "type" in data
    assert data["type"] == "full"


def test_sync_start_incremental(auth_headers):
    response = client.post("/api/v1/sync/start?sync_type=incremental", headers=auth_headers)
    assert response.status_code == 200


def test_sync_start_invalid_type(auth_headers):
    response = client.post("/api/v1/sync/start?sync_type=invalid", headers=auth_headers)
    assert response.status_code == 422  # validation error


# ── Organize Tests ───────────────────────────────────────────

def test_organize_start(auth_headers):
    """Test the new /organize/start endpoint."""
    response = client.post("/api/v1/organize/start", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_organize_start_with_rule(auth_headers):
    response = client.post("/api/v1/organize/start?rule_id=1", headers=auth_headers)
    assert response.status_code == 200


# ── Dashboard / Logs Tests ───────────────────────────────────

def test_dashboard_stats(auth_headers):
    response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
    assert response.status_code == 200
    assert "data" in response.json()


def test_dashboard_errors(auth_headers):
    response = client.get("/api/v1/dashboard/errors", headers=auth_headers)
    assert response.status_code == 200


def test_logs_list(auth_headers):
    response = client.get("/api/v1/logs/", headers=auth_headers)
    assert response.status_code == 200


def test_logs_stats(auth_headers):
    response = client.get("/api/v1/logs/stats", headers=auth_headers)
    assert response.status_code == 200


# ── Cache Tests ──────────────────────────────────────────────

def test_cache_clear_sync(auth_headers):
    response = client.post("/api/v1/cache/clear/sync", headers=auth_headers)
    assert response.status_code == 200


def test_cache_clear_tmdb(auth_headers):
    response = client.post("/api/v1/cache/clear/tmdb", headers=auth_headers)
    assert response.status_code == 200
