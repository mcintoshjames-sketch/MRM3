"""Tests for security hardening features (Phase 2 P1)."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.models.user import User
from app.core.security import verify_password
from app.models.audit_log import AuditLog
import app.api.analytics as analytics

class MockAnalyticsSession:
    def __init__(self, real_session):
        self.real_session = real_session

    def execute(self, statement, params=None):
        # Convert statement to string to check for SET commands
        # statement is likely a TextClause
        stmt_str = str(statement).strip().upper()
        if stmt_str.startswith("SET "):
            return None
        return self.real_session.execute(statement, params)

    def rollback(self):
        self.real_session.rollback()
    
    def close(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class TestAnalyticsSecurity:
    """Test security controls for analytics endpoint (SEC-01)."""

    def test_analytics_valid_select(self, client, admin_headers, db_session):
        """Test valid SELECT query is allowed."""
        # Mock SessionLocal to return our proxy session
        mock_session_cls = MagicMock()
        mock_session_cls.return_value = MockAnalyticsSession(db_session)

        with patch("app.api.analytics.SessionLocal", mock_session_cls):
            response = client.post(
                "/analytics/query",
                headers=admin_headers,
                json={"query": "SELECT 1"}
            )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_analytics_invalid_dml(self, client, admin_headers, db_session):
        """Test INSERT/UPDATE/DELETE/DROP are blocked."""
        forbidden_queries = [
            "INSERT INTO users (email, full_name, password_hash, role_id, lob_id, high_fluctuation_flag) VALUES ('hacker@example.com', 'Hacker', 'hash', 1, 1, false)",
            "UPDATE users SET full_name='Hacked'",
            "DELETE FROM users",
            "DROP TABLE users",
            "TRUNCATE users",
            "GRANT ALL PRIVILEGES ON DATABASE mrm_db TO hacker"
        ]
        
        mock_session_cls = MagicMock()
        mock_session_cls.return_value = MockAnalyticsSession(db_session)

        with patch("app.api.analytics.SessionLocal", mock_session_cls):
            for query in forbidden_queries:
                response = client.post(
                    "/analytics/query",
                    headers=admin_headers,
                    json={"query": query}
                )
                # If validation fails, we get 400.
                # If validation passes and execution succeeds (e.g. INSERT), we get 200 (fail).
                # If validation passes and execution fails (SQL error), we get 400 but wrong detail.
                assert response.status_code == 400, f"Query '{query}' should have failed but got {response.status_code}"
                assert "read-only" in response.json()["detail"], f"Query '{query}' failed with unexpected error: {response.json()['detail']}"

    def test_analytics_multiple_statements(self, client, admin_headers):
        """Test multiple statements are blocked."""
        response = client.post(
            "/analytics/query",
            headers=admin_headers,
            json={"query": "SELECT 1; SELECT 2"}
        )
        assert response.status_code == 400
        assert "single-statement" in response.json()["detail"]

    def test_analytics_non_admin(self, client, auth_headers):
        """Test non-admin cannot access analytics."""
        response = client.post(
            "/analytics/query",
            headers=auth_headers,
            json={"query": "SELECT 1"}
        )
        assert response.status_code == 403

    def test_analytics_audit_log_on_success(self, client, admin_headers, db_session):
        """Audit log entry recorded for successful analytics query."""
        mock_session_cls = MagicMock()
        mock_session_cls.return_value = MockAnalyticsSession(db_session)

        with patch("app.api.analytics.SessionLocal", mock_session_cls):
            response = client.post(
                "/analytics/query",
                headers=admin_headers,
                json={"query": "SELECT 1"}
            )

        assert response.status_code == 200
        audit_row = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "AnalyticsQuery"
        ).order_by(AuditLog.log_id.desc()).first()
        assert audit_row is not None
        assert audit_row.changes.get("outcome") == "success"

    def test_analytics_audit_log_on_block(self, client, admin_headers, db_session, monkeypatch):
        """Audit log entry recorded for blocked analytics query."""
        monkeypatch.setattr(analytics, "ANALYTICS_DB_ROLE", "analytics_readonly")
        monkeypatch.setattr(analytics, "ANALYTICS_SEARCH_PATH", "public")

        response = client.post(
            "/analytics/query",
            headers=admin_headers,
            json={"query": "SELECT 1; SELECT 2"}
        )

        assert response.status_code == 400
        audit_row = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "AnalyticsQuery"
        ).order_by(AuditLog.log_id.desc()).first()
        assert audit_row is not None
        assert audit_row.changes.get("outcome") == "blocked"


class TestUserSelfUpdate:
    """Test user self-service update (SEC-03)."""

    def test_update_me_success(self, client, auth_headers, db_session):
        """Test updating own name and password."""
        # Update name and password
        response = client.patch(
            "/auth/users/me",
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "password": "newpassword123",
                "current_password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

        # Verify password changed in DB
        # Need to expire session to see changes made by the request
        db_session.expire_all()
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert verify_password("newpassword123", user.password_hash)

    def test_update_me_wrong_current_password(self, client, auth_headers):
        """Test update fails with wrong current password."""
        response = client.patch(
            "/auth/users/me",
            headers=auth_headers,
            json={
                "password": "newpassword123",
                "current_password": "wrongpassword"
            }
        )
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]

    def test_update_me_restricted_fields(self, client, auth_headers, db_session):
        """Test restricted fields (role, email) cannot be updated."""
        response = client.patch(
            "/auth/users/me",
            headers=auth_headers,
            json={
                "full_name": "Hacker Attempt",
                "role": "Admin",
                "email": "admin@example.com",
                "current_password": "testpass123"
            }
        )
        assert response.status_code == 200
        
        # Verify fields did NOT change
        db_session.expire_all()
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert user.full_name == "Hacker Attempt"
        # user.role is a property returning string display name
        assert user.role == "User"  # Should still be User
        assert user.email == "test@example.com"  # Should still be original email


class TestConfigValidation:
    """Test configuration validation logic (SEC-04)."""

    def test_validate_dev_settings(self):
        """Test development settings pass validation."""
        settings = Settings(
            ENVIRONMENT="development",
            SECRET_KEY="dev-secret",
            DATABASE_URL="postgresql://user:pass@localhost/db"
        )
        # Should not raise
        settings.validate_production_settings()

    def test_validate_prod_default_secret(self):
        """Test production with default secret fails."""
        settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dev-secret-key-change-in-production",
            DATABASE_URL="postgresql://prod:pass@db/prod",
            JWT_ISSUER="mrm",
            JWT_AUDIENCE="mrm"
        )
        with pytest.raises(SystemExit):
            settings.validate_production_settings()

    def test_validate_prod_short_secret(self):
        """Test production with short secret fails."""
        settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short",
            DATABASE_URL="postgresql://prod:pass@db/prod",
            JWT_ISSUER="mrm",
            JWT_AUDIENCE="mrm"
        )
        with pytest.raises(SystemExit):
            settings.validate_production_settings()

    def test_validate_prod_default_db(self):
        """Test production with default DB URL fails."""
        settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="very-long-secure-secret-key-for-production-use",
            DATABASE_URL="postgresql://mrm_user:mrm_pass@db:5432/mrm_db",
            JWT_ISSUER="mrm",
            JWT_AUDIENCE="mrm"
        )
        with pytest.raises(SystemExit):
            settings.validate_production_settings()

    def test_validate_prod_settings_pass(self):
        """Test production with valid settings passes validation."""
        settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="very-long-secure-secret-key-for-production-use",
            DATABASE_URL="postgresql://prod_user:prod_pass@db.prod.internal:5432/prod_db",
            JWT_ISSUER="mrm-prod",
            JWT_AUDIENCE="mrm-prod"
        )
        settings.validate_production_settings()
