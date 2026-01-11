"""Tests for regional version scope functionality."""
import pytest
from datetime import date, timedelta
from app.models.region import Region


@pytest.fixture
def test_region(db_session):
    """Create a test region."""
    region = Region(code="US", name="United States", requires_regional_approval=True)
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


@pytest.fixture(autouse=True)
def _seed_validation_taxonomies(taxonomy_values):
    """Ensure validation taxonomies exist for version auto-validation."""
    return taxonomy_values


class TestRegionalVersionScope:
    """Test regional scope fields on model versions."""

    def test_create_global_version(self, client, auth_headers, sample_model):
        """Test creating a GLOBAL version."""
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Global minor update",
                "scope": "GLOBAL"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["scope"] == "GLOBAL"
        assert data["affected_region_ids"] is None

    def test_create_regional_version(self, client, auth_headers, sample_model, test_region):
        """Test creating a REGIONAL version with affected regions."""
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Regional update for specific region",
                "scope": "REGIONAL",
                "affected_region_ids": [test_region.region_id]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["scope"] == "REGIONAL"
        assert test_region.region_id in data["affected_region_ids"]

    def test_create_version_with_production_dates(self, client, auth_headers, sample_model):
        """Test creating version with planned and actual production dates."""
        future_date = (date.today() + timedelta(days=120)).isoformat()
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Version with production dates",
                "scope": "GLOBAL",
                "planned_production_date": future_date
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["planned_production_date"] == future_date
        assert data["actual_production_date"] is None

    def test_scope_defaults_to_global(self, client, auth_headers, sample_model):
        """Test that scope defaults to GLOBAL if not specified."""
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Version without explicit scope"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["scope"] == "GLOBAL"


class TestRegionalVersionsEndpoint:
    """Test the regional-versions endpoint."""

    def test_get_regional_versions_no_regions(self, client, auth_headers, sample_model):
        """Test getting regional versions for model without regions."""
        response = client.get(
            f"/models/{sample_model.model_id}/regional-versions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == sample_model.model_id
        assert data["model_name"] == sample_model.model_name
        assert isinstance(data["regional_versions"], list)
        # Should return empty list if model has no regions assigned
        assert len(data["regional_versions"]) == 0

    def test_regional_versions_endpoint_requires_auth(self, client, sample_model):
        """Test that regional-versions endpoint requires authentication."""
        response = client.get(f"/models/{sample_model.model_id}/regional-versions")
        # RLS returns 403 instead of 401 when not authenticated
        assert response.status_code in [401, 403]


class TestAutoValidationWithRegionalScope:
    """Test auto-validation creation with regional scope."""

    def test_major_version_creates_validation_request(self, client, auth_headers, sample_model):
        """Test that MAJOR version auto-creates validation request (if policies configured)."""
        future_date = (date.today() + timedelta(days=120)).isoformat()
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MAJOR",
                "change_description": "Major change requiring validation",
                "scope": "GLOBAL",
                "planned_production_date": future_date
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Version created successfully
        assert data["change_type"] == "MAJOR"
        assert data["scope"] == "GLOBAL"

        # If validation created, verify it's configured correctly
        if data.get("validation_request_created"):
            assert data.get("validation_request_id") is not None
            assert data.get("validation_type") in ["TARGETED", "INTERIM"]

    def test_regional_major_version_links_regions(self, client, auth_headers, sample_model, test_region):
        """Test that REGIONAL MAJOR version properly stores regional scope."""
        future_date = (date.today() + timedelta(days=120)).isoformat()
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MAJOR",
                "change_description": "Regional major change",
                "scope": "REGIONAL",
                "affected_region_ids": [test_region.region_id],
                "planned_production_date": future_date
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Verify regional scope is stored correctly
        assert data["scope"] == "REGIONAL"
        assert test_region.region_id in data["affected_region_ids"]

        # If validation request was created, verify regions are linked
        if data.get("validation_request_id"):
            val_response = client.get(
                f"/validation-workflow/requests/{data['validation_request_id']}",
                headers=auth_headers
            )
            if val_response.status_code == 200:
                val_data = val_response.json()
                region_ids = [r["region_id"] for r in val_data.get("regions", [])]
                assert test_region.region_id in region_ids

    def test_urgent_major_version_creates_interim_validation(self, client, auth_headers, sample_model):
        """Test that MAJOR version with near-term date creates INTERIM validation (if policies configured)."""
        near_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MAJOR",
                "change_description": "Urgent change",
                "scope": "GLOBAL",
                "planned_production_date": near_date
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Version created successfully
        assert data["change_type"] == "MAJOR"

        # If validation was created with near-term date, it should be INTERIM
        if data.get("validation_type"):
            assert data.get("validation_type") == "INTERIM"
            # Warning should be present for insufficient lead time
            validation_warning = data.get("validation_warning", "")
            assert "lead time" in validation_warning.lower()

    def test_minor_version_no_validation(self, client, auth_headers, sample_model):
        """Test that MINOR version does not create validation request."""
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Minor change - no validation needed",
                "scope": "GLOBAL"
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Should NOT create validation request
        assert data.get("validation_request_created") is False
        assert data.get("validation_request_id") is None


class TestProductionDateHandling:
    """Test production date field handling."""

    def test_planned_date_maps_to_legacy_field(self, client, auth_headers, sample_model):
        """Test that planned_production_date maps to legacy production_date field."""
        planned_date = (date.today() + timedelta(days=90)).isoformat()
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Testing date mapping",
                "planned_production_date": planned_date
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Both fields should have the same value
        assert data["planned_production_date"] == planned_date
        assert data["production_date"] == planned_date

    def test_legacy_production_date_still_works(self, client, auth_headers, sample_model):
        """Test that legacy production_date field still works."""
        prod_date = (date.today() + timedelta(days=90)).isoformat()
        response = client.post(
            f"/models/{sample_model.model_id}/versions",
            headers=auth_headers,
            json={
                "change_type": "MINOR",
                "change_description": "Using legacy field",
                "production_date": prod_date
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Legacy field should map to planned_production_date
        assert data["production_date"] == prod_date
        assert data["planned_production_date"] == prod_date
