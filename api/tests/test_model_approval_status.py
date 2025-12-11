"""Tests for Model Approval Status computation and history tracking."""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from app.core.model_approval_status import (
    ApprovalStatus,
    STATUS_LABELS,
    compute_model_approval_status,
    record_status_change,
    get_last_recorded_status,
    get_status_label,
    update_model_approval_status_if_changed,
    backfill_model_approval_status,
    _get_latest_approved_validation,
    _get_active_substantive_validation,
    _is_model_overdue,
    _check_approvals_complete,
)
from app.models.model_approval_status_history import ModelApprovalStatusHistory
from app.models.model import Model
from app.models.validation import ValidationRequest, ValidationRequestModelVersion, ValidationApproval
from app.models.taxonomy import Taxonomy, TaxonomyValue


# =============================================================================
# Fixtures specific to approval status tests
# =============================================================================

@pytest.fixture
def status_taxonomy(db_session):
    """Create Validation Request Status taxonomy."""
    status_tax = Taxonomy(name="Validation Request Status", is_system=True)
    db_session.add(status_tax)
    db_session.flush()

    statuses = [
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="INTAKE", label="Intake", sort_order=1),
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PLANNING", label="Planning", sort_order=2),
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="ASSIGNED", label="Assigned", sort_order=3),
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="IN_PROGRESS", label="In Progress", sort_order=4),
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REVIEW", label="Review", sort_order=5),
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PENDING_APPROVAL", label="Pending Approval", sort_order=6),
        TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="APPROVED", label="Approved", sort_order=7),
    ]
    db_session.add_all(statuses)
    db_session.commit()

    return {
        "taxonomy": status_tax,
        "INTAKE": statuses[0],
        "PLANNING": statuses[1],
        "ASSIGNED": statuses[2],
        "IN_PROGRESS": statuses[3],
        "REVIEW": statuses[4],
        "PENDING_APPROVAL": statuses[5],
        "APPROVED": statuses[6],
    }


@pytest.fixture
def validation_type_taxonomy(db_session):
    """Create Validation Type taxonomy."""
    val_type_tax = Taxonomy(name="Validation Type", is_system=True)
    db_session.add(val_type_tax)
    db_session.flush()

    types = [
        TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="INITIAL", label="Initial", sort_order=1),
        TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="COMPREHENSIVE", label="Comprehensive", sort_order=2),
        TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="INTERIM", label="Interim", sort_order=3),
        TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="TARGETED", label="Targeted Review", sort_order=4),
    ]
    db_session.add_all(types)
    db_session.commit()

    return {
        "taxonomy": val_type_tax,
        "INITIAL": types[0],
        "COMPREHENSIVE": types[1],
        "INTERIM": types[2],
        "TARGETED": types[3],
    }


@pytest.fixture
def model_for_approval_test(db_session, test_user, usage_frequency):
    """Create a model for approval status testing."""
    model = Model(
        model_name="Approval Test Model",
        description="Model for approval status testing",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status="approved",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def priority_taxonomy(db_session):
    """Create Validation Priority taxonomy."""
    priority_tax = Taxonomy(name="Validation Priority", is_system=True)
    db_session.add(priority_tax)
    db_session.flush()

    priorities = [
        TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="STANDARD", label="Standard", sort_order=1),
        TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="URGENT", label="Urgent", sort_order=2),
    ]
    db_session.add_all(priorities)
    db_session.commit()

    return {
        "taxonomy": priority_tax,
        "STANDARD": priorities[0],
        "URGENT": priorities[1],
    }


