"""
TDD Tests for Pre-Transition Warnings

These tests define the API contract for warnings displayed before transitioning
a validation request to certain statuses (e.g., PENDING_APPROVAL, APPROVED).

Warning Types:
1. OPEN_FINDINGS - Prior validations have unresolved findings
2. PENDING_RECOMMENDATIONS - Model has open recommendations not yet addressed
3. UNADDRESSED_ATTESTATIONS - Model owner has pending attestation items

Endpoint: GET /validation-workflow/requests/{id}/pre-transition-warnings
Query Param: target_status (e.g., "PENDING_APPROVAL")
"""
import pytest
from datetime import date, datetime, timedelta
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.validation import (
    ValidationRequest, ValidationRequestModelVersion,
    ValidationFinding, ValidationPolicy
)
from app.models.recommendation import Recommendation
from app.models.attestation import AttestationRecord, AttestationCycle
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.core.time import utc_now


@pytest.fixture
def pre_transition_setup(db_session, taxonomy_values, test_user, usage_frequency):
    """Setup taxonomies, policies and base data for pre-transition warning tests."""
    # Ensure Validation Request Status taxonomy exists
    status_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status").first()
    if not status_tax:
        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        db_session.add(status_tax)
        db_session.flush()

        statuses = [
            ("INTAKE", "Intake", 100),
            ("PLANNING", "Planning", 101),
            ("IN_PROGRESS", "In Progress", 102),
            ("REVIEW", "Review", 103),
            ("PENDING_APPROVAL", "Pending Approval", 104),
            ("APPROVED", "Approved", 105),
            ("ON_HOLD", "On Hold", 106),
            ("CANCELLED", "Cancelled", 107)
        ]
        for code, label, sort_order in statuses:
            val = TaxonomyValue(
                taxonomy_id=status_tax.taxonomy_id,
                code=code, label=label, sort_order=sort_order
            )
            db_session.add(val)

    # Ensure Recommendation Status taxonomy exists
    rec_status_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Recommendation Status").first()
    if not rec_status_tax:
        rec_status_tax = Taxonomy(name="Recommendation Status", is_system=True)
        db_session.add(rec_status_tax)
        db_session.flush()

        rec_statuses = [
            ("DRAFT", "Draft"),
            ("PENDING_RESPONSE", "Pending Response"),
            ("IN_PROGRESS", "In Progress"),
            ("PENDING_CLOSURE", "Pending Closure"),
            ("CLOSED", "Closed")
        ]
        for i, (code, label) in enumerate(rec_statuses):
            val = TaxonomyValue(
                taxonomy_id=rec_status_tax.taxonomy_id,
                code=code, label=label, sort_order=i + 1
            )
            db_session.add(val)

    # Ensure Priority taxonomy exists
    priority_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Priority").first()
    if not priority_tax:
        priority_tax = Taxonomy(name="Priority", is_system=True)
        db_session.add(priority_tax)
        db_session.flush()

        priorities = [("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")]
        for i, (code, label) in enumerate(priorities):
            val = TaxonomyValue(
                taxonomy_id=priority_tax.taxonomy_id,
                code=code, label=label, sort_order=i + 1
            )
            db_session.add(val)

    # Ensure Recommendation Priority taxonomy exists
    rec_priority_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Recommendation Priority").first()
    if not rec_priority_tax:
        rec_priority_tax = Taxonomy(name="Recommendation Priority", is_system=True)
        db_session.add(rec_priority_tax)
        db_session.flush()

        rec_priorities = [("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")]
        for i, (code, label) in enumerate(rec_priorities):
            val = TaxonomyValue(
                taxonomy_id=rec_priority_tax.taxonomy_id,
                code=code, label=label, sort_order=i + 1
            )
            db_session.add(val)

    db_session.commit()

    # Get key status IDs
    in_progress_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "IN_PROGRESS"
    ).join(Taxonomy).filter(Taxonomy.name == "Validation Request Status").first()

    review_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "REVIEW"
    ).join(Taxonomy).filter(Taxonomy.name == "Validation Request Status").first()

    pending_approval_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "PENDING_APPROVAL"
    ).join(Taxonomy).filter(Taxonomy.name == "Validation Request Status").first()

    approved_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "APPROVED"
    ).join(Taxonomy).filter(Taxonomy.name == "Validation Request Status").first()

    # Get recommendation status IDs
    rec_pending_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "PENDING_RESPONSE"
    ).join(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()

    rec_closed_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "CLOSED"
    ).join(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()

    medium_priority = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "MEDIUM"
    ).join(Taxonomy).filter(Taxonomy.name == "Priority").first()

    rec_medium_priority = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "MEDIUM"
    ).join(Taxonomy).filter(Taxonomy.name == "Recommendation Priority").first()

    # Create a test model
    model = Model(
        model_name="Pre-Transition Test Model",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        risk_tier_id=taxonomy_values["tier1"].value_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    return {
        "model": model,
        "in_progress_status_id": in_progress_status.value_id if in_progress_status else None,
        "review_status_id": review_status.value_id if review_status else None,
        "pending_approval_status_id": pending_approval_status.value_id if pending_approval_status else None,
        "approved_status_id": approved_status.value_id if approved_status else None,
        "rec_pending_status_id": rec_pending_status.value_id if rec_pending_status else None,
        "rec_closed_status_id": rec_closed_status.value_id if rec_closed_status else None,
        "validation_type_id": taxonomy_values["initial"].value_id,
        "priority_id": medium_priority.value_id if medium_priority else None,
        "rec_priority_id": rec_medium_priority.value_id if rec_medium_priority else None,
        "tier1_id": taxonomy_values["tier1"].value_id
    }


class TestPreTransitionWarningsEndpoint:
    """Tests for GET /validation-workflow/requests/{id}/pre-transition-warnings"""

    def test_endpoint_returns_200_with_valid_request(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: Endpoint should return 200 with valid request_id and target_status.
        """
        setup = pre_transition_setup

        # Create a validation request in REVIEW status
        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        # Link model to request
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=setup["model"].model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "warnings" in data
        assert "can_proceed" in data
        assert "target_status" in data
        assert data["target_status"] == "PENDING_APPROVAL"

    def test_endpoint_returns_404_for_invalid_request(
        self, client, auth_headers
    ):
        """
        TDD Test: Endpoint should return 404 for non-existent request_id.
        """
        response = client.get(
            "/validation-workflow/requests/99999/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_endpoint_requires_target_status_param(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: Endpoint should return 422 when target_status is missing.
        """
        setup = pre_transition_setup

        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings",
            headers=auth_headers
        )
        assert response.status_code == 422


class TestOpenFindingsWarning:
    """Tests for OPEN_FINDINGS warning type."""

    def test_warning_generated_for_open_findings(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: OPEN_FINDINGS warning should be generated when prior validations
        have unresolved findings.

        Scenario: Model has a prior approved validation with an open finding.
        Expected: Warning with type OPEN_FINDINGS and details about the finding.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create prior approved validation request
        prior_request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["approved_status_id"],
            target_completion_date=date.today() - timedelta(days=60),
            completion_date=date.today() - timedelta(days=60),
            requestor_id=test_user.user_id
        )
        db_session.add(prior_request)
        db_session.flush()

        # Link model to prior request
        prior_link = ValidationRequestModelVersion(
            request_id=prior_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(prior_link)

        # Create an open finding for the prior validation
        finding = ValidationFinding(
            request_id=prior_request.request_id,
            finding_type="DATA_QUALITY",
            severity="HIGH",
            title="Data quality issue identified",
            description="Test data has anomalies",
            status="OPEN",
            identified_by_id=test_user.user_id
        )
        db_session.add(finding)
        db_session.flush()

        # Create current validation request in REVIEW status
        current_request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(current_request)
        db_session.flush()

        current_link = ValidationRequestModelVersion(
            request_id=current_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(current_link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{current_request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["warnings"]) >= 1

        finding_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "OPEN_FINDINGS"),
            None
        )
        assert finding_warning is not None
        assert finding_warning["severity"] == "WARNING"
        assert finding_warning["model_id"] == model.model_id
        assert "open" in finding_warning["message"].lower() or "finding" in finding_warning["message"].lower()
        assert finding_warning["details"]["finding_count"] >= 1

    def test_no_warning_when_all_findings_resolved(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: No OPEN_FINDINGS warning when all prior findings are resolved.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create prior approved validation with RESOLVED finding
        prior_request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["approved_status_id"],
            target_completion_date=date.today() - timedelta(days=60),
            completion_date=date.today() - timedelta(days=60),
            requestor_id=test_user.user_id
        )
        db_session.add(prior_request)
        db_session.flush()

        prior_link = ValidationRequestModelVersion(
            request_id=prior_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(prior_link)

        # Finding is RESOLVED
        finding = ValidationFinding(
            request_id=prior_request.request_id,
            finding_type="DATA_QUALITY",
            severity="HIGH",
            title="Previously resolved issue",
            description="This was resolved",
            status="RESOLVED",
            identified_by_id=test_user.user_id,
            resolved_at=utc_now()
        )
        db_session.add(finding)

        # Current request
        current_request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(current_request)
        db_session.flush()

        current_link = ValidationRequestModelVersion(
            request_id=current_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(current_link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{current_request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        finding_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "OPEN_FINDINGS"),
            None
        )
        assert finding_warning is None


class TestPendingRecommendationsWarning:
    """Tests for PENDING_RECOMMENDATIONS warning type."""

    def test_warning_generated_for_pending_recommendations(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: PENDING_RECOMMENDATIONS warning should be generated when model
        has recommendations in non-closed status.

        Scenario: Model has a recommendation in PENDING_RESPONSE status.
        Expected: Warning with type PENDING_RECOMMENDATIONS and count.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create a pending recommendation for the model
        recommendation = Recommendation(
            recommendation_code="REC-TEST-0001",
            model_id=model.model_id,
            title="Outstanding recommendation",
            description="This needs to be addressed",
            priority_id=setup["rec_priority_id"],
            current_status_id=setup["rec_pending_status_id"],
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30),
            assigned_to_id=test_user.user_id,
            created_by_id=test_user.user_id
        )
        db_session.add(recommendation)

        # Create validation request in REVIEW status
        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        rec_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "PENDING_RECOMMENDATIONS"),
            None
        )
        assert rec_warning is not None
        assert rec_warning["severity"] == "WARNING"
        assert rec_warning["model_id"] == model.model_id
        assert "recommendation" in rec_warning["message"].lower()
        assert rec_warning["details"]["recommendation_count"] >= 1

    def test_no_warning_when_recommendations_closed(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: No PENDING_RECOMMENDATIONS warning when all recommendations are closed.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create a CLOSED recommendation
        recommendation = Recommendation(
            recommendation_code="REC-TEST-0002",
            model_id=model.model_id,
            title="Closed recommendation",
            description="This was addressed",
            priority_id=setup["rec_priority_id"],
            current_status_id=setup["rec_closed_status_id"],
            original_target_date=date.today() - timedelta(days=30),
            current_target_date=date.today() - timedelta(days=30),
            assigned_to_id=test_user.user_id,
            created_by_id=test_user.user_id,
            closed_at=datetime.now()
        )
        db_session.add(recommendation)

        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        rec_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "PENDING_RECOMMENDATIONS"),
            None
        )
        assert rec_warning is None


class TestUnaddressedAttestationsWarning:
    """Tests for UNADDRESSED_ATTESTATIONS warning type."""

    def test_warning_generated_for_pending_attestations(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: UNADDRESSED_ATTESTATIONS warning should be generated when model
        owner has pending attestation items.

        Scenario: Model owner has an attestation record in PENDING status.
        Expected: Warning with type UNADDRESSED_ATTESTATIONS and details.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create an attestation cycle
        cycle = AttestationCycle(
            cycle_name="Q4 2025 Attestation",
            period_start_date=date.today() - timedelta(days=30),
            period_end_date=date.today() + timedelta(days=30),
            submission_due_date=date.today() + timedelta(days=30),
            status="OPEN"
        )
        db_session.add(cycle)
        db_session.flush()

        # Create pending attestation for model owner
        attestation = AttestationRecord(
            cycle_id=cycle.cycle_id,
            model_id=model.model_id,
            attesting_user_id=test_user.user_id,  # Model owner
            due_date=date.today() + timedelta(days=30),
            status="PENDING"
        )
        db_session.add(attestation)

        # Create validation request
        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        attest_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "UNADDRESSED_ATTESTATIONS"),
            None
        )
        assert attest_warning is not None
        assert attest_warning["severity"] == "WARNING"
        assert attest_warning["model_id"] == model.model_id
        assert "attestation" in attest_warning["message"].lower()
        assert attest_warning["details"]["attestation_count"] >= 1

    def test_no_warning_when_attestations_completed(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: No UNADDRESSED_ATTESTATIONS warning when all attestations completed.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create completed attestation
        cycle = AttestationCycle(
            cycle_name="Q3 2025 Attestation",
            period_start_date=date.today() - timedelta(days=90),
            period_end_date=date.today() - timedelta(days=30),
            submission_due_date=date.today() - timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(cycle)
        db_session.flush()

        attestation = AttestationRecord(
            cycle_id=cycle.cycle_id,
            model_id=model.model_id,
            attesting_user_id=test_user.user_id,
            due_date=date.today() - timedelta(days=35),
            status="ACCEPTED",
            attested_at=utc_now() - timedelta(days=35)
        )
        db_session.add(attestation)

        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        attest_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "UNADDRESSED_ATTESTATIONS"),
            None
        )
        assert attest_warning is None


