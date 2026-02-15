"""
Comprehensive API tests for auth and dashboard endpoints.

Uses FastAPI TestClient with an in-memory SQLite database so that
no running server is required.

Author: HydroClaude Test Team
Date: 2025-11-20
"""

import os
os.environ.setdefault("TESTING", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.database import Base, get_db
from backend.api.models import User, Project, SimulationJob, SimulationResult  # noqa: F401 – register models
from backend.api.main import app
from backend.api.utils.limiter import limiter

# ---------------------------------------------------------------------------
# In-memory test database (StaticPool ensures single shared connection)
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite://"  # in-memory

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Disable rate limiting for tests so requests are not throttled
limiter.enabled = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """FastAPI TestClient using the overridden DB."""
    # Clear the token blacklist between tests
    from backend.api.routes.auth import _token_blacklist
    _token_blacklist.clear()
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """Register a test user and return (username, password, response_data)."""
    username = "testuser"
    password = "Str0ngP@ss"
    email = "test@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": email},
    )
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    return username, password, resp.json()


@pytest.fixture
def auth_header(client, registered_user):
    """Log in the registered user and return Authorization header dict."""
    username, password, _ = registered_user
    resp = client.post(
        "/api/auth/login/json",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Registration tests
# ===========================================================================
class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "Pass1234",
                "email": "new@example.com",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert "id" in data
        # UserPublic response_model excludes password_hash
        assert "password_hash" not in data

    def test_register_duplicate_username(self, client, registered_user):
        username, _, _ = registered_user
        resp = client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": "Other1pass",
                "email": "other@example.com",
            },
        )
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_duplicate_email(self, client, registered_user):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "anotheruser",
                "password": "Other1pass",
                "email": "test@example.com",
            },
        )
        assert resp.status_code == 400

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "badmail",
                "password": "Pass1234",
                "email": "not-an-email",
            },
        )
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "username": "short",
                "password": "ab",
                "email": "short@example.com",
            },
        )
        assert resp.status_code == 422