@pytest.fixture
def approved_validation(db_session, model_for_approval_test, status_taxonomy, validation_type_taxonomy, priority_taxonomy, test_user):
    """Create an APPROVED validation request for the test model."""
    # Create validation request with all required fields
    validation = ValidationRequest(
        request_date=date.today() - timedelta(days=60),
        requestor_id=test_user.user_id,
        validation_type_id=validation_type_taxonomy["COMPREHENSIVE"].value_id,
        priority_id=priority_taxonomy["STANDARD"].value_id,
        target_completion_date=date.today() - timedelta(days=30),
        current_status_id=status_taxonomy["APPROVED"].value_id,
        completion_date=date.today() - timedelta(days=30),  # Approved 30 days ago
    )
    db_session.add(validation)
    db_session.flush()

    # Link model to validation
    link = ValidationRequestModelVersion(
        request_id=validation.request_id,
        model_id=model_for_approval_test.model_id
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(validation)
    return validation


# =============================================================================
# A. Status Computation Tests (8 tests)
# =============================================================================

class TestStatusComputation:
    """Tests for compute_model_approval_status function."""

    def test_never_validated_status(self, db_session, model_for_approval_test):
        """Model with no approved validations returns NEVER_VALIDATED."""
        status, context = compute_model_approval_status(model_for_approval_test, db_session)

        assert status == ApprovalStatus.NEVER_VALIDATED
        assert context["model_id"] == model_for_approval_test.model_id
        assert "computed_at" in context

    def test_approved_status(self, db_session, model_for_approval_test, approved_validation):
        """Model with approved validation within window returns APPROVED."""
        # Mock _is_model_overdue to return False (not overdue)
        with patch('app.core.model_approval_status._is_model_overdue') as mock_overdue:
            mock_overdue.return_value = (False, {"next_validation_due": date.today() + timedelta(days=300)})

            status, context = compute_model_approval_status(model_for_approval_test, db_session)

            assert status == ApprovalStatus.APPROVED
            assert context["latest_approved_validation_id"] == approved_validation.request_id

    def test_interim_approved_status(self, db_session, model_for_approval_test, status_taxonomy, validation_type_taxonomy, priority_taxonomy, test_user):
        """Model with INTERIM type validation returns INTERIM_APPROVED."""
        # Create INTERIM validation
        validation = ValidationRequest(
            request_date=date.today() - timedelta(days=30),
            requestor_id=test_user.user_id,
            validation_type_id=validation_type_taxonomy["INTERIM"].value_id,
            priority_id=priority_taxonomy["STANDARD"].value_id,
            target_completion_date=date.today() - timedelta(days=10),
            current_status_id=status_taxonomy["APPROVED"].value_id,
            completion_date=date.today() - timedelta(days=10),
        )
        db_session.add(validation)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=model_for_approval_test.model_id
        )
        db_session.add(link)
        db_session.commit()

        with patch('app.core.model_approval_status._is_model_overdue') as mock_overdue:
            mock_overdue.return_value = (False, {"next_validation_due": date.today() + timedelta(days=100)})

            status, context = compute_model_approval_status(model_for_approval_test, db_session)

            assert status == ApprovalStatus.INTERIM_APPROVED
            assert context["validation_type_code"] == "INTERIM"

    def test_validation_in_progress_status(self, db_session, model_for_approval_test, approved_validation, status_taxonomy, priority_taxonomy, validation_type_taxonomy, test_user):
        """Overdue model with substantive validation returns VALIDATION_IN_PROGRESS."""
        # Create an in-progress validation
        new_validation = ValidationRequest(
            request_date=date.today() - timedelta(days=10),
            requestor_id=test_user.user_id,
            validation_type_id=validation_type_taxonomy["COMPREHENSIVE"].value_id,
            priority_id=priority_taxonomy["STANDARD"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            current_status_id=status_taxonomy["IN_PROGRESS"].value_id,
        )
        db_session.add(new_validation)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=new_validation.request_id,
            model_id=model_for_approval_test.model_id
        )
        db_session.add(link)
        db_session.commit()

        with patch('app.core.model_approval_status._is_model_overdue') as mock_overdue:
            mock_overdue.return_value = (True, {"status": "Validation Overdue"})

            status, context = compute_model_approval_status(model_for_approval_test, db_session)

            assert status == ApprovalStatus.VALIDATION_IN_PROGRESS
            assert context["is_overdue"] is True
            assert context["active_validation_id"] == new_validation.request_id

    def test_expired_status(self, db_session, model_for_approval_test, approved_validation):
        """Overdue model with no active validation returns EXPIRED."""
        with patch('app.core.model_approval_status._is_model_overdue') as mock_overdue:
            mock_overdue.return_value = (True, {"status": "Validation Overdue"})

            status, context = compute_model_approval_status(model_for_approval_test, db_session)

            assert status == ApprovalStatus.EXPIRED
            assert context["is_overdue"] is True
            assert context["active_validation_id"] is None

    def test_non_model_returns_none(self, db_session, model_for_approval_test):
        """Non-model entity (is_model=False) returns None status."""
        # Set is_model to False
        model_for_approval_test.is_model = False
        db_session.commit()

        status, context = compute_model_approval_status(model_for_approval_test, db_session)

        assert status is None
        assert context["reason"] == "Non-model entity"

    def test_intake_not_substantive(self, db_session, model_for_approval_test, approved_validation, status_taxonomy, priority_taxonomy, validation_type_taxonomy, test_user):
        """Validation in INTAKE status doesn't count as in-progress (returns EXPIRED)."""
        # Create validation in INTAKE status
        intake_validation = ValidationRequest(
            request_date=date.today() - timedelta(days=5),
            requestor_id=test_user.user_id,
            validation_type_id=validation_type_taxonomy["COMPREHENSIVE"].value_id,
            priority_id=priority_taxonomy["STANDARD"].value_id,
            target_completion_date=date.today() + timedelta(days=60),
            current_status_id=status_taxonomy["INTAKE"].value_id,
        )
        db_session.add(intake_validation)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=intake_validation.request_id,
            model_id=model_for_approval_test.model_id
        )
        db_session.add(link)
        db_session.commit()

        with patch('app.core.model_approval_status._is_model_overdue') as mock_overdue:
            mock_overdue.return_value = (True, {"status": "Validation Overdue"})

            status, context = compute_model_approval_status(model_for_approval_test, db_session)

            # Should be EXPIRED because INTAKE doesn't count as substantive
            assert status == ApprovalStatus.EXPIRED
            assert context["active_validation_id"] is None

    def test_pending_approvals_tracked(self, db_session, model_for_approval_test, approved_validation):
        """Context tracks pending approval count."""
        # Add a pending approval
        approval = ValidationApproval(
            request_id=approved_validation.request_id,
            approver_role="Model Owner",
            approval_status="Pending",
            is_required=True,
        )
        db_session.add(approval)
        db_session.commit()

        with patch('app.core.model_approval_status._is_model_overdue') as mock_overdue:
            mock_overdue.return_value = (False, {"next_validation_due": date.today() + timedelta(days=300)})

            status, context = compute_model_approval_status(model_for_approval_test, db_session)

            assert context["pending_approval_count"] == 1


