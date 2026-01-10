"""Tests for Model Overlays API endpoints."""
# Run (from api/): DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest tests/test_model_overlays.py
from datetime import date, timedelta

import pytest

from app.core.time import utc_now
from app.core.monitoring_membership import MonitoringMembershipService
from app.models import Model, ModelOverlay, ModelLimitation, Region, Taxonomy, TaxonomyValue
from app.models.audit_log import AuditLog
from app.models.kpm import KpmCategory, Kpm
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringFrequency,
    MonitoringPlan,
    MonitoringPlanMetric,
    MonitoringResult,
)
from app.models.team import Team


@pytest.fixture
def test_region(db_session):
    """Create a test region."""
    region = Region(code="NA", name="North America")
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


@pytest.fixture
def other_model(db_session, second_user, usage_frequency):
    """Create a second model for mismatch validation tests."""
    model = Model(
        model_name="Other Model",
        description="Another test model",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id,
        row_approval_status="Draft",
        submitted_by_user_id=second_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def limitation_category(db_session):
    """Create a Limitation Category taxonomy value."""
    taxonomy = Taxonomy(name="Limitation Category", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()
    value = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="DATA",
        label="Data",
        sort_order=1
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def sample_limitation(db_session, sample_model, validator_user, limitation_category):
    """Create a limitation for the sample model."""
    limitation = ModelLimitation(
        model_id=sample_model.model_id,
        significance="Non-Critical",
        category_id=limitation_category.value_id,
        description="Test limitation",
        impact_assessment="Test impact",
        conclusion="Accept",
        conclusion_rationale="Test rationale",
        is_retired=False,
        created_by_id=validator_user.user_id,
    )
    db_session.add(limitation)
    db_session.commit()
    db_session.refresh(limitation)
    return limitation


@pytest.fixture
def other_limitation(db_session, other_model, validator_user, limitation_category):
    """Create a limitation for another model."""
    limitation = ModelLimitation(
        model_id=other_model.model_id,
        significance="Non-Critical",
        category_id=limitation_category.value_id,
        description="Other limitation",
        impact_assessment="Other impact",
        conclusion="Accept",
        conclusion_rationale="Other rationale",
        is_retired=False,
        created_by_id=validator_user.user_id,
    )
    db_session.add(limitation)
    db_session.commit()
    db_session.refresh(limitation)
    return limitation


def _create_monitoring_setup(db_session, model, entered_by_id):
    """Create monitoring plan, cycle, and result for a model."""
    plan = MonitoringPlan(
        name="Test Plan",
        description="Test monitoring plan",
        frequency=MonitoringFrequency.MONTHLY,
    )
    db_session.add(plan)
    db_session.flush()

    kpm_category = KpmCategory(
        code="PERF",
        name="Performance",
        description="Performance metrics",
        sort_order=1
    )
    db_session.add(kpm_category)
    db_session.flush()

    kpm = Kpm(
        category_id=kpm_category.category_id,
        name="Test Metric",
        description="Test metric description",
        sort_order=1
    )
    db_session.add(kpm)
    db_session.flush()

    metric = MonitoringPlanMetric(
        plan_id=plan.plan_id,
        kpm_id=kpm.kpm_id,
    )
    db_session.add(metric)
    db_session.flush()

    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=date(2025, 1, 1),
        period_end_date=date(2025, 1, 31),
        submission_due_date=date(2025, 2, 10),
        report_due_date=date(2025, 2, 15),
        status="DATA_COLLECTION",
    )
    db_session.add(cycle)
    db_session.flush()

    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [model.model_id],
        changed_by_user_id=entered_by_id,
        reason="Overlay test setup",
    )

    result = MonitoringResult(
        cycle_id=cycle.cycle_id,
        plan_metric_id=metric.metric_id,
        model_id=model.model_id,
        entered_by_user_id=entered_by_id,
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    return {"plan": plan, "metric": metric, "cycle": cycle, "result": result}


@pytest.fixture
def monitoring_setup(db_session, sample_model, admin_user):
    """Monitoring setup for the sample model."""
    return _create_monitoring_setup(db_session, sample_model, admin_user.user_id)


@pytest.fixture
def other_monitoring_setup(db_session, other_model, admin_user):
    """Monitoring setup for another model."""
    return _create_monitoring_setup(db_session, other_model, admin_user.user_id)


@pytest.fixture
def sample_overlay(db_session, sample_model, validator_user):
    """Create a sample overlay for list/update tests."""
    overlay = ModelOverlay(
        model_id=sample_model.model_id,
        overlay_kind="OVERLAY",
        is_underperformance_related=True,
        description="Temporary overlay for instability",
        rationale="Performance drift detected",
        effective_from=utc_now().date() - timedelta(days=5),
        effective_to=None,
        is_retired=False,
        created_by_id=validator_user.user_id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(overlay)
    db_session.commit()
    db_session.refresh(overlay)
    return overlay


@pytest.fixture
def active_model(db_session, test_user, usage_frequency):
    """Create an active model for report tests."""
    model = Model(
        model_name="Active Model",
        description="Active model for reporting",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status=None,
        submitted_by_user_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class TestListOverlays:
    """Tests for listing model overlays."""

    def test_list_overlays_empty(self, client, sample_model, auth_headers):
        response = client.get(
            f"/models/{sample_model.model_id}/overlays",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_overlays_excludes_retired_by_default(
        self, client, db_session, sample_model, auth_headers, sample_overlay, validator_user
    ):
        sample_overlay.is_retired = True
        sample_overlay.retirement_reason = "No longer needed"
        sample_overlay.retired_by_id = validator_user.user_id
        sample_overlay.retirement_date = utc_now()
        db_session.commit()

        response = client.get(
            f"/models/{sample_model.model_id}/overlays",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_overlays_include_retired(
        self, client, db_session, sample_model, auth_headers, sample_overlay, validator_user
    ):
        sample_overlay.is_retired = True
        sample_overlay.retirement_reason = "No longer needed"
        sample_overlay.retired_by_id = validator_user.user_id
        sample_overlay.retirement_date = utc_now()
        db_session.commit()

        response = client.get(
            f"/models/{sample_model.model_id}/overlays?include_retired=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_overlays_filters(
        self, client, db_session, sample_model, auth_headers, validator_user, test_region
    ):
        overlay_a = ModelOverlay(
            model_id=sample_model.model_id,
            overlay_kind="OVERLAY",
            is_underperformance_related=True,
            description="Overlay A",
            rationale="Rationale A",
            effective_from=utc_now().date() - timedelta(days=1),
            region_id=test_region.region_id,
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        overlay_b = ModelOverlay(
            model_id=sample_model.model_id,
            overlay_kind="MANAGEMENT_JUDGEMENT",
            is_underperformance_related=False,
            description="Overlay B",
            rationale="Rationale B",
            effective_from=utc_now().date() - timedelta(days=2),
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        db_session.add_all([overlay_a, overlay_b])
        db_session.commit()

        response = client.get(
            f"/models/{sample_model.model_id}/overlays?overlay_kind=OVERLAY",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["overlay_kind"] == "OVERLAY"

        response = client.get(
            f"/models/{sample_model.model_id}/overlays?is_underperformance_related=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["overlay_kind"] == "MANAGEMENT_JUDGEMENT"

        response = client.get(
            f"/models/{sample_model.model_id}/overlays?region_id={test_region.region_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["overlay_kind"] == "OVERLAY"


class TestCreateOverlay:
    """Tests for creating overlays."""

    def test_create_overlay_success(self, client, sample_model, validator_headers):
        payload = {
            "overlay_kind": "OVERLAY",
            "is_underperformance_related": True,
            "description": "Increase conservatism in PD estimates",
            "rationale": "Sustained underperformance in backtesting",
            "effective_from": str(utc_now().date()),
        }
        response = client.post(
            f"/models/{sample_model.model_id}/overlays",
            headers=validator_headers,
            json=payload
        )
        assert response.status_code == 201
        data = response.json()
        assert data["overlay_kind"] == "OVERLAY"
        assert data["model_id"] == sample_model.model_id

    def test_create_overlay_forbidden_for_owner(self, client, sample_model, auth_headers):
        payload = {
            "overlay_kind": "OVERLAY",
            "is_underperformance_related": True,
            "description": "Overlay description",
            "rationale": "Overlay rationale",
            "effective_from": str(utc_now().date()),
        }
        response = client.post(
            f"/models/{sample_model.model_id}/overlays",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 403

    def test_create_overlay_missing_required_fields(self, client, sample_model, validator_headers):
        payload = {
            "overlay_kind": "OVERLAY",
            "is_underperformance_related": True,
        }
        response = client.post(
            f"/models/{sample_model.model_id}/overlays",
            headers=validator_headers,
            json=payload
        )
        assert response.status_code == 422

    def test_create_overlay_rejects_mismatched_monitoring_result(
        self, client, sample_model, validator_headers, other_monitoring_setup
    ):
        payload = {
            "overlay_kind": "OVERLAY",
            "is_underperformance_related": True,
            "description": "Overlay description",
            "rationale": "Overlay rationale",
            "effective_from": str(utc_now().date()),
            "trigger_monitoring_result_id": other_monitoring_setup["result"].result_id
        }
        response = client.post(
            f"/models/{sample_model.model_id}/overlays",
            headers=validator_headers,
            json=payload
        )
        assert response.status_code == 400

    def test_create_overlay_allows_monitoring_cycle_after_transfer(
        self,
        client,
        db_session,
        sample_model,
        admin_user,
        monitoring_setup,
        validator_headers,
    ):
        plan_b = MonitoringPlan(
            name="Overlay Transfer Plan",
            description="Plan after transfer",
            frequency=MonitoringFrequency.MONTHLY,
        )
        db_session.add(plan_b)
        db_session.flush()

        MonitoringMembershipService(db_session).transfer_model(
            model_id=sample_model.model_id,
            to_plan_id=plan_b.plan_id,
            changed_by_user_id=admin_user.user_id,
            reason="Transfer before overlay",
        )
        db_session.commit()

        payload = {
            "overlay_kind": "OVERLAY",
            "is_underperformance_related": True,
            "description": "Overlay after transfer",
            "rationale": "Monitoring cycle reference",
            "effective_from": str(utc_now().date()),
            "trigger_monitoring_cycle_id": monitoring_setup["cycle"].cycle_id,
        }
        response = client.post(
            f"/models/{sample_model.model_id}/overlays",
            headers=validator_headers,
            json=payload
        )
        assert response.status_code == 200
        assert response.json()["trigger_monitoring_cycle_id"] == monitoring_setup["cycle"].cycle_id

    def test_create_overlay_rejects_mismatched_limitation(
        self, client, sample_model, validator_headers, other_limitation
    ):
        payload = {
            "overlay_kind": "OVERLAY",
            "is_underperformance_related": True,
            "description": "Overlay description",
            "rationale": "Overlay rationale",
            "effective_from": str(utc_now().date()),
            "related_limitation_id": other_limitation.limitation_id
        }
        response = client.post(
            f"/models/{sample_model.model_id}/overlays",
            headers=validator_headers,
            json=payload
        )
        assert response.status_code == 400


class TestUpdateOverlay:
    """Tests for updating overlays."""

    def test_update_overlay_allowed_fields_and_audit_log(
        self, client, db_session, sample_overlay, validator_headers, sample_limitation
    ):
        payload = {
            "evidence_description": "Monitoring report Q1-2025",
            "related_limitation_id": sample_limitation.limitation_id
        }
        response = client.patch(
            f"/overlays/{sample_overlay.overlay_id}",
            headers=validator_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_description"] == "Monitoring report Q1-2025"
        assert data["related_limitation_id"] == sample_limitation.limitation_id

        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelOverlay",
            AuditLog.entity_id == sample_overlay.overlay_id,
            AuditLog.action == "UPDATE"
        ).first()
        assert audit_log is not None
        assert "evidence_description" in audit_log.changes["old"]
        assert audit_log.changes["new"]["evidence_description"] == "Monitoring report Q1-2025"

    def test_update_overlay_rejects_immutable_fields(
        self, client, sample_overlay, validator_headers
    ):
        response = client.patch(
            f"/overlays/{sample_overlay.overlay_id}",
            headers=validator_headers,
            json={"rationale": "New rationale"}
        )
        assert response.status_code == 400

    def test_update_overlay_rejects_retired(
        self, client, db_session, sample_overlay, validator_headers, validator_user
    ):
        sample_overlay.is_retired = True
        sample_overlay.retirement_reason = "No longer needed"
        sample_overlay.retired_by_id = validator_user.user_id
        sample_overlay.retirement_date = utc_now()
        db_session.commit()

        response = client.patch(
            f"/overlays/{sample_overlay.overlay_id}",
            headers=validator_headers,
            json={"evidence_description": "Should not update"}
        )
        assert response.status_code == 400


class TestRetireOverlay:
    """Tests for retiring overlays."""

    def test_retire_overlay_success(self, client, db_session, sample_overlay, validator_headers):
        response = client.post(
            f"/overlays/{sample_overlay.overlay_id}/retire",
            headers=validator_headers,
            json={"retirement_reason": "Overlay no longer needed"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_retired"] is True
        assert data["retirement_reason"] == "Overlay no longer needed"

        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelOverlay",
            AuditLog.entity_id == sample_overlay.overlay_id,
            AuditLog.action == "RETIRE"
        ).first()
        assert audit_log is not None


class TestModelOverlayReport:
    """Tests for the model overlays report endpoint."""

    def test_report_in_effect_underperformance_only(
        self, client, db_session, active_model, validator_user, auth_headers
    ):
        today = utc_now().date()
        overlay_in_effect = ModelOverlay(
            model_id=active_model.model_id,
            overlay_kind="OVERLAY",
            is_underperformance_related=True,
            description="Active overlay",
            rationale="Performance gap",
            effective_from=today - timedelta(days=10),
            effective_to=None,
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        overlay_expired = ModelOverlay(
            model_id=active_model.model_id,
            overlay_kind="OVERLAY",
            is_underperformance_related=True,
            description="Expired overlay",
            rationale="Expired",
            effective_from=today - timedelta(days=30),
            effective_to=today - timedelta(days=1),
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        overlay_non_under = ModelOverlay(
            model_id=active_model.model_id,
            overlay_kind="OVERLAY",
            is_underperformance_related=False,
            description="Not underperformance",
            rationale="Other reason",
            effective_from=today - timedelta(days=5),
            effective_to=None,
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        overlay_retired = ModelOverlay(
            model_id=active_model.model_id,
            overlay_kind="OVERLAY",
            is_underperformance_related=True,
            description="Retired overlay",
            rationale="Retired",
            effective_from=today - timedelta(days=5),
            effective_to=None,
            is_retired=True,
            retirement_reason="Retired",
            retirement_date=utc_now(),
            retired_by_id=validator_user.user_id,
            created_by_id=validator_user.user_id,
        )
        db_session.add_all([overlay_in_effect, overlay_expired, overlay_non_under, overlay_retired])
        db_session.commit()

        response = client.get(
            "/reports/model-overlays",
            headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["overlay_id"] == overlay_in_effect.overlay_id
        assert items[0]["has_monitoring_traceability"] is False

    def test_report_filters_team_region_risk_tier_and_pending(
        self, client, db_session, active_model, test_region, risk_tier_taxonomy, lob_hierarchy, validator_user, auth_headers, usage_frequency
    ):
        team = Team(name="Risk Team", description="Test team", is_active=True)
        db_session.add(team)
        db_session.flush()
        lob_hierarchy["retail"].team_id = team.team_id

        active_model.risk_tier_id = risk_tier_taxonomy["TIER_1"].value_id
        db_session.flush()

        today = utc_now().date()
        overlay = ModelOverlay(
            model_id=active_model.model_id,
            overlay_kind="MANAGEMENT_JUDGEMENT",
            is_underperformance_related=True,
            description="Regional judgement",
            rationale="Region specific adjustment",
            effective_from=today - timedelta(days=1),
            region_id=test_region.region_id,
            is_retired=False,
            created_by_id=validator_user.user_id,
        )

        pending_model = Model(
            model_name="Pending Decommission Model",
            description="Pending model",
            development_type="In-House",
            status="Pending Decommission",
            owner_id=active_model.owner_id,
            row_approval_status=None,
            submitted_by_user_id=active_model.owner_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(pending_model)
        db_session.flush()

        pending_overlay = ModelOverlay(
            model_id=pending_model.model_id,
            overlay_kind="OVERLAY",
            is_underperformance_related=True,
            description="Pending overlay",
            rationale="Pending rationale",
            effective_from=today - timedelta(days=2),
            is_retired=False,
            created_by_id=validator_user.user_id,
        )

        db_session.add_all([overlay, pending_overlay])
        db_session.commit()

        response = client.get(
            f"/reports/model-overlays?region_id={test_region.region_id}&team_id={team.team_id}&risk_tier=TIER_1&overlay_kind=MANAGEMENT_JUDGEMENT",
            headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["overlay_id"] == overlay.overlay_id

        response = client.get(
            "/reports/model-overlays?include_pending_decommission=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert any(item["model_id"] == pending_model.model_id for item in items)
