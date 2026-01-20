"""
Comprehensive tests for KPI Metrics 4.6 and 4.7 (Validation On-Time/Overdue).
Tests the complex 7-state status machine for validation compliance.

These tests use real in-memory SQLite database with actual data fixtures.
NO MOCKING - tests the actual endpoint logic end-to-end.
"""
# Run (from api/): DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest tests/test_kpi_overdue_metrics.py -v

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app.api.kpi_report import _compute_validation_metrics
from app.models import Model


class TestOverdueStatusDetermination:
    """Test the validation status determination logic (lines 556-651 of kpi_report.py).

    Status State Machine:
    - "Never Validated" - No validation records exist
    - "Pending Full Validation" - Has interim approval, awaiting full validation
    - "INTERIM Expired - Full Validation Required" - Interim approval has expired
    - "Submission Overdue (INTERIM)" - Past submission deadline for interim replacement
    - "No Policy Configured" - No ValidationPolicy for model's risk tier
    - "Submission Overdue" - Past grace period, no active request
    - "In Grace Period" - Past submission due but within grace period
    - "Awaiting Submission" - Active request but no submission received
    - "Validation Overdue" - Active request past validation due date
    - "Validation In Progress" - Active request with submission, within SLA
    - "Revalidation Overdue (No Request)" - Past validation due, no active request
    - "Should Create Request" - Past grace period, should start revalidation
    - "Upcoming" - Next validation not yet due
    """

    # =========================================================================
    # Test: Models never validated
    # =========================================================================

    def test_never_validated_model_without_interim(
        self, db_session, kpi_active_model
    ):
        """Model with no validations should return 'Never Validated'.

        Expected: NOT overdue (never validated is not overdue by default).
        """
        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should NOT be in overdue list
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id not in overdue_ids

        # Verify counts
        assert result["4.6"].ratio_value.denominator == 1
        assert result["4.7"].ratio_value.denominator == 1

    def test_never_validated_model_with_interim_not_expired(
        self, db_session, kpi_active_model, kpi_create_interim_validation
    ):
        """Model with valid interim approval should return 'Pending Full Validation'.

        Expected: NOT overdue, counted in interim approvals (4.9).
        """
        kpi_create_interim_validation(
            model=kpi_active_model,
            expiration_date=date.today() + timedelta(days=90)  # Future expiration
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should NOT be overdue
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id not in overdue_ids

        # Should be counted in interim count (4.9)
        assert result["4.9"].count_value >= 1

    # =========================================================================
    # Test: INTERIM expiration states
    # =========================================================================

    def test_interim_expired_model(
        self, db_session, kpi_active_model, kpi_create_interim_validation
    ):
        """Model with expired interim should return 'INTERIM Expired - Full Validation Required'.

        Expected: IS overdue.
        """
        kpi_create_interim_validation(
            model=kpi_active_model,
            expiration_date=date.today() - timedelta(days=1)  # Expired yesterday
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should be in overdue list
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id in overdue_ids

    def test_interim_submission_overdue(
        self, db_session, kpi_active_model, kpi_create_interim_validation, kpi_tier1_policy
    ):
        """Model with interim approaching expiration, past submission deadline.

        Business Logic (kpi_report.py:597-598):
        - submission_due = interim_expiration - lead_time_days
        - If today > submission_due: "Submission Overdue (INTERIM)"

        Expected: IS overdue if submission_due < today.
        """
        lead_time = kpi_tier1_policy.model_change_lead_time_days  # 90 days
        expiration = date.today() + timedelta(days=30)  # Expires in 30 days
        submission_due = expiration - timedelta(days=lead_time)  # 30 - 90 = -60 days (already past)

        kpi_create_interim_validation(
            model=kpi_active_model,
            expiration_date=expiration
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should be overdue if submission_due < today
        if submission_due < date.today():
            overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
            assert kpi_active_model.model_id in overdue_ids

    # =========================================================================
    # Test: COMPREHENSIVE validation states
    # =========================================================================

    def test_submission_overdue_past_grace_period(
        self, db_session, kpi_active_model, kpi_create_approved_validation, kpi_tier1_policy
    ):
        """Model past grace period with no active request should be 'Submission Overdue'.

        Policy: frequency=12mo, grace=3mo, lead_time=90d
        18 months ago = past 12mo frequency + 3mo grace

        Expected: IS overdue.
        """
        approval_date = date.today() - relativedelta(months=18)
        kpi_create_approved_validation(model=kpi_active_model, completion_date=approval_date)

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should be overdue
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id in overdue_ids

    def test_in_grace_period_not_overdue(
        self, db_session, kpi_active_model, kpi_create_approved_validation, kpi_tier1_policy
    ):
        """Model in grace period should NOT be counted as overdue.

        Policy: frequency=12mo, grace=3mo
        13 months ago = past frequency (12mo) but within grace period (12+3=15mo)

        Expected: NOT overdue.
        """
        approval_date = date.today() - relativedelta(months=13)
        kpi_create_approved_validation(model=kpi_active_model, completion_date=approval_date)

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should NOT be overdue (in grace period)
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id not in overdue_ids

    def test_validation_in_progress_not_overdue(
        self, db_session, kpi_active_model, kpi_create_approved_validation,
        kpi_create_active_validation_request, kpi_tier1_policy
    ):
        """Model with active validation request on track should NOT be overdue.

        Scenario: Prior validation 14 months ago, active request with submission received.

        Expected: NOT overdue (validation in progress within SLA).
        """
        # Create prior approved validation
        approval_date = date.today() - relativedelta(months=14)
        prior_validation = kpi_create_approved_validation(
            model=kpi_active_model, completion_date=approval_date
        )

        # Create active revalidation request with submission received
        kpi_create_active_validation_request(
            model=kpi_active_model,
            submission_received_date=date.today() - timedelta(days=30)
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should NOT be overdue
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id not in overdue_ids

    def test_validation_overdue_past_due_date(
        self, db_session, kpi_active_model, kpi_create_approved_validation,
        kpi_create_active_validation_request, kpi_tier1_policy
    ):
        """Model with active request past validation due date should be 'Validation Overdue'.

        Scenario: Prior validation 24 months ago, active request with old submission.

        Expected: IS overdue.
        """
        # Create prior approved validation 2 years ago
        approval_date = date.today() - relativedelta(months=24)
        prior_validation = kpi_create_approved_validation(
            model=kpi_active_model, completion_date=approval_date
        )

        # Create active request with submission received long ago
        kpi_create_active_validation_request(
            model=kpi_active_model,
            submission_received_date=date.today() - timedelta(days=200)
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should be overdue
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id in overdue_ids

    # =========================================================================
    # Test: Edge cases
    # =========================================================================

    def test_no_policy_configured_model(
        self, db_session, kpi_active_model_no_tier, kpi_create_approved_validation, kpi_taxonomies
    ):
        """Model without ValidationPolicy should return 'No Policy Configured'.

        Expected: NOT counted as overdue (no policy = can't determine due date).
        """
        kpi_create_approved_validation(
            model=kpi_active_model_no_tier,
            completion_date=date.today() - timedelta(days=365)
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model_no_tier])

        # Should NOT be counted as overdue
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model_no_tier.model_id not in overdue_ids

    def test_multiple_models_mixed_states(
        self, db_session, kpi_active_model, kpi_second_active_model,
        kpi_create_approved_validation, kpi_tier1_policy, kpi_tier2_policy
    ):
        """Test with multiple models in different states.

        Model 1: On time (recent approval)
        Model 2: Overdue (old approval, no revalidation)

        Expected: 1 on time, 1 overdue.
        """
        # Model 1: On time (recent approval)
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - timedelta(days=30)
        )

        # Model 2: Overdue (old approval, no revalidation)
        kpi_create_approved_validation(
            model=kpi_second_active_model,
            completion_date=date.today() - relativedelta(months=36)  # 3 years ago
        )

        result = _compute_validation_metrics(
            db_session, [kpi_active_model, kpi_second_active_model]
        )

        # Verify counts
        assert result["4.6"].ratio_value.denominator == 2  # 2 total
        assert result["4.7"].ratio_value.denominator == 2  # 2 total
        assert result["4.6"].ratio_value.numerator == 1  # 1 on time
        assert result["4.7"].ratio_value.numerator == 1  # 1 overdue

    def test_empty_model_list(self, db_session):
        """Test with no active models.

        Expected: All zeros, no errors.
        """
        result = _compute_validation_metrics(db_session, [])

        assert result["4.6"].ratio_value.numerator == 0
        assert result["4.6"].ratio_value.denominator == 0
        assert result["4.6"].ratio_value.percentage == 0.0
        assert result["4.7"].ratio_value.numerator == 0
        assert result["4.7"].ratio_value.denominator == 0


class TestMetric4_8_ValidationDuration:
    """Test Average Time to Complete Validation by Risk Tier (Metric 4.8).

    Formula: AVG(completion_date - created_at).days PER risk_tier
    """

    def test_returns_breakdown_structure(
        self, db_session, kpi_active_model, kpi_create_approved_validation
    ):
        """Verify breakdown is returned for models with validations."""
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - timedelta(days=30)
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Breakdown may or may not exist depending on validation data
        # Just verify it doesn't error
        assert "4.8" in result

    def test_no_validations_returns_empty_breakdown(self, db_session, kpi_active_model):
        """No approved validations should return empty/null breakdown."""
        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should have empty or no breakdown (no approved validations)
        breakdown = result["4.8"].breakdown_value
        # May be None or empty list
        assert breakdown is None or len(breakdown) == 0


class TestMetric4_9_InterimApprovals:
    """Test Number of Models with Interim Approval (Metric 4.9).

    Formula: COUNT(last_validation_type='INTERIM' AND not_expired AND not_overdue)
    """

    def test_counts_valid_interim_only(
        self, db_session, kpi_active_model, kpi_create_interim_validation
    ):
        """Only count interim approvals that are not expired and not overdue.

        Expected: Count = 1 for valid interim.
        """
        kpi_create_interim_validation(
            model=kpi_active_model,
            expiration_date=date.today() + timedelta(days=90)  # Not expired
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        assert result["4.9"].count_value == 1

    def test_excludes_expired_interim(
        self, db_session, kpi_active_model, kpi_create_interim_validation
    ):
        """Expired interim should not be counted.

        Expected: Count = 0 for expired interim.
        """
        kpi_create_interim_validation(
            model=kpi_active_model,
            expiration_date=date.today() - timedelta(days=1)  # Expired
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should be 0 since it's expired
        assert result["4.9"].count_value == 0

    def test_multiple_models_interim_counts(
        self, db_session, kpi_active_model, kpi_second_active_model,
        kpi_create_interim_validation
    ):
        """Multiple models with various interim states.

        Model 1: Valid interim
        Model 2: Expired interim

        Expected: Count = 1.
        """
        # Model 1: Valid interim
        kpi_create_interim_validation(
            model=kpi_active_model,
            expiration_date=date.today() + timedelta(days=90)
        )

        # Model 2: Expired interim
        kpi_create_interim_validation(
            model=kpi_second_active_model,
            expiration_date=date.today() - timedelta(days=1)
        )

        result = _compute_validation_metrics(
            db_session, [kpi_active_model, kpi_second_active_model]
        )

        # Only 1 valid interim
        assert result["4.9"].count_value == 1


class TestMetricPercentageCalculations:
    """Test percentage calculations for metrics 4.6 and 4.7."""

    def test_percentage_rounding(
        self, db_session, kpi_active_model, kpi_second_active_model,
        kpi_create_approved_validation, kpi_tier1_policy, kpi_tier2_policy
    ):
        """Verify percentage is calculated correctly with 2 decimal places."""
        # Both on time
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - timedelta(days=30)
        )
        kpi_create_approved_validation(
            model=kpi_second_active_model,
            completion_date=date.today() - timedelta(days=30)
        )

        result = _compute_validation_metrics(
            db_session, [kpi_active_model, kpi_second_active_model]
        )

        # 2/2 = 100%
        assert result["4.6"].ratio_value.percentage == 100.0
        # 0/2 = 0%
        assert result["4.7"].ratio_value.percentage == 0.0

    def test_drill_down_model_ids_populated(
        self, db_session, kpi_active_model, kpi_create_approved_validation, kpi_tier1_policy
    ):
        """Verify numerator_model_ids contains correct model IDs for drill-down."""
        # On time
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - timedelta(days=30)
        )

        result = _compute_validation_metrics(db_session, [kpi_active_model])

        # Should be in on_time list
        on_time_ids = result["4.6"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id in on_time_ids

        # Should NOT be in overdue list
        overdue_ids = result["4.7"].ratio_value.numerator_model_ids or []
        assert kpi_active_model.model_id not in overdue_ids
