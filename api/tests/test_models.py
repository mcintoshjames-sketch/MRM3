"""Tests for models CRUD endpoints."""
from datetime import date
import pytest
from app.models.map_application import MapApplication
from app.models.model_application import ModelApplication
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.taxonomy import Taxonomy, TaxonomyValue


def _create_relationship_type_other(db_session):
    """Create Application Relationship Type taxonomy with OTHER code."""
    taxonomy = Taxonomy(
        name="Application Relationship Type",
        description="Types of model-application relationships",
        is_system=True
    )
    db_session.add(taxonomy)
    db_session.flush()

    value = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="OTHER",
        label="Other",
        sort_order=1
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


def _create_map_application(db_session, status="Active"):
    """Create a MAP application with configurable status."""
    app = MapApplication(
        application_code="APP-MRSA-001",
        application_name="MRSA Supporting App",
        department="Risk",
        status=status
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    return app


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
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
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
                "description": "Minimal model description",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
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

    def test_create_model_missing_description(self, client, auth_headers, test_user, usage_frequency):
        """Test creating model without description fails."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "No Description Model",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 422

    def test_create_model_missing_initial_implementation_date(self, client, auth_headers, test_user, usage_frequency):
        """Test creating model without implementation date fails."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "No Implementation Date Model",
                "description": "Missing implementation date",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 422

    def test_create_model_missing_developer_for_in_house(self, client, auth_headers, test_user, usage_frequency):
        """Test creating in-house model without developer fails."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "No Developer Model",
                "description": "Missing developer",
                "development_type": "In-House",
                "owner_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 400

    def test_create_mrsa_requires_supporting_application(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        mrsa_risk_level_taxonomy
    ):
        """Test creating an MRSA without supporting application fails."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "MRSA Missing App",
                "description": "MRSA create test",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": False,
                "is_mrsa": True,
                "mrsa_risk_level_id": mrsa_risk_level_taxonomy["high_risk"].value_id,
                "mrsa_risk_rationale": "High-risk MRSA rationale"
            }
        )
        assert response.status_code == 400
        assert "Supporting application is required" in response.json()["detail"]

    def test_create_mrsa_with_nonexistent_supporting_application_fails(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        mrsa_risk_level_taxonomy
    ):
        """Test creating an MRSA with missing MAP app fails."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "MRSA Missing MAP App",
                "description": "MRSA create test",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": False,
                "is_mrsa": True,
                "mrsa_risk_level_id": mrsa_risk_level_taxonomy["high_risk"].value_id,
                "mrsa_risk_rationale": "High-risk MRSA rationale",
                "supporting_application_id": 99999
            }
        )
        assert response.status_code == 400
        assert "not found in MAP" in response.json()["detail"]

    def test_create_mrsa_with_inactive_supporting_application_fails(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        mrsa_risk_level_taxonomy,
        db_session
    ):
        """Test creating an MRSA with inactive app fails."""
        supporting_app = _create_map_application(db_session, status="Decommissioned")
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "MRSA Inactive App",
                "description": "MRSA create test",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": False,
                "is_mrsa": True,
                "mrsa_risk_level_id": mrsa_risk_level_taxonomy["high_risk"].value_id,
                "mrsa_risk_rationale": "High-risk MRSA rationale",
                "supporting_application_id": supporting_app.application_id
            }
        )
        assert response.status_code == 400
        assert "must be Active" in response.json()["detail"]

    def test_create_mrsa_with_supporting_application_creates_link(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        mrsa_risk_level_taxonomy,
        db_session
    ):
        """Test creating an MRSA auto-creates model_application row."""
        supporting_app = _create_map_application(db_session, status="Active")
        other_relationship_type = _create_relationship_type_other(db_session)

        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "MRSA With App",
                "description": "MRSA create test",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": False,
                "is_mrsa": True,
                "mrsa_risk_level_id": mrsa_risk_level_taxonomy["high_risk"].value_id,
                "mrsa_risk_rationale": "High-risk MRSA rationale",
                "supporting_application_id": supporting_app.application_id
            }
        )
        assert response.status_code == 201

        model_id = response.json()["model_id"]
        relationship = db_session.query(ModelApplication).filter(
            ModelApplication.model_id == model_id,
            ModelApplication.application_id == supporting_app.application_id
        ).first()
        assert relationship is not None
        assert relationship.relationship_type_id == other_relationship_type.value_id
        assert relationship.relationship_direction == "UNKNOWN"
        assert relationship.effective_date == date.today()

    def test_create_non_mrsa_without_supporting_application_still_succeeds(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency
    ):
        """Test non-MRSA create remains backward compatible."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Non-MRSA Regression",
                "description": "Regular model create",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": True,
                "is_mrsa": False
            }
        )
        assert response.status_code == 201

    def test_create_non_mrsa_with_supporting_application_is_ignored(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        db_session
    ):
        """Test supporting_application_id is ignored for non-MRSA create."""
        supporting_app = _create_map_application(db_session, status="Active")
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Non-MRSA With App",
                "description": "Regular model create",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": True,
                "is_mrsa": False,
                "supporting_application_id": supporting_app.application_id
            }
        )
        assert response.status_code == 201

        model_id = response.json()["model_id"]
        relationship = db_session.query(ModelApplication).filter(
            ModelApplication.model_id == model_id
        ).first()
        assert relationship is None

    def test_create_mrsa_requires_non_model_classification(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        mrsa_risk_level_taxonomy,
        db_session
    ):
        """Test is_mrsa=true with is_model=true fails."""
        supporting_app = _create_map_application(db_session, status="Active")
        _create_relationship_type_other(db_session)
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Invalid MRSA Classification",
                "description": "MRSA create test",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": True,
                "is_mrsa": True,
                "mrsa_risk_level_id": mrsa_risk_level_taxonomy["high_risk"].value_id,
                "mrsa_risk_rationale": "High-risk MRSA rationale",
                "supporting_application_id": supporting_app.application_id
            }
        )
        assert response.status_code == 400
        assert "is_model=false" in response.json()["detail"]

    def test_create_mrsa_missing_other_relationship_taxonomy_returns_500(
        self,
        client,
        auth_headers,
        test_user,
        usage_frequency,
        mrsa_risk_level_taxonomy,
        db_session
    ):
        """Test create fails with explicit config error when OTHER is missing."""
        supporting_app = _create_map_application(db_session, status="Active")
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "MRSA Missing OTHER Taxonomy",
                "description": "MRSA create test",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "is_model": False,
                "is_mrsa": True,
                "mrsa_risk_level_id": mrsa_risk_level_taxonomy["high_risk"].value_id,
                "mrsa_risk_rationale": "High-risk MRSA rationale",
                "supporting_application_id": supporting_app.application_id
            }
        )
        assert response.status_code == 500
        assert response.json()["detail"] == (
            "Server configuration error: Application Relationship Type taxonomy with code OTHER not found"
        )

    def test_create_model_with_region_owner(
        self,
        client,
        auth_headers,
        test_user,
        second_user,
        usage_frequency,
        db_session
    ):
        region = Region(code="US", name="United States")
        db_session.add(region)
        db_session.commit()
        db_session.refresh(region)

        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Regional Owner Model",
                "description": "Model with regional owner",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id],
                "model_regions": [
                    {
                        "region_id": region.region_id,
                        "shared_model_owner_id": second_user.user_id
                    }
                ]
            }
        )
        assert response.status_code == 201
        model_id = response.json()["model_id"]
        model_region = db_session.query(ModelRegion).filter(
            ModelRegion.model_id == model_id,
            ModelRegion.region_id == region.region_id
        ).first()
        assert model_region is not None
        assert model_region.shared_model_owner_id == second_user.user_id


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

    def test_update_model_regions_preserves_owner_on_region_ids_update(
        self,
        client,
        auth_headers,
        sample_model,
        second_user,
        db_session
    ):
        us_region = Region(code="US", name="United States")
        eu_region = Region(code="EU", name="Europe")
        db_session.add_all([us_region, eu_region])
        db_session.commit()
        db_session.refresh(us_region)
        db_session.refresh(eu_region)

        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={
                "model_regions": [
                    {
                        "region_id": us_region.region_id,
                        "shared_model_owner_id": second_user.user_id
                    }
                ]
            }
        )
        assert response.status_code == 200

        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"region_ids": [us_region.region_id, eu_region.region_id]}
        )
        assert response.status_code == 200

        model_region = db_session.query(ModelRegion).filter(
            ModelRegion.model_id == sample_model.model_id,
            ModelRegion.region_id == us_region.region_id
        ).first()
        assert model_region is not None
        assert model_region.shared_model_owner_id == second_user.user_id

    def test_update_model_cannot_clear_description(self, client, auth_headers, sample_model):
        """Test that description cannot be cleared once set."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"description": ""}
        )
        assert response.status_code == 400

    def test_update_model_cannot_clear_developer(self, client, auth_headers, sample_model, second_user):
        """Test that developer cannot be cleared once set."""
        set_resp = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"developer_id": second_user.user_id}
        )
        assert set_resp.status_code == 200

        clear_resp = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"developer_id": None}
        )
        assert clear_resp.status_code == 400

    def test_update_model_cannot_clear_usage_frequency(self, client, auth_headers, sample_model):
        """Test that usage frequency cannot be cleared once set."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"usage_frequency_id": None}
        )
        assert response.status_code == 400


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
        from app.models.role import Role
        from app.core.roles import RoleCode
        from app.core.security import get_password_hash
        role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
        level5_user = User(
            email="level5user@example.com",
            full_name="Level 5 User",
            password_hash=get_password_hash("test123"),
            role_id=role_id,
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
        from app.models.role import Role
        from app.core.roles import RoleCode
        from app.core.security import get_password_hash
        role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
        deep_user = User(
            email="deepuser@example.com",
            full_name="Deep User",
            password_hash=get_password_hash("test123"),
            role_id=role_id,
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
                "developer_id": test_user.user_id,
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "initial_implementation_date": date.today().isoformat(),
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "business_line_name" in data
        # test_user's LOB is Retail Banking (level 1)
        assert data["business_line_name"] == "Retail Banking"


class TestModelLastUpdated:
    """Test model_last_updated computed field (production date of latest ACTIVE version)."""

    def test_model_last_updated_no_versions(self, client, auth_headers, sample_model):
        """Test model_last_updated is null when model has no versions."""
        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "model_last_updated" in data
        assert data["model_last_updated"] is None

    def test_model_last_updated_no_active_version(
        self, client, auth_headers, db_session, sample_model, test_user
    ):
        """Test model_last_updated is null when no ACTIVE version exists."""
        from datetime import date
        from app.models.model_version import ModelVersion

        # Create a DRAFT version (not ACTIVE)
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Initial version",
            created_by_id=test_user.user_id,
            status="DRAFT",
            actual_production_date=date(2025, 1, 15)
        )
        db_session.add(version)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["model_last_updated"] is None

    def test_model_last_updated_with_active_version(
        self, client, auth_headers, db_session, sample_model, test_user
    ):
        """Test model_last_updated returns actual_production_date of ACTIVE version."""
        from datetime import date
        from app.models.model_version import ModelVersion

        # Create an ACTIVE version with actual_production_date
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Production version",
            created_by_id=test_user.user_id,
            status="ACTIVE",
            actual_production_date=date(2025, 6, 15)
        )
        db_session.add(version)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["model_last_updated"] == "2025-06-15"

    def test_model_last_updated_ignores_planned_production_date(
        self, client, auth_headers, db_session, sample_model, test_user
    ):
        """Test model_last_updated does NOT fall back to planned_production_date."""
        from datetime import date
        from app.models.model_version import ModelVersion

        # Create ACTIVE version with only planned_production_date (no actual)
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Planned version",
            created_by_id=test_user.user_id,
            status="ACTIVE",
            planned_production_date=date(2025, 12, 25),  # Future date
            actual_production_date=None  # Not yet deployed
        )
        db_session.add(version)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should be null - NOT the planned_production_date
        assert data["model_last_updated"] is None

    def test_model_last_updated_ignores_legacy_production_date(
        self, client, auth_headers, db_session, sample_model, test_user
    ):
        """Test model_last_updated does NOT fall back to legacy production_date field."""
        from datetime import date
        from app.models.model_version import ModelVersion

        # Create ACTIVE version with only legacy production_date (no actual)
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Legacy version",
            created_by_id=test_user.user_id,
            status="ACTIVE",
            production_date=date(2024, 1, 1),  # Legacy field
            actual_production_date=None  # Not using actual field
        )
        db_session.add(version)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should be null - NOT the legacy production_date
        assert data["model_last_updated"] is None

    def test_model_last_updated_in_list_endpoint(
        self, client, auth_headers, db_session, sample_model, test_user
    ):
        """Test model_last_updated is included in list endpoint."""
        from datetime import date
        from app.models.model_version import ModelVersion

        # Create ACTIVE version
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Production version",
            created_by_id=test_user.user_id,
            status="ACTIVE",
            actual_production_date=date(2025, 3, 20)
        )
        db_session.add(version)
        db_session.commit()

        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_last_updated"] == "2025-03-20"

    def test_model_last_updated_multiple_versions_returns_active(
        self, client, auth_headers, db_session, sample_model, test_user
    ):
        """Test model_last_updated returns date from ACTIVE version when multiple exist."""
        from datetime import date
        from app.models.model_version import ModelVersion

        # Create SUPERSEDED version (older)
        old_version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Old version",
            created_by_id=test_user.user_id,
            status="SUPERSEDED",
            actual_production_date=date(2024, 1, 1)
        )
        db_session.add(old_version)

        # Create ACTIVE version (current)
        active_version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="2.0",
            change_type="MAJOR",
            change_description="Current version",
            created_by_id=test_user.user_id,
            status="ACTIVE",
            actual_production_date=date(2025, 6, 1)
        )
        db_session.add(active_version)

        # Create DRAFT version (future)
        draft_version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="3.0",
            change_type="MINOR",
            change_description="Future version",
            created_by_id=test_user.user_id,
            status="DRAFT",
            planned_production_date=date(2025, 12, 1)
        )
        db_session.add(draft_version)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should return the ACTIVE version's date, not SUPERSEDED or DRAFT
        assert data["model_last_updated"] == "2025-06-01"


