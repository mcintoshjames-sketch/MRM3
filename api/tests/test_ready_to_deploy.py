"""
TDD tests for Phase 5.3: Ready to Deploy Surfacing.

This feature surfaces versions that are validated (APPROVED) but not yet deployed,
helping model owners identify what needs to be deployed.

These tests are written BEFORE implementation (TDD "red" phase).
"""
import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.validation import ValidationRequest
from app.models.version_deployment_task import VersionDeploymentTask
from app.core.time import utc_now
from app.core.security import create_access_token


# NOTE: test_user, admin_user, and db_session fixtures come from conftest.py


@pytest.fixture
def admin_headers(admin_user):
    """Get authorization headers for admin user."""
    token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(test_user):
    """Get authorization headers for regular user."""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regions(db_session) -> list[Region]:
    """Create test regions."""
    existing_us = db_session.query(Region).filter(Region.code == "US").first()
    existing_uk = db_session.query(Region).filter(Region.code == "UK").first()

    regions = []
    if not existing_us:
        us = Region(code="US", name="United States", requires_regional_approval=False)
        db_session.add(us)
        regions.append(us)
    else:
        regions.append(existing_us)

    if not existing_uk:
        uk = Region(code="UK", name="United Kingdom", requires_regional_approval=True)
        db_session.add(uk)
        regions.append(uk)
    else:
        regions.append(existing_uk)

    db_session.commit()
    for r in regions:
        db_session.refresh(r)
    return regions


