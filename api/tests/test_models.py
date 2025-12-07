"""Tests for models CRUD endpoints."""
import pytest


class TestListModels:
    """Test GET /models/ endpoint."""

    def test_list_models_empty(self, client, auth_headers):
        """Test listing models when none exist."""
        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_models_with_data(self, client, auth_headers, sample_model):
        """Test listing models returns all models."""
        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_name"] == "Test Model"

    def test_list_models_unauthenticated(self, client):
        """Test listing models without auth fails."""
        response = client.get("/models/")
        assert response.status_code == 403  # FastAPI OAuth2 returns 403 for missing token


class TestCreateModel:
    """Test POST /models/ endpoint."""

    def test_create_model_success(self, client, auth_headers, test_user, usage_frequency):
        """Test creating a new model."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "New Model",
                "description": "A new model",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]  # Must include self as model user
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "New Model"
        assert data["description"] == "A new model"
        assert data["status"] == "In Development"
        assert "model_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_model_minimal(self, client, auth_headers, test_user, usage_frequency):
        """Test creating model with minimal fields."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Minimal Model",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]  # Must include self as model user
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "Minimal Model"
        assert data["status"] == "In Development"  # Default

    def test_create_model_unauthenticated(self, client, test_user):
        """Test creating model without auth fails."""
        response = client.post(
            "/models/",
            json={
                "model_name": "Model",
                "owner_id": test_user.user_id
            }
        )
        assert response.status_code == 403  # FastAPI OAuth2 returns 403 for missing token

    def test_create_model_missing_required_field(self, client, auth_headers):
        """Test creating model without required field fails."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={"description": "No name"}
        )
        assert response.status_code == 422


class TestGetModel:
    """Test GET /models/{model_id} endpoint."""

    def test_get_model_success(self, client, auth_headers, sample_model):
        """Test getting a specific model."""
        response = client.get(
            f"/models/{sample_model.model_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == sample_model.model_id
        assert data["model_name"] == "Test Model"

    def test_get_model_not_found(self, client, auth_headers):
        """Test getting non-existent model fails."""
        response = client.get("/models/9999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_model_unauthenticated(self, client, sample_model):
        """Test getting model without auth fails."""
        response = client.get(f"/models/{sample_model.model_id}")
        assert response.status_code == 403  # FastAPI OAuth2 returns 403 for missing token


class TestUpdateModel:
    """Test PATCH /models/{model_id} endpoint."""

    def test_update_model_single_field(self, client, auth_headers, sample_model):
        """Test updating a single field."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"model_name": "Updated Model"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "Updated Model"
        assert data["description"] == "A test model"  # Unchanged

    def test_update_model_multiple_fields(self, client, auth_headers, sample_model):
        """Test updating multiple fields."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={
                "model_name": "Fully Updated",
                "description": "New description",
                "status": "Active"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "Fully Updated"
        assert data["description"] == "New description"
        assert data["status"] == "Active"

    def test_update_model_not_found(self, client, auth_headers):
        """Test updating non-existent model fails."""
        response = client.patch(
            "/models/9999",
            headers=auth_headers,
            json={"model_name": "Ghost"}
        )
        assert response.status_code == 404

    def test_update_model_unauthenticated(self, client, sample_model):
        """Test updating model without auth fails."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            json={"model_name": "Hacked"}
        )
        assert response.status_code == 403  # FastAPI OAuth2 returns 403 for missing token


class TestDeleteModel:
    """Test DELETE /models/{model_id} endpoint."""

    def test_delete_model_success(self, client, auth_headers, sample_model):
        """Test deleting a model."""
        response = client.delete(
            f"/models/{sample_model.model_id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_model_not_found(self, client, auth_headers):
        """Test deleting non-existent model fails."""
        response = client.delete("/models/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_model_unauthenticated(self, client, sample_model):
        """Test deleting model without auth fails."""
        response = client.delete(f"/models/{sample_model.model_id}")
        assert response.status_code == 403  # FastAPI OAuth2 returns 403 for missing token