class TestHasGlobalRiskAssessment:
    """Test has_global_risk_assessment flag on model responses."""

    def test_detail_false_when_no_assessment(self, client, auth_headers, sample_model):
        """GET /models/{id} returns has_global_risk_assessment=false when none exists."""
        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["has_global_risk_assessment"] is False

    def test_detail_true_when_global_assessment_exists(
        self, client, auth_headers, sample_model, db_session
    ):
        """GET /models/{id} returns has_global_risk_assessment=true when a global assessment exists."""
        from app.models.risk_assessment import ModelRiskAssessment
        from app.core.time import utc_now

        assessment = ModelRiskAssessment(
            model_id=sample_model.model_id,
            region_id=None,  # Global assessment
            quantitative_rating="MEDIUM",
            assessed_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(assessment)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["has_global_risk_assessment"] is True

    def test_detail_false_when_only_regional_assessment(
        self, client, auth_headers, sample_model, db_session
    ):
        """Regional-only assessments do NOT set has_global_risk_assessment to true."""
        from app.models.risk_assessment import ModelRiskAssessment
        from app.models.region import Region
        from app.core.time import utc_now

        region = Region(code="US", name="United States")
        db_session.add(region)
        db_session.flush()

        assessment = ModelRiskAssessment(
            model_id=sample_model.model_id,
            region_id=region.region_id,  # Regional, not global
            quantitative_rating="HIGH",
            assessed_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(assessment)
        db_session.commit()

        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["has_global_risk_assessment"] is False

    def test_list_includes_flag(self, client, auth_headers, sample_model, db_session):
        """GET /models/ includes has_global_risk_assessment on each item."""
        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["has_global_risk_assessment"] is False

        # Add a global assessment
        from app.models.risk_assessment import ModelRiskAssessment
        from app.core.time import utc_now

        assessment = ModelRiskAssessment(
            model_id=sample_model.model_id,
            region_id=None,
            quantitative_rating="LOW",
            assessed_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(assessment)
        db_session.commit()

        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        model_item = next(m for m in data if m["model_id"] == sample_model.model_id)
        assert model_item["has_global_risk_assessment"] is True

    def test_get_does_not_write_to_db(
        self, client, auth_headers, sample_model, db_session
    ):
        """GET /models/{id} does NOT modify risk_tier_id — stale data is only fixed by migration."""
        from app.models.risk_assessment import ModelRiskAssessment
        from app.core.time import utc_now

        # Create a tier taxonomy value
        tier_tax = Taxonomy(name="Model Risk Tier", is_system=True)
        db_session.add(tier_tax)
        db_session.flush()
        tier_value = TaxonomyValue(
            taxonomy_id=tier_tax.taxonomy_id, code="TIER_1", label="Tier 1 (High)", sort_order=1
        )
        db_session.add(tier_value)
        db_session.flush()

        # Set model to a stale risk_tier_id (None) while assessment has a final_tier_id
        sample_model.risk_tier_id = None
        assessment = ModelRiskAssessment(
            model_id=sample_model.model_id,
            region_id=None,
            quantitative_rating="HIGH",
            final_tier_id=tier_value.value_id,
            assessed_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(assessment)
        db_session.commit()

        # GET should not modify the DB
        response = client.get(f"/models/{sample_model.model_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify model's risk_tier_id was NOT changed by GET
        db_session.refresh(sample_model)
        assert sample_model.risk_tier_id is None  # Still stale — GET is read-only