@pytest.fixture
def model_with_approved_version(
    db_session,
    test_user: User,
    taxonomy_values,
    regions: list[Region],
    usage_frequency
) -> tuple[Model, ModelVersion, ValidationRequest]:
    """Create model with an APPROVED validation - ready to deploy."""
    # Create model
    model = Model(
        model_name="Ready to Deploy Model",
        description="Model with approved validation",
        development_type="In-House",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    # Add regions to model
    for region in regions:
        mr = ModelRegion(model_id=model.model_id, region_id=region.region_id)
        db_session.add(mr)
    db_session.commit()

    # Create validation request (model is linked via version.validation_request_id)
    val_request = ValidationRequest(
        requestor_id=test_user.user_id,
        validation_type_id=taxonomy_values["initial"].value_id,
        priority_id=taxonomy_values["priority_standard"].value_id,
        current_status_id=taxonomy_values["status_approved"].value_id,
        request_date=date.today() - timedelta(days=30),
        target_completion_date=date.today() + timedelta(days=30),
        trigger_reason="Initial validation"
    )
    db_session.add(val_request)
    db_session.commit()
    db_session.refresh(val_request)

    # Create version linked to validation
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0.0",
        change_type="MAJOR",
        change_description="Initial version with approved validation",
        created_by_id=test_user.user_id,
        status="APPROVED",
        validation_request_id=val_request.request_id
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    return model, version, val_request


@pytest.fixture
def model_with_pending_validation(
    db_session,
    test_user: User,
    taxonomy_values,
    regions: list[Region],
    usage_frequency
) -> tuple[Model, ModelVersion, ValidationRequest]:
    """Create model with IN_PROGRESS validation - NOT ready to deploy."""
    # Create model
    model = Model(
        model_name="Not Ready Model",
        description="Model with pending validation",
        development_type="In-House",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    # Add regions to model
    for region in regions:
        mr = ModelRegion(model_id=model.model_id, region_id=region.region_id)
        db_session.add(mr)
    db_session.commit()

    # Create validation request (model is linked via version.validation_request_id)
    val_request = ValidationRequest(
        requestor_id=test_user.user_id,
        validation_type_id=taxonomy_values["initial"].value_id,
        priority_id=taxonomy_values["priority_standard"].value_id,
        current_status_id=taxonomy_values["status_in_progress"].value_id,
        request_date=date.today() - timedelta(days=10),
        target_completion_date=date.today() + timedelta(days=60),
        trigger_reason="Initial validation"
    )
    db_session.add(val_request)
    db_session.commit()
    db_session.refresh(val_request)

    # Create version linked to validation
    version = ModelVersion(
        model_id=model.model_id,
        version_number="2.0.0",
        change_type="MAJOR",
        change_description="Version with pending validation",
        created_by_id=test_user.user_id,
        status="IN_VALIDATION",
        validation_request_id=val_request.request_id
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    return model, version, val_request


class TestReadyToDeployEndpoint:
    """Tests for the GET /versions/ready-to-deploy endpoint."""

    def test_lists_versions_with_approved_validation_not_deployed(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """
        Versions with APPROVED validation and no CONFIRMED deployments
        should appear in ready-to-deploy list.
        """
        model, version, val_request = model_with_approved_version

        response = client.get(
            "/versions/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should find our version
        version_ids = [v["version_id"] for v in data]
        assert version.version_id in version_ids

        # Check the version data
        version_data = next(v for v in data if v["version_id"] == version.version_id)
        assert version_data["model_name"] == model.model_name
        assert version_data["version_number"] == "1.0.0"
        assert version_data["validation_status"] == "Approved"
        assert version_data["deployed_regions_count"] == 0
        assert version_data["total_regions_count"] == 2  # US and UK

    def test_excludes_versions_with_pending_validation(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        model_with_pending_validation: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """
        Versions with validation NOT approved should not appear
        in ready-to-deploy list.
        """
        _, approved_version, _ = model_with_approved_version
        _, pending_version, _ = model_with_pending_validation

        response = client.get(
            "/versions/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        version_ids = [v["version_id"] for v in data]

        # Approved version should be present
        assert approved_version.version_id in version_ids

        # Pending version should NOT be present
        assert pending_version.version_id not in version_ids

    def test_excludes_fully_deployed_versions(
        self,
        client: TestClient,
        db_session,
        admin_user: User,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        regions: list[Region]
    ):
        """
        Versions that are fully deployed (CONFIRMED in all regions)
        should not appear in ready-to-deploy list.
        """
        model, version, _ = model_with_approved_version

        # Create CONFIRMED deployment tasks for all regions
        for region in regions:
            task = VersionDeploymentTask(
                version_id=version.version_id,
                model_id=model.model_id,
                region_id=region.region_id,
                planned_production_date=date.today(),
                actual_production_date=date.today(),
                assigned_to_id=admin_user.user_id,
                status="CONFIRMED",
                confirmed_at=utc_now(),
                confirmed_by_id=admin_user.user_id
            )
            db_session.add(task)
        db_session.commit()

        response = client.get(
            "/versions/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        version_ids = [v["version_id"] for v in data]
        assert version.version_id not in version_ids

    def test_includes_partially_deployed_versions(
        self,
        client: TestClient,
        db_session,
        admin_user: User,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        regions: list[Region]
    ):
        """
        Versions deployed to some but not all regions should still
        appear in ready-to-deploy list with remaining regions indicated.
        """
        model, version, _ = model_with_approved_version

        # Deploy to only US region (first region)
        us_region = regions[0]  # US
        task = VersionDeploymentTask(
            version_id=version.version_id,
            model_id=model.model_id,
            region_id=us_region.region_id,
            planned_production_date=date.today(),
            actual_production_date=date.today(),
            assigned_to_id=admin_user.user_id,
            status="CONFIRMED",
            confirmed_at=utc_now(),
            confirmed_by_id=admin_user.user_id
        )
        db_session.add(task)
        db_session.commit()

        response = client.get(
            "/versions/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Version should still be present (not fully deployed)
        version_data = next(
            (v for v in data if v["version_id"] == version.version_id),
            None
        )
        assert version_data is not None
        assert version_data["deployed_regions_count"] == 1
        assert version_data["total_regions_count"] == 2
        assert "UK" in version_data["pending_regions"]

    def test_shows_pending_deployment_tasks(
        self,
        client: TestClient,
        db_session,
        admin_user: User,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        regions: list[Region]
    ):
        """
        Ready-to-deploy should indicate if pending deployment tasks exist.
        """
        model, version, _ = model_with_approved_version

        # Create a PENDING deployment task for US region
        us_region = regions[0]
        task = VersionDeploymentTask(
            version_id=version.version_id,
            model_id=model.model_id,
            region_id=us_region.region_id,
            planned_production_date=date.today() + timedelta(days=7),
            assigned_to_id=admin_user.user_id,
            status="PENDING"
        )
        db_session.add(task)
        db_session.commit()

        response = client.get(
            "/versions/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        version_data = next(
            (v for v in data if v["version_id"] == version.version_id),
            None
        )
        assert version_data is not None
        assert version_data["pending_tasks_count"] == 1
        assert version_data["has_pending_tasks"] is True


class TestReadyToDeployFiltering:
    """Tests for filtering options on ready-to-deploy endpoint."""

    def test_filter_by_model_id(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """Can filter ready-to-deploy by specific model."""
        model, version, _ = model_with_approved_version

        response = client.get(
            f"/versions/ready-to-deploy?model_id={model.model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # All results should be for the specified model
        for v in data:
            assert v["model_id"] == model.model_id

    def test_filter_by_owner(
        self,
        client: TestClient,
        db_session,
        user_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """Model owners can filter to see only their ready-to-deploy versions."""
        model, version, _ = model_with_approved_version

        response = client.get(
            "/versions/ready-to-deploy?my_models_only=true",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should include the model owned by test_user
        version_ids = [v["version_id"] for v in data]
        assert version.version_id in version_ids


class TestReadyToDeploySummary:
    """Tests for the ready-to-deploy summary/count endpoint."""

    def test_summary_returns_counts(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        model_with_pending_validation: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """Summary endpoint returns count of ready-to-deploy versions."""
        response = client.get(
            "/versions/ready-to-deploy/summary",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should have count of ready versions
        assert "ready_count" in data
        assert data["ready_count"] >= 1  # At least the approved one

        # Should have count of partially deployed
        assert "partially_deployed_count" in data

        # Should have count of versions with pending tasks
        assert "with_pending_tasks_count" in data

    def test_summary_for_model_owner(
        self,
        client: TestClient,
        db_session,
        user_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """
        Summary for model owner shows their ready-to-deploy count.
        This is useful for dashboard badges.
        """
        response = client.get(
            "/versions/ready-to-deploy/summary?my_models_only=true",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least 1 ready version (the one they own)
        assert data["ready_count"] >= 1


class TestReadyToDeployAccessControl:
    """Tests for access control on ready-to-deploy endpoints."""

    def test_admin_sees_all_ready_versions(
        self,
        client: TestClient,
        db_session,
        admin_user: User,
        test_user: User,
        taxonomy_values,
        regions: list[Region],
        usage_frequency
    ):
        """Admin users can see all ready-to-deploy versions across all models."""
        # Create model owned by different user
        model = Model(
            model_name="Other User Model",
            description="Model owned by different user",
            development_type="In-House",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        # Add regions
        for region in regions:
            mr = ModelRegion(model_id=model.model_id, region_id=region.region_id)
            db_session.add(mr)
        db_session.commit()

        # Create approved validation (model is linked via version.validation_request_id)
        val_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["priority_standard"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            request_date=date.today(),
            target_completion_date=date.today() + timedelta(days=30),
            trigger_reason="Initial validation"
        )
        db_session.add(val_request)
        db_session.commit()
        db_session.refresh(val_request)

        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0.0",
            change_type="MAJOR",
            change_description="Version for access control test",
            created_by_id=test_user.user_id,
            status="APPROVED",
            validation_request_id=val_request.request_id
        )
        db_session.add(version)
        db_session.commit()
        db_session.refresh(version)

        # Admin should see this version
        token = create_access_token(data={"sub": admin_user.email})
        response = client.get(
            "/versions/ready-to-deploy",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        version_ids = [v["version_id"] for v in data]
        assert version.version_id in version_ids

    def test_user_sees_only_accessible_models(
        self,
        client: TestClient,
        db_session,
        test_user: User,
        admin_user: User,
        taxonomy_values,
        regions: list[Region],
        usage_frequency
    ):
        """
        Non-admin users should only see ready-to-deploy versions
        for models they own or are delegates for.
        """
        # Create model owned by admin (not test_user)
        admin_model = Model(
            model_name="Admin Owned Model",
            description="Model owned by admin",
            development_type="In-House",
            owner_id=admin_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(admin_model)
        db_session.commit()
        db_session.refresh(admin_model)

        for region in regions:
            mr = ModelRegion(model_id=admin_model.model_id, region_id=region.region_id)
            db_session.add(mr)
        db_session.commit()

        # Create approved validation (model is linked via version.validation_request_id)
        val_request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["priority_standard"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            request_date=date.today(),
            target_completion_date=date.today() + timedelta(days=30),
            trigger_reason="Initial validation"
        )
        db_session.add(val_request)
        db_session.commit()
        db_session.refresh(val_request)

        admin_version = ModelVersion(
            model_id=admin_model.model_id,
            version_number="1.0.0",
            change_type="MAJOR",
            change_description="Admin model version",
            created_by_id=admin_user.user_id,
            status="APPROVED",
            validation_request_id=val_request.request_id
        )
        db_session.add(admin_version)
        db_session.commit()
        db_session.refresh(admin_version)

        # Test user should NOT see admin's model version
        token = create_access_token(data={"sub": test_user.email})
        response = client.get(
            "/versions/ready-to-deploy",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        version_ids = [v["version_id"] for v in data]
        assert admin_version.version_id not in version_ids


class TestReadyToDeployResponseSchema:
    """Tests for the response schema of ready-to-deploy endpoints."""

    def test_response_includes_required_fields(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """Verify response includes all required fields for UI display."""
        response = client.get(
            "/versions/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least one version
        assert len(data) > 0

        version_data = data[0]

        # Required fields for display
        required_fields = [
            "version_id",
            "version_number",
            "model_id",
            "model_name",
            "validation_status",
            "validation_approved_date",
            "total_regions_count",
            "deployed_regions_count",
            "pending_regions",
            "pending_tasks_count",
            "has_pending_tasks",
            "owner_name",
            "days_since_approval"
        ]

        for field in required_fields:
            assert field in version_data, f"Missing field: {field}"

    def test_response_sorted_by_days_since_approval(
        self,
        client: TestClient,
        db_session,
        admin_user: User,
        test_user: User,
        taxonomy_values,
        regions: list[Region],
        usage_frequency
    ):
        """Results should be sorted by days since approval (oldest first)."""
        # Create two models with different approval dates
        for i, days_ago in enumerate([5, 15]):
            model = Model(
                model_name=f"Sort Test Model {i}",
                description=f"Model approved {days_ago} days ago",
                development_type="In-House",
                owner_id=test_user.user_id,
                usage_frequency_id=usage_frequency["daily"].value_id
            )
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)

            for region in regions:
                mr = ModelRegion(model_id=model.model_id, region_id=region.region_id)
                db_session.add(mr)
            db_session.commit()

            # Create approved validation request (model linked via version.validation_request_id)
            val_request = ValidationRequest(
                requestor_id=test_user.user_id,
                validation_type_id=taxonomy_values["initial"].value_id,
                priority_id=taxonomy_values["priority_standard"].value_id,
                current_status_id=taxonomy_values["status_approved"].value_id,
                request_date=date.today() - timedelta(days=days_ago + 10),
                target_completion_date=date.today() - timedelta(days=days_ago),
                completion_date=date.today() - timedelta(days=days_ago),
                trigger_reason="Periodic revalidation"
            )
            db_session.add(val_request)
            db_session.commit()
            db_session.refresh(val_request)

            version = ModelVersion(
                model_id=model.model_id,
                version_number="1.0.0",
                change_type="MAJOR",
                change_description=f"Version approved {days_ago} days ago",
                created_by_id=test_user.user_id,
                status="APPROVED",
                validation_request_id=val_request.request_id
            )
            db_session.add(version)
            db_session.commit()

        token = create_access_token(data={"sub": admin_user.email})
        response = client.get(
            "/versions/ready-to-deploy",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should be sorted by days_since_approval descending (oldest first)
        days_values = [v["days_since_approval"] for v in data if "days_since_approval" in v]
        if len(days_values) >= 2:
            assert days_values == sorted(days_values, reverse=True), \
                "Results should be sorted by days since approval (oldest first)"


# =============================================================================
# NEW TDD TESTS: Per-Region Granularity & Version Source
# =============================================================================
# These tests are for the NEW /deployment-tasks/ready-to-deploy endpoint
# that returns one row per (version, region) and includes version_source.
# =============================================================================

class TestReadyToDeployPerRegionGranularity:
    """
    TDD tests for per-region granularity in ready-to-deploy endpoint.

    The new endpoint should return ONE ROW per (version, region) combination,
    not one row per version. This allows the UI to show deployment status
    for each region independently.
    """

    def test_per_region_granularity_returns_multiple_rows_per_version(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        regions: list[Region]
    ):
        """
        A version deployed to 2 regions should return 2 rows in the response.

        Frontend expects: one row per region to show individual deploy buttons.
        """
        model, version, _ = model_with_approved_version

        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find all rows for our version
        version_rows = [r for r in data if r["version_id"] == version.version_id]

        # Should have 2 rows (one per region: US and UK)
        assert len(version_rows) == 2, \
            f"Expected 2 rows for version (one per region), got {len(version_rows)}"

        # Each row should have a different region
        region_ids = {r["region_id"] for r in version_rows}
        assert len(region_ids) == 2, "Each row should be for a different region"

    def test_per_region_row_includes_region_details(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        regions: list[Region]
    ):
        """
        Each per-region row should include region_id, region_code, and region_name.
        """
        model, version, _ = model_with_approved_version

        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find rows for our version
        version_rows = [r for r in data if r["version_id"] == version.version_id]
        assert len(version_rows) > 0

        row = version_rows[0]

        # Required region fields
        assert "region_id" in row, "Row must include region_id"
        assert "region_code" in row, "Row must include region_code (e.g., 'US')"
        assert "region_name" in row, "Row must include region_name (e.g., 'United States')"

        # Verify values
        region_codes = [r.code for r in regions]
        assert row["region_code"] in region_codes

    def test_per_region_excludes_deployed_regions_only(
        self,
        client: TestClient,
        db_session,
        admin_user: User,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest],
        regions: list[Region]
    ):
        """
        If a version is deployed to US but not UK, only UK row should appear.

        Each row represents a region where deployment is still pending.
        """
        model, version, _ = model_with_approved_version

        # Deploy to US region only
        us_region = regions[0]  # US
        task = VersionDeploymentTask(
            version_id=version.version_id,
            model_id=model.model_id,
            region_id=us_region.region_id,
            planned_production_date=date.today(),
            actual_production_date=date.today(),
            assigned_to_id=admin_user.user_id,
            status="CONFIRMED",
            confirmed_at=utc_now(),
            confirmed_by_id=admin_user.user_id
        )
        db_session.add(task)
        db_session.commit()

        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find rows for our version
        version_rows = [r for r in data if r["version_id"] == version.version_id]

        # Should have only 1 row (UK, since US is deployed)
        assert len(version_rows) == 1, \
            f"Expected 1 row (only UK pending), got {len(version_rows)}"

        # That row should be for UK, not US
        assert version_rows[0]["region_code"] == "UK", \
            "Only UK region should appear (US is already deployed)"


class TestReadyToDeployVersionSource:
    """
    TDD tests for version_source field indicating how version was linked.

    version_source indicates whether the version was:
    - "explicit": User explicitly linked this specific version to validation
    - "inferred": System auto-suggested the version (e.g., latest draft)
    """

    def test_explicit_version_source_when_version_explicitly_linked(
        self,
        client: TestClient,
        db_session,
        test_user: User,
        admin_headers,
        taxonomy_values,
        regions: list[Region],
        usage_frequency
    ):
        """
        When version is explicitly linked to validation request,
        version_source should be "explicit".

        Explicit linking means: version.validation_request_id was set
        explicitly when creating the validation (not auto-inferred).
        """
        # Create model
        model = Model(
            model_name="Explicit Link Model",
            description="Model for explicit version source test",
            development_type="In-House",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        for region in regions:
            mr = ModelRegion(model_id=model.model_id, region_id=region.region_id)
            db_session.add(mr)
        db_session.commit()

        # Create version FIRST (before validation)
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0.0",
            change_type="MAJOR",
            change_description="Version created before validation",
            created_by_id=test_user.user_id,
            status="DRAFT"
        )
        db_session.add(version)
        db_session.commit()
        db_session.refresh(version)

        # Create validation request and EXPLICITLY link the version
        val_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["priority_standard"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            request_date=date.today() - timedelta(days=10),
            target_completion_date=date.today(),
            trigger_reason="Initial validation",
            # Mark as explicit version linking
            version_source="explicit"
        )
        db_session.add(val_request)
        db_session.commit()
        db_session.refresh(val_request)

        # Link version to validation (explicit link)
        version.validation_request_id = val_request.request_id
        version.status = "APPROVED"
        db_session.commit()

        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find our version's rows
        version_rows = [r for r in data if r["version_id"] == version.version_id]
        assert len(version_rows) > 0, "Version should appear in ready-to-deploy"

        # All rows for this version should have version_source="explicit"
        for row in version_rows:
            assert "version_source" in row, "Response must include version_source field"
            assert row["version_source"] == "explicit", \
                "Explicitly linked version should have version_source='explicit'"

    def test_inferred_version_source_when_version_auto_suggested(
        self,
        client: TestClient,
        db_session,
        test_user: User,
        admin_headers,
        taxonomy_values,
        regions: list[Region],
        usage_frequency
    ):
        """
        When version was auto-suggested by the system (not explicitly selected),
        version_source should be "inferred".

        Inferred linking happens when:
        - System auto-selected latest draft version
        - Version was created as part of validation submission
        """
        # Create model
        model = Model(
            model_name="Inferred Link Model",
            description="Model for inferred version source test",
            development_type="In-House",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        for region in regions:
            mr = ModelRegion(model_id=model.model_id, region_id=region.region_id)
            db_session.add(mr)
        db_session.commit()

        # Create validation request FIRST (before version)
        # This simulates the system auto-creating/linking the version
        val_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["priority_standard"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            request_date=date.today() - timedelta(days=10),
            target_completion_date=date.today(),
            trigger_reason="System-triggered revalidation",
            # Mark as inferred version linking
            version_source="inferred"
        )
        db_session.add(val_request)
        db_session.commit()
        db_session.refresh(val_request)

        # Create version linked to validation (auto-suggested)
        version = ModelVersion(
            model_id=model.model_id,
            version_number="2.0.0",
            change_type="MAJOR",
            change_description="Version auto-linked by system",
            created_by_id=test_user.user_id,
            status="APPROVED",
            validation_request_id=val_request.request_id
        )
        db_session.add(version)
        db_session.commit()
        db_session.refresh(version)

        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find our version's rows
        version_rows = [r for r in data if r["version_id"] == version.version_id]
        assert len(version_rows) > 0, "Version should appear in ready-to-deploy"

        # All rows for this version should have version_source="inferred"
        for row in version_rows:
            assert "version_source" in row, "Response must include version_source field"
            assert row["version_source"] == "inferred", \
                "Auto-suggested version should have version_source='inferred'"

    def test_version_source_field_is_required_in_response(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """
        Every row in ready-to-deploy response MUST include version_source.

        Frontend uses this to show different UI treatments for explicit vs inferred.
        """
        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Every row must have version_source
        for row in data:
            assert "version_source" in row, \
                f"Row for version {row.get('version_id')} missing version_source field"
            assert row["version_source"] in ("explicit", "inferred"), \
                f"version_source must be 'explicit' or 'inferred', got: {row['version_source']}"


class TestReadyToDeployNewEndpointSchema:
    """
    TDD tests for the new /deployment-tasks/ready-to-deploy endpoint schema.

    This validates the complete response schema including per-region
    granularity and version_source fields.
    """

    def test_new_endpoint_response_includes_all_required_fields(
        self,
        client: TestClient,
        db_session,
        admin_headers,
        model_with_approved_version: tuple[Model, ModelVersion, ValidationRequest]
    ):
        """
        New endpoint response must include all fields for UI display.
        """
        response = client.get(
            "/deployment-tasks/ready-to-deploy",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Should have at least one ready-to-deploy row"

        row = data[0]

        # Version fields
        assert "version_id" in row
        assert "version_number" in row
        assert "model_id" in row
        assert "model_name" in row

        # Region fields (per-region granularity)
        assert "region_id" in row
        assert "region_code" in row
        assert "region_name" in row

        # Source indicator
        assert "version_source" in row

        # Validation info
        assert "validation_request_id" in row
        assert "validation_approved_date" in row

        # Deployment status for this specific region
        assert "has_pending_task" in row
        assert "pending_task_id" in row or row.get("has_pending_task") is False

        # Owner info
        assert "owner_id" in row
        assert "owner_name" in row

    def test_my_models_filter_works_on_new_endpoint(
        self,
        client: TestClient,
        db_session,
        test_user: User,
        admin_user: User,
        taxonomy_values,
        regions: list[Region],
        usage_frequency
    ):
        """
        my_models_only=true filter should work on new endpoint.
        """
        # Create model owned by test_user
        user_model = Model(
            model_name="User Owned Model",
            description="Model owned by test user",
            development_type="In-House",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(user_model)
        db_session.commit()
        db_session.refresh(user_model)

        for region in regions:
            mr = ModelRegion(model_id=user_model.model_id, region_id=region.region_id)
            db_session.add(mr)
        db_session.commit()

        val_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["priority_standard"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            request_date=date.today() - timedelta(days=5),
            target_completion_date=date.today(),
            trigger_reason="Test validation"
        )
        db_session.add(val_request)
        db_session.commit()
        db_session.refresh(val_request)

        user_version = ModelVersion(
            model_id=user_model.model_id,
            version_number="1.0.0",
            change_type="MAJOR",
            change_description="User's version",
            created_by_id=test_user.user_id,
            status="APPROVED",
            validation_request_id=val_request.request_id
        )
        db_session.add(user_version)
        db_session.commit()
        db_session.refresh(user_version)

        # Create model owned by admin (should NOT appear for test_user)
        admin_model = Model(
            model_name="Admin Owned Model",
            description="Model owned by admin",
            development_type="In-House",
            owner_id=admin_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(admin_model)
        db_session.commit()
        db_session.refresh(admin_model)

        for region in regions:
            mr = ModelRegion(model_id=admin_model.model_id, region_id=region.region_id)
            db_session.add(mr)
        db_session.commit()

        admin_val = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["priority_standard"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            request_date=date.today() - timedelta(days=5),
            target_completion_date=date.today(),
            trigger_reason="Admin validation"
        )
        db_session.add(admin_val)
        db_session.commit()
        db_session.refresh(admin_val)

        admin_version = ModelVersion(
            model_id=admin_model.model_id,
            version_number="1.0.0",
            change_type="MAJOR",
            change_description="Admin's version",
            created_by_id=admin_user.user_id,
            status="APPROVED",
            validation_request_id=admin_val.request_id
        )
        db_session.add(admin_version)
        db_session.commit()
        db_session.refresh(admin_version)

        # Test user with my_models_only filter
        token = create_access_token(data={"sub": test_user.email})
        response = client.get(
            "/deployment-tasks/ready-to-deploy?my_models_only=true",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should include user's version rows
        version_ids = {r["version_id"] for r in data}
        assert user_version.version_id in version_ids, \
            "Should include user's own model version"

        # Should NOT include admin's version rows
        assert admin_version.version_id not in version_ids, \
            "Should NOT include admin's model version with my_models_only=true"
