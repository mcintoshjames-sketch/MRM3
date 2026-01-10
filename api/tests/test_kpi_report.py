"""TDD Integration tests for KPI Report region filtering.

These tests use real in-memory SQLite database with actual data fixtures.
NO MOCKING - tests the actual endpoint logic end-to-end.
"""
# Run (from api/): DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest tests/test_kpi_report.py
from datetime import date, timedelta

import pytest
from app.core.monitoring_membership import MonitoringMembershipService
from app.core.time import utc_now
from app.api.kpi_report import METRIC_DEFINITIONS
from app.models.kpm import KpmCategory, Kpm
from app.models import Model, ModelVersion
from app.models.region import Region
from app.models.model_region import ModelRegion
from app.models.monitoring import (
    MonitoringPlan,
    MonitoringPlanMetric,
    MonitoringCycle,
    MonitoringResult,
    MonitoringFrequency,
    MonitoringCycleStatus,
)


@pytest.fixture
def kpi_regions(db_session):
    """Create test regions for KPI filtering tests."""
    us = Region(code="US", name="United States")
    uk = Region(code="UK", name="United Kingdom")
    empty = Region(code="EMPTY", name="Empty Region")  # No models deployed here
    db_session.add_all([us, uk, empty])
    db_session.commit()
    return {"us": us, "uk": uk, "empty": empty}


@pytest.fixture
def kpi_models_with_regions(db_session, admin_user, kpi_regions, usage_frequency, lob_hierarchy):
    """Create models deployed to different regions.

    Creates 3 active models:
    - us_only: Deployed ONLY to US (1 region)
    - uk_only: Deployed ONLY to UK (1 region)
    - global_model: Deployed to BOTH US AND UK (2 regions)

    Expected counts:
    - No filter: 3 models
    - US filter: 2 models (us_only + global_model)
    - UK filter: 2 models (uk_only + global_model)
    - EMPTY filter: 0 models
    """
    # Create 3 active models
    model_us = Model(
        model_name="US Credit Model",
        status="Active",
        owner_id=admin_user.user_id,
        development_type="In-House",
        usage_frequency_id=usage_frequency["daily"].value_id,
        row_approval_status="approved"
    )
    model_uk = Model(
        model_name="UK Risk Model",
        status="Active",
        owner_id=admin_user.user_id,
        development_type="In-House",
        usage_frequency_id=usage_frequency["daily"].value_id,
        row_approval_status="approved"
    )
    model_global = Model(
        model_name="Global Pricing Model",
        status="Active",
        owner_id=admin_user.user_id,
        development_type="In-House",
        usage_frequency_id=usage_frequency["daily"].value_id,
        row_approval_status="approved"
    )
    db_session.add_all([model_us, model_uk, model_global])
    db_session.flush()

    # Create versions for deployment
    ver_us = ModelVersion(
        model_id=model_us.model_id,
        version_number="1.0",
        change_type="Initial",
        change_description="Initial version",
        created_by_id=admin_user.user_id
    )
    ver_uk = ModelVersion(
        model_id=model_uk.model_id,
        version_number="1.0",
        change_type="Initial",
        change_description="Initial version",
        created_by_id=admin_user.user_id
    )
    ver_global = ModelVersion(
        model_id=model_global.model_id,
        version_number="1.0",
        change_type="Initial",
        change_description="Initial version",
        created_by_id=admin_user.user_id
    )
    db_session.add_all([ver_us, ver_uk, ver_global])
    db_session.flush()

    # Deploy: US model to US only
    db_session.add(ModelRegion(
        model_id=model_us.model_id,
        region_id=kpi_regions["us"].region_id,
        version_id=ver_us.version_id
    ))
    # Deploy: UK model to UK only
    db_session.add(ModelRegion(
        model_id=model_uk.model_id,
        region_id=kpi_regions["uk"].region_id,
        version_id=ver_uk.version_id
    ))
    # Deploy: Global model to BOTH US and UK
    db_session.add(ModelRegion(
        model_id=model_global.model_id,
        region_id=kpi_regions["us"].region_id,
        version_id=ver_global.version_id
    ))
    db_session.add(ModelRegion(
        model_id=model_global.model_id,
        region_id=kpi_regions["uk"].region_id,
        version_id=ver_global.version_id
    ))
    db_session.commit()

    return {
        "us_only": model_us,      # In US only (1 region)
        "uk_only": model_uk,      # In UK only (1 region)
        "global": model_global,   # In US AND UK (2 regions)
    }


