"""Tests for validation workflow API endpoints."""
import pytest
import json
from datetime import date, timedelta
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.validation import (
    ValidationRequest, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationApproval
)
from app.models.model import Model
from app.models.validation_grouping import ValidationGroupingMemory
from app.models.region import Region
from app.models.model_region import ModelRegion


@pytest.fixture
def workflow_taxonomies(db_session):
    """Create all workflow-related taxonomy values."""
    # Validation Priority
    priority_tax = Taxonomy(name="Validation Priority", is_system=True)
    db_session.add(priority_tax)
    db_session.flush()

    critical = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="CRITICAL", label="Critical", sort_order=1)
    high = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="HIGH", label="High", sort_order=2)
    medium = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="MEDIUM", label="Medium", sort_order=3)
    low = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="LOW", label="Low", sort_order=4)

    # Validation Request Status
    status_tax = Taxonomy(name="Validation Request Status", is_system=True)
    db_session.add(status_tax)
    db_session.flush()

    intake = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="INTAKE", label="Intake", sort_order=1)
    planning = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PLANNING", label="Planning", sort_order=2)
    in_progress = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="IN_PROGRESS", label="In Progress", sort_order=3)
    review = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REVIEW", label="Review", sort_order=4)
    pending_approval = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PENDING_APPROVAL", label="Pending Approval", sort_order=5)
    approved = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="APPROVED", label="Approved", sort_order=6)
    on_hold = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="ON_HOLD", label="On Hold", sort_order=7)
    cancelled = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="CANCELLED", label="Cancelled", sort_order=8)

    # Validation Type
    type_tax = Taxonomy(name="Validation Type", is_system=True)
    db_session.add(type_tax)
    db_session.flush()

    initial_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="INITIAL", label="Initial Validation", sort_order=1)
    annual_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="ANNUAL", label="Annual Review", sort_order=2)

    # Work Component Type
    component_tax = Taxonomy(name="Work Component Type", is_system=True)
    db_session.add(component_tax)
    db_session.flush()

    conceptual = TaxonomyValue(taxonomy_id=component_tax.taxonomy_id, code="CONCEPTUAL_SOUNDNESS", label="Conceptual Soundness Review", sort_order=1)
    data_quality = TaxonomyValue(taxonomy_id=component_tax.taxonomy_id, code="DATA_QUALITY", label="Data Quality Assessment", sort_order=2)
    implementation = TaxonomyValue(taxonomy_id=component_tax.taxonomy_id, code="IMPLEMENTATION", label="Implementation Testing", sort_order=3)
    performance = TaxonomyValue(taxonomy_id=component_tax.taxonomy_id, code="PERFORMANCE", label="Performance Testing", sort_order=4)
    documentation = TaxonomyValue(taxonomy_id=component_tax.taxonomy_id, code="DOCUMENTATION", label="Documentation Review", sort_order=5)

    # Work Component Status
    comp_status_tax = Taxonomy(name="Work Component Status", is_system=True)
    db_session.add(comp_status_tax)
    db_session.flush()

    not_started = TaxonomyValue(taxonomy_id=comp_status_tax.taxonomy_id, code="NOT_STARTED", label="Not Started", sort_order=1)
    comp_in_progress = TaxonomyValue(taxonomy_id=comp_status_tax.taxonomy_id, code="IN_PROGRESS", label="In Progress", sort_order=2)
    completed = TaxonomyValue(taxonomy_id=comp_status_tax.taxonomy_id, code="COMPLETED", label="Completed", sort_order=3)

    # Overall Rating
    rating_tax = Taxonomy(name="Overall Rating", is_system=True)
    db_session.add(rating_tax)
    db_session.flush()

    fit_for_purpose = TaxonomyValue(taxonomy_id=rating_tax.taxonomy_id, code="FIT_FOR_PURPOSE", label="Fit for Purpose", sort_order=1)
    fit_with_conditions = TaxonomyValue(taxonomy_id=rating_tax.taxonomy_id, code="FIT_WITH_CONDITIONS", label="Fit with Conditions", sort_order=2)
    not_fit = TaxonomyValue(taxonomy_id=rating_tax.taxonomy_id, code="NOT_FIT", label="Not Fit for Purpose", sort_order=3)

    db_session.add_all([
        critical, high, medium, low,
        intake, planning, in_progress, review, pending_approval, approved, on_hold, cancelled,
        initial_val, annual_val,
        conceptual, data_quality, implementation, performance, documentation,
        not_started, comp_in_progress, completed,
        fit_for_purpose, fit_with_conditions, not_fit
    ])
    db_session.commit()

    return {
        "priority": {"critical": critical, "high": high, "medium": medium, "low": low},
        "status": {
            "intake": intake, "planning": planning, "in_progress": in_progress,
            "review": review, "pending_approval": pending_approval, "approved": approved,
            "on_hold": on_hold, "cancelled": cancelled
        },
        "type": {"initial": initial_val, "annual": annual_val},
        "component_type": {
            "conceptual": conceptual, "data_quality": data_quality,
            "implementation": implementation, "performance": performance, "documentation": documentation
        },
        "component_status": {
            "not_started": not_started, "in_progress": comp_in_progress, "completed": completed
        },
        "rating": {
            "fit_for_purpose": fit_for_purpose, "fit_with_conditions": fit_with_conditions, "not_fit": not_fit
        }
    }


