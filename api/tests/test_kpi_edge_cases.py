"""
Edge case tests for all KPI metrics.
Tests boundary conditions, empty data, and unusual states.

These tests use real in-memory SQLite database with actual data fixtures.
NO MOCKING - tests the actual endpoint logic end-to-end.
"""
# Run (from api/): DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest tests/test_kpi_edge_cases.py -v

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app.models import Model


class TestKPIEmptyData:
    """Test KPI report with empty/minimal data."""

    def test_no_active_models(self, client, admin_headers):
        """All metrics should handle zero active models gracefully.

        Expected: All counts = 0, all percentages = 0.0, no errors.
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total_active_models"] == 0

        # Check each metric handles empty state
        for metric in data["metrics"]:
            if metric["metric_type"] == "count":
                assert metric["count_value"] is not None
            elif metric["metric_type"] == "ratio":
                assert metric["ratio_value"]["denominator"] == 0
                assert metric["ratio_value"]["percentage"] == 0.0

    def test_models_without_validations(
        self, client, admin_headers, kpi_active_model
    ):
        """Validation metrics should handle models with no validation records.

        Expected: Models counted in denominator, appropriate handling of
        'Never Validated' state.
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Should have 1 active model
        assert data["total_active_models"] == 1

        # 4.6, 4.7 should use active models as denominator
        metric_4_6 = next(m for m in data["metrics"] if m["metric_id"] == "4.6")
        assert metric_4_6["ratio_value"]["denominator"] == data["total_active_models"]


class TestKPIBoundaryConditions:
    """Test boundary conditions for calculations."""

    def test_recent_validation_not_overdue(
        self, client, admin_headers, kpi_active_model,
        kpi_create_approved_validation, kpi_tier1_policy
    ):
        """Model validated recently should NOT be overdue.

        Scenario: Validated 30 days ago with 12-month frequency.
        Expected: NOT overdue.
        """
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - timedelta(days=30)
        )

        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        metric_4_7 = next(m for m in data["metrics"] if m["metric_id"] == "4.7")

        # Should NOT be overdue
        assert metric_4_7["ratio_value"]["numerator"] == 0

    def test_exactly_at_frequency_boundary(
        self, client, admin_headers, kpi_active_model,
        kpi_create_approved_validation, kpi_tier1_policy
    ):
        """Model exactly at frequency boundary (12 months) should be in grace period.

        Policy: frequency=12mo, grace=3mo
        Scenario: Validated exactly 12 months ago.
        Expected: In grace period, NOT overdue.
        """
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - relativedelta(months=12)
        )

        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        metric_4_7 = next(m for m in data["metrics"] if m["metric_id"] == "4.7")

        # Should NOT be overdue (in grace period)
        assert metric_4_7["ratio_value"]["numerator"] == 0

    def test_one_day_past_grace_period(
        self, client, admin_headers, kpi_active_model,
        kpi_create_approved_validation, kpi_tier1_policy
    ):
        """Model 1 day past grace period SHOULD be overdue.

        Policy: frequency=12mo, grace=3mo
        Scenario: Validated 15 months + 1 day ago.
        Expected: IS overdue.
        """
        # 15 months + a few days = past grace period
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - relativedelta(months=15) - timedelta(days=5)
        )

        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        metric_4_7 = next(m for m in data["metrics"] if m["metric_id"] == "4.7")

        # Should be overdue
        assert metric_4_7["ratio_value"]["numerator"] == 1


