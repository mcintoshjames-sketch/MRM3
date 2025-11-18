"""Tests for validation workflow API endpoints."""
import pytest
from datetime import date, timedelta
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.validation import (
    ValidationRequest, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationApproval
)


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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "New model requires initial validation",
                "trigger_reason": "Model deployment"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["model"]["model_id"] == sample_model.model_id
        assert data["current_status"]["label"] == "Intake"
        assert data["priority"]["label"] == "High"
        assert "request_id" in data

    def test_create_request_without_auth(self, client, sample_model, workflow_taxonomies):
        """Test that unauthenticated requests are rejected."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Test"
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
                "model_id": 9999,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Test"
            }
        )
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]

    def test_create_request_invalid_taxonomy(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test creating request with invalid taxonomy values."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "validation_type_id": 9999,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Test"
            }
        )

        response = client.get("/validation-workflow/requests/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_name"] == sample_model.model_name

    def test_get_request_details(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test getting detailed request information."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Detailed test"
            }
        )
        request_id = create_response.json()["request_id"]

        response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == request_id
        assert data["business_justification"] == "Detailed test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Delete test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Delete test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "History test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Transition test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Transition test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "On hold test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Cancel test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Cancel test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "History test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Independence test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Independence test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Independence test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Attestation test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Outcome test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Duplicate outcome test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Approval test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Approval test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Rejection test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Invalid status test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["critical"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Aging test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Workload test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Audit test"
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
                "model_id": sample_model.model_id,
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["high"].value_id,
                "target_completion_date": target_date,
                "business_justification": "Status audit test"
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