class TestValidationRequestCRUD:
    """Test basic CRUD operations for validation requests."""

    def test_create_request_success(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test creating a validation request."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],  # Fixed to use model_ids (plural) from Phase 1
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Model deployment"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["models"][0]["model_id"] == sample_model.model_id  # Fixed to use models (plural)
        assert data["current_status"]["label"] == "Intake"
        assert data["priority"]["label"] == "High"
        assert "request_id" in data

    def test_create_request_without_auth(self, client, sample_model, workflow_taxonomies):
        """Test that unauthenticated requests are rejected."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response.status_code in [401, 403]  # FastAPI returns 403 for missing auth header

    def test_create_request_invalid_model(self, client, admin_headers, workflow_taxonomies):
        """Test creating request with non-existent model."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [9999],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Test"
            }
        )
        assert response.status_code == 404
        assert "models not found" in response.json()["detail"].lower()  # Updated for multi-model support

    def test_create_request_invalid_taxonomy(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test creating request with invalid taxonomy values."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": 9999,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response.status_code in [400, 404]  # May be 404 if taxonomy not found
        assert "not found" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_list_requests_empty(self, client, admin_headers, workflow_taxonomies):
        """Test listing requests when none exist."""
        response = client.get("/validation-workflow/requests/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_requests_with_data(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test listing requests with data."""
        # Create a request first
        target_date = (date.today() + timedelta(days=30)).isoformat()
        client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )

        response = client.get("/validation-workflow/requests/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_names"][0] == sample_model.model_name

    def test_get_request_details(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test getting detailed request information."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == request_id
        # Should have default work components created
        assert "work_components" in data

    def test_get_request_not_found(self, client, admin_headers, workflow_taxonomies):
        """Test getting non-existent request."""
        response = client.get("/validation-workflow/requests/9999", headers=admin_headers)
        assert response.status_code == 404

    def test_delete_request(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test deleting a request (Admin only)."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.delete(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        assert get_response.status_code == 404

    def test_delete_request_non_admin(self, client, validator_headers, admin_headers, sample_model, workflow_taxonomies):
        """Test that non-admins cannot delete requests."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.delete(f"/validation-workflow/requests/{request_id}", headers=validator_headers)
        assert response.status_code == 403

    def test_creates_initial_status_history(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test that creating a request creates initial status history entry."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        data = response.json()

        # Should have 1 history entry
        assert len(data["status_history"]) == 1
        assert data["status_history"][0]["new_status"]["label"] == "Intake"


class TestStatusTransitions:
    """Test status transition validation."""

    def test_valid_transition_intake_to_planning(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test valid transition from Intake to Planning."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["planning"].value_id,
                "reason": "Moving to planning phase"
            }
        )
        assert response.status_code == 200
        assert response.json()["current_status"]["label"] == "Planning"

    def test_invalid_transition_intake_to_approved(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test invalid direct transition from Intake to Approved."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["approved"].value_id,
                "reason": "Trying to skip steps"
            }
        )
        assert response.status_code == 400
        assert "Invalid status transition" in response.json()["detail"]

    def test_transition_to_on_hold(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test that On Hold can be reached from any active status."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["on_hold"].value_id,
                "reason": "Waiting for additional information"
            }
        )
        assert response.status_code == 200
        assert response.json()["current_status"]["label"] == "On Hold"

    def test_transition_to_cancelled(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test transitioning to Cancelled status."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["cancelled"].value_id,
                "reason": "Model deprecated"
            }
        )
        assert response.status_code == 200
        assert response.json()["current_status"]["label"] == "Cancelled"

    def test_cannot_transition_from_cancelled(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test that Cancelled is a terminal status."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Move to cancelled
        client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["cancelled"].value_id,
                "reason": "Model deprecated"
            }
        )

        # Try to reopen
        response = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["intake"].value_id,
                "reason": "Trying to reopen"
            }
        )
        assert response.status_code == 400
        assert "Invalid status transition" in response.json()["detail"]

    def test_status_change_creates_history(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test that status changes are recorded in history."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["planning"].value_id,
                "change_reason": "Moving to planning"
            }
        )

        response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        data = response.json()

        # Should have 2 history entries (initial + transition)
        assert len(data["status_history"]) == 2
        # History may be ordered ascending or descending - find the entries by their content
        initial_entry = None
        transition_entry = None
        for entry in data["status_history"]:
            if entry["new_status"]["label"] == "Intake":
                initial_entry = entry
            elif entry["new_status"]["label"] == "Planning":
                transition_entry = entry

        # Verify initial entry exists
        assert initial_entry is not None, "Initial history entry not found"
        # Initial entry may have None old_status or same status
        assert initial_entry["old_status"] is None or initial_entry["old_status"]["label"] == "Intake"

        # Verify transition entry exists
        assert transition_entry is not None, "Transition history entry not found"
        assert transition_entry["old_status"]["label"] == "Intake"
        assert transition_entry["new_status"]["label"] == "Planning"
        assert transition_entry["change_reason"] == "Moving to planning"


class TestValidatorIndependence:
    """Test validator independence enforcement."""

    def test_cannot_assign_model_owner_as_validator(self, client, admin_headers, sample_model, test_user, workflow_taxonomies):
        """Test that model owner cannot be assigned as validator."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Try to assign model owner as validator
        response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": test_user.user_id,  # test_user is the model owner
                "is_primary": True,
                "independence_attestation": True
            }
        )
        assert response.status_code == 400
        assert "independence" in response.json()["detail"].lower()

    def test_cannot_assign_model_developer_as_validator(self, client, admin_headers, db_session, sample_model, second_user, workflow_taxonomies):
        """Test that model developer cannot be assigned as validator."""
        # Set second_user as developer
        sample_model.developer_id = second_user.user_id
        db_session.commit()

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Try to assign developer as validator
        response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": second_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )
        assert response.status_code == 400
        assert "independence" in response.json()["detail"].lower()

    def test_can_assign_independent_validator(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test that independent validator can be assigned."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )
        assert response.status_code == 201
        assert response.json()["validator"]["user_id"] == validator_user.user_id

    def test_must_attest_independence(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test that independence attestation is required."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": False  # Not attested
            }
        )
        assert response.status_code == 400
        assert "attestation" in response.json()["detail"].lower()


class TestOutcomeCreation:
    """Test outcome creation validation."""

    def test_outcome_includes_required_fields(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test that outcome includes all required information."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Move to Planning status
        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["planning"].value_id, "reason": "Moving to planning"}
        )
        assert status_update.status_code == 200

        # Assign validator (required before moving to Review)
        client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )

        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["in_progress"].value_id, "reason": "Moving to in_progress"}
        )
        assert status_update.status_code == 200

        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["review"].value_id, "reason": "Moving to review"}
        )
        assert status_update.status_code == 200

        # Create outcome with all fields
        effective_date = date.today().isoformat()

        response = client.post(
            f"/validation-workflow/requests/{request_id}/outcome",
            headers=admin_headers,
            json={
                "overall_rating_id": workflow_taxonomies["rating"]["fit_with_conditions"].value_id,
                "executive_summary": "Model performs well but requires monitoring",
                "recommended_review_frequency": 6,
                "effective_date": effective_date
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["overall_rating"]["label"] == "Fit with Conditions"
        assert data["executive_summary"] == "Model performs well but requires monitoring"
        assert data["recommended_review_frequency"] == 6

    def test_cannot_create_duplicate_outcome(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test that only one outcome can exist per request."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Move to Planning status
        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["planning"].value_id, "reason": "Moving to planning"}
        )
        assert status_update.status_code == 200

        # Assign validator (required before moving to Review)
        client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )

        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["in_progress"].value_id, "reason": "Moving to in_progress"}
        )
        assert status_update.status_code == 200

        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["review"].value_id, "reason": "Moving to review"}
        )
        assert status_update.status_code == 200

        # Create first outcome
        client.post(
            f"/validation-workflow/requests/{request_id}/outcome",
            headers=admin_headers,
            json={
                "overall_rating_id": workflow_taxonomies["rating"]["fit_for_purpose"].value_id,
                "executive_summary": "First outcome",
                "recommended_review_frequency": 12,
                "effective_date": date.today().isoformat()
            }
        )

        # Try to create second outcome
        response = client.post(
            f"/validation-workflow/requests/{request_id}/outcome",
            headers=admin_headers,
            json={
                "overall_rating_id": workflow_taxonomies["rating"]["not_fit"].value_id,
                "executive_summary": "Second outcome",
                "recommended_review_frequency": 3,
                "effective_date": date.today().isoformat()
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()


class TestApprovalWorkflow:
    """Test approval workflow functionality."""

    def test_add_approval_request(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies):
        """Test adding an approval request."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": admin_user.user_id,
                "approver_role": "Model Risk Committee"
            }
        )
        assert response.status_code == 201
        assert response.json()["approval_status"] == "Pending"

    def test_submit_approval(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies):
        """Test submitting an approval decision."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Add approval request
        approval_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": admin_user.user_id,
                "approver_role": "Model Risk Committee"
            }
        )
        approval_id = approval_response.json()["approval_id"]

        # Submit approval
        response = client.patch(
            f"/validation-workflow/approvals/{approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Approved",
                "comments": "Approved with no concerns"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approval_status"] == "Approved"
        assert data["comments"] == "Approved with no concerns"
        # Check that decision timestamp was recorded
        assert "updated_at" in data or "created_at" in data

    def test_reject_approval(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies):
        """Test rejecting an approval."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        approval_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": admin_user.user_id,
                "approver_role": "Senior Management"
            }
        )
        approval_id = approval_response.json()["approval_id"]

        response = client.patch(
            f"/validation-workflow/approvals/{approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Rejected",
                "comments": "Additional analysis required"
            }
        )
        assert response.status_code == 200
        assert response.json()["approval_status"] == "Rejected"

    def test_invalid_approval_status(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies):
        """Test that invalid approval status is rejected."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        approval_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": admin_user.user_id,
                "approver_role": "Committee"
            }
        )
        approval_id = approval_response.json()["approval_id"]

        response = client.patch(
            f"/validation-workflow/approvals/{approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Invalid"
            }
        )
        assert response.status_code == 422  # Validation error