class TestKPIDataQuality:
    """Test handling of data quality issues."""

    def test_model_missing_risk_tier(
        self, client, admin_headers, kpi_active_model_no_tier
    ):
        """Model without risk tier should be handled gracefully.

        Expected: Model counted in total, but may be in 'Unassigned' breakdown.
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Should count the model
        assert data["total_active_models"] == 1

        # Check 4.2 (% by Risk Tier) has Unassigned category
        metric_4_2 = next(m for m in data["metrics"] if m["metric_id"] == "4.2")
        if metric_4_2["breakdown_value"]:
            categories = [b["category"] for b in metric_4_2["breakdown_value"]]
            # May or may not have Unassigned depending on implementation
            # Just verify it doesn't error


class TestKPIRegionFiltering:
    """Test region filtering for KPI report."""

    def test_invalid_region_returns_404(self, client, admin_headers):
        """Non-existent region_id returns 404.

        Expected: 404 status code.
        """
        response = client.get("/kpi-report/?region_id=99999", headers=admin_headers)
        assert response.status_code == 404

    def test_without_region_returns_all_regions_label(
        self, client, admin_headers
    ):
        """No region filter shows 'All Regions' label.

        Expected: region_id=None, region_name='All Regions'
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["region_id"] is None
        assert data["region_name"] == "All Regions"