class TestKPIReportRegionFiltering:
    """Integration tests for KPI Report region filtering - NO MOCKING."""

    def test_without_region_returns_all_models(
        self, client, admin_headers, kpi_models_with_regions
    ):
        """No region filter returns all 3 active models."""
        response = client.get("/kpi-report/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["region_id"] is None
        assert data["region_name"] == "All Regions"
        assert data["total_active_models"] == 3  # All 3 models

    def test_with_us_region_returns_us_models(
        self, client, admin_headers, kpi_regions, kpi_models_with_regions
    ):
        """US region filter returns 2 models (us_only + global)."""
        response = client.get(
            f"/kpi-report/?region_id={kpi_regions['us'].region_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["region_id"] == kpi_regions["us"].region_id
        assert data["region_name"] == "United States"
        assert data["total_active_models"] == 2  # us_only + global

    def test_with_uk_region_returns_uk_models(
        self, client, admin_headers, kpi_regions, kpi_models_with_regions
    ):
        """UK region filter returns 2 models (uk_only + global)."""
        response = client.get(
            f"/kpi-report/?region_id={kpi_regions['uk'].region_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["region_id"] == kpi_regions["uk"].region_id
        assert data["region_name"] == "United Kingdom"
        assert data["total_active_models"] == 2  # uk_only + global

    def test_empty_region_returns_zero_models(
        self, client, admin_headers, kpi_regions, kpi_models_with_regions
    ):
        """Empty region (no deployments) returns 0 models."""
        response = client.get(
            f"/kpi-report/?region_id={kpi_regions['empty'].region_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_active_models"] == 0
        # Metric 4.1 should also be 0
        metric_4_1 = next(m for m in data["metrics"] if m["metric_id"] == "4.1")
        assert metric_4_1["count_value"] == 0

    def test_invalid_region_returns_404(self, client, admin_headers):
        """Non-existent region_id returns 404."""
        response = client.get("/kpi-report/?region_id=99999", headers=admin_headers)
        assert response.status_code == 404

    def test_metric_4_1_matches_total_active_models(
        self, client, admin_headers, kpi_regions, kpi_models_with_regions
    ):
        """Metric 4.1 (Total Active Models) equals total_active_models for region."""
        response = client.get(
            f"/kpi-report/?region_id={kpi_regions['us'].region_id}",
            headers=admin_headers
        )

        data = response.json()
        metric_4_1 = next(m for m in data["metrics"] if m["metric_id"] == "4.1")
        assert metric_4_1["count_value"] == data["total_active_models"]

    def test_all_metrics_present(
        self, client, admin_headers, kpi_regions, kpi_models_with_regions
    ):
        """All metrics are returned regardless of region filter."""
        response = client.get(
            f"/kpi-report/?region_id={kpi_regions['us'].region_id}",
            headers=admin_headers
        )

        data = response.json()
        assert len(data["metrics"]) == len(METRIC_DEFINITIONS)

    def test_region_response_includes_region_info(
        self, client, admin_headers, kpi_regions, kpi_models_with_regions
    ):
        """Response includes region_id and region_name fields."""
        # Test with region filter
        response = client.get(
            f"/kpi-report/?region_id={kpi_regions['us'].region_id}",
            headers=admin_headers
        )
        data = response.json()
        assert "region_id" in data
        assert "region_name" in data
        assert data["region_id"] == kpi_regions["us"].region_id
        assert data["region_name"] == "United States"

        # Test without region filter
        response = client.get("/kpi-report/", headers=admin_headers)
        data = response.json()
        assert "region_id" in data
        assert "region_name" in data
        assert data["region_id"] is None
        assert data["region_name"] == "All Regions"


class TestKPIReportMonitoringTransfer:
    """Regression tests for monitoring metrics after plan transfer."""

    def test_monitoring_metrics_unchanged_after_transfer(
        self,
        client,
        admin_headers,
        admin_user,
        usage_frequency,
        db_session,
    ):
        model = Model(
            model_name="Monitoring KPI Model",
            status="Active",
            owner_id=admin_user.user_id,
            development_type="In-House",
            usage_frequency_id=usage_frequency["daily"].value_id,
            row_approval_status=None,
            submitted_by_user_id=admin_user.user_id,
        )
        db_session.add(model)
        db_session.flush()

        plan_a = MonitoringPlan(
            name="Monitoring KPI Plan A",
            description="Plan before transfer",
            frequency=MonitoringFrequency.QUARTERLY,
            data_submission_lead_days=10,
            reporting_lead_days=20,
            next_submission_due_date=date.today(),
            next_report_due_date=date.today() + timedelta(days=20),
            is_active=True,
        )
        plan_b = MonitoringPlan(
            name="Monitoring KPI Plan B",
            description="Plan after transfer",
            frequency=MonitoringFrequency.QUARTERLY,
            data_submission_lead_days=10,
            reporting_lead_days=20,
            next_submission_due_date=date.today(),
            next_report_due_date=date.today() + timedelta(days=20),
            is_active=True,
        )
        db_session.add_all([plan_a, plan_b])
        db_session.flush()

        MonitoringMembershipService(db_session).replace_plan_models(
            plan_a.plan_id,
            [model.model_id],
            changed_by_user_id=admin_user.user_id,
            reason="KPI monitoring setup",
        )

        category = KpmCategory(
            code="KPI_MON",
            name="Monitoring KPI",
            sort_order=1,
        )
        db_session.add(category)
        db_session.flush()
        kpm = Kpm(
            category_id=category.category_id,
            name="KPI Metric",
            sort_order=1,
        )
        db_session.add(kpm)
        db_session.flush()
        metric = MonitoringPlanMetric(
            plan_id=plan_a.plan_id,
            kpm_id=kpm.kpm_id,
            sort_order=1,
            is_active=True,
        )
        db_session.add(metric)
        db_session.flush()

        cycle = MonitoringCycle(
            plan_id=plan_a.plan_id,
            period_start_date=date.today() - timedelta(days=90),
            period_end_date=date.today() - timedelta(days=1),
            submission_due_date=date.today(),
            report_due_date=date.today() + timedelta(days=7),
            status=MonitoringCycleStatus.APPROVED.value,
            submitted_at=utc_now(),
            submitted_by_user_id=admin_user.user_id,
            completed_at=utc_now(),
            completed_by_user_id=admin_user.user_id,
        )
        db_session.add(cycle)
        db_session.flush()

        result = MonitoringResult(
            cycle_id=cycle.cycle_id,
            plan_metric_id=metric.metric_id,
            model_id=model.model_id,
            numeric_value=0.4,
            calculated_outcome="RED",
            entered_by_user_id=admin_user.user_id,
        )
        db_session.add(result)
        db_session.commit()

        resp_before = client.get("/kpi-report/", headers=admin_headers)
        assert resp_before.status_code == 200
        metrics_before = {
            m["metric_id"]: m for m in resp_before.json().get("metrics", [])
        }

        MonitoringMembershipService(db_session).transfer_model(
            model_id=model.model_id,
            to_plan_id=plan_b.plan_id,
            changed_by_user_id=admin_user.user_id,
            reason="KPI transfer",
        )
        db_session.commit()

        resp_after = client.get("/kpi-report/", headers=admin_headers)
        assert resp_after.status_code == 200
        metrics_after = {
            m["metric_id"]: m for m in resp_after.json().get("metrics", [])
        }

        for metric_id in ["4.10", "4.11"]:
            before = metrics_before[metric_id]["ratio_value"]
            after = metrics_after[metric_id]["ratio_value"]
            assert before["numerator"] == after["numerator"]
            assert before["denominator"] == after["denominator"]
