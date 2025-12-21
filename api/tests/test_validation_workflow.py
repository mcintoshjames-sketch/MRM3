"""Tests for validation workflow API endpoints."""
import pytest
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import text
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.validation import (
    ValidationRequest, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationApproval
)
from app.models.model import Model
from app.models.validation_grouping import ValidationGroupingMemory
from app.models.region import Region
from app.models.model_region import ModelRegion
from app.models.risk_assessment import (
    QualitativeRiskFactor,
    QualitativeFactorGuidance,
    ModelRiskAssessment,
    QualitativeFactorAssessment
)
from app.core.time import utc_now


@pytest.fixture
def workflow_taxonomies(db_session):
    """Create all workflow-related taxonomy values."""
    # Validation Priority
    priority_tax = Taxonomy(name="Validation Priority", is_system=True)
    db_session.add(priority_tax)
    db_session.flush()

    urgent = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="URGENT", label="Urgent", sort_order=1)
    medium = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="MEDIUM", label="Medium", sort_order=2)
    standard = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="STANDARD", label="Standard", sort_order=3)

    # Validation Request Status
    status_tax = Taxonomy(name="Validation Request Status", is_system=True)
    db_session.add(status_tax)
    db_session.flush()

    intake = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="INTAKE", label="Intake", sort_order=1)
    planning = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PLANNING", label="Planning", sort_order=2)
    in_progress = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="IN_PROGRESS", label="In Progress", sort_order=3)
    review = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REVIEW", label="Review", sort_order=4)
    pending_approval = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PENDING_APPROVAL", label="Pending Approval", sort_order=5)
    revision = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REVISION", label="Revision", sort_order=5.5)
    approved = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="APPROVED", label="Approved", sort_order=6)
    on_hold = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="ON_HOLD", label="On Hold", sort_order=7)
    cancelled = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="CANCELLED", label="Cancelled", sort_order=8)

    # Validation Type
    type_tax = Taxonomy(name="Validation Type", is_system=True)
    db_session.add(type_tax)
    db_session.flush()

    initial_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="INITIAL", label="Initial Validation", sort_order=1)
    comprehensive_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="COMPREHENSIVE", label="Comprehensive Review", sort_order=2)
    targeted_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="TARGETED", label="Targeted Review", sort_order=3)
    interim_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="INTERIM", label="Interim Review", sort_order=4)

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
    not_fit = TaxonomyValue(taxonomy_id=rating_tax.taxonomy_id, code="NOT_FIT", label="Not Fit for Purpose", sort_order=2)

    db_session.add_all([
        urgent, medium, standard,
        intake, planning, in_progress, review, pending_approval, revision, approved, on_hold, cancelled,
        initial_val, comprehensive_val, targeted_val, interim_val,
        conceptual, data_quality, implementation, performance, documentation,
        not_started, comp_in_progress, completed,
        fit_for_purpose, not_fit
    ])
    db_session.commit()

    return {
        "priority": {"urgent": urgent, "medium": medium, "standard": standard},
        "status": {
            "intake": intake, "planning": planning, "in_progress": in_progress,
            "review": review, "pending_approval": pending_approval, "revision": revision, "approved": approved,
            "on_hold": on_hold, "cancelled": cancelled
        },
        "type": {"initial": initial_val, "comprehensive": comprehensive_val, "targeted": targeted_val, "interim": interim_val},
        "component_type": {
            "conceptual": conceptual, "data_quality": data_quality,
            "implementation": implementation, "performance": performance, "documentation": documentation
        },
        "component_status": {
            "not_started": not_started, "in_progress": comp_in_progress, "completed": completed
        },
        "rating": {
            "fit_for_purpose": fit_for_purpose, "not_fit": not_fit
        }
    }


@pytest.fixture
def qualitative_factors(db_session):
    """Create the 4 standard qualitative risk factors with guidance."""
    factors_data = [
        {
            "code": "REPUTATION_LEGAL",
            "name": "Reputation, Regulatory Compliance and/or Financial Reporting Risk",
            "weight": Decimal("0.3000"),
            "sort_order": 1
        },
        {
            "code": "COMPLEXITY",
            "name": "Complexity of the Model",
            "weight": Decimal("0.3000"),
            "sort_order": 2
        },
        {
            "code": "USAGE_DEPENDENCY",
            "name": "Model Usage and Model Dependency",
            "weight": Decimal("0.2000"),
            "sort_order": 3
        },
        {
            "code": "STABILITY",
            "name": "Stability of the Model",
            "weight": Decimal("0.2000"),
            "sort_order": 4
        }
    ]

    factors = []
    for data in factors_data:
        factor = QualitativeRiskFactor(**data)
        db_session.add(factor)
        db_session.flush()

        # Add guidance for each rating level
        for rating, points in [("HIGH", 3), ("MEDIUM", 2), ("LOW", 1)]:
            guidance = QualitativeFactorGuidance(
                factor_id=factor.factor_id,
                rating=rating,
                points=points,
                description=f"{rating} guidance for {data['code']}",
                sort_order=4 - points  # HIGH first
            )
            db_session.add(guidance)

        factors.append(factor)

    db_session.commit()
    return factors