class TestDashboardEndpoints:
    """Test dashboard and reporting endpoints."""

    def test_aging_report_empty(self, client, admin_headers, workflow_taxonomies):
        """Test aging report with no data."""
        response = client.get("/validation-workflow/dashboard/aging", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_aging_report_with_data(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test aging report returns requests with days in status."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["critical"].value_id,
                "target_completion_date": target_date,
            }
        )

        response = client.get("/validation-workflow/dashboard/aging", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == "Critical"

    def test_workload_report(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test validator workload report."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Assign validator
        client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )

        response = client.get("/validation-workflow/dashboard/workload", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # Find our validator
        validator_workload = next((w for w in data if w["validator_id"] == validator_user.user_id), None)
        assert validator_workload is not None
        assert validator_workload["active_assignments"] >= 1


class TestAuditLogging:
    """Test that validation workflow operations create audit logs."""

    def test_create_request_creates_audit_log(self, client, admin_headers, sample_model, workflow_taxonomies, db_session):
        """Test that creating a request creates an audit log entry."""
        from app.models import AuditLog

        target_date = (date.today() + timedelta(days=30)).isoformat()
        client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )

        logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest",
            AuditLog.action == "CREATE"
        ).all()

        assert len(logs) > 0

    def test_status_change_creates_audit_log(self, client, admin_headers, sample_model, workflow_taxonomies, db_session):
        """Test that status changes create audit log entries."""
        from app.models import AuditLog

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        initial_count = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest"
        ).count()

        client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["planning"].value_id,
                "reason": "Moving to planning"
            }
        )

        final_count = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest"
        ).count()

        assert final_count > initial_count


