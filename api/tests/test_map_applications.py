"""Tests for MAP Applications and Model-Application relationships."""
import pytest
from datetime import date
from app.models.map_application import MapApplication
from app.models.model_application import ModelApplication
from app.models.model import Model
from app.models.user import User
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.core.security import get_password_hash, create_access_token
from app.core.roles import RoleCode
from app.models.role import Role


def get_role_id(db_session, role_code: str) -> int:
    return db_session.query(Role).filter(Role.code == role_code).first().role_id


class TestMapApplicationsAPI:
    """Tests for the MAP Applications search API."""

    @pytest.fixture
    def sample_applications(self, db_session):
        """Create sample MAP applications for testing."""
        apps = [
            MapApplication(
                application_code="APP-001",
                application_name="Enterprise Data Warehouse",
                description="Central data repository",
                owner_name="John Smith",
                owner_email="john@example.com",
                department="IT",
                technology_stack="Snowflake/AWS",
                criticality_tier="Critical",
                status="Active"
            ),
            MapApplication(
                application_code="APP-002",
                application_name="Risk Analytics Platform",
                description="Risk calculations engine",
                owner_name="Jane Doe",
                owner_email="jane@example.com",
                department="Risk",
                technology_stack="Python/Spark",
                criticality_tier="High",
                status="Active"
            ),
            MapApplication(
                application_code="APP-003",
                application_name="Legacy System",
                description="Old decommissioned system",
                department="Finance",
                status="Decommissioned"
            ),
        ]
        for app in apps:
            db_session.add(app)
        db_session.commit()
        return apps

    def test_list_applications_empty(self, client, admin_headers):
        """Test listing applications when none exist."""
        response = client.get("/map/applications", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_applications_with_data(self, client, admin_headers, sample_applications):
        """Test listing applications returns data."""
        response = client.get("/map/applications", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # By default only active applications
        assert len(data) >= 2
        assert any(app["application_code"] == "APP-001" for app in data)

    def test_search_applications_by_name(self, client, admin_headers, sample_applications):
        """Test searching applications by name."""
        response = client.get("/map/applications?search=Risk", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["application_name"] == "Risk Analytics Platform"

    def test_search_applications_by_code(self, client, admin_headers, sample_applications):
        """Test searching applications by code."""
        response = client.get("/map/applications?search=APP-001", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["application_code"] == "APP-001"

    def test_filter_applications_by_department(self, client, admin_headers, sample_applications):
        """Test filtering applications by department."""
        response = client.get("/map/applications?department=IT", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["department"] == "IT"

    def test_filter_applications_by_status(self, client, admin_headers, sample_applications):
        """Test filtering applications by status."""
        response = client.get("/map/applications?status=Decommissioned", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "Decommissioned"

    def test_filter_applications_by_criticality(self, client, admin_headers, sample_applications):
        """Test filtering applications by criticality tier."""
        response = client.get("/map/applications?criticality_tier=Critical", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["criticality_tier"] == "Critical"

    def test_get_application_by_id(self, client, admin_headers, sample_applications):
        """Test getting a specific application by ID."""
        app_id = sample_applications[0].application_id
        response = client.get(f"/map/applications/{app_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["application_code"] == "APP-001"
        assert data["owner_email"] == "john@example.com"

    def test_get_application_not_found(self, client, admin_headers):
        """Test getting non-existent application returns 404."""
        response = client.get("/map/applications/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_list_departments(self, client, admin_headers, sample_applications):
        """Test listing available departments."""
        response = client.get("/map/departments", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "IT" in data
        assert "Risk" in data

    def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated requests are denied."""
        response = client.get("/map/applications")
        assert response.status_code == 401 or response.status_code == 403


class TestModelApplicationsAPI:
    """Tests for Model-Application relationship API."""

    @pytest.fixture
    def relationship_taxonomy(self, db_session):
        """Create Application Relationship Type taxonomy."""
        taxonomy = Taxonomy(
            name="Application Relationship Type",
            description="Types of model-application relationships"
        )
        db_session.add(taxonomy)
        db_session.flush()

        values = [
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="DATA_SOURCE",
                label="Data Source",
                sort_order=1
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="EXECUTION",
                label="Execution Platform",
                sort_order=2
            ),
        ]
        for v in values:
            db_session.add(v)
        db_session.commit()
        return {"taxonomy": taxonomy, "data_source": values[0], "execution": values[1]}

    @pytest.fixture
    def test_model_for_apps(self, db_session, admin_user, usage_frequency):
        """Create a test model owned by admin for application tests."""
        model = Model(
            model_name="Test Model for Applications",
            owner_id=admin_user.user_id,
            row_approval_status="approved",
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    @pytest.fixture
    def test_application(self, db_session):
        """Create a test MAP application."""
        app = MapApplication(
            application_code="APP-TEST",
            application_name="Test Application",
            department="Test Dept",
            status="Active"
        )
        db_session.add(app)
        db_session.commit()
        return app

    def test_list_model_applications_empty(self, client, admin_headers, test_model_for_apps):
        """Test listing applications for a model when none linked."""
        response = client.get(f"/models/{test_model_for_apps.model_id}/applications", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_add_application_to_model(self, client, admin_headers, test_model_for_apps, test_application, relationship_taxonomy):
        """Test adding an application link to a model."""
        payload = {
            "application_id": test_application.application_id,
            "relationship_type_id": relationship_taxonomy["data_source"].value_id,
            "description": "Primary data source",
            "effective_date": "2025-01-01"
        }
        response = client.post(
            f"/models/{test_model_for_apps.model_id}/applications",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["application"]["application_code"] == "APP-TEST"
        assert data["relationship_type"]["code"] == "DATA_SOURCE"
        assert data["description"] == "Primary data source"

    def test_add_duplicate_application_fails(self, client, admin_headers, test_model_for_apps, test_application, relationship_taxonomy, db_session):
        """Test that adding duplicate application link fails."""
        # First add
        link = ModelApplication(
            model_id=test_model_for_apps.model_id,
            application_id=test_application.application_id,
            relationship_type_id=relationship_taxonomy["data_source"].value_id
        )
        db_session.add(link)
        db_session.commit()

        # Try to add again
        payload = {
            "application_id": test_application.application_id,
            "relationship_type_id": relationship_taxonomy["execution"].value_id
        }
        response = client.post(
            f"/models/{test_model_for_apps.model_id}/applications",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 409  # Conflict - already exists
        assert "already exists" in response.json()["detail"].lower()

    def test_list_model_applications_with_data(self, client, admin_headers, test_model_for_apps, test_application, relationship_taxonomy, db_session):
        """Test listing applications for a model with linked apps."""
        link = ModelApplication(
            model_id=test_model_for_apps.model_id,
            application_id=test_application.application_id,
            relationship_type_id=relationship_taxonomy["data_source"].value_id,
            effective_date=date(2025, 1, 1)
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(f"/models/{test_model_for_apps.model_id}/applications", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["application"]["application_code"] == "APP-TEST"

    def test_remove_application_soft_delete(self, client, admin_headers, test_model_for_apps, test_application, relationship_taxonomy, db_session):
        """Test removing application link uses soft delete."""
        link = ModelApplication(
            model_id=test_model_for_apps.model_id,
            application_id=test_application.application_id,
            relationship_type_id=relationship_taxonomy["data_source"].value_id
        )
        db_session.add(link)
        db_session.commit()

        response = client.delete(
            f"/models/{test_model_for_apps.model_id}/applications/{test_application.application_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify soft delete (end_date set)
        db_session.refresh(link)
        assert link.end_date is not None

    def test_include_inactive_shows_ended_links(self, client, admin_headers, test_model_for_apps, test_application, relationship_taxonomy, db_session):
        """Test include_inactive parameter shows ended relationships."""
        link = ModelApplication(
            model_id=test_model_for_apps.model_id,
            application_id=test_application.application_id,
            relationship_type_id=relationship_taxonomy["data_source"].value_id,
            end_date=date(2025, 1, 1)  # Already ended
        )
        db_session.add(link)
        db_session.commit()

        # Without include_inactive
        response = client.get(f"/models/{test_model_for_apps.model_id}/applications", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # With include_inactive
        response = client.get(f"/models/{test_model_for_apps.model_id}/applications?include_inactive=true", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_non_owner_cannot_add_application(self, client, db_session, test_model_for_apps, test_application, relationship_taxonomy, lob_hierarchy):
        """Test that non-owner/non-admin cannot add application links."""
        # Create a different user (regular User role)
        other_user = User(
            email="other_map@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Other User",
            role_id=get_role_id(db_session, RoleCode.USER.value),
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(other_user)
        db_session.commit()

        token = create_access_token(data={"sub": other_user.email})
        other_headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "application_id": test_application.application_id,
            "relationship_type_id": relationship_taxonomy["data_source"].value_id
        }
        response = client.post(
            f"/models/{test_model_for_apps.model_id}/applications",
            json=payload,
            headers=other_headers
        )
        assert response.status_code == 403

    def test_model_not_found(self, client, admin_headers, test_application, relationship_taxonomy):
        """Test adding application to non-existent model."""
        payload = {
            "application_id": test_application.application_id,
            "relationship_type_id": relationship_taxonomy["data_source"].value_id
        }
        response = client.post(
            "/models/99999/applications",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_application_not_found(self, client, admin_headers, test_model_for_apps, relationship_taxonomy):
        """Test adding non-existent application to model."""
        payload = {
            "application_id": 99999,
            "relationship_type_id": relationship_taxonomy["data_source"].value_id
        }
        response = client.post(
            f"/models/{test_model_for_apps.model_id}/applications",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 404