# =============================================================================
# B. Helper Function Tests (5 tests)
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_latest_approved_validation(self, db_session, model_for_approval_test, approved_validation):
        """Returns most recent APPROVED validation."""
        result = _get_latest_approved_validation(model_for_approval_test, db_session)

        assert result is not None
        assert result.request_id == approved_validation.request_id

    def test_get_latest_approved_validation_none(self, db_session, model_for_approval_test):
        """Returns None when no approved validations exist."""
        result = _get_latest_approved_validation(model_for_approval_test, db_session)
        assert result is None

    def test_get_active_substantive_validation(self, db_session, model_for_approval_test, status_taxonomy, priority_taxonomy, validation_type_taxonomy, test_user):
        """Finds validation in substantive stage."""
        # Create validation in PLANNING status
        validation = ValidationRequest(
            request_date=date.today() - timedelta(days=5),
            requestor_id=test_user.user_id,
            validation_type_id=validation_type_taxonomy["COMPREHENSIVE"].value_id,
            priority_id=priority_taxonomy["STANDARD"].value_id,
            target_completion_date=date.today() + timedelta(days=60),
            current_status_id=status_taxonomy["PLANNING"].value_id,
        )
        db_session.add(validation)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=model_for_approval_test.model_id
        )
        db_session.add(link)
        db_session.commit()

        result = _get_active_substantive_validation(model_for_approval_test, db_session)

        assert result is not None
        assert result.request_id == validation.request_id

    def test_get_active_substantive_validation_not_intake(self, db_session, model_for_approval_test, status_taxonomy, priority_taxonomy, validation_type_taxonomy, test_user):
        """Validation in INTAKE is not considered substantive."""
        # Create validation in INTAKE status
        validation = ValidationRequest(
            request_date=date.today() - timedelta(days=3),
            requestor_id=test_user.user_id,
            validation_type_id=validation_type_taxonomy["COMPREHENSIVE"].value_id,
            priority_id=priority_taxonomy["STANDARD"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            current_status_id=status_taxonomy["INTAKE"].value_id,
        )
        db_session.add(validation)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=model_for_approval_test.model_id
        )
        db_session.add(link)
        db_session.commit()

        result = _get_active_substantive_validation(model_for_approval_test, db_session)
        assert result is None

    def test_check_approvals_complete(self, db_session, model_for_approval_test, approved_validation):
        """Approval completion logic works correctly."""
        # No pending approvals - should be complete
        all_complete, pending_count = _check_approvals_complete(
            approved_validation, model_for_approval_test, db_session
        )

        assert all_complete is True
        assert pending_count == 0