class TestValidationGroupingMemory:
    """Test validation grouping memory functionality (Phase 1)."""

    def test_grouping_memory_created_for_multi_model_regular_validation(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test that grouping memory is created for multi-model regular validations."""
        from app.models.validation_grouping import ValidationGroupingMemory
        
        # Create a second model
        second_model = Model(
            model_name="Test Model 2",
            description="Second test model",
            owner_id=1,
            development_type="In-House",
            status="Active"
        )
        db_session.add(second_model)
        db_session.commit()
        db_session.refresh(second_model)

        # Create multi-model validation with regular validation type (ANNUAL)
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, second_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review cycle"
            }
        )
        assert response.status_code == 201
        request_id = response.json()["request_id"]

        # Check that grouping memory was created for both models
        memory1 = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        memory2 = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == second_model.model_id
        ).first()

        assert memory1 is not None
        assert memory2 is not None
        assert memory1.last_validation_request_id == request_id
        assert memory2.last_validation_request_id == request_id
        assert memory1.is_regular_validation is True
        assert memory2.is_regular_validation is True

        # Check that each model has the other in its grouped_model_ids
        import json
        grouped_ids_1 = json.loads(memory1.grouped_model_ids)
        grouped_ids_2 = json.loads(memory2.grouped_model_ids)
        
        assert second_model.model_id in grouped_ids_1
        assert sample_model.model_id in grouped_ids_2

    def test_grouping_memory_not_created_for_single_model(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test that grouping memory is NOT created for single-model validations."""
        from app.models.validation_grouping import ValidationGroupingMemory
        
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review"
            }
        )
        assert response.status_code == 201

        # Check that NO grouping memory was created
        memory = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        
        assert memory is None

    def test_grouping_memory_not_created_for_targeted_validation(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test that grouping memory is NOT created for targeted validations."""
        from app.models.validation_grouping import ValidationGroupingMemory
        from app.models.taxonomy import Taxonomy, TaxonomyValue
        
        # Create TARGETED validation type
        type_tax = db_session.query(Taxonomy).filter(Taxonomy.name == "Validation Type").first()
        targeted_val = TaxonomyValue(
            taxonomy_id=type_tax.taxonomy_id,
            code="TARGETED",
            label="Targeted Review",
            sort_order=10
        )
        db_session.add(targeted_val)
        db_session.commit()
        db_session.refresh(targeted_val)

        # Create a second model
        second_model = Model(
            model_name="Test Model 2",
            description="Second test model",
            owner_id=1,
            development_type="In-House",
            status="Active"
        )
        db_session.add(second_model)
        db_session.commit()
        db_session.refresh(second_model)

        # Create multi-model validation with TARGETED type
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, second_model.model_id],
                "validation_type_id": targeted_val.value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Change-driven validation"
            }
        )
        assert response.status_code == 201

        # Check that NO grouping memory was created
        memory1 = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        memory2 = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == second_model.model_id
        ).first()
        
        assert memory1 is None
        assert memory2 is None

    def test_grouping_memory_updates_on_new_validation(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test that grouping memory updates when a new validation is created."""
        from app.models.validation_grouping import ValidationGroupingMemory
        
        # Create three models
        model2 = Model(model_name="Model 2", owner_id=1, development_type="In-House", status="Active")
        model3 = Model(model_name="Model 3", owner_id=1, development_type="In-House", status="Active")
        db_session.add_all([model2, model3])
        db_session.commit()
        db_session.refresh(model2)
        db_session.refresh(model3)

        # First validation: Model 1 + Model 2
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response1 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, model2.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review"
            }
        )
        assert response1.status_code == 201
        request_id_1 = response1.json()["request_id"]

        # Check initial memory
        memory1_initial = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        assert memory1_initial.last_validation_request_id == request_id_1

        # Second validation: Model 1 + Model 3
        response2 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, model3.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review"
            }
        )
        assert response2.status_code == 201
        request_id_2 = response2.json()["request_id"]

        # Check updated memory - should now point to second validation
        db_session.expire(memory1_initial)  # Force reload
        memory1_updated = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        
        assert memory1_updated.last_validation_request_id == request_id_2
        grouped_ids = json.loads(memory1_updated.grouped_model_ids)
        assert model3.model_id in grouped_ids
        assert model2.model_id not in grouped_ids  # Should be replaced

    def test_validation_suggestions_endpoint_success(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test GET /models/{id}/validation-suggestions endpoint."""
        # Create second model
        model2 = Model(model_name="Model 2", owner_id=1, development_type="In-House", status="Active")
        db_session.add(model2)
        db_session.commit()
        db_session.refresh(model2)

        # Create multi-model validation
        target_date = (date.today() + timedelta(days=30)).isoformat()
        client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, model2.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review"
            }
        )

        # Get suggestions for model 1
        response = client.get(
            f"/models/{sample_model.model_id}/validation-suggestions",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "suggested_model_ids" in data
        assert "suggested_models" in data
        assert model2.model_id in data["suggested_model_ids"]
        assert len(data["suggested_models"]) == 1
        assert data["suggested_models"][0]["model_id"] == model2.model_id

    def test_validation_suggestions_endpoint_no_memory(
        self, client, admin_headers, sample_model
    ):
        """Test suggestions endpoint returns empty when no grouping memory exists."""
        response = client.get(
            f"/models/{sample_model.model_id}/validation-suggestions",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["suggested_model_ids"] == []
        assert data["suggested_models"] == []
        assert data["last_validation_request_id"] is None

    def test_validation_suggestions_endpoint_model_not_found(
        self, client, admin_headers
    ):
        """Test suggestions endpoint returns 404 for non-existent model."""
        response = client.get(
            "/models/99999/validation-suggestions",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_validation_suggestions_endpoint_requires_auth(
        self, client, sample_model
    ):
        """Test suggestions endpoint requires authentication."""
        response = client.get(f"/models/{sample_model.model_id}/validation-suggestions")
        assert response.status_code == 403

    def test_three_model_grouping(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test grouping memory with three models."""
        from app.models.validation_grouping import ValidationGroupingMemory
        
        # Create two more models
        model2 = Model(model_name="Model 2", owner_id=1, development_type="In-House", status="Active")
        model3 = Model(model_name="Model 3", owner_id=1, development_type="In-House", status="Active")
        db_session.add_all([model2, model3])
        db_session.commit()
        db_session.refresh(model2)
        db_session.refresh(model3)

        # Create validation with all three models
        target_date = (date.today() + timedelta(days=30)).isoformat()
        client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, model2.model_id, model3.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review"
            }
        )

        # Check memory for each model
        memory1 = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        
        grouped_ids = json.loads(memory1.grouped_model_ids)
        assert len(grouped_ids) == 2
        assert model2.model_id in grouped_ids
        assert model3.model_id in grouped_ids
        assert sample_model.model_id not in grouped_ids  # Should not include itself


