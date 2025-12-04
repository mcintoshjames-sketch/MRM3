"""Tests for model enhancements (development type, vendor, developer, users)."""
import pytest


class TestModelDevelopmentType:
    """Test model development type validation."""

    def test_create_inhouse_model(self, client, auth_headers, test_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "In-House Model",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["development_type"] == "In-House"
        assert data["vendor_id"] is None

    def test_create_third_party_model_with_vendor(self, client, auth_headers, test_user, sample_vendor, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Third-Party Model",
                "development_type": "Third-Party",
                "owner_id": test_user.user_id,
                "vendor_id": sample_vendor.vendor_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["development_type"] == "Third-Party"
        assert data["vendor_id"] == sample_vendor.vendor_id
        assert data["vendor"]["name"] == "Test Vendor"

    def test_create_third_party_without_vendor_fails(self, client, auth_headers, test_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Invalid Third-Party",
                "development_type": "Third-Party",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 400
        assert "Vendor is required" in response.json()["detail"]

    def test_update_to_third_party_without_vendor_fails(self, client, auth_headers, sample_model):
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"development_type": "Third-Party"}
        )
        assert response.status_code == 400
        assert "Vendor is required" in response.json()["detail"]

    def test_update_to_third_party_with_vendor(self, client, auth_headers, sample_model, sample_vendor):
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={
                "development_type": "Third-Party",
                "vendor_id": sample_vendor.vendor_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["development_type"] == "Third-Party"
        assert data["vendor_id"] == sample_vendor.vendor_id


class TestModelOwnerDeveloper:
    """Test model owner and developer relationships."""

    def test_model_returns_owner_details(self, client, auth_headers, sample_model):
        response = client.get(
            f"/models/{sample_model.model_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "owner" in data
        assert data["owner"]["full_name"] == "Test User"
        assert data["owner"]["email"] == "test@example.com"

    def test_create_model_with_developer(self, client, auth_headers, test_user, second_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Model with Developer",
                "owner_id": test_user.user_id,
                "developer_id": second_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["developer_id"] == second_user.user_id
        assert data["developer"]["full_name"] == "Developer User"

    def test_create_model_invalid_owner_fails(self, client, auth_headers, test_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Invalid Owner",
                "development_type": "In-House",
                "owner_id": 9999,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id, 9999]  # Include self AND invalid owner
            }
        )
        # Validation checks owner_id exists AFTER checking user_ids
        assert response.status_code == 404
        assert "Owner user not found" in response.json()["detail"]

    def test_create_model_invalid_developer_fails(self, client, auth_headers, test_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Invalid Developer",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "developer_id": 9999,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]  # Must include self as model user
            }
        )
        assert response.status_code == 404
        assert "Developer user not found" in response.json()["detail"]

    def test_update_model_owner(self, client, auth_headers, sample_model, second_user):
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"owner_id": second_user.user_id}
        )
        assert response.status_code == 200
        assert response.json()["owner_id"] == second_user.user_id

    def test_update_model_developer(self, client, auth_headers, sample_model, second_user):
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"developer_id": second_user.user_id}
        )
        assert response.status_code == 200
        assert response.json()["developer_id"] == second_user.user_id

    def test_update_model_invalid_owner_fails(self, client, auth_headers, sample_model):
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"owner_id": 9999}
        )
        assert response.status_code == 404
        assert "Owner user not found" in response.json()["detail"]


class TestModelUsers:
    """Test model users many-to-many relationship."""

    def test_create_model_with_users(self, client, auth_headers, test_user, second_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Model with Users",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id, second_user.user_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["users"]) == 2
        user_names = [u["full_name"] for u in data["users"]]
        assert "Test User" in user_names
        assert "Developer User" in user_names

    def test_create_model_with_invalid_user_fails(self, client, auth_headers, test_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Invalid Users",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id, 9999]
            }
        )
        assert response.status_code == 404
        assert "model users not found" in response.json()["detail"]

    def test_update_model_users(self, client, auth_headers, sample_model, test_user, second_user):
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"user_ids": [second_user.user_id]}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 1
        assert data["users"][0]["user_id"] == second_user.user_id

    def test_model_without_users_returns_empty_list(self, client, auth_headers, sample_model):
        response = client.get(
            f"/models/{sample_model.model_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["users"] == []

    def test_list_models_includes_users(self, client, auth_headers, sample_model, test_user, second_user, db_session):
        # Add users to model
        from app.models.user import User
        sample_model.users = [test_user, second_user]
        db_session.commit()

        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert len(data[0]["users"]) == 2


class TestModelVendorValidation:
    """Test vendor validation in models."""

    def test_create_model_with_invalid_vendor_fails(self, client, auth_headers, test_user, usage_frequency):
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Invalid Vendor",
                "development_type": "Third-Party",
                "owner_id": test_user.user_id,
                "vendor_id": 9999,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 404
        assert "Vendor not found" in response.json()["detail"]

    def test_update_model_with_invalid_vendor_fails(self, client, auth_headers, sample_model, sample_vendor):
        # First make it third-party with valid vendor
        client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={
                "development_type": "Third-Party",
                "vendor_id": sample_vendor.vendor_id
            }
        )

        # Try to update to invalid vendor
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"vendor_id": 9999}
        )
        assert response.status_code == 404
        assert "Vendor not found" in response.json()["detail"]


class TestAuthUsersEndpoint:
    """Test the /auth/users endpoint."""

    def test_list_users(self, client, auth_headers, test_user, second_user):
        response = client.get("/auth/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        emails = [u["email"] for u in data]
        assert "test@example.com" in emails
        assert "developer@example.com" in emails

    def test_list_users_unauthenticated(self, client):
        response = client.get("/auth/users")
        assert response.status_code == 403