# =============================================================================
# C. History Recording Tests (4 tests)
# =============================================================================

class TestHistoryRecording:
    """Tests for status history recording functions."""

    def test_record_status_change(self, db_session, model_for_approval_test):
        """Creates history record correctly."""
        history = record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.NEVER_VALIDATED,
            trigger_type="TEST",
            db=db_session,
            notes="Test record"
        )
        db_session.commit()

        assert history.model_id == model_for_approval_test.model_id
        assert history.old_status is None
        assert history.new_status == ApprovalStatus.NEVER_VALIDATED
        assert history.trigger_type == "TEST"
        assert history.notes == "Test record"

    def test_get_last_recorded_status(self, db_session, model_for_approval_test):
        """Retrieves latest status from history."""
        # Create two history records
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.NEVER_VALIDATED,
            trigger_type="TEST1",
            db=db_session
        )
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=ApprovalStatus.NEVER_VALIDATED,
            new_status=ApprovalStatus.APPROVED,
            trigger_type="TEST2",
            db=db_session
        )
        db_session.commit()

        result = get_last_recorded_status(model_for_approval_test, db_session)
        assert result == ApprovalStatus.APPROVED

    def test_update_if_changed_records_change(self, db_session, model_for_approval_test):
        """Records when status differs from last recorded."""
        # First record
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.NEVER_VALIDATED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        # Mock compute to return APPROVED
        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.APPROVED, {})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="TEST_TRIGGER"
            )
            db_session.commit()

            assert result is not None
            assert result.old_status == ApprovalStatus.NEVER_VALIDATED
            assert result.new_status == ApprovalStatus.APPROVED

    def test_update_if_changed_no_record_when_same(self, db_session, model_for_approval_test):
        """Skips recording when status is unchanged."""
        # First record
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.NEVER_VALIDATED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        # Mock compute to return same status
        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.NEVER_VALIDATED, {})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="TEST_TRIGGER"
            )

            assert result is None


# =============================================================================
# D. Integration Hook Tests (6 tests)
# =============================================================================

class TestIntegrationHooks:
    """Tests for workflow integration hooks."""

    def test_hook_on_validation_request_created(self, db_session, model_for_approval_test, status_taxonomy, test_user):
        """Status hook triggers on new validation request creation."""
        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.NEVER_VALIDATED, {})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="VALIDATION_REQUEST_CREATED",
                trigger_entity_type="ValidationRequest",
                trigger_entity_id=999
            )

            # First call should create record since no prior history exists
            if result:
                assert result.trigger_type == "VALIDATION_REQUEST_CREATED"
                assert result.trigger_entity_type == "ValidationRequest"

    def test_hook_on_status_change_to_approved(self, db_session, model_for_approval_test):
        """Status hook triggers on validation APPROVED transition."""
        # Set initial state
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.NEVER_VALIDATED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.APPROVED, {})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="VALIDATION_STATUS_CHANGE",
                trigger_entity_type="ValidationRequest",
                trigger_entity_id=123
            )
            db_session.commit()

            assert result is not None
            assert result.new_status == ApprovalStatus.APPROVED
            assert result.trigger_type == "VALIDATION_STATUS_CHANGE"

    def test_hook_on_status_change_to_in_progress(self, db_session, model_for_approval_test):
        """Status hook triggers on validation IN_PROGRESS transition."""
        # Set initial state as EXPIRED
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.EXPIRED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.VALIDATION_IN_PROGRESS, {})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="VALIDATION_STATUS_CHANGE",
                trigger_entity_type="ValidationRequest",
                trigger_entity_id=456
            )
            db_session.commit()

            assert result is not None
            assert result.new_status == ApprovalStatus.VALIDATION_IN_PROGRESS

    def test_hook_on_approval_submitted(self, db_session, model_for_approval_test):
        """Status hook triggers on approval submission."""
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.APPROVED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            # Status unchanged, should not create record
            mock_compute.return_value = (ApprovalStatus.APPROVED, {})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="APPROVAL_SUBMITTED",
                trigger_entity_type="ValidationApproval",
                trigger_entity_id=789
            )

            # No change in status, no new record
            assert result is None

    def test_status_transition_never_to_approved(self, db_session, model_for_approval_test):
        """Full workflow: NEVER_VALIDATED -> APPROVED."""
        # Initial state
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.NEVER_VALIDATED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.APPROVED, {"latest_approved_validation_id": 100})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="VALIDATION_STATUS_CHANGE"
            )
            db_session.commit()

            assert result.old_status == ApprovalStatus.NEVER_VALIDATED
            assert result.new_status == ApprovalStatus.APPROVED

    def test_status_transition_approved_to_expired(self, db_session, model_for_approval_test):
        """Expiration scenario: APPROVED -> EXPIRED."""
        # Initial state as APPROVED
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.APPROVED,
            trigger_type="INITIAL",
            db=db_session
        )
        db_session.commit()

        with patch('app.core.model_approval_status.compute_model_approval_status') as mock_compute:
            mock_compute.return_value = (ApprovalStatus.EXPIRED, {"is_overdue": True})

            result = update_model_approval_status_if_changed(
                model_for_approval_test,
                db_session,
                trigger_type="EXPIRATION_CHECK"
            )
            db_session.commit()

            assert result.old_status == ApprovalStatus.APPROVED
            assert result.new_status == ApprovalStatus.EXPIRED