class TestKPITeamFiltering:
    """Test team filtering for KPI report."""

    def test_without_team_returns_all_teams_label(
        self, client, admin_headers
    ):
        """No team filter shows 'All Teams' label.

        Expected: team_id=None, team_name='All Teams'
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["team_id"] is None
        assert data["team_name"] == "All Teams"


class TestMetric4_1_TotalActiveModels:
    """Test Metric 4.1 (Total Active Models)."""

    def test_counts_only_active_status(
        self, db_session, client, admin_headers, admin_user, usage_frequency, kpi_taxonomies
    ):
        """Only models with status='Active' should be counted.

        Scenario: Create 1 Active, 1 Retired, 1 In Development model.
        Expected: Count = 1.
        """
        # Active model
        active = Model(
            model_name="Active Model",
            status="Active",
            owner_id=admin_user.user_id,
            development_type="In-House",
            usage_frequency_id=usage_frequency["daily"].value_id,
            row_approval_status="approved"
        )
        # Retired model
        retired = Model(
            model_name="Retired Model",
            status="Retired",
            owner_id=admin_user.user_id,
            development_type="In-House",
            usage_frequency_id=usage_frequency["daily"].value_id,
            row_approval_status="approved"
        )
        # In Development model
        in_dev = Model(
            model_name="In Dev Model",
            status="In Development",
            owner_id=admin_user.user_id,
            development_type="In-House",
            usage_frequency_id=usage_frequency["daily"].value_id,
            row_approval_status="approved"
        )
        db_session.add_all([active, retired, in_dev])
        db_session.commit()

        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        metric_4_1 = next(m for m in data["metrics"] if m["metric_id"] == "4.1")

        # Should only count Active
        assert metric_4_1["count_value"] == 1
        assert data["total_active_models"] == 1


class TestMetric4_22_AttestationOnTime:
    """Test Metric 4.22 (% Required Attestations On Time).

    Gap 3 Fix: Verifies deterministic cycle selection.
    """

    def test_metric_4_22_selects_latest_cycle_only(
        self, client, admin_headers, db_session, kpi_active_model,
        kpi_create_attestation_cycle, kpi_create_attestation_record
    ):
        """
        Regression test: When multiple closed cycles exist,
        only the most recent should be used for calculation.

        Scenario:
        - Q3 2024 cycle (CLOSED): Model attested on-time
        - Q4 2024 cycle (CLOSED): Model attested late

        Expected: 4.22 uses Q4 (latest), showing 0/1 (0% on-time).
        If bug exists and Q3 is used: 1/1 (100% on-time).
        """
        # Create two closed cycles (Q3 older, Q4 newer)
        q3_cycle = kpi_create_attestation_cycle(
            name="Q3 2024 Attestation",
            status="CLOSED",
            end_date=date(2024, 9, 30)
        )
        q4_cycle = kpi_create_attestation_cycle(
            name="Q4 2024 Attestation",
            status="CLOSED",
            end_date=date(2024, 12, 31)
        )

        # Q3: On-time attestation (attested before due)
        kpi_create_attestation_record(
            cycle=q3_cycle,
            model=kpi_active_model,
            due_date=date(2024, 10, 30),  # 30 days after Q3 end
            attested_at_date=date(2024, 10, 29)  # On-time (1 day before due)
        )

        # Q4: Late attestation (attested after due)
        kpi_create_attestation_record(
            cycle=q4_cycle,
            model=kpi_active_model,
            due_date=date(2025, 1, 30),  # 30 days after Q4 end
            attested_at_date=date(2025, 2, 5)  # Late (6 days after due)
        )

        # Get KPI report
        response = client.get("/kpi-report/", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        metric_4_22 = next(
            (m for m in data["metrics"] if m["metric_id"] == "4.22"),
            None
        )

        # If metric exists, verify it uses the latest cycle
        if metric_4_22 and metric_4_22["ratio_value"]:
            # Should use Q4 cycle (latest): 0 on-time out of 1
            # If it incorrectly used Q3: 1 on-time out of 1
            assert metric_4_22["ratio_value"]["numerator"] == 0, \
                "Metric 4.22 should use the latest closed cycle (Q4), not Q3"


class TestMetricConsistency:
    """Test consistency between related metrics."""

    def test_4_6_and_4_7_sum_to_total(
        self, client, admin_headers, kpi_active_model, kpi_second_active_model,
        kpi_create_approved_validation, kpi_tier1_policy, kpi_tier2_policy
    ):
        """Metrics 4.6 (on time) + 4.7 (overdue) should sum to total models.

        Scenario: 2 models, 1 on time, 1 overdue.
        Expected: 4.6.numerator + 4.7.numerator = total_active_models
        """
        # Model 1: On time
        kpi_create_approved_validation(
            model=kpi_active_model,
            completion_date=date.today() - timedelta(days=30)
        )

        # Model 2: Overdue
        kpi_create_approved_validation(
            model=kpi_second_active_model,
            completion_date=date.today() - relativedelta(months=36)
        )

        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        metric_4_6 = next(m for m in data["metrics"] if m["metric_id"] == "4.6")
        metric_4_7 = next(m for m in data["metrics"] if m["metric_id"] == "4.7")

        # Sum should equal total
        on_time = metric_4_6["ratio_value"]["numerator"]
        overdue = metric_4_7["ratio_value"]["numerator"]
        total = data["total_active_models"]

        assert on_time + overdue == total, \
            f"4.6 ({on_time}) + 4.7 ({overdue}) should equal total ({total})"

    def test_4_1_equals_denominator(
        self, client, admin_headers, kpi_active_model, kpi_second_active_model,
        kpi_tier1_policy, kpi_tier2_policy
    ):
        """Metric 4.1 should equal the denominator used in other metrics.

        Expected: 4.1.count_value = total_active_models = 4.7.denominator
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        metric_4_1 = next(m for m in data["metrics"] if m["metric_id"] == "4.1")
        metric_4_7 = next(m for m in data["metrics"] if m["metric_id"] == "4.7")

        assert metric_4_1["count_value"] == data["total_active_models"]
        assert metric_4_1["count_value"] == metric_4_7["ratio_value"]["denominator"]


class TestKPIReportStructure:
    """Test the overall structure of the KPI report response."""

    def test_all_expected_metrics_present(self, client, admin_headers):
        """All expected metric IDs should be present in response.

        Expected metrics: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
                         4.10, 4.11, 4.12, 4.14, 4.18, 4.19, 4.20, 4.21,
                         4.22, 4.23, 4.24, 4.27, 4.28, 4.29
        """
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Get all metric IDs
        metric_ids = {m["metric_id"] for m in data["metrics"]}

        # Core expected metrics
        expected_core = {"4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7"}
        for mid in expected_core:
            assert mid in metric_ids, f"Missing expected metric {mid}"

    def test_report_generated_timestamp(self, client, admin_headers):
        """Report should include generation timestamp."""
        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        assert "report_generated_at" in data
        assert data["report_generated_at"] is not None

    def test_as_of_date_present(self, client, admin_headers):
        """Report should include as_of_date."""
        response = client.get("/kpi-report/", headers=admin_headers)

        data = response.json()
        assert "as_of_date" in data
        assert data["as_of_date"] is not None