class TestMultipleWarnings:
    """Tests for multiple warning types in a single response."""

    def test_multiple_warnings_returned(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: Multiple warning types should be returned when multiple conditions exist.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Setup: Open finding from prior validation
        prior_request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["approved_status_id"],
            target_completion_date=date.today() - timedelta(days=60),
            completion_date=date.today() - timedelta(days=60),
            requestor_id=test_user.user_id
        )
        db_session.add(prior_request)
        db_session.flush()

        prior_link = ValidationRequestModelVersion(
            request_id=prior_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(prior_link)

        finding = ValidationFinding(
            request_id=prior_request.request_id,
            finding_type="DATA_QUALITY",
            severity="HIGH",
            title="Open finding",
            description="Not resolved",
            status="OPEN",
            identified_by_id=test_user.user_id
        )
        db_session.add(finding)

        # Setup: Pending recommendation
        recommendation = Recommendation(
            recommendation_code="REC-TEST-0003",
            model_id=model.model_id,
            title="Pending recommendation",
            description="Needs work",
            priority_id=setup["rec_priority_id"],
            current_status_id=setup["rec_pending_status_id"],
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30),
            assigned_to_id=test_user.user_id,
            created_by_id=test_user.user_id
        )
        db_session.add(recommendation)

        # Setup: Pending attestation
        cycle = AttestationCycle(
            cycle_name="Current Attestation",
            period_start_date=date.today() - timedelta(days=10),
            period_end_date=date.today() + timedelta(days=20),
            submission_due_date=date.today() + timedelta(days=20),
            status="OPEN"
        )
        db_session.add(cycle)
        db_session.flush()

        attestation = AttestationRecord(
            cycle_id=cycle.cycle_id,
            model_id=model.model_id,
            attesting_user_id=test_user.user_id,
            due_date=date.today() + timedelta(days=20),
            status="PENDING"
        )
        db_session.add(attestation)

        # Current validation request
        current_request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(current_request)
        db_session.flush()

        current_link = ValidationRequestModelVersion(
            request_id=current_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(current_link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{current_request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should have all three warning types
        warning_types = [w["warning_type"] for w in data["warnings"]]
        assert "OPEN_FINDINGS" in warning_types
        assert "PENDING_RECOMMENDATIONS" in warning_types
        assert "UNADDRESSED_ATTESTATIONS" in warning_types

        # All are warnings, so can_proceed should be True
        assert data["can_proceed"] is True


class TestCanProceedLogic:
    """Tests for can_proceed determination."""

    def test_can_proceed_true_with_only_warnings(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: can_proceed should be True when there are only WARNING severities.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Just a pending recommendation (WARNING, not ERROR)
        recommendation = Recommendation(
            recommendation_code="REC-TEST-0004",
            model_id=model.model_id,
            title="Advisory recommendation",
            description="Consider this",
            priority_id=setup["rec_priority_id"],
            current_status_id=setup["rec_pending_status_id"],
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30),
            assigned_to_id=test_user.user_id,
            created_by_id=test_user.user_id
        )
        db_session.add(recommendation)

        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["warnings"]) >= 1
        assert data["can_proceed"] is True

    def test_can_proceed_true_with_no_warnings(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: can_proceed should be True when there are no warnings.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Clean request with no issues
        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["warnings"]) == 0
        assert data["can_proceed"] is True


class TestWarningResponseSchema:
    """Tests for the warning response schema structure."""

    def test_warning_response_contains_required_fields(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: Warning response should contain all required fields.
        """
        setup = pre_transition_setup
        model = setup["model"]

        # Create a warning condition
        recommendation = Recommendation(
            recommendation_code="REC-TEST-0005",
            model_id=model.model_id,
            title="Test recommendation",
            description="For schema test",
            priority_id=setup["rec_priority_id"],
            current_status_id=setup["rec_pending_status_id"],
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30),
            assigned_to_id=test_user.user_id,
            created_by_id=test_user.user_id
        )
        db_session.add(recommendation)

        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Top-level response fields
        assert "request_id" in data
        assert "target_status" in data
        assert "warnings" in data
        assert "can_proceed" in data

        # Each warning should have required fields
        for warning in data["warnings"]:
            assert "warning_type" in warning
            assert "severity" in warning
            assert "message" in warning
            assert "model_id" in warning
            assert "model_name" in warning
            assert "details" in warning

    def test_warning_severity_values(
        self, client, db_session, test_user, auth_headers, pre_transition_setup
    ):
        """
        TDD Test: Warning severity should be one of: ERROR, WARNING, INFO.
        """
        setup = pre_transition_setup
        model = setup["model"]

        recommendation = Recommendation(
            recommendation_code="REC-TEST-0006",
            model_id=model.model_id,
            title="Severity test",
            description="Check severity value",
            priority_id=setup["rec_priority_id"],
            current_status_id=setup["rec_pending_status_id"],
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30),
            assigned_to_id=test_user.user_id,
            created_by_id=test_user.user_id
        )
        db_session.add(recommendation)

        request = ValidationRequest(
            validation_type_id=setup["validation_type_id"],
            priority_id=setup["priority_id"],
            current_status_id=setup["review_status_id"],
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=test_user.user_id
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/validation-workflow/requests/{request.request_id}/pre-transition-warnings?target_status=PENDING_APPROVAL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        valid_severities = {"ERROR", "WARNING", "INFO"}
        for warning in data["warnings"]:
            assert warning["severity"] in valid_severities