def create_complete_risk_assessment(db_session, model_id, factors):
    """
    Helper function to create a complete global risk assessment for a model.
    This is needed for validation workflow tests that require a model to have
    a risk assessment before transitioning to REVIEW status.
    """
    # Create the global assessment (region_id = None)
    assessment = ModelRiskAssessment(
        model_id=model_id,
        region_id=None,  # Global assessment
        quantitative_rating="MEDIUM",
        assessed_at=utc_now(),
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db_session.add(assessment)
    db_session.flush()

    # Add factor assessments for all factors
    for factor in factors:
        factor_assessment = QualitativeFactorAssessment(
            assessment_id=assessment.assessment_id,
            factor_id=factor.factor_id,
            rating="MEDIUM",
            comment="Test assessment for workflow",
            weight_at_assessment=factor.weight,  # Required field
            score=Decimal("2.00") * factor.weight  # MEDIUM = 2 points
        )
        db_session.add(factor_assessment)

    db_session.commit()
    return assessment


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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Model deployment"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["models"][0]["model_id"] == sample_model.model_id  # Fixed to use models (plural)
        assert data["current_status"]["label"] == "Intake"
        assert data["priority"]["label"] == "Standard"
        assert "request_id" in data

    def test_create_request_without_auth(self, client, sample_model, workflow_taxonomies):
        """Test that unauthenticated requests are rejected."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

    def test_valid_transition_intake_to_planning(self, client, admin_headers, sample_model, workflow_taxonomies, validator_user):
        """Test valid transition from Intake to Planning."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Assign primary validator to satisfy workflow rule
        assign_response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_response.status_code == 201

        current = client.get(
            f"/validation-workflow/requests/{request_id}", headers=admin_headers
        ).json()["current_status"]["label"]
        assert current == "Planning"

    def test_invalid_transition_intake_to_approved(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test invalid direct transition from Intake to Approved."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

    def test_review_requires_plan_when_region_enforces(
        self, client, admin_headers, validator_user, sample_model, workflow_taxonomies, db_session, qualitative_factors
    ):
        """Ensure regions with plan enforcement block status change without a plan."""
        from app.models.region import Region

        # Create risk assessment for the model (required before transitioning to REVIEW)
        create_complete_risk_assessment(db_session, sample_model.model_id, qualitative_factors)

        region = Region(code="NA", name="North America",
                        requires_regional_approval=False, enforce_validation_plan=True)
        db_session.add(region)
        db_session.commit()
        db_session.refresh(region)

        # Link model to enforcing region
        sample_model.wholly_owned_region_id = region.region_id
        db_session.commit()

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
                "region_ids": [region.region_id]
            }
        )
        request_id = create_response.json()["request_id"]

        # Assign primary validator
        assign_response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_response.status_code == 201

        # Move to In Progress (should already be in Planning after assignment)
        resp = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["in_progress"].value_id,
                "reason": "Moving to in_progress"
            }
        )
        assert resp.status_code == 200

        # Attempt Review without plan should fail
        review_resp = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["review"].value_id,
                "reason": "Attempt review without plan"
            }
        )
        print(f"DEBUG: review_resp.status_code = {review_resp.status_code}")
        print(f"DEBUG: review_resp.json() = {review_resp.json()}")
        assert review_resp.status_code == 400, f"Expected 400 but got {review_resp.status_code}: {review_resp.json()}"
        assert "Validation plan is required" in review_resp.json()["detail"]

        # Create plan then retry
        plan_resp = client.post(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={}
        )
        assert plan_resp.status_code == 201

        review_resp = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["review"].value_id,
                "reason": "Move to review with plan"
            }
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["current_status"]["code"] == "REVIEW"

    def test_review_allows_no_plan_when_region_not_enforcing(
        self, client, admin_headers, validator_user, sample_model, workflow_taxonomies, db_session, qualitative_factors
    ):
        """Regions without enforcement should not block review when plan is absent."""
        from app.models.region import Region

        # Create risk assessment for the model (required before transitioning to REVIEW)
        create_complete_risk_assessment(db_session, sample_model.model_id, qualitative_factors)

        region = Region(code="LA", name="Latin America",
                        requires_regional_approval=False, enforce_validation_plan=False)
        db_session.add(region)
        db_session.commit()
        db_session.refresh(region)

        sample_model.wholly_owned_region_id = region.region_id
        db_session.commit()

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
                "region_ids": [region.region_id]
            }
        )
        request_id = create_response.json()["request_id"]

        assign_response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_response.status_code == 201

        # Move to In Progress (should already be in Planning after assignment)
        resp = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["in_progress"].value_id,
                "reason": "Moving to in_progress"
            }
        )
        assert resp.status_code == 200

        review_resp = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["review"].value_id,
                "reason": "Review without plan for non-enforcing region"
            }
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["current_status"]["code"] == "REVIEW"

    def test_transition_to_cancelled(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test transitioning to Cancelled status."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

    def test_status_change_creates_history(self, client, admin_headers, sample_model, workflow_taxonomies, validator_user):
        """Test that status changes are recorded in history."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        assign_response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_response.status_code == 201

        client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["in_progress"].value_id,
                "change_reason": "Moving to in_progress"
            }
        )

        response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        data = response.json()

        # Should have history entries for Intake, Planning (auto), and In Progress
        assert len(data["status_history"]) >= 2
        planning_entry = next((h for h in data["status_history"] if h["new_status"]["label"] == "Planning"), None)
        in_progress_entry = next((h for h in data["status_history"] if h["new_status"]["label"] == "In Progress"), None)

        assert planning_entry is not None, "Planning history entry not found"
        assert in_progress_entry is not None, "In Progress history entry not found"


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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

    def test_auto_transition_intake_to_planning_on_assignment(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test that validation request automatically transitions from INTAKE to PLANNING when validator is assigned."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create request in INTAKE status
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
                "current_status_id": workflow_taxonomies["status"]["intake"].value_id
            }
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        # Verify it's in INTAKE status
        get_response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        assert get_response.json()["current_status"]["code"] == "INTAKE"

        # Assign validator
        assign_response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True,
                "estimated_hours": 40.0
            }
        )
        assert assign_response.status_code == 201

        # Verify status auto-transitioned to PLANNING
        get_response_after = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        response_data = get_response_after.json()
        assert response_data["current_status"]["code"] == "PLANNING", \
            f"Expected PLANNING status after validator assignment, got {response_data['current_status']['code']}"

        # Verify status history shows the transition
        status_history = response_data["status_history"]
        assert len(status_history) >= 2, "Should have at least 2 status history entries"

        # Find the planning transition
        planning_entry = next((h for h in status_history if h["new_status"]["code"] == "PLANNING"), None)
        assert planning_entry is not None, "Should have status history entry for PLANNING"
        assert "auto" in planning_entry["change_reason"].lower() or "assigned" in planning_entry["change_reason"].lower(), \
            f"Change reason should indicate auto-transition: {planning_entry['change_reason']}"


class TestOutcomeCreation:
    """Test outcome creation validation."""

    def test_outcome_includes_required_fields(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies, db_session, qualitative_factors):
        """Test that outcome includes all required information."""
        # Create risk assessment for the model (required before transitioning to REVIEW)
        create_complete_risk_assessment(db_session, sample_model.model_id, qualitative_factors)

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Assign validator (required before moving to Planning and beyond)
        assign_resp = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_resp.status_code == 201

        # Move to Planning status
        status_update = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={"new_status_id": workflow_taxonomies["status"]["in_progress"].value_id, "reason": "Moving to in_progress"}
        )
        print("status update response", status_update.status_code, status_update.text)
        detail = status_update.json()
        assert status_update.status_code == 200, detail

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
                "overall_rating_id": workflow_taxonomies["rating"]["fit_for_purpose"].value_id,
                "executive_summary": "Model performs well with no material concerns",
                "effective_date": effective_date
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["overall_rating"]["label"] == "Fit for Purpose"
        assert data["executive_summary"] == "Model performs well with no material concerns"

    def test_cannot_create_duplicate_outcome(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies, db_session, qualitative_factors):
        """Test that only one outcome can exist per request."""
        # Create risk assessment for the model (required before transitioning to REVIEW)
        create_complete_risk_assessment(db_session, sample_model.model_id, qualitative_factors)

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        assign_resp = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_resp.status_code == 201

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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

    def test_submit_approval(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies, db_session, validator_user, qualitative_factors):
        """Test submitting an approval decision."""
        # Create risk assessment for the model (required before transitioning to REVIEW)
        create_complete_risk_assessment(db_session, sample_model.model_id, qualitative_factors)

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Assign validator (transitions to PLANNING)
        client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )

        # Transition: PLANNING → IN_PROGRESS → REVIEW
        for status_key in ["in_progress", "review"]:
            client.patch(
                f"/validation-workflow/requests/{request_id}/status",
                headers=admin_headers,
                json={
                    "new_status_id": workflow_taxonomies["status"][status_key].value_id,
                    "change_reason": f"Moving to {status_key}"
                }
            )

        # Create outcome (required before PENDING_APPROVAL)
        client.post(
            f"/validation-workflow/requests/{request_id}/outcome",
            headers=admin_headers,
            json={
                "overall_rating_id": workflow_taxonomies["rating"]["fit_for_purpose"].value_id,
                "executive_summary": "Validation complete",
                "effective_date": date.today().isoformat()
            }
        )

        # Transition to PENDING_APPROVAL (required before submitting approvals)
        client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["pending_approval"].value_id,
                "change_reason": "Ready for approval"
            }
        )

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

    def test_rejected_approval_status_no_longer_allowed(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies):
        """Test that 'Rejected' approval status is no longer valid.

        As of the workflow update, 'Rejected' is not a valid approval status.
        Users should use 'Sent Back' for revisions or cancel the workflow entirely.
        """
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

        # Attempt to submit "Rejected" status - should fail with 422
        response = client.patch(
            f"/validation-workflow/approvals/{approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Rejected",
                "comments": "Attempting rejection"
            }
        )
        assert response.status_code == 422  # Validation error - Rejected is not allowed
        # Verify error mentions the invalid status
        error_detail = response.json()["detail"]
        assert any("approval_status" in str(e.get("loc", "")) for e in error_detail)

    def test_invalid_approval_status(self, client, admin_headers, sample_model, admin_user, workflow_taxonomies):
        """Test that invalid approval status is rejected."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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

    def test_auto_transition_to_approved_when_all_approvals_complete(
        self, client, admin_headers, sample_model, admin_user, workflow_taxonomies, db_session, validator_user, qualitative_factors
    ):
        """Test that validation request auto-transitions to APPROVED when all required approvals are complete."""
        from app.models.validation import ValidationRequest

        # Create risk assessment for the model (required before transitioning to REVIEW)
        create_complete_risk_assessment(db_session, sample_model.model_id, qualitative_factors)

        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create validation request (starts at INTAKE)
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        # Assign a primary validator (required before transitioning to PLANNING)
        assign_response = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "independence_attestation": True
            }
        )
        assert assign_response.status_code == 201

        # Transition: PLANNING → IN_PROGRESS → REVIEW
        for status_key, reason in [
            ("in_progress", "Starting validation work"),
            ("review", "Entering review phase"),
        ]:
            status_value = workflow_taxonomies["status"][status_key]
            status_response = client.patch(
                f"/validation-workflow/requests/{request_id}/status",
                headers=admin_headers,
                json={
                    "new_status_id": status_value.value_id,
                    "change_reason": reason
                }
            )
            assert status_response.status_code == 200, f"Failed to transition to {status_key}: {status_response.json()}"

        # Create outcome (required before PENDING_APPROVAL)
        outcome_response = client.post(
            f"/validation-workflow/requests/{request_id}/outcome",
            headers=admin_headers,
            json={
                "overall_rating_id": workflow_taxonomies["rating"]["fit_for_purpose"].value_id,
                "executive_summary": "Model validation complete with satisfactory results",
                "effective_date": date.today().isoformat()
            }
        )
        assert outcome_response.status_code == 201, f"Failed to create outcome: {outcome_response.json()}"

        # Transition to PENDING_APPROVAL
        pending_approval_status = workflow_taxonomies["status"]["pending_approval"]
        status_response = client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": pending_approval_status.value_id,
                "change_reason": "Ready for approval"
            }
        )
        assert status_response.status_code == 200, f"Failed to transition to pending_approval: {status_response.json()}"

        # Verify we're at PENDING_APPROVAL
        get_response = client.get(f"/validation-workflow/requests/{request_id}", headers=admin_headers)
        assert get_response.json()["current_status"]["code"] == "PENDING_APPROVAL"

        # Add two required approvals
        approval1_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": admin_user.user_id,
                "approver_role": "Model Risk Committee",
                "is_required": True
            }
        )
        assert approval1_response.status_code == 201
        approval1_id = approval1_response.json()["approval_id"]

        approval2_response = client.post(
            f"/validation-workflow/requests/{request_id}/approvals",
            headers=admin_headers,
            json={
                "approver_id": admin_user.user_id,
                "approver_role": "Senior Management",
                "is_required": True
            }
        )
        assert approval2_response.status_code == 201
        approval2_id = approval2_response.json()["approval_id"]

        # Submit first approval - should NOT auto-transition (still missing one)
        response1 = client.patch(
            f"/validation-workflow/approvals/{approval1_id}",
            headers=admin_headers,
            json={
                "approval_status": "Approved",
                "comments": "First approval complete"
            }
        )
        assert response1.status_code == 200
        assert response1.json()["approval_status"] == "Approved"

        # Check request is still PENDING_APPROVAL
        get_response = client.get(
            f"/validation-workflow/requests/{request_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["current_status"]["code"] == "PENDING_APPROVAL"

        # Submit second approval - should auto-transition to APPROVED
        response2 = client.patch(
            f"/validation-workflow/approvals/{approval2_id}",
            headers=admin_headers,
            json={
                "approval_status": "Approved",
                "comments": "Second approval complete"
            }
        )
        assert response2.status_code == 200
        assert response2.json()["approval_status"] == "Approved"

        # Verify request auto-transitioned to APPROVED
        db_session.expire_all()  # Force refresh from DB
        final_response = client.get(
            f"/validation-workflow/requests/{request_id}",
            headers=admin_headers
        )
        assert final_response.status_code == 200
        assert final_response.json()["current_status"]["code"] == "APPROVED", \
            f"Expected APPROVED, got {final_response.json()['current_status']['code']}"


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
                "priority_id": workflow_taxonomies["priority"]["urgent"].value_id,
                "target_completion_date": target_date,
            }
        )

        response = client.get("/validation-workflow/dashboard/aging", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == "Urgent"

    def test_workload_report(self, client, admin_headers, sample_model, validator_user, workflow_taxonomies):
        """Test validator workload report."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )

        logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest",
            AuditLog.action == "CREATE"
        ).all()

        assert len(logs) > 0

    def test_status_change_creates_audit_log(self, client, admin_headers, sample_model, workflow_taxonomies, db_session, validator_user):
        """Test that status changes create audit log entries."""
        from app.models import AuditLog

        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        request_id = create_response.json()["request_id"]

        # Assign validator to allow status transition
        assign_resp = client.post(
            f"/validation-workflow/requests/{request_id}/assignments",
            headers=admin_headers,
            json={
                "validator_id": validator_user.user_id,
                "is_primary": True,
                "is_reviewer": False,
                "independence_attestation": True
            }
        )
        assert assign_resp.status_code == 201

        initial_count = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest"
        ).count()

        client.patch(
            f"/validation-workflow/requests/{request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["in_progress"].value_id,
                "reason": "Moving to in_progress"
            }
        )

        final_count = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ValidationRequest"
        ).count()

        assert final_count > initial_count


class TestValidationGroupingMemory:
    """Test validation grouping memory functionality (Phase 1)."""

    def test_grouping_memory_created_for_multi_model_regular_validation(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session, usage_frequency
    ):
        """Test that grouping memory is created for multi-model regular validations."""
        from app.models.validation_grouping import ValidationGroupingMemory

        # Create a second model
        second_model = Model(
            model_name="Test Model 2",
            description="Second test model",
            owner_id=1,
            development_type="In-House",
            status="Active",
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(second_model)
        db_session.commit()
        db_session.refresh(second_model)

        # Create multi-model validation with regular validation type (COMPREHENSIVE)
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id, second_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Periodic review cycle"
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Comprehensive review"
            }
        )
        assert response.status_code == 201

        # Check that NO grouping memory was created
        memory = db_session.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == sample_model.model_id
        ).first()
        
        assert memory is None

    def test_grouping_memory_not_created_for_targeted_validation(
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session, usage_frequency
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
            status="Active",
            usage_frequency_id=usage_frequency["daily"].value_id
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
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session, usage_frequency
    ):
        """Test that grouping memory updates when a new validation is created."""
        from app.models.validation_grouping import ValidationGroupingMemory

        # Create three models
        model2 = Model(model_name="Model 2", owner_id=1, development_type="In-House", status="Active", usage_frequency_id=usage_frequency["daily"].value_id)
        model3 = Model(model_name="Model 3", owner_id=1, development_type="In-House", status="Active", usage_frequency_id=usage_frequency["daily"].value_id)
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Comprehensive review"
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Comprehensive review"
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
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session, usage_frequency
    ):
        """Test GET /models/{id}/validation-suggestions endpoint."""
        # Create second model
        model2 = Model(model_name="Model 2", owner_id=1, development_type="In-House", status="Active", usage_frequency_id=usage_frequency["daily"].value_id)
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Comprehensive review"
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
        self, client, admin_headers, sample_model, workflow_taxonomies, db_session, usage_frequency
    ):
        """Test grouping memory with three models."""
        from app.models.validation_grouping import ValidationGroupingMemory

        # Create two more models
        model2 = Model(model_name="Model 2", owner_id=1, development_type="In-House", status="Active", usage_frequency_id=usage_frequency["daily"].value_id)
        model3 = Model(model_name="Model 3", owner_id=1, development_type="In-House", status="Active", usage_frequency_id=usage_frequency["daily"].value_id)
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Comprehensive review"
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
                "trigger_reason": "Comprehensive review"
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
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
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
    def models_with_regions(self, db_session, test_user, regions, usage_frequency):
        """Create models with regional associations."""
        from app.models.model import Model

        # Model 1: US only
        model1 = Model(
            model_name="US Credit Risk Model",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active",
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        # Model 2: EU only
        model2 = Model(
            model_name="EU Fraud Detection Model",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active",
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        # Model 3: US and APAC
        model3 = Model(
            model_name="Global Pricing Model",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active",
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        # Model 4: No regions
        model4 = Model(
            model_name="Internal Tool",
            development_type="In-House",
            owner_id=test_user.user_id,
            status="Active",
            usage_frequency_id=usage_frequency["daily"].value_id
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
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
    ):
        """Test that global validations auto-assign Global Approvers."""
        # Create a Global Approver user
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash

        global_approver = User(
            email="global.approver@example.com",
            full_name="Global Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(global_approver)
        db_session.commit()

        # Create a global validation (no region_id)
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Comprehensive review"
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
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
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
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
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
            role=UserRole.GLOBAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(global_approver)
        db_session.commit()

        # Create a regional validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
    ):
        """Test that all Global Approvers are assigned to global validations."""
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash

        # Create multiple Global Approvers
        approver1 = User(
            email="global1@example.com",
            full_name="Global Approver 1",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        approver2 = User(
            email="global2@example.com",
            full_name="Global Approver 2",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        approver3 = User(
            email="global3@example.com",
            full_name="Global Approver 3",
            password_hash=get_password_hash("password123"),
            role=UserRole.GLOBAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add_all([approver1, approver2, approver3])
        db_session.commit()

        # Create a global validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
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
            role=UserRole.GLOBAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(global_approver)
        db_session.commit()

        # Create a global validation
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
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


class TestRegionalApprovalScopeHierarchy:
    """Test the regional approval scope hierarchy logic.

    Priority hierarchy:
    1. Explicit scoped regions (user override) - highest priority
    2. Any GLOBAL version present - triggers global behavior (all deployment regions)
    3. Only REGIONAL versions - use their specific regions
    4. Fallback - use all deployment regions
    """

    def test_scoped_validation_only_requires_scoped_region_approval(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
    ):
        """Test that validation scoped to APAC does NOT require UK approval even if model deployed to UK."""
        from app.models.user import User, UserRole, user_regions
        from app.models.region import Region
        from app.models.model_region import ModelRegion
        from app.core.security import get_password_hash
        from app.models.validation import ValidationApproval

        # Create regions: APAC, UK, US
        apac_region = Region(code="APAC", name="Asia Pacific", requires_regional_approval=True)
        uk_region = Region(code="UK", name="United Kingdom", requires_regional_approval=True)
        us_region = Region(code="US", name="United States", requires_regional_approval=True)
        db_session.add_all([apac_region, uk_region, us_region])
        db_session.flush()

        # Deploy sample model to all three regions
        for region in [apac_region, uk_region, us_region]:
            db_session.add(ModelRegion(model_id=sample_model.model_id, region_id=region.region_id))
        db_session.commit()

        # Create regional approvers for each region
        apac_approver = User(
            email="apac.approver@example.com",
            full_name="APAC Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        uk_approver = User(
            email="uk.approver@example.com",
            full_name="UK Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add_all([apac_approver, uk_approver])
        db_session.flush()

        # Associate approvers with regions
        db_session.execute(user_regions.insert().values(user_id=apac_approver.user_id, region_id=apac_region.region_id))
        db_session.execute(user_regions.insert().values(user_id=uk_approver.user_id, region_id=uk_region.region_id))
        db_session.commit()

        # Create validation SCOPED to APAC only
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "APAC-scoped validation test",
                "region_ids": [apac_region.region_id]  # Only APAC
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify ONLY APAC approver was assigned, NOT UK
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        approver_ids = {a.approver_id for a in approvals}
        assert apac_approver.user_id in approver_ids, "APAC approver should be assigned"
        assert uk_approver.user_id not in approver_ids, "UK approver should NOT be assigned for APAC-scoped validation"

    def test_regional_version_triggers_version_region_approval(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
    ):
        """Test that REGIONAL-scope version triggers approvals only for its affected regions."""
        from app.models.user import User, UserRole, user_regions
        from app.models.region import Region
        from app.models.model_region import ModelRegion
        from app.models.model_version import ModelVersion
        from app.models.model_version_region import ModelVersionRegion
        from app.core.security import get_password_hash
        from app.models.validation import ValidationApproval

        # Create regions: APAC, UK
        apac_region = Region(code="APAC2", name="Asia Pacific 2", requires_regional_approval=True)
        uk_region = Region(code="UK2", name="United Kingdom 2", requires_regional_approval=True)
        db_session.add_all([apac_region, uk_region])
        db_session.flush()

        # Deploy sample model to both regions
        for region in [apac_region, uk_region]:
            db_session.add(ModelRegion(model_id=sample_model.model_id, region_id=region.region_id))
        db_session.flush()

        # Create a REGIONAL-scope version affecting only APAC
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="1.1",
            change_type="MAJOR",
            change_description="APAC-only calibration update",
            created_by_id=1,
            scope="REGIONAL"
        )
        db_session.add(version)
        db_session.flush()

        # Link version to APAC region only
        db_session.add(ModelVersionRegion(version_id=version.version_id, region_id=apac_region.region_id))
        db_session.commit()

        # Create regional approvers
        apac_approver = User(
            email="apac2.approver@example.com",
            full_name="APAC2 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        uk_approver = User(
            email="uk2.approver@example.com",
            full_name="UK2 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add_all([apac_approver, uk_approver])
        db_session.flush()

        db_session.execute(user_regions.insert().values(user_id=apac_approver.user_id, region_id=apac_region.region_id))
        db_session.execute(user_regions.insert().values(user_id=uk_approver.user_id, region_id=uk_region.region_id))
        db_session.commit()

        # Create validation WITHOUT explicit scope but WITH REGIONAL-scope version linked
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "REGIONAL version test",
                "model_versions": {sample_model.model_id: version.version_id}  # Link the REGIONAL version
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify only APAC approver (from version's affected regions) was assigned
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        approver_ids = {a.approver_id for a in approvals}
        assert apac_approver.user_id in approver_ids, "APAC approver should be assigned (version affected region)"
        assert uk_approver.user_id not in approver_ids, "UK approver should NOT be assigned for REGIONAL version affecting only APAC"

    def test_global_version_requires_all_deployment_regions(
        self, client, db_session, admin_headers, sample_model, workflow_taxonomies, lob_hierarchy
    ):
        """Test that GLOBAL-scope version triggers approvals for ALL deployment regions."""
        from app.models.user import User, UserRole, user_regions
        from app.models.region import Region
        from app.models.model_region import ModelRegion
        from app.models.model_version import ModelVersion
        from app.core.security import get_password_hash
        from app.models.validation import ValidationApproval

        # Create regions: APAC, UK
        apac_region = Region(code="APAC3", name="Asia Pacific 3", requires_regional_approval=True)
        uk_region = Region(code="UK3", name="United Kingdom 3", requires_regional_approval=True)
        db_session.add_all([apac_region, uk_region])
        db_session.flush()

        # Deploy sample model to both regions
        for region in [apac_region, uk_region]:
            db_session.add(ModelRegion(model_id=sample_model.model_id, region_id=region.region_id))
        db_session.flush()

        # Create a GLOBAL-scope version
        version = ModelVersion(
            model_id=sample_model.model_id,
            version_number="2.0",
            change_type="MAJOR",
            change_description="Global model update",
            created_by_id=1,
            scope="GLOBAL"
        )
        db_session.add(version)
        db_session.commit()

        # Create regional approvers for both regions
        apac_approver = User(
            email="apac3.approver@example.com",
            full_name="APAC3 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        uk_approver = User(
            email="uk3.approver@example.com",
            full_name="UK3 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add_all([apac_approver, uk_approver])
        db_session.flush()

        db_session.execute(user_regions.insert().values(user_id=apac_approver.user_id, region_id=apac_region.region_id))
        db_session.execute(user_regions.insert().values(user_id=uk_approver.user_id, region_id=uk_region.region_id))
        db_session.commit()

        # Create validation with GLOBAL-scope version linked
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "GLOBAL version test",
                "model_versions": {sample_model.model_id: version.version_id}  # Link the GLOBAL version
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify BOTH regional approvers were assigned (all deployment regions)
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        approver_ids = {a.approver_id for a in approvals}
        assert apac_approver.user_id in approver_ids, "APAC approver should be assigned for GLOBAL version"
        assert uk_approver.user_id in approver_ids, "UK approver should be assigned for GLOBAL version"

    def test_governance_region_always_required(
        self, client, db_session, admin_headers, workflow_taxonomies, lob_hierarchy
    ):
        """Test that wholly-owned region approval is always required even in scoped validations."""
        from app.models.user import User, UserRole, user_regions
        from app.models.region import Region
        from app.models.model_region import ModelRegion
        from app.models.model import Model
        from app.core.security import get_password_hash
        from app.models.validation import ValidationApproval

        # Create regions: US (governance), APAC (deployment only)
        us_region = Region(code="US4", name="United States 4", requires_regional_approval=True)
        apac_region = Region(code="APAC4", name="Asia Pacific 4", requires_regional_approval=True)
        db_session.add_all([us_region, apac_region])
        db_session.flush()

        # Create a model with US as governance region (wholly_owned_region_id)
        model = Model(
            model_name="Governance Test Model",
            description="Model with governance region",
            development_type="In-House",
            owner_id=1,
            status="Active",
            usage_frequency_id=1,  # Required field
            wholly_owned_region_id=us_region.region_id  # US is governance region
        )
        db_session.add(model)
        db_session.flush()

        # Also deploy to APAC
        db_session.add(ModelRegion(model_id=model.model_id, region_id=apac_region.region_id))
        db_session.commit()

        # Create regional approvers
        us_approver = User(
            email="us4.approver@example.com",
            full_name="US4 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        apac_approver = User(
            email="apac4.approver@example.com",
            full_name="APAC4 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add_all([us_approver, apac_approver])
        db_session.flush()

        db_session.execute(user_regions.insert().values(user_id=us_approver.user_id, region_id=us_region.region_id))
        db_session.execute(user_regions.insert().values(user_id=apac_approver.user_id, region_id=apac_region.region_id))
        db_session.commit()

        # Create validation SCOPED to APAC only
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "APAC-scoped but governance required",
                "region_ids": [apac_region.region_id]  # Scoped to APAC only
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify BOTH APAC (scoped) AND US (governance) approvers are assigned
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        approver_ids = {a.approver_id for a in approvals}
        assert apac_approver.user_id in approver_ids, "APAC approver should be assigned (scoped region)"
        assert us_approver.user_id in approver_ids, "US approver should be assigned (governance region always required)"

    def test_mixed_version_scopes_global_wins(
        self, client, db_session, admin_headers, workflow_taxonomies, lob_hierarchy
    ):
        """Test that if validation has both REGIONAL and GLOBAL versions, GLOBAL triggers all regions."""
        from app.models.user import User, UserRole, user_regions
        from app.models.region import Region
        from app.models.model_region import ModelRegion
        from app.models.model_version import ModelVersion
        from app.models.model_version_region import ModelVersionRegion
        from app.models.model import Model
        from app.core.security import get_password_hash
        from app.models.validation import ValidationApproval

        # Create regions: EU, UK, APAC
        eu_region = Region(code="EU5", name="European Union 5", requires_regional_approval=True)
        uk_region = Region(code="UK5", name="United Kingdom 5", requires_regional_approval=True)
        apac_region = Region(code="APAC5", name="Asia Pacific 5", requires_regional_approval=True)
        db_session.add_all([eu_region, uk_region, apac_region])
        db_session.flush()

        # Create two models
        model1 = Model(
            model_name="Model with REGIONAL version",
            description="Test model 1",
            development_type="In-House",
            owner_id=1,
            status="Active",
            usage_frequency_id=1  # Required field
        )
        model2 = Model(
            model_name="Model with GLOBAL version",
            description="Test model 2",
            development_type="In-House",
            owner_id=1,
            status="Active",
            usage_frequency_id=1  # Required field
        )
        db_session.add_all([model1, model2])
        db_session.flush()

        # Deploy model1 to APAC only, model2 to EU and UK
        db_session.add(ModelRegion(model_id=model1.model_id, region_id=apac_region.region_id))
        db_session.add(ModelRegion(model_id=model2.model_id, region_id=eu_region.region_id))
        db_session.add(ModelRegion(model_id=model2.model_id, region_id=uk_region.region_id))
        db_session.flush()

        # Create REGIONAL version for model1 affecting only APAC
        regional_version = ModelVersion(
            model_id=model1.model_id,
            version_number="1.0",
            change_type="MINOR",
            change_description="APAC calibration",
            created_by_id=1,
            scope="REGIONAL"
        )
        db_session.add(regional_version)
        db_session.flush()
        db_session.add(ModelVersionRegion(version_id=regional_version.version_id, region_id=apac_region.region_id))

        # Create GLOBAL version for model2
        global_version = ModelVersion(
            model_id=model2.model_id,
            version_number="2.0",
            change_type="MAJOR",
            change_description="Global update",
            created_by_id=1,
            scope="GLOBAL"
        )
        db_session.add(global_version)
        db_session.commit()

        # Create regional approvers for all regions
        eu_approver = User(
            email="eu5.approver@example.com",
            full_name="EU5 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        uk_approver = User(
            email="uk5.approver@example.com",
            full_name="UK5 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        apac_approver = User(
            email="apac5.approver@example.com",
            full_name="APAC5 Regional Approver",
            password_hash=get_password_hash("password123"),
            role=UserRole.REGIONAL_APPROVER,
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add_all([eu_approver, uk_approver, apac_approver])
        db_session.flush()

        db_session.execute(user_regions.insert().values(user_id=eu_approver.user_id, region_id=eu_region.region_id))
        db_session.execute(user_regions.insert().values(user_id=uk_approver.user_id, region_id=uk_region.region_id))
        db_session.execute(user_regions.insert().values(user_id=apac_approver.user_id, region_id=apac_region.region_id))
        db_session.commit()

        # Create validation covering BOTH models with their respective versions
        response = client.post(
            "/validation-workflow/requests/",
            json={
                "model_ids": [model1.model_id, model2.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": "2025-12-31",
                "trigger_reason": "Mixed REGIONAL+GLOBAL version test",
                "model_versions": {
                    model1.model_id: regional_version.version_id,  # REGIONAL
                    model2.model_id: global_version.version_id      # GLOBAL
                }
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        validation_request = response.json()

        # Verify ALL regional approvers are assigned (GLOBAL wins, triggers all deployment regions)
        approvals = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request["request_id"]
        ).all()

        approver_ids = {a.approver_id for a in approvals}
        # GLOBAL version means ALL deployment regions should have approvers
        assert eu_approver.user_id in approver_ids, "EU approver should be assigned (GLOBAL version triggers all regions)"
        assert uk_approver.user_id in approver_ids, "UK approver should be assigned (GLOBAL version triggers all regions)"
        assert apac_approver.user_id in approver_ids, "APAC approver should be assigned (from REGIONAL version + GLOBAL fallback)"


class TestPriorValidationAutoPopulation:
    """Test auto-population of prior_validation_request_id and prior_full_validation_request_id."""

    def test_auto_populate_prior_validation_id(self, client, admin_headers, db_session, sample_model, workflow_taxonomies):
        """Test that prior_validation_request_id is auto-populated with most recent APPROVED validation."""
        # First create and approve a validation request
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response1 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response1.status_code == 201
        first_request = response1.json()

        # Manually set status to APPROVED (simulate approval)
        validation_req = db_session.query(ValidationRequest).filter(
            ValidationRequest.request_id == first_request['request_id']
        ).first()
        validation_req.current_status_id = workflow_taxonomies['status']['approved'].value_id
        validation_req.completion_date = datetime.now()
        db_session.commit()

        # Now create a second validation request for the same model
        response2 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response2.status_code == 201
        second_request = response2.json()

        # Verify prior_validation_request_id is auto-populated
        assert second_request["prior_validation_request_id"] == first_request["request_id"]

    def test_auto_populate_prior_full_validation_id(self, client, admin_headers, db_session, sample_model, workflow_taxonomies):
        """Test that prior_full_validation_request_id is auto-populated with most recent APPROVED INITIAL/COMPREHENSIVE."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create an INITIAL validation and approve it
        response1 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response1.status_code == 201
        initial_request = response1.json()

        # Approve the INITIAL validation
        validation_req = db_session.query(ValidationRequest).filter(
            ValidationRequest.request_id == initial_request['request_id']
        ).first()
        validation_req.current_status_id = workflow_taxonomies['status']['approved'].value_id
        validation_req.completion_date = datetime.now()
        db_session.commit()

        # Create a COMPREHENSIVE validation - this should have prior_full pointing to INITIAL
        response2 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response2.status_code == 201
        comprehensive_request = response2.json()

        # prior_full should point to the INITIAL validation
        assert comprehensive_request["prior_full_validation_request_id"] == initial_request["request_id"]

    def test_prior_validation_fields_null_when_no_prior(self, client, admin_headers, sample_model, workflow_taxonomies):
        """Test that prior validation fields are null when no prior APPROVED validations exist."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create first validation - no prior exists
        response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Both prior fields should be null
        assert data["prior_validation_request_id"] is None
        assert data["prior_full_validation_request_id"] is None

    def test_manual_prior_validation_id_preserved(self, client, admin_headers, db_session, sample_model, workflow_taxonomies):
        """Test that manually provided prior_validation_request_id is preserved."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create first validation
        response1 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response1.status_code == 201
        first_request = response1.json()

        # Approve first validation
        validation_req1 = db_session.query(ValidationRequest).filter(
            ValidationRequest.request_id == first_request['request_id']
        ).first()
        validation_req1.current_status_id = workflow_taxonomies['status']['approved'].value_id
        validation_req1.completion_date = datetime.now() - timedelta(days=1)
        db_session.commit()

        # Create second validation
        response2 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["medium"].value_id,
                "target_completion_date": target_date,
            }
        )
        assert response2.status_code == 201
        second_request = response2.json()

        # Approve second validation
        validation_req2 = db_session.query(ValidationRequest).filter(
            ValidationRequest.request_id == second_request['request_id']
        ).first()
        validation_req2.current_status_id = workflow_taxonomies['status']['approved'].value_id
        validation_req2.completion_date = datetime.now()
        db_session.commit()

        # Create third validation with manual prior_validation_request_id pointing to first
        response3 = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [sample_model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": target_date,
                "prior_validation_request_id": first_request["request_id"],  # Manual override
            }
        )
        assert response3.status_code == 201
        third_request = response3.json()

        # Manual prior should be preserved (first_request), not auto-populated with second_request
        assert third_request["prior_validation_request_id"] == first_request["request_id"]