# ===========================================================================
# Login tests
# ===========================================================================
class TestLogin:
    def test_login_json_success(self, client, registered_user):
        username, password, _ = registered_user
        resp = client.post(
            "/api/auth/login/json",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user"]["username"] == username

    def test_login_form_success(self, client, registered_user):
        username, password, _ = registered_user
        resp = client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == username

    def test_login_wrong_password(self, client, registered_user):
        username, _, _ = registered_user
        resp = client.post(
            "/api/auth/login/json",
            json={"username": username, "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login/json",
            json={"username": "ghost", "password": "Pass1234"},
        )
        assert resp.status_code == 401


# ===========================================================================
# Token refresh tests
# ===========================================================================
class TestRefreshToken:
    def test_refresh_success(self, client, auth_header):
        resp = client.post("/api/auth/refresh", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_no_token(self, client):
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401


# ===========================================================================
# /auth/me tests
# ===========================================================================
class TestGetMe:
    def test_get_me_success(self, client, auth_header, registered_user):
        resp = client.get("/api/auth/me", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        username, _, _ = registered_user
        assert data["username"] == username
        assert "email" in data
        assert "id" in data

    def test_get_me_no_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ===========================================================================
# Logout tests
# ===========================================================================
class TestLogout:
    def test_logout_success(self, client, auth_header):
        resp = client.post("/api/auth/logout", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    def test_logout_no_auth(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401


# ===========================================================================
# Change password tests
# ===========================================================================
class TestChangePassword:
    def test_change_password_success(self, client, auth_header, registered_user):
        _, old_password, _ = registered_user
        resp = client.post(
            "/api/auth/change-password",
            headers=auth_header,
            json={
                "current_password": old_password,
                "new_password": "NewStr0ngP@ss",
            },
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_change_password_wrong_current(self, client, auth_header):
        resp = client.post(
            "/api/auth/change-password",
            headers=auth_header,
            json={
                "current_password": "WrongOldPass1",
                "new_password": "NewStr0ngP@ss",
            },
        )
        assert resp.status_code == 400

    def test_change_password_weak_new(self, client, auth_header, registered_user):
        _, old_password, _ = registered_user
        resp = client.post(
            "/api/auth/change-password",
            headers=auth_header,
            json={
                "current_password": old_password,
                "new_password": "weakpassword",  # no uppercase/digit
            },
        )
        assert resp.status_code == 422

    def test_change_password_no_auth(self, client):
        resp = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "Whatever1",
                "new_password": "NewStr0ngP@ss",
            },
        )
        assert resp.status_code == 401


# ===========================================================================
# Forgot password tests
# ===========================================================================
class TestForgotPassword:
    def test_forgot_password_existing_email(self, client, registered_user):
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    def test_forgot_password_nonexistent_email(self, client):
        """Should still return 200 to prevent email enumeration."""
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200

    def test_forgot_password_invalid_email(self, client):
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422


# ===========================================================================
# Dashboard stats tests
# ===========================================================================
class TestDashboardStats:
    def test_dashboard_stats_empty(self, client, auth_header):
        resp = client.get("/api/dashboard/stats", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] == 0
        assert data["running_jobs"] == 0
        assert data["completed_jobs"] == 0
        assert data["pending_jobs"] == 0
        assert data["failed_jobs"] == 0
        assert isinstance(data["recent_jobs"], list)
        assert len(data["recent_jobs"]) == 0

    def test_dashboard_stats_no_auth(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 401

    def test_dashboard_stats_with_project(self, client, auth_header):
        """Create a project, then verify stats update."""
        proj_resp = client.post(
            "/api/projects",
            headers=auth_header,
            json={"name": "Test Project", "description": "A test"},
        )
        assert proj_resp.status_code in (200, 201), f"Create project failed: {proj_resp.text}"

        resp = client.get("/api/dashboard/stats", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] >= 1


# ===========================================================================
# Health & root endpoint tests
# ===========================================================================
class TestHealthAndRoot:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["status"] == "running"

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data

    def test_docs(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200


# ===========================================================================
# Full auth flow integration test
# ===========================================================================
class TestAuthFlowIntegration:
    def test_full_auth_lifecycle(self, client):
        """Register -> Login -> /me -> Change password -> Login with new -> Logout"""
        # 1. Register
        reg = client.post(
            "/api/auth/register",
            json={
                "username": "lifecycle",
                "password": "Init1Pass",
                "email": "life@example.com",
            },
        )
        assert reg.status_code == 201

        # 2. Login
        login = client.post(
            "/api/auth/login/json",
            json={"username": "lifecycle", "password": "Init1Pass"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. /me
        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["username"] == "lifecycle"

        # 4. Change password
        change = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "current_password": "Init1Pass",
                "new_password": "Changed1Pass",
            },
        )
        assert change.status_code == 200

        # 5. Login with new password
        new_login = client.post(
            "/api/auth/login/json",
            json={"username": "lifecycle", "password": "Changed1Pass"},
        )
        assert new_login.status_code == 200
        new_token = new_login.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        # 6. Logout
        logout = client.post("/api/auth/logout", headers=new_headers)
        assert logout.status_code == 200

    def test_old_password_fails_after_change(self, client):
        """After changing password, the old password should no longer work."""
        client.post(
            "/api/auth/register",
            json={
                "username": "pwchange",
                "password": "Old1Pass!",
                "email": "pwchange@example.com",
            },
        )
        login = client.post(
            "/api/auth/login/json",
            json={"username": "pwchange", "password": "Old1Pass!"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "current_password": "Old1Pass!",
                "new_password": "New1Pass!",
            },
        )

        old_login = client.post(
            "/api/auth/login/json",
            json={"username": "pwchange", "password": "Old1Pass!"},
        )
        assert old_login.status_code == 401
