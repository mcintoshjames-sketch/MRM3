import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.core.deps import get_current_user, get_db
from app.core.config import settings
import app.api.analytics as analytics


@pytest.fixture
def mock_db_session():
    with patch("app.api.analytics.SessionLocal") as mock:
        session = MagicMock()
        mock.return_value.__enter__.return_value = session
        yield session


@pytest.fixture
def admin_user():
    user = MagicMock(spec=User)
    user.user_id = 1
    user.email = "admin@example.com"
    user.role = "admin"
    user.role_ref = MagicMock()
    user.role_ref.code = "ADMIN"
    user.is_active = True
    return user


@pytest.fixture
def client(admin_user):
    def override_get_current_user():
        return admin_user

    def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def analytics_config(monkeypatch):
    monkeypatch.setattr(analytics, "ANALYTICS_DB_ROLE", "analytics_readonly")
    monkeypatch.setattr(analytics, "ANALYTICS_SEARCH_PATH", "public")
    monkeypatch.setattr(analytics, "WARNED_MISSING_ANALYTICS_ROLE", False)
    monkeypatch.setattr(analytics, "WARNED_MISSING_ANALYTICS_SEARCH_PATH", False)


def test_readonly_role_switch_applied(client, mock_db_session):
    """SEC-01 Addendum: Ensure we switch to a restricted role."""
    client.post("/analytics/query", json={"query": "SELECT 1"})

    # Check if SET LOCAL ROLE was called
    calls = [str(call.args[0])
             for call in mock_db_session.execute.call_args_list]
    has_role_switch = any("SET LOCAL ROLE" in call for call in calls)
    assert has_role_switch, "Expected analytics role switch to be applied"


def test_extra_timeouts_set(client, mock_db_session):
    """SEC-01 Addendum: Ensure lock_timeout and idle timeouts are set."""
    client.post("/analytics/query", json={"query": "SELECT 1"})

    calls = [str(call.args[0])
             for call in mock_db_session.execute.call_args_list]
    has_lock_timeout = any("lock_timeout" in call for call in calls)
    has_idle_timeout = any("idle_in_transaction_session_timeout" in call for call in calls)
    assert has_lock_timeout, "Expected lock_timeout to be set"
    assert has_idle_timeout, "Expected idle_in_transaction_session_timeout to be set"


def test_dangerous_functions_allowed(client, mock_db_session):
    """SEC-01 Addendum: Dangerous functions like pg_sleep should be blocked."""
    response = client.post(
        "/analytics/query", json={"query": "SELECT pg_sleep(1)"})
    assert response.status_code == 400
    assert "read-only" in response.json()["detail"]


def test_explain_analyze_allowed(client, mock_db_session):
    """SEC-01 Addendum: EXPLAIN ANALYZE should be blocked (it executes code)."""
    response = client.post(
        "/analytics/query", json={"query": "EXPLAIN ANALYZE SELECT 1"})
    assert response.status_code == 400
    assert "read-only" in response.json()["detail"]


def test_sql_wrapping_applied(client, mock_db_session):
    """SEC-01 Addendum: Query should be wrapped in LIMIT clause."""
    query = "SELECT * FROM users"
    client.post("/analytics/query", json={"query": query})

    # Check the actual executed query
    executed_queries = [str(call.args[0])
                        for call in mock_db_session.execute.call_args_list]

    # Filter out SET commands
    user_queries = [q for q in executed_queries if "SELECT * FROM users" in q]
    assert len(user_queries) > 0
    assert "SELECT * FROM (SELECT * FROM users) AS limited LIMIT" in user_queries[0]


def test_sql_wrapping_with_user_limit(client, mock_db_session):
    """SEC-01 Addendum: Queries with LIMIT should still be wrapped."""
    query = "SELECT * FROM users LIMIT 1000000"
    client.post("/analytics/query", json={"query": query})

    executed_queries = [str(call.args[0])
                        for call in mock_db_session.execute.call_args_list]
    user_queries = [q for q in executed_queries if "SELECT * FROM users" in q]
    assert len(user_queries) > 0
    assert "SELECT * FROM (SELECT * FROM users LIMIT 1000000) AS limited LIMIT" in user_queries[0]


def test_missing_role_in_production_returns_error(client, monkeypatch):
    """SEC-01 Addendum: Production must require ANALYTICS_DB_ROLE."""
    monkeypatch.setattr(analytics, "ANALYTICS_DB_ROLE", None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    response = client.post("/analytics/query", json={"query": "SELECT 1"})
    assert response.status_code == 500
    assert "Analytics role is not configured" in response.json()["detail"]
