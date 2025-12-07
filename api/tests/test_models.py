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


class TestBusinessLineName:
    """Test business_line_name computed field on model responses."""

    def test_model_list_includes_business_line_name(self, client, auth_headers, sample_model, lob_hierarchy):
        """Test that listing models includes business_line_name derived from owner's LOB."""
        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # test_user's LOB is retail (level 1), which is at or above LOB4 (level 5)
        # so business_line_name should be the actual LOB name
        assert "business_line_name" in data[0]
        assert data[0]["business_line_name"] == "Retail Banking"

    def test_model_detail_includes_business_line_name(self, client, auth_headers, sample_model, lob_hierarchy):
        """Test that getting a model includes business_line_name derived from owner's LOB."""
        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "business_line_name" in data
        assert data["business_line_name"] == "Retail Banking"

    def test_business_line_name_at_target_level(
        self, client, admin_headers, admin_user, db_session, lob_hierarchy, usage_frequency
    ):
        """Test business_line_name when owner's LOB is at the target level (LOB4 = level 5)."""
        from app.models.lob import LOBUnit
        from app.models.model import Model

        # Create deeper LOB hierarchy to reach level 5 (LOB4)
        # Level 3
        lob3 = LOBUnit(
            code="L3", name="Level 3 LOB", org_unit="30001",
            level=3, parent_id=lob_hierarchy["credit"].lob_id, is_active=True
        )
        db_session.add(lob3)
        db_session.flush()

        # Level 4
        lob4 = LOBUnit(
            code="L4", name="Level 4 LOB", org_unit="40001",
            level=4, parent_id=lob3.lob_id, is_active=True
        )
        db_session.add(lob4)
        db_session.flush()

        # Level 5 (LOB4 - the target level)
        lob5 = LOBUnit(
            code="L5", name="Level 5 LOB (Target)", org_unit="50001",
            level=5, parent_id=lob4.lob_id, is_active=True
        )
        db_session.add(lob5)
        db_session.flush()

        # Create user at level 5
        from app.models.user import User
        from app.core.security import get_password_hash
        level5_user = User(
            email="level5user@example.com",
            full_name="Level 5 User",
            password_hash=get_password_hash("test123"),
            role="User",
            lob_id=lob5.lob_id
        )
        db_session.add(level5_user)
        db_session.commit()

        # Create model with owner at level 5
        model = Model(
            model_name="Level 5 Test Model",
            description="Test model with owner at level 5",
            development_type="In-House",
            status="In Development",
            owner_id=level5_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Get model and check business_line_name
        response = client.get(f"/models/{model.model_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # User's LOB is at level 5 (target), so business_line_name should be their actual LOB
        assert data["business_line_name"] == "Level 5 LOB (Target)"

    def test_business_line_name_deeper_than_target_rolls_up(
        self, client, admin_headers, admin_user, db_session, lob_hierarchy, usage_frequency
    ):
        """Test business_line_name rolls up when owner's LOB is deeper than target level."""
        from app.models.lob import LOBUnit
        from app.models.model import Model

        # Create deeper LOB hierarchy extending beyond level 5
        # Level 3
        lob3 = LOBUnit(
            code="D3", name="Deep Level 3", org_unit="30002",
            level=3, parent_id=lob_hierarchy["credit"].lob_id, is_active=True
        )
        db_session.add(lob3)
        db_session.flush()

        # Level 4
        lob4 = LOBUnit(
            code="D4", name="Deep Level 4", org_unit="40002",
            level=4, parent_id=lob3.lob_id, is_active=True
        )
        db_session.add(lob4)
        db_session.flush()

        # Level 5 (LOB4 - the target level)
        lob5 = LOBUnit(
            code="D5", name="Deep Level 5 (Target)", org_unit="50002",
            level=5, parent_id=lob4.lob_id, is_active=True
        )
        db_session.add(lob5)
        db_session.flush()

        # Level 6 (deeper than target)
        lob6 = LOBUnit(
            code="D6", name="Deep Level 6", org_unit="60001",
            level=6, parent_id=lob5.lob_id, is_active=True
        )
        db_session.add(lob6)
        db_session.flush()

        # Level 7 (even deeper)
        lob7 = LOBUnit(
            code="D7", name="Deep Level 7", org_unit="70001",
            level=7, parent_id=lob6.lob_id, is_active=True
        )
        db_session.add(lob7)
        db_session.commit()

        # Create user at level 7
        from app.models.user import User
        from app.core.security import get_password_hash
        deep_user = User(
            email="deepuser@example.com",
            full_name="Deep User",
            password_hash=get_password_hash("test123"),
            role="User",
            lob_id=lob7.lob_id
        )
        db_session.add(deep_user)
        db_session.commit()

        # Create model with owner at level 7
        model = Model(
            model_name="Deep LOB Test Model",
            description="Test model with owner deeper than LOB4",
            development_type="In-House",
            status="In Development",
            owner_id=deep_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Get model and check business_line_name rolls up to level 5
        response = client.get(f"/models/{model.model_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # User's LOB is at level 7, should roll up to level 5 (LOB4)
        assert data["business_line_name"] == "Deep Level 5 (Target)"

    def test_business_line_name_above_target_returns_actual_lob(
        self, client, admin_headers, admin_user, sample_model, lob_hierarchy
    ):
        """Test business_line_name returns actual LOB when owner's LOB is above target level."""
        # sample_model's owner (test_user) has LOB at level 1 (Retail Banking)
        # Since level 1 < 5 (LOB4 target), should return actual LOB name
        response = client.get(f"/models/{sample_model.model_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["business_line_name"] == "Retail Banking"

    def test_create_model_includes_business_line_name(
        self, client, auth_headers, test_user, usage_frequency, lob_hierarchy
    ):
        """Test that creating a model returns business_line_name in response."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "New Model With Business Line",
                "description": "Testing business_line_name on create",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "business_line_name" in data
        # test_user's LOB is Retail Banking (level 1)
        assert data["business_line_name"] == "Retail Banking"
