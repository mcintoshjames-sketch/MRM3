"""Tests for version deployment tasks functionality."""
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from app.models.region import Region
from app.models.model_version import ModelVersion
from app.models.version_deployment_task import VersionDeploymentTask
from app.models.validation import ValidationRequest
from app.models.taxonomy import TaxonomyValue


@pytest.fixture
def test_region(db_session):
    """Create a test region."""
    region = Region(code="US", name="United States", requires_regional_approval=True)
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


@pytest.fixture
def test_version(db_session, sample_model, test_user):
    """Create a test version."""
    future_date = date.today() + timedelta(days=30)
    version = ModelVersion(
        model_id=sample_model.model_id,
        version_number="1.0.0",
        change_type="MAJOR",
        change_description="Test version for deployment",
        planned_production_date=future_date,
        scope="GLOBAL",
        created_by_id=test_user.user_id
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return version


@pytest.fixture
def deployment_task(db_session, sample_model, test_version, test_user):
    """Create a deployment task."""
    future_date = date.today() + timedelta(days=30)
    task = VersionDeploymentTask(
        version_id=test_version.version_id,
        model_id=sample_model.model_id,
        region_id=None,  # Global deployment
        planned_production_date=future_date,
        assigned_to_id=test_user.user_id,
        status="PENDING"
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestDeploymentTasksList:
    """Test deployment tasks list endpoint."""

    def test_get_my_tasks(self, client, auth_headers, deployment_task):
        """Test getting my deployment tasks."""
        response = client.get(
            "/deployment-tasks/my-tasks",
            headers=auth_headers
        )
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) >= 1

        # Find our task
        task_data = next((t for t in tasks if t["task_id"] == deployment_task.task_id), None)
        assert task_data is not None
        assert task_data["status"] == "PENDING"
        assert task_data["model_name"] == "Test Model"

    def test_my_tasks_requires_auth(self, client):
        """Test that my-tasks endpoint requires authentication."""
        response = client.get("/deployment-tasks/my-tasks")
        assert response.status_code in [401, 403]


class TestDeploymentTaskConfirmation:
    """Test deployment task confirmation."""

    def test_confirm_deployment_without_validation(self, client, auth_headers, deployment_task):
        """Test confirming deployment when no validation exists."""
        today = date.today().isoformat()

        response = client.patch(
            f"/deployment-tasks/{deployment_task.task_id}/confirm",
            headers=auth_headers,
            json={
                "actual_production_date": today,
                "confirmation_notes": "Deployed successfully"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CONFIRMED"
        assert data["actual_production_date"] == today
        assert data["confirmation_notes"] == "Deployed successfully"
        assert data["deployed_before_validation_approved"] is False

    def test_confirm_requires_override_when_validation_not_approved(
        self, client, auth_headers, deployment_task, test_version, db_session, taxonomy_values
    ):
        """Test that confirming without validation approval requires override reason."""
        # Create a validation request with INTAKE status (not approved)
        val_request = ValidationRequest(
            request_date=date.today(),
            requestor_id=auth_headers["user_id"] if "user_id" in auth_headers else 1,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["tier1"].value_id,  # Using tier1 as priority for simplicity
            target_completion_date=date.today() + timedelta(days=90),
            current_status_id=taxonomy_values["initial"].value_id,  # Not approved
            trigger_reason="Test validation"
        )
        db_session.add(val_request)
        db_session.flush()

        # Link validation to version
        test_version.validation_request_id = val_request.request_id
        db_session.commit()

        today = date.today().isoformat()

        # Try to confirm without override reason - should fail
        response = client.patch(
            f"/deployment-tasks/{deployment_task.task_id}/confirm",
            headers=auth_headers,
            json={
                "actual_production_date": today,
                "confirmation_notes": "Deployed"
            }
        )

        assert response.status_code == 400
        assert "validation_not_approved" in str(response.json())

    def test_confirm_with_validation_override(
        self, client, auth_headers, deployment_task, test_version, db_session, taxonomy_values
    ):
        """Test that confirming with override reason works when validation not approved."""
        # Create a validation request with INTAKE status
        val_request = ValidationRequest(
            request_date=date.today(),
            requestor_id=1,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["tier1"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            current_status_id=taxonomy_values["initial"].value_id,  # Not approved
            trigger_reason="Test validation"
        )
        db_session.add(val_request)
        db_session.flush()

        # Link validation to version
        test_version.validation_request_id = val_request.request_id
        db_session.commit()

        today = date.today().isoformat()

        # Confirm with override reason - should succeed
        response = client.patch(
            f"/deployment-tasks/{deployment_task.task_id}/confirm",
            headers=auth_headers,
            json={
                "actual_production_date": today,
                "confirmation_notes": "Emergency deployment",
                "validation_override_reason": "Critical production bug fix - approved by CRO"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CONFIRMED"
        assert data["deployed_before_validation_approved"] is True
        assert data["validation_override_reason"] == "Critical production bug fix - approved by CRO"

    def test_cannot_confirm_twice(self, client, auth_headers, deployment_task):
        """Test that cannot confirm an already confirmed task."""
        today = date.today().isoformat()

        # First confirmation
        response = client.patch(
            f"/deployment-tasks/{deployment_task.task_id}/confirm",
            headers=auth_headers,
            json={
                "actual_production_date": today,
                "confirmation_notes": "Deployed"
            }
        )
        assert response.status_code == 200

        # Try to confirm again - should fail
        response = client.patch(
            f"/deployment-tasks/{deployment_task.task_id}/confirm",
            headers=auth_headers,
            json={
                "actual_production_date": today,
                "confirmation_notes": "Deployed again"
            }
        )
        assert response.status_code == 400
        assert "Cannot confirm task with status" in response.json()["detail"]


class TestDeploymentTaskPermissions:
    """Test deployment task permissions."""

    def test_cannot_access_others_tasks(self, client, auth_headers, second_user_headers, deployment_task):
        """Test that users cannot access deployment tasks assigned to others."""
        # deployment_task is assigned to test_user
        # Try to access with second_user
        response = client.get(
            f"/deployment-tasks/{deployment_task.task_id}",
            headers=second_user_headers
        )
        assert response.status_code == 403

    def test_cannot_confirm_others_tasks(self, client, second_user_headers, deployment_task):
        """Test that users cannot confirm deployment tasks assigned to others."""
        today = date.today().isoformat()

        response = client.patch(
            f"/deployment-tasks/{deployment_task.task_id}/confirm",
            headers=second_user_headers,
            json={
                "actual_production_date": today,
                "confirmation_notes": "Deployed"
            }
        )
        assert response.status_code == 403


class TestBulkDeploymentConfirmation:
    """Test bulk confirmation reliability with savepoints."""

    def test_bulk_confirm_partial_success(self, client, admin_headers, db_session, sample_model, admin_user):
        """One failing task should not rollback successful confirmations."""
        future_date = date.today() + timedelta(days=30)

        ok_version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="2.0.0",
            change_type="MAJOR",
            change_description="OK version",
            planned_production_date=future_date,
            scope="GLOBAL",
            created_by_id=admin_user.user_id
        )
        bad_version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="3.0.0",
            change_type="MAJOR",
            change_description="Bad version",
            planned_production_date=future_date,
            scope="GLOBAL",
            created_by_id=admin_user.user_id
        )
        db_session.add_all([ok_version, bad_version])
        db_session.commit()

        ok_task = VersionDeploymentTask(
            version_id=ok_version.version_id,
            model_id=sample_model.model_id,
            region_id=None,
            planned_production_date=future_date,
            assigned_to_id=admin_user.user_id,
            status="PENDING"
        )
        bad_task = VersionDeploymentTask(
            version_id=bad_version.version_id,
            model_id=sample_model.model_id,
            region_id=None,
            planned_production_date=future_date,
            assigned_to_id=admin_user.user_id,
            status="PENDING"
        )
        db_session.add_all([ok_task, bad_task])
        db_session.commit()

        def guard_update_version(db, version):
            if version.version_id == bad_version.version_id:
                raise RuntimeError("forced failure")
            return None

        with patch(
            "app.api.version_deployment_tasks.check_and_update_version_production_date",
            side_effect=guard_update_version
        ):
            response = client.post(
                "/deployment-tasks/bulk/confirm",
                headers=admin_headers,
                json={
                    "task_ids": [ok_task.task_id, bad_task.task_id],
                    "actual_production_date": date.today().isoformat(),
                    "confirmation_notes": "Bulk confirm test"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert ok_task.task_id in data["succeeded"]
        assert any(item["task_id"] == bad_task.task_id for item in data["failed"])

        db_session.expire_all()
        refreshed_ok = db_session.get(VersionDeploymentTask, ok_task.task_id)
        refreshed_bad = db_session.get(VersionDeploymentTask, bad_task.task_id)
        assert refreshed_ok.status == "CONFIRMED"
        assert refreshed_bad.status == "PENDING"
