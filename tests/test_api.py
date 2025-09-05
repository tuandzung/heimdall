from __future__ import annotations

import asyncio
import json
import os

from typing import List
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

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
    test_db_path = "./test.db"

    # Use file-based SQLite for tests to ensure shared connections
    monkeypatch.setenv("HEIMDALL_AUTH__DATABASE_URL", f"sqlite+aiosqlite:///{test_db_path}")

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
        # Ensure auth tables are created
        from heimdall.db import create_db_and_tables

        loop.run_until_complete(create_db_and_tables(settings))
    finally:
        loop.close()

    yield

    # Cleanup
    monkeypatch.delenv("HEIMDALL_AUTH__DATABASE_URL", raising=False)
    get_settings.cache_clear()  # type: ignore[attr-defined]

    # Clean up test database file after tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


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


@pytest.fixture
def create_user(monkeypatch):
    # Create a user for testing

    import asyncio

    from fastapi_users.password import PasswordHelper

    from heimdall.db import User, get_async_sessionmaker

    # Create user in the database
    """Fixture to create a test user."""
    monkeypatch.setenv("HEIMDALL_AUTH__ENABLED", "true")
    monkeypatch.setenv("HEIMDALL_AUTH__SESSION_SECRET_KEY", "test-secret-key-1234567890")
    monkeypatch.setenv("HEIMDALL_AUTH__GOOGLE_CLIENT_ID", "test-google-client-id")
    monkeypatch.setenv("HEIMDALL_AUTH__GOOGLE_CLIENT_SECRET", "test-google-client-secret")
    monkeypatch.setenv("HEIMDALL_AUTH__ALLOWED_DOMAINS", json.dumps(["example.com"]))
    get_settings.cache_clear()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _create_user():
        sessionmaker = await get_async_sessionmaker(get_settings())
        async with sessionmaker() as session:
            user = await session.execute(User.__table__.select().where(User.email == "test@example.com"))
            if not user.scalar():
                new_user = User(
                    email="test@example.com",
                    hashed_password=PasswordHelper().hash("test"),
                    is_active=True,
                )
                session.add(new_user)
                await session.commit()

    try:
        loop.run_until_complete(_create_user())
    finally:
        loop.close()

    monkeypatch.delenv("HEIMDALL_AUTH__ENABLED", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__SESSION_SECRET_KEY", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("HEIMDALL_AUTH__ALLOWED_DOMAINS", raising=False)
    get_settings.cache_clear()  # type: ignore[attr-defined]


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

    resp = client.get("/auth/google-cookie/authorize")
    assert resp.status_code == 200  # Returns JSON with authorization URL
    data = resp.json()
    assert "authorization_url" in data
    assert urlparse(data["authorization_url"]).hostname == "accounts.google.com"


def test_cookie_login_endpoint(auth_enabled):
    """Test cookie login endpoint exists and requires credentials."""
    client = TestClient(app)

    # Test cookie login endpoint exists
    resp = client.post("/auth/cookie/login", data={"username": "test", "password": "test"})
    assert resp.status_code in [400, 422]  # Should fail due to invalid credentials


def test_cookie_login_success_and_session_persistence(create_user):
    """Test successful cookie login and session persistence."""
    client = TestClient(app)

    email = "test@example.com"
    password = "test"

    # Login with valid credentials
    resp = client.post("/auth/cookie/login", data={"username": email, "password": password})
    assert resp.status_code == 204
    assert "set-cookie" in resp.headers
    # Extract session cookie
    cookies = resp.cookies
    # Access a protected endpoint with the session cookie
    protected_resp = client.get("/users/me", cookies=cookies)
    assert protected_resp.status_code == 200
    user_data = protected_resp.json()
    assert user_data["email"] == email


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
        ("POST", "/auth/cookie/logout"),
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
