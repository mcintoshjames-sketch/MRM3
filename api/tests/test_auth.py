"""Tests for authentication endpoints."""
import pytest


class TestLogin:
    """Test /auth/login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login returns token."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"}
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user fails."""
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "anypass"}
        )
        assert response.status_code == 401

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        response = client.post(
            "/auth/login",
            json={"email": "not-an-email", "password": "anypass"}
        )
        assert response.status_code == 422


class TestGetMe:
    """Test /auth/me endpoint."""

    def test_get_me_authenticated(self, client, test_user, auth_headers):
        """Test getting current user info when authenticated."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "User"
        assert "capabilities" in data
        assert data["capabilities"]["can_view_audit_logs"] is False
        assert data["capabilities"]["can_edit_monitoring_plan"] is False
        assert data["capabilities"]["can_approve_model"] is False

    def test_get_me_admin_capabilities(self, client, admin_user, admin_headers):
        """Test admin capabilities are returned for /auth/me."""
        response = client.get("/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@example.com"
        assert data["role"] == "Admin"
        assert "capabilities" in data
        assert data["capabilities"]["can_view_audit_logs"] is True
        assert data["capabilities"]["can_edit_monitoring_plan"] is True
        assert data["capabilities"]["can_approve_model"] is True

    def test_get_me_unauthenticated(self, client):
        """Test getting current user without token fails."""
        response = client.get("/auth/me")
        assert response.status_code == 403  # FastAPI OAuth2 returns 403 for missing token

    def test_get_me_invalid_token(self, client):
        """Test getting current user with invalid token fails."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestRegister:
    """Test /auth/register endpoint."""

    def test_register_new_user(self, client, lob_hierarchy):
        """Test registering a new user."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "newpass123",
                "role": "User",
                "lob_id": lob_hierarchy["retail"].lob_id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "User"
        assert "user_id" in data

    def test_register_duplicate_email(self, client, test_user, lob_hierarchy):
        """Test registering with existing email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "full_name": "Another User",
                "password": "somepass123",
                "role": "User",
                "lob_id": lob_hierarchy["retail"].lob_id
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_admin_role(self, client, lob_hierarchy):
        """Test registering user with admin role."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newadmin@example.com",
                "full_name": "New Admin",
                "password": "adminpass123",
                "role": "Admin",
                "lob_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 201
        assert response.json()["role"] == "Admin"

    def test_register_invalid_email(self, client, lob_hierarchy):
        """Test registering with invalid email format."""
        response = client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "full_name": "User",
                "password": "pass123",
                "role": "User",
                "lob_id": lob_hierarchy["retail"].lob_id
            }
        )
        assert response.status_code == 422