# ==================== SEND-BACK WORKFLOW TESTS ====================


class TestSendBackWorkflow:
    """Tests for the Send Back approval workflow feature."""

    def test_send_back_requires_comments(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that sending back requires mandatory comments."""
        # Create validation request in PENDING_APPROVAL status with a Global approval
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.flush()

        # Create Global approval
        global_approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="Global Approver",
            approval_type="Global",
            is_required=True,
            approval_status="Pending",
            created_at=datetime.now()
        )
        db_session.add(global_approval)
        db_session.commit()

        # Try to send back without comments
        response = client.patch(
            f"/validation-workflow/approvals/{global_approval.approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Sent Back",
                "comments": ""
            }
        )
        assert response.status_code == 400
        assert "comments are required" in response.json()["detail"].lower()

        # Try with whitespace-only comments
        response2 = client.patch(
            f"/validation-workflow/approvals/{global_approval.approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Sent Back",
                "comments": "   "
            }
        )
        assert response2.status_code == 400
        assert "comments are required" in response2.json()["detail"].lower()

    def test_send_back_only_global_regional(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that only Global and Regional approvers can send back."""
        # Create validation request
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.flush()

        # Create Conditional approval
        conditional_approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="Model Owner",
            approval_type="Conditional",
            is_required=True,
            approval_status="Pending",
            created_at=datetime.now()
        )
        db_session.add(conditional_approval)
        db_session.commit()

        # Try to send back with Conditional approver (should fail)
        response = client.patch(
            f"/validation-workflow/approvals/{conditional_approval.approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Sent Back",
                "comments": "Please revise documentation"
            }
        )
        assert response.status_code == 400
        assert "global and regional" in response.json()["detail"].lower()

    def test_send_back_transitions_to_revision(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that sending back transitions status to REVISION."""
        # Create validation request in PENDING_APPROVAL
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.flush()

        # Create Global approval
        global_approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="Global Approver",
            approval_type="Global",
            is_required=True,
            approval_status="Pending",
            created_at=datetime.now()
        )
        db_session.add(global_approval)
        db_session.commit()

        # Send back with comments
        response = client.patch(
            f"/validation-workflow/approvals/{global_approval.approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Sent Back",
                "comments": "Please address the data quality concerns."
            }
        )
        assert response.status_code == 200

        # Verify approval status
        db_session.refresh(global_approval)
        assert global_approval.approval_status == "Sent Back"

        # Verify validation request status is now REVISION
        db_session.refresh(validation_req)
        assert validation_req.current_status_id == workflow_taxonomies["status"]["revision"].value_id

        # Verify status history entry was created with snapshot
        history = db_session.query(ValidationStatusHistory).filter(
            ValidationStatusHistory.request_id == validation_req.request_id,
            ValidationStatusHistory.new_status_id == workflow_taxonomies["status"]["revision"].value_id
        ).first()
        assert history is not None
        assert "Sent back" in history.change_reason
        assert history.additional_context is not None
        snapshot = json.loads(history.additional_context)
        assert "sent_back_by_approval_id" in snapshot
        assert snapshot["sent_back_by_approval_id"] == global_approval.approval_id

    def test_resubmit_resets_sender_approval(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that resubmitting from REVISION resets the sender's approval."""
        # Create validation request in REVISION status
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["revision"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.flush()

        # Create outcome (required for PENDING_APPROVAL transition)
        outcome = ValidationOutcome(
            request_id=validation_req.request_id,
            overall_rating_id=workflow_taxonomies["rating"]["fit_for_purpose"].value_id,
            executive_summary="Test validation summary",
            effective_date=date.today(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(outcome)
        db_session.flush()

        # Create validator assignment (required for PENDING_APPROVAL transition)
        assignment = ValidationAssignment(
            request_id=validation_req.request_id,
            validator_id=admin_user.user_id,
            is_primary=True,
            assignment_date=date.today(),
            created_at=datetime.now()
        )
        db_session.add(assignment)
        db_session.flush()

        # Create approvals - one "Sent Back" (the sender), one "Approved"
        sender_approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="Global Approver",
            approval_type="Global",
            is_required=True,
            approval_status="Sent Back",
            approved_at=datetime.now(),
            created_at=datetime.now()
        )
        other_approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="Regional Approver",
            approval_type="Regional",
            is_required=True,
            approval_status="Approved",
            approved_at=datetime.now(),
            created_at=datetime.now()
        )
        db_session.add_all([sender_approval, other_approval])
        db_session.flush()

        # Create snapshot history entry (simulating the send-back)
        snapshot = {
            "snapshot_at": datetime.now().isoformat(),
            "overall_rating": None,
            "recommendation_ids": [],
            "limitation_ids": [],
            "sent_back_by_approval_id": sender_approval.approval_id,
            "sent_back_by_role": "Global"
        }
        history_entry = ValidationStatusHistory(
            request_id=validation_req.request_id,
            old_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            new_status_id=workflow_taxonomies["status"]["revision"].value_id,
            changed_by_id=admin_user.user_id,
            change_reason="Sent back for revisions",
            additional_context=json.dumps(snapshot),
            changed_at=datetime.now()
        )
        db_session.add(history_entry)
        db_session.commit()

        # Resubmit for approval (REVISION -> PENDING_APPROVAL)
        response = client.patch(
            f"/validation-workflow/requests/{validation_req.request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["pending_approval"].value_id,
                "change_reason": "Addressed feedback, resubmitting for approval"
            }
        )
        assert response.status_code == 200

        # Verify sender's approval was reset
        db_session.refresh(sender_approval)
        assert sender_approval.approval_status == "Pending"
        assert sender_approval.approved_at is None

        # Verify other approval stays Approved (no material changes)
        db_session.refresh(other_approval)
        assert other_approval.approval_status == "Approved"

    def test_regional_send_back_works(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that Regional approvers can also send back."""
        # Create validation request
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.flush()

        # Create Regional approval
        regional_approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="US Regional Approver",
            approval_type="Regional",
            is_required=True,
            approval_status="Pending",
            created_at=datetime.now()
        )
        db_session.add(regional_approval)
        db_session.commit()

        # Send back with Regional approver
        response = client.patch(
            f"/validation-workflow/approvals/{regional_approval.approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Sent Back",
                "comments": "Regional compliance requirements not fully addressed."
            }
        )
        assert response.status_code == 200

        # Verify status changed to REVISION
        db_session.refresh(validation_req)
        assert validation_req.current_status_id == workflow_taxonomies["status"]["revision"].value_id

    def test_effective_challenge_pdf_endpoint(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that the effective challenge PDF export endpoint works."""
        # Create validation request
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.commit()

        # Request PDF report
        response = client.get(
            f"/validation-workflow/requests/{validation_req.request_id}/effective-challenge-report",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert f"effective_challenge_VR{validation_req.request_id}.pdf" in response.headers.get("content-disposition", "")

    def test_manual_revision_status_blocked(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that manual status changes to REVISION are blocked - must use send-back flow."""
        # Create validation request in PENDING_APPROVAL status
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["pending_approval"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.commit()

        # Try to manually set status to REVISION (should be blocked)
        response = client.patch(
            f"/validation-workflow/requests/{validation_req.request_id}/status",
            headers=admin_headers,
            json={
                "new_status_id": workflow_taxonomies["status"]["revision"].value_id,
                "change_reason": "Attempting manual revision"
            }
        )
        assert response.status_code == 400
        assert "Cannot manually set status to Revision" in response.json()["detail"]
        assert "Send Back" in response.json()["detail"]

        # Verify status did not change
        db_session.refresh(validation_req)
        assert validation_req.current_status_id == workflow_taxonomies["status"]["pending_approval"].value_id

    def test_approval_blocked_before_pending_approval_status(
        self, client, admin_headers, db_session, workflow_taxonomies, sample_model, admin_user
    ):
        """Test that approvals cannot be submitted before the request reaches PENDING_APPROVAL status."""
        # Create validation request in IN_PROGRESS status (not yet at approval stage)
        validation_req = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
            priority_id=workflow_taxonomies["priority"]["medium"].value_id,
            current_status_id=workflow_taxonomies["status"]["in_progress"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        validation_req.models = [sample_model]
        db_session.add(validation_req)
        db_session.flush()

        # Create an approval (as if added prematurely)
        approval = ValidationApproval(
            request_id=validation_req.request_id,
            approver_id=admin_user.user_id,
            approver_role="US Regional Approver",
            approval_type="Regional",
            is_required=True,
            approval_status="Pending",
            created_at=datetime.now()
        )
        db_session.add(approval)
        db_session.commit()

        # Try to submit approval while request is still IN_PROGRESS (should be blocked)
        response = client.patch(
            f"/validation-workflow/approvals/{approval.approval_id}",
            headers=admin_headers,
            json={
                "approval_status": "Approved",
                "comments": "Attempting premature approval"
            }
        )
        assert response.status_code == 400
        assert "Cannot submit approval" in response.json()["detail"]
        assert "Pending Approval" in response.json()["detail"]

        # Verify approval status did not change
        db_session.refresh(approval)
        assert approval.approval_status == "Pending"
        assert approval.approved_at is None


# ==================== SCOPE-ONLY VALIDATION PLAN TESTS ====================

class TestScopeOnlyValidationPlans:
    """Tests for scope-only validation plans (TARGETED, INTERIM types)."""

    def test_create_plan_targeted_scope_only_no_components(
        self, client, db_session, admin_user, admin_headers, workflow_taxonomies, risk_tier_taxonomy, usage_frequency
    ):
        """Test that TARGETED validation plans are created without components."""
        # Create a model
        model = Model(
            model_name="Test Model for Targeted",
            description="Test",
            status="Active",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=risk_tier_taxonomy["TIER_2"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Create a validation request with TARGETED type
        request_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["targeted"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": (date.today() + timedelta(days=30)).isoformat()
            }
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        # Create validation plan
        plan_response = client.post(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={}  # Empty body for scope-only plans
        )
        assert plan_response.status_code == 201
        plan_data = plan_response.json()

        # Verify scope-only plan has no components
        assert plan_data["is_scope_only"] is True
        assert plan_data["validation_type_code"] == "TARGETED"
        assert len(plan_data["components"]) == 0
        assert plan_data["material_deviation_from_standard"] is False

    def test_create_plan_interim_scope_only_no_components(
        self, client, db_session, admin_user, admin_headers, workflow_taxonomies, risk_tier_taxonomy, usage_frequency
    ):
        """Test that INTERIM validation plans are created without components."""
        # Create a model
        model = Model(
            model_name="Test Model for Interim",
            description="Test",
            status="Active",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=risk_tier_taxonomy["TIER_2"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Create a validation request with INTERIM type
        request_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["interim"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": (date.today() + timedelta(days=30)).isoformat()
            }
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        # Create validation plan
        plan_response = client.post(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={}
        )
        assert plan_response.status_code == 201
        plan_data = plan_response.json()

        # Verify scope-only plan has no components
        assert plan_data["is_scope_only"] is True
        assert plan_data["validation_type_code"] == "INTERIM"
        assert len(plan_data["components"]) == 0
        assert plan_data["material_deviation_from_standard"] is False

    def test_create_plan_initial_full_plan_with_components(
        self, client, db_session, admin_user, admin_headers, workflow_taxonomies, risk_tier_taxonomy, usage_frequency
    ):
        """Test that INITIAL validation plans are created with all components."""
        # Create a model
        model = Model(
            model_name="Test Model for Initial",
            description="Test",
            status="Active",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=risk_tier_taxonomy["TIER_2"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Create a validation request with INITIAL type
        request_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["initial"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": (date.today() + timedelta(days=30)).isoformat()
            }
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        # Create validation plan
        plan_response = client.post(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={}
        )
        assert plan_response.status_code == 201
        plan_data = plan_response.json()

        # Verify full plan is NOT scope-only (components would be created if definitions existed)
        assert plan_data["is_scope_only"] is False
        assert plan_data["validation_type_code"] == "INITIAL"
        # Note: components list may be empty in test env without ValidationComponentDefinition records
        # The key verification is that is_scope_only=False for full plan types

    def test_get_plan_scope_only_returns_flag(
        self, client, db_session, admin_user, admin_headers, workflow_taxonomies, risk_tier_taxonomy, usage_frequency
    ):
        """Test that GET validation plan returns is_scope_only flag correctly."""
        # Create a model
        model = Model(
            model_name="Test Model for GET Scope Only",
            description="Test",
            status="Active",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=risk_tier_taxonomy["TIER_2"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Create a validation request with TARGETED type
        request_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["targeted"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": (date.today() + timedelta(days=30)).isoformat()
            }
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        # Create validation plan
        plan_response = client.post(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={}
        )
        assert plan_response.status_code == 201

        # GET the plan and verify is_scope_only flag
        get_response = client.get(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers
        )
        assert get_response.status_code == 200
        plan_data = get_response.json()

        assert plan_data["is_scope_only"] is True
        assert plan_data["validation_type_code"] == "TARGETED"

    def test_update_scope_only_plan_only_scope_summary(
        self, client, db_session, admin_user, admin_headers, workflow_taxonomies, risk_tier_taxonomy, usage_frequency
    ):
        """Test that updating a scope-only plan only updates the scope summary."""
        # Create a model
        model = Model(
            model_name="Test Model for Update Scope Only",
            description="Test",
            status="Active",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=risk_tier_taxonomy["TIER_2"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        # Create a validation request with TARGETED type
        request_response = client.post(
            "/validation-workflow/requests/",
            headers=admin_headers,
            json={
                "model_ids": [model.model_id],
                "validation_type_id": workflow_taxonomies["type"]["targeted"].value_id,
                "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
                "target_completion_date": (date.today() + timedelta(days=30)).isoformat()
            }
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        # Create validation plan
        plan_response = client.post(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={}
        )
        assert plan_response.status_code == 201

        # Update the plan with scope summary and try to set material deviation
        update_response = client.patch(
            f"/validation-workflow/requests/{request_id}/plan",
            headers=admin_headers,
            json={
                "overall_scope_summary": "This is a targeted review scope summary.",
                "material_deviation_from_standard": True,  # Should be ignored
                "overall_deviation_rationale": "Should be ignored"
            }
        )
        assert update_response.status_code == 200
        updated_plan = update_response.json()

        # Verify scope summary was updated but material deviation was forced to false
        assert updated_plan["overall_scope_summary"] == "This is a targeted review scope summary."
        assert updated_plan["material_deviation_from_standard"] is False
        assert updated_plan["is_scope_only"] is True
