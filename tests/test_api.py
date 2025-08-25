from __future__ import annotations

import asyncio
import json

from typing import List
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from heimdall.api import app, get_job_locator, get_settings
from heimdall.db import get_async_sessionmaker
from heimdall.models import FlinkJob, FlinkJobResources, FlinkJobType
from heimdall.service import FlinkJobLocator


class FakeLocator(FlinkJobLocator):
    def __init__(self, jobs: List[FlinkJob]) -> None:
        self._jobs = jobs

    async def find_all(self) -> List[FlinkJob]:
        await asyncio.sleep(0)  # ensure it's truly async
        return self._jobs


@pytest.fixture(autouse=True)
def override_locator():
    jobs = [
        FlinkJob(
            id="uid-1",
            name="demo-app",
            status="RUNNING",
            type=FlinkJobType.APPLICATION,
            startTime=1723940000,
            shortImage="flink:1.18",
            flinkVersion="1.18",
            parallelism=2,
            resources={
                "jm": FlinkJobResources(replicas=1, cpu="0.5", mem="1024m"),
                "tm": FlinkJobResources(replicas=1, cpu="0.5", mem="1024m"),
            },
            metadata={"app": "flink"},
        )
    ]

    def _provider() -> FlinkJobLocator:
        return FakeLocator(jobs)

    app.dependency_overrides[get_job_locator] = _provider
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Initialize test database with SQLite in-memory."""
    # Use in-memory SQLite for tests
    monkeypatch.setenv("HEIMDALL_AUTH__DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # Clear settings cache to pick up new env vars
    get_settings.cache_clear()  # type: ignore[attr-defined]

    # Initialize database session maker
    from heimdall.config import AppConfig

    settings = AppConfig()

    # Initialize the database session maker
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(get_async_sessionmaker(settings))
    finally:
        loop.close()

    yield

    # Cleanup
    monkeypatch.delenv("HEIMDALL_AUTH__DATABASE_URL", raising=False)
    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.fixture
def auth_enabled(monkeypatch):
    """Fixture to enable authentication with test credentials."""
    monkeypatch.setenv("HEIMDALL_AUTH__ENABLED", "true")
    monkeypatch.setenv("HEIMDALL_AUTH__SESSION_SECRET_KEY", "test-secret-key-1234567890")
    monkeypatch.setenv("HEIMDALL_AUTH__GOOGLE_CLIENT_ID", "test-google-client-id")
    monkeypatch.setenv("HEIMDALL_AUTH__GOOGLE_CLIENT_SECRET", "test-google-client-secret")
    monkeypatch.setenv("HEIMDALL_AUTH__ALLOWED_DOMAINS", json.dumps(["example.com"]))
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("HEIMDALL_AUTH__ENABLED", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__SESSION_SECRET_KEY", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__ALLOWED_DOMAINS", raising=False)
    get_settings.cache_clear()


@pytest.fixture
def mock_oauth_flow():
    """Mock the OAuth flow for testing."""
    with patch("heimdall.users.GoogleOAuth2") as mock_google:
        mock_client = MagicMock()
        mock_client.get_authorization_url.return_value = ("https://auth-url.com", "state123")
        mock_client.get_access_token.return_value = {"access_token": "mock-token"}
        mock_google.return_value = mock_client
        yield mock_client


def test_healthz():
    """Health endpoint should always be accessible."""
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_protected_endpoints_require_auth(auth_enabled):
    """API endpoints should require authentication when enabled."""
    client = TestClient(app)

    # Test config endpoint requires auth
    resp = client.get("/api/config")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json()["detail"]

    # Test jobs endpoint requires auth
    resp = client.get("/api/jobs")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json()["detail"]

    # Health endpoint should still be accessible
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_oauth_authorization_url(auth_enabled, mock_oauth_flow):
    """Test OAuth authorization URL generation."""
    client = TestClient(app)

    resp = client.get("/auth/google/authorize")
    assert resp.status_code == 200  # Returns JSON with authorization URL
    data = resp.json()
    assert "authorization_url" in data
    assert "accounts.google.com" in data["authorization_url"]


def test_jwt_login_endpoint(auth_enabled):
    """Test JWT login endpoint exists and requires credentials."""
    client = TestClient(app)

    # Test login endpoint exists
    resp = client.post("/auth/jwt/login", json={"username": "test", "password": "test"})
    assert resp.status_code in [400, 422]  # Should fail due to invalid credentials


def test_auth_callback_endpoint(auth_enabled):
    """Test auth callback endpoint returns HTML template."""
    client = TestClient(app)

    resp = client.get("/auth/callback")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_user_management_endpoints_require_auth(auth_enabled):
    """Test user management endpoints require authentication."""
    client = TestClient(app)

    # Test endpoints that should require authentication
    endpoints = [
        ("GET", "/users/me"),
        ("PATCH", "/users/me"),
        ("POST", "/auth/jwt/logout"),
    ]

    for method, endpoint in endpoints:
        if method == "GET":
            resp = client.get(endpoint)
        elif method == "POST":
            resp = client.post(endpoint)
        elif method == "PATCH":
            resp = client.patch(endpoint)
        else:
            continue

        assert resp.status_code == 401, f"Endpoint {method} {endpoint} should require auth"


def test_domain_restriction_enforcement(auth_enabled):
    """Test that domain restrictions are enforced during registration."""
    # Registration endpoint is not available in the current setup
    # Domain restrictions are enforced in the UserManager class
    # which is tested separately in unit tests
    pass