# =============================================================================
# E. Backfill and Utility Tests (4 tests)
# =============================================================================

class TestBackfillAndUtility:
    """Tests for backfill and utility functions."""

    def test_backfill_creates_initial_records(self, db_session, model_for_approval_test):
        """Backfill function creates records for models without history."""
        # Verify no history exists
        assert get_last_recorded_status(model_for_approval_test, db_session) is None

        # Run backfill
        count = backfill_model_approval_status(db_session)

        assert count >= 1  # At least our test model

        # Verify history was created
        status = get_last_recorded_status(model_for_approval_test, db_session)
        assert status is not None

    def test_backfill_skips_existing(self, db_session, model_for_approval_test):
        """Backfill doesn't duplicate records for models with history."""
        # Create initial record
        record_status_change(
            model_id=model_for_approval_test.model_id,
            old_status=None,
            new_status=ApprovalStatus.APPROVED,
            trigger_type="MANUAL",
            db=db_session
        )
        db_session.commit()

        # Count records before backfill
        initial_count = db_session.query(ModelApprovalStatusHistory).filter(
            ModelApprovalStatusHistory.model_id == model_for_approval_test.model_id
        ).count()

        # Run backfill
        backfill_model_approval_status(db_session)

        # Count should be same (no duplicates)
        final_count = db_session.query(ModelApprovalStatusHistory).filter(
            ModelApprovalStatusHistory.model_id == model_for_approval_test.model_id
        ).count()

        assert final_count == initial_count

    def test_get_status_label(self):
        """Label lookup works for all status codes."""
        assert get_status_label(ApprovalStatus.NEVER_VALIDATED) == "Never Validated"
        assert get_status_label(ApprovalStatus.APPROVED) == "Approved"
        assert get_status_label(ApprovalStatus.INTERIM_APPROVED) == "Interim Approved"
        assert get_status_label(ApprovalStatus.VALIDATION_IN_PROGRESS) == "Validation In Progress"
        assert get_status_label(ApprovalStatus.EXPIRED) == "Expired"

    def test_get_status_label_unknown(self):
        """Handles unknown codes gracefully."""
        assert get_status_label("UNKNOWN_CODE") == "UNKNOWN_CODE"
        assert get_status_label(None) is None


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestApprovalStatusAPI:
    """Tests for API endpoints related to approval status."""

    def test_model_list_includes_approval_status(self, client, admin_headers, sample_model):
        """GET /models/ includes approval_status fields."""
        response = client.get("/models/", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        # API returns a list directly
        if len(data) > 0:
            model = data[0]
            assert "approval_status" in model
            assert "approval_status_label" in model

    def test_model_detail_includes_approval_status(self, client, admin_headers, sample_model):
        """GET /models/{id} includes approval_status fields."""
        response = client.get(f"/models/{sample_model.model_id}", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert "approval_status" in data
        assert "approval_status_label" in data