class TestValidationLifecycleEnhancements:
    """Test Phase 3: Admin decline and unlink approval functionality."""

    def test_admin_decline_validation_request(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test admin can decline a validation request."""
        # Create validation request
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Annual review"
            }
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        # Decline the validation request
        decline_response = client.patch(
            f"/validation-workflow/requests/{request_id}/decline",
            headers=admin_headers,
            json={
                "decline_reason": "Minor documentation update, validation not required"
            }
        )

        assert decline_response.status_code == 200
        data = decline_response.json()
        assert data["current_status"]["code"] == "CANCELLED"
        assert "decline_reason" not in data  # Not in response schema, but stored in DB

        # Verify in database
        from app.models.validation import ValidationRequest
        request = db_session.query(ValidationRequest).filter(
            ValidationRequest.request_id == request_id
        ).first()
        assert request.decline_reason == "Minor documentation update, validation not required"
        assert request.declined_by_id is not None
        assert request.declined_at is not None

    def test_non_admin_cannot_decline_validation(
        self, client, admin_headers, validator_headers, sample_model, workflow_taxonomies
    ):
        """Test non-admin users cannot decline validation requests."""
        # Create validation request as admin
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date
            }
        )
        request_id = create_response.json()["request_id"]

        # Try to decline as validator (should fail)
        decline_response = client.patch(
            f"/validation-workflow/requests/{request_id}/decline",
            headers=validator_headers,
            json={
                "decline_reason": "Should not work"
            }
        )

        assert decline_response.status_code == 403
        assert "Only admins can decline" in decline_response.json()["detail"]

    def test_admin_unlink_regional_approval(
        self, client, admin_headers, validator_user, sample_model, workflow_taxonomies, db_session
    ):
        """Test admin can unlink a regional approval."""
        # Create validation request
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date
            }
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        # Create an approval requirement using validator_user
        approval_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": validator_user.user_id,
                "approver_role": "Regional Approver",
                "is_required": True
            }
        )
        assert approval_response.status_code == 201
        approval_id = approval_response.json()["approval_id"]

        # Unlink the approval
        import json as json_lib
        unlink_response = client.request(
            "DELETE",
            f"/validation-workflow/approvals/{approval_id}/unlink",
            headers=admin_headers,
            content=json_lib.dumps({"unlink_reason": "Regional approver unavailable"})
        )

        assert unlink_response.status_code == 200
        data = unlink_response.json()
        assert data["approval_status"] == "Removed"
        assert data["is_required"] == False

    def test_non_admin_cannot_unlink_approval(
        self, client, validator_headers
    ):
        """Test non-admin users cannot unlink approvals."""
        import json as json_lib
        unlink_response = client.request(
            "DELETE",
            "/validation-workflow/approvals/1/unlink",
            headers=validator_headers,
            content=json_lib.dumps({"unlink_reason": "Should not work"})
        )

        assert unlink_response.status_code == 403
        assert "Only admins can unlink" in unlink_response.json()["detail"]

    def test_decline_creates_audit_log(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session
    ):
        """Test that declining a validation creates an audit log entry."""
        # Create validation request
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date
            }
        )
        request_id = create_response.json()["request_id"]

        # Decline the request
        client.patch(
            f"/validation-workflow/requests/{request_id}/decline",
            headers=admin_headers,
            json={
                "decline_reason": "Test decline reason"
            }
        )

        # Check audit log
        from app.models.audit_log import AuditLog
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest",
            AuditLog.entity_id == request_id,
            AuditLog.action == "DECLINED"
        ).first()

        assert audit_log is not None
        assert "decline_reason" in audit_log.changes
        assert audit_log.changes["decline_reason"] == "Test decline reason"

    def test_unlink_creates_audit_log(
        self, client, admin_headers, validator_user, sample_model, workflow_taxonomies, db_session
    ):
        """Test that unlinking an approval creates an audit log entry."""
        # Create validation request
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["annual"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date
            }
        )
        request_id = create_response.json()["request_id"]

        # Create approval using validator_user
        approval_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": validator_user.user_id,
                "approver_role": "Regional Approver",
                "is_required": True
            }
        )
        approval_id = approval_response.json()["approval_id"]

        # Unlink approval
        import json as json_lib
        client.request(
            "DELETE",
            f"/validation-workflow/approvals/{approval_id}/unlink",
            headers=admin_headers,
            content=json_lib.dumps({"unlink_reason": "Test unlink reason"})
        )

        # Check audit log
        from app.models.audit_log import AuditLog
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationApproval",
            AuditLog.entity_id == request_id,
            AuditLog.action == "APPROVAL_UNLINKED"
        ).first()

        assert audit_log is not None
        assert "unlink_reason" in audit_log.changes
        assert audit_log.changes["unlink_reason"] == "Test unlink reason"


class TestRegionalScopeIntelligence:
    """Test Phase 4: Regional Scope Intelligence."""

    @pytest.fixture
    def regions(self, db_session):
        """Create sample regions."""
        us_region = Region(
            code="US",
            name="United States",
            requires_regional_approval=True
        )
        eu_region = Region(
            code="EU",
            name="European Union",
            requires_regional_approval=True
        )
        apac_region = Region(
            code="APAC",
            name="Asia Pacific",
            requires_regional_approval=False
        )
        db_session.add_all([us_region, eu_region, apac_region])
        db_session.commit()
        return {"us": us_region, "eu": eu_region, "apac": apac_region}

    @pytest.fixture
    def models_with_regions(self, db_session, test_user, regions):
        """Create models with regional associations."""
        from app.models.model import Model

        # Model 1: US only
        model1 = Model(
            model_name="US Credit Risk Model",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active"
        )
        # Model 2: EU only
        model2 = Model(
            model_name="EU Fraud Detection Model",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active"
        )
        # Model 3: US and APAC
        model3 = Model(
            model_name="Global Pricing Model",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active"
        )
        # Model 4: No regions
        model4 = Model(
            model_name="Internal Tool",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active"
        )

        db_session.add_all([model1, model2, model3, model4])
        db_session.commit()

        # Add model-region links
        mr1 = ModelRegion(model_id=model1.model_id, region_id=regions["us"].region_id)
        mr2 = ModelRegion(model_id=model2.model_id, region_id=regions["eu"].region_id)
        mr3_us = ModelRegion(model_id=model3.model_id, region_id=regions["us"].region_id)
        mr3_apac = ModelRegion(model_id=model3.model_id, region_id=regions["apac"].region_id)

        db_session.add_all([mr1, mr2, mr3_us, mr3_apac])
        db_session.commit()

        return {
            "us_only": model1,
            "eu_only": model2,
            "us_apac": model3,
            "no_region": model4
        }

    def test_preview_regions_single_model_with_region(
        self, client, admin_headers, models_with_regions, regions
    ):
        """Test preview-regions endpoint with a single model that has regions."""
        model_id = models_with_regions["us_only"].model_id

        response = client.get(
            f"/validation-workflow/requests/preview-regions?model_ids={model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggested_regions" in data
        assert len(data["suggested_regions"]) == 1
        assert data["suggested_regions"][0]["code"] == "US"
        assert data["suggested_regions"][0]["requires_regional_approval"] is True

    def test_preview_regions_multiple_models_union(
        self, client, admin_headers, models_with_regions, regions
    ):
        """Test that multiple models return union of all regions."""
        # Select US-only and EU-only models
        model_ids = f"{models_with_regions['us_only'].model_id},{models_with_regions['eu_only'].model_id}"

        response = client.get(
            f"/validation-workflow/requests/preview-regions?model_ids={model_ids}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggested_regions"]) == 2

        region_codes = {r["code"] for r in data["suggested_regions"]}
        assert region_codes == {"US", "EU"}

    def test_preview_regions_overlapping_regions(
        self, client, admin_headers, models_with_regions, regions
    ):
        """Test that overlapping regions are deduplicated."""
        # Select US-only and US+APAC models (both have US)
        model_ids = f"{models_with_regions['us_only'].model_id},{models_with_regions['us_apac'].model_id}"

        response = client.get(
            f"/validation-workflow/requests/preview-regions?model_ids={model_ids}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggested_regions"]) == 2

        region_codes = {r["code"] for r in data["suggested_regions"]}
        assert region_codes == {"US", "APAC"}

    def test_preview_regions_model_without_regions(
        self, client, admin_headers, models_with_regions
    ):
        """Test model with no regional associations returns empty list."""
        model_id = models_with_regions["no_region"].model_id

        response = client.get(
            f"/validation-workflow/requests/preview-regions?model_ids={model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggested_regions"]) == 0

    def test_preview_regions_mixed_models(
        self, client, admin_headers, models_with_regions, regions
    ):
        """Test mix of models with and without regions."""
        # Select US-only and no-region models
        model_ids = f"{models_with_regions['us_only'].model_id},{models_with_regions['no_region'].model_id}"

        response = client.get(
            f"/validation-workflow/requests/preview-regions?model_ids={model_ids}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggested_regions"]) == 1
        assert data["suggested_regions"][0]["code"] == "US"

    def test_preview_regions_all_models(
        self, client, admin_headers, models_with_regions, regions
    ):
        """Test selecting all models returns union of all regions."""
        model_ids = ",".join([
            str(models_with_regions["us_only"].model_id),
            str(models_with_regions["eu_only"].model_id),
            str(models_with_regions["us_apac"].model_id),
            str(models_with_regions["no_region"].model_id)
        ])

        response = client.get(
            f"/validation-workflow/requests/preview-regions?model_ids={model_ids}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggested_regions"]) == 3

        region_codes = {r["code"] for r in data["suggested_regions"]}
        assert region_codes == {"US", "EU", "APAC"}

    def test_preview_regions_invalid_format(self, client, admin_headers):
        """Test invalid model_ids format returns 400."""
        response = client.get(
            "/validation-workflow/requests/preview-regions?model_ids=abc,def",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "Invalid model_ids format" in response.json()["detail"]

    def test_preview_regions_requires_auth(self, client):
        """Test that preview-regions endpoint requires authentication."""
        response = client.get(
            "/validation-workflow/requests/preview-regions?model_ids=1,2,3"
        )

        assert response.status_code == 403


class TestSmartApproverAssignment:
    """Test Phase 5: Smart Approver Assignment."""

    def test_global_validation_assigns_global_approver(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies
    ):
        """Test that global validations auto-assign Global Approvers."""
        # Create a Global Approver user
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash

        global_approver = User(
            email="global.approver@example.com",
            full_name="Global Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER
        )
        db_session.add(global_approver)
        db_session.commit()

        # Create a global validation (no region_id)
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Annual review"
                # region_id is NOT provided → global validation
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify Global Approver was auto-assigned
        from app.models.validation import ValidationApproval
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        assert len(approvals) == 1
        assert approvals[0].approver_id == global_approver.user_id
        assert approvals[0].approver_role == "Global Approver"
        assert approvals[0].is_required is True
        assert approvals[0].approval_status == "Pending"

    def test_regional_validation_with_approval_required_assigns_regional_approver(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies
    ):
        """Test that regional validations with requires_regional_approval=True assign Regional Approvers."""
        from app.models.user import User, UserRole, user_regions
        from app.models.region import Region
        from app.core.security import get_password_hash

        # Create a region with requires_regional_approval=True
        region = Region(
            code="US",
            name="United States",
            requires_regional_approval=True
        )
        db_session.add(region)
        db_session.flush()

        # Create a Regional Approver for this region
        regional_approver = User(
            email="us.approver@example.com",
            full_name="US Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER
        )
        db_session.add(regional_approver)
        db_session.flush()

        # Associate approver with region
        db_session.execute(
            user_regions.insert().values(
                user_id=regional_approver.user_id,
                region_id=region.region_id
            )
        )
        db_session.commit()

        # Create a regional validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Regional compliance check",
                "region_ids": [region.region_id]
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify Regional Approver was auto-assigned
        from app.models.validation import ValidationApproval
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        assert len(approvals) == 1
        assert approvals[0].approver_id == regional_approver.user_id
        assert approvals[0].approver_role == f"Regional Approver ({region.code})"
        assert approvals[0].is_required is True
        assert approvals[0].approval_status == "Pending"

    def test_regional_validation_without_approval_required_assigns_global_approver(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies
    ):
        """Test that regional validations with requires_regional_approval=False assign Global Approvers."""
        from app.models.user import User, UserRole
        from app.models.region import Region
        from app.core.security import get_password_hash

        # Create a region with requires_regional_approval=False
        region = Region(
            code="APAC",
            name="Asia Pacific",
            requires_regional_approval=False
        )
        db_session.add(region)
        db_session.flush()

        # Create a Global Approver
        global_approver = User(
            email="global.approver2@example.com",
            full_name="Global Approver 2",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER
        )
        db_session.add(global_approver)
        db_session.commit()

        # Create a regional validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Regional check",
                "region_ids": [region.region_id]
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify Global Approver was auto-assigned (not Regional)
        from app.models.validation import ValidationApproval
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        assert len(approvals) == 1
        assert approvals[0].approver_id == global_approver.user_id
        assert approvals[0].approver_role == "Global Approver"
        assert approvals[0].is_required is True
        assert approvals[0].approval_status == "Pending"

    def test_multiple_global_approvers_all_assigned(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies
    ):
        """Test that all Global Approvers are assigned to global validations."""
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash

        # Create multiple Global Approvers
        approver1 = User(
            email="global1@example.com",
            full_name="Global Approver 1",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER
        )
        approver2 = User(
            email="global2@example.com",
            full_name="Global Approver 2",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER
        )
        approver3 = User(
            email="global3@example.com",
            full_name="Global Approver 3",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER
        )
        db_session.add_all([approver1, approver2, approver3])
        db_session.commit()

        # Create a global validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Test multiple approvers"
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify all 3 Global Approvers were assigned
        from app.models.validation import ValidationApproval
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        assert len(approvals) == 3
        approver_ids = {a.approver_id for a in approvals}
        assert approver_ids == {approver1.user_id, approver2.user_id, approver3.user_id}

        for approval in approvals:
            assert approval.approver_role == "Global Approver"
            assert approval.is_required is True
            assert approval.approval_status == "Pending"

    def test_no_approvers_available_creates_no_approvals(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies
    ):
        """Test that when no approvers exist, no approvals are created (graceful handling)."""
        # Ensure no Global Approvers exist (cleanup any from previous tests)
        from app.models.user import User, UserRole
        db_session.query(User).filter(
            User.role.in_([UserRole.GLOBAL_APPROVER, UserRole.REGIONAL_APPROVER])
        ).delete(synchronize_session=False)
        db_session.commit()

        # Create a global validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Test no approvers"
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify no approvals were created
        from app.models.validation import ValidationApproval
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        assert len(approvals) == 0

    def test_audit_log_created_for_approver_assignment(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies
    ):
        """Test that auto-assigning approvers creates an audit log entry."""
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.models.audit_log import AuditLog

        # Create a Global Approver
        global_approver = User(
            email="audittest@example.com",
            full_name="Audit Test Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER
        )
        db_session.add(global_approver)
        db_session.commit()

        # Create a global validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Audit test"
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify audit log entry was created
        audit_entry = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest",
            AuditLog.entity_id == validation_request["request_id"],
            AuditLog.action == "AUTO_ASSIGN_APPROVERS"
        ).first()

        assert audit_entry is not None
        assert audit_entry.changes["approvers_assigned"] == 1
        assert audit_entry.changes["assignment_type"] == "Automatic"
        assert len(audit_entry.changes["approvers"]) == 1
        assert audit_entry.changes["approvers"][0]["approver_id"] == global_approver.user_id
        assert audit_entry.changes["approvers"][0]["role"] == "Global Approver"
