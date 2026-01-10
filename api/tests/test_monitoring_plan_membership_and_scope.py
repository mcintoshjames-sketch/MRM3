"""Tests for monitoring plan membership ledger and cycle scope behavior."""
# Run (from api/): DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest tests/test_monitoring_plan_membership_and_scope.py
# Postgres-only (local test DB): TEST_DATABASE_URL=postgresql://postgres:postgres_admin@localhost:5434/postgres \
#   DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest -m postgres tests/test_monitoring_plan_membership_and_scope.py
from datetime import date, timedelta
import threading
import time

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.monitoring_membership import MonitoringMembershipService
from app.core.monitoring_scope import get_cycle_scope_models, materialize_cycle_scope
from app.core.security import get_password_hash
from app.core.time import utc_now
from app.core.roles import RoleCode
from app.models.lob import LOBUnit
from app.models.model import Model
from app.models.role import Role
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.user import User
from app.models.kpm import KpmCategory, Kpm
from app.models.monitoring import (
    MonitoringPlan,
    MonitoringPlanMembership,
    MonitoringPlanVersion,
    MonitoringPlanModelSnapshot,
    MonitoringPlanMetric,
    MonitoringFrequency,
    MonitoringCycle,
    MonitoringCycleStatus,
    MonitoringCycleModelScope,
    MonitoringResult,
    monitoring_plan_models,
)


def _create_plan(db_session, name: str) -> MonitoringPlan:
    plan = MonitoringPlan(
        name=name,
        description=f"{name} description",
        frequency=MonitoringFrequency.QUARTERLY,
        data_submission_lead_days=10,
        reporting_lead_days=20,
        next_submission_due_date=date.today(),
        next_report_due_date=date.today() + timedelta(days=20),
        is_active=True,
    )
    db_session.add(plan)
    db_session.flush()
    return plan


def _create_plan_metric(db_session, plan_id: int) -> MonitoringPlanMetric:
    category = KpmCategory(
        code=f"CAT_{plan_id}",
        name="Performance",
        sort_order=1,
    )
    db_session.add(category)
    db_session.flush()

    kpm = Kpm(
        category_id=category.category_id,
        name=f"Metric {plan_id}",
        sort_order=1,
    )
    db_session.add(kpm)
    db_session.flush()

    metric = MonitoringPlanMetric(
        plan_id=plan_id,
        kpm_id=kpm.kpm_id,
        sort_order=1,
        is_active=True,
    )
    db_session.add(metric)
    db_session.flush()
    return metric


def _create_active_version(db_session, plan_id: int, user_id: int) -> MonitoringPlanVersion:
    version = MonitoringPlanVersion(
        plan_id=plan_id,
        version_number=1,
        version_name="v1",
        effective_date=date.today(),
        published_by_user_id=user_id,
        is_active=True,
    )
    db_session.add(version)
    db_session.flush()
    return version


def _create_cycle(db_session, plan_id: int, status: str) -> MonitoringCycle:
    cycle = MonitoringCycle(
        plan_id=plan_id,
        period_start_date=date.today(),
        period_end_date=date.today() + timedelta(days=30),
        submission_due_date=date.today() + timedelta(days=40),
        report_due_date=date.today() + timedelta(days=50),
        status=status,
    )
    db_session.add(cycle)
    db_session.flush()
    return cycle


def _create_lob_unit(db_session) -> LOBUnit:
    lob = LOBUnit(
        code="TEST",
        name="Test LOB",
        org_unit="S0001",
        level=0,
        is_active=True,
    )
    db_session.add(lob)
    db_session.flush()
    return lob


def _create_usage_frequency(db_session) -> TaxonomyValue:
    taxonomy = Taxonomy(name="Usage Frequency", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()
    value = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="DAILY",
        label="Daily",
        sort_order=1,
    )
    db_session.add(value)
    db_session.flush()
    return value


def _create_user(db_session, email: str, role_code: str, lob_id: int) -> User:
    role_id = db_session.query(Role).filter(Role.code == role_code).first().role_id
    user = User(
        email=email,
        full_name=email.split("@")[0].title(),
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_id,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_model(db_session, owner_id: int, usage_frequency_id: int) -> Model:
    model = Model(
        model_name="Membership Model",
        description="Model for membership tests",
        development_type="In-House",
        status="Active",
        owner_id=owner_id,
        submitted_by_user_id=owner_id,
        row_approval_status=None,
        usage_frequency_id=usage_frequency_id,
    )
    db_session.add(model)
    db_session.flush()
    return model


@pytest.fixture
def transfer_scenario(db_session, sample_model, admin_user):
    """Fixture to set up a standard transfer scenario.

    Creates:
    - Plan A (Source)
    - Plan B (Destination)
    - Initial Membership: sample_model -> Plan A

    Returns a dictionary with the created objects.
    """
    plan_a = _create_plan(db_session, "Plan A")
    plan_b = _create_plan(db_session, "Plan B")

    # Establish initial membership in Plan A
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Initial setup",
    )
    db_session.commit()

    return {
        "plan_a": plan_a,
        "plan_b": plan_b,
        "model": sample_model
    }


@pytest.fixture
def historical_cycle_setup(db_session, transfer_scenario, admin_user):
    """Fixture to create a historical closed cycle for validation.

    Creates:
    - Cycle C1 in Plan A (APPROVED status)
    - Scope: sample_model is in scope for C1

    Returns the cycle object.
    """
    data = transfer_scenario
    plan_a = data["plan_a"]
    model = data["model"]

    # Create a closed cycle
    cycle = _create_cycle(db_session, plan_a.plan_id,
                          MonitoringCycleStatus.APPROVED.value)

    # Manually create the immutable scope row (mimicking the system behavior at lock time)
    scope = MonitoringCycleModelScope(
        cycle_id=cycle.cycle_id,
        model_id=model.model_id,
        locked_at=cycle.period_end_date,
        scope_source="membership_ledger"
    )
    db_session.add(scope)
    db_session.commit()

    return cycle


@pytest.mark.postgres
def test_active_membership_unique_model_enforced(postgres_db_session):
    # Requires partial unique index from Alembic migration (not created by Base.metadata.create_all).
    # Run with migrations or add the index manually before executing this test.
    lob = _create_lob_unit(postgres_db_session)
    usage_frequency = _create_usage_frequency(postgres_db_session)
    owner = _create_user(
        postgres_db_session,
        "owner@example.com",
        RoleCode.USER.value,
        lob.lob_id,
    )
    model = _create_model(postgres_db_session, owner.user_id, usage_frequency.value_id)
    plan_a = _create_plan(postgres_db_session, "Plan A")
    plan_b = _create_plan(postgres_db_session, "Plan B")
    postgres_db_session.commit()

    postgres_db_session.add(MonitoringPlanMembership(
        model_id=model.model_id,
        plan_id=plan_a.plan_id,
        effective_from=utc_now(),
    ))
    postgres_db_session.commit()

    postgres_db_session.add(MonitoringPlanMembership(
        model_id=model.model_id,
        plan_id=plan_b.plan_id,
        effective_from=utc_now(),
    ))
    with pytest.raises(IntegrityError):
        postgres_db_session.commit()
    postgres_db_session.rollback()


def test_membership_effective_dates_enforced(db_session, sample_model, admin_user):
    plan = _create_plan(db_session, "Plan Dates")
    bad_membership = MonitoringPlanMembership(
        model_id=sample_model.model_id,
        plan_id=plan.plan_id,
        effective_from=utc_now(),
        effective_to=utc_now() - timedelta(days=1),
        changed_by_user_id=admin_user.user_id,
    )
    db_session.add(bad_membership)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_membership_service_adds_projection(db_session, sample_model, admin_user):
    plan = _create_plan(db_session, "Plan Projection")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Add model",
    )
    db_session.commit()

    membership = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
        MonitoringPlanMembership.plan_id == plan.plan_id,
        MonitoringPlanMembership.effective_to.is_(None),
    ).one()
    assert membership is not None

    projection = db_session.execute(
        monitoring_plan_models.select().where(
            monitoring_plan_models.c.plan_id == plan.plan_id,
            monitoring_plan_models.c.model_id == sample_model.model_id,
        )
    ).fetchone()
    assert projection is not None


def test_membership_service_removes_projection(db_session, sample_model, admin_user):
    plan = _create_plan(db_session, "Plan Remove")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Add model",
    )
    db_session.commit()

    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [],
        changed_by_user_id=admin_user.user_id,
        reason="Remove model",
    )
    db_session.commit()

    membership = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
        MonitoringPlanMembership.plan_id == plan.plan_id,
    ).one()
    assert membership.effective_to is not None

    projection = db_session.execute(
        monitoring_plan_models.select().where(
            monitoring_plan_models.c.plan_id == plan.plan_id,
            monitoring_plan_models.c.model_id == sample_model.model_id,
        )
    ).fetchone()
    assert projection is None


def test_transfer_updates_membership_and_projection(
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "Plan A")
    plan_b = _create_plan(db_session, "Plan B")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Membership setup",
    )
    db_session.commit()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "Transfer for test"},
    )
    assert response.status_code == 200

    db_session.expire_all()
    active_membership = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
        MonitoringPlanMembership.effective_to.is_(None),
    ).one()
    assert active_membership.plan_id == plan_b.plan_id

    closed_membership = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
        MonitoringPlanMembership.plan_id == plan_a.plan_id,
    ).one()
    assert closed_membership.effective_to is not None

    plan_a_link = db_session.execute(
        monitoring_plan_models.select().where(
            monitoring_plan_models.c.plan_id == plan_a.plan_id,
            monitoring_plan_models.c.model_id == sample_model.model_id,
        )
    ).fetchone()
    plan_b_link = db_session.execute(
        monitoring_plan_models.select().where(
            monitoring_plan_models.c.plan_id == plan_b.plan_id,
            monitoring_plan_models.c.model_id == sample_model.model_id,
        )
    ).fetchone()
    assert plan_a_link is None
    assert plan_b_link is not None


def test_cycle_scope_materialized_on_start(
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan = _create_plan(db_session, "Scope Plan")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Scope setup",
    )
    _create_active_version(db_session, plan.plan_id, admin_user.user_id)
    cycle = _create_cycle(db_session, plan.plan_id,
                          MonitoringCycleStatus.PENDING.value)
    db_session.commit()

    response = client.post(
        f"/monitoring/cycles/{cycle.cycle_id}/start",
        headers=admin_headers,
    )
    assert response.status_code == 200

    db_session.expire_all()
    scopes = db_session.query(MonitoringCycleModelScope).filter(
        MonitoringCycleModelScope.cycle_id == cycle.cycle_id
    ).all()
    assert {scope.model_id for scope in scopes} == {sample_model.model_id}


def test_transfer_blocked_when_cycle_active(
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "Active Plan")
    plan_b = _create_plan(db_session, "Destination Plan")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Blocking setup",
    )
    _create_cycle(db_session, plan_a.plan_id,
                  MonitoringCycleStatus.DATA_COLLECTION.value)
    db_session.commit()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "Should fail"},
    )
    assert response.status_code == 400
    assert "transfer not allowed" in response.json()["detail"].lower()


def test_transfer_allows_pending_cycle(
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "Pending Plan")
    plan_b = _create_plan(db_session, "Pending Destination")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Pending setup",
    )
    _create_cycle(db_session, plan_a.plan_id, MonitoringCycleStatus.PENDING.value)
    db_session.commit()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "Pending transfer"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("status", [
    MonitoringCycleStatus.APPROVED.value,
    MonitoringCycleStatus.CANCELLED.value,
])
def test_transfer_allows_closed_cycles(
    status,
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "Closed Plan")
    plan_b = _create_plan(db_session, "Closed Destination")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Closed setup",
    )
    _create_cycle(db_session, plan_a.plan_id, status)
    db_session.commit()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "Closed transfer"},
    )
    assert response.status_code == 200


def test_transfer_noop_when_same_plan(
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan = _create_plan(db_session, "No-op Plan")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="No-op setup",
    )
    db_session.commit()

    membership = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
        MonitoringPlanMembership.effective_to.is_(None),
    ).one()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan.plan_id, "reason": "No-op transfer"},
    )
    assert response.status_code == 200

    db_session.expire_all()
    memberships = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
    ).all()
    assert len(memberships) == 1
    assert memberships[0].membership_id == membership.membership_id


def test_transfer_creates_membership_when_unmonitored(
    client,
    admin_headers,
    sample_model,
    db_session,
):
    plan = _create_plan(db_session, "Unmonitored Plan")
    db_session.commit()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan.plan_id, "reason": "Initial assign"},
    )
    assert response.status_code == 200
    assert response.json()["from_plan_id"] is None

    membership = db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == sample_model.model_id,
        MonitoringPlanMembership.effective_to.is_(None),
    ).one()
    assert membership.plan_id == plan.plan_id


def test_transfer_forbidden_for_non_admin(
    client,
    auth_headers,
    sample_model,
    db_session,
):
    plan = _create_plan(db_session, "Auth Plan")
    db_session.commit()

    response = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=auth_headers,
        json={"to_plan_id": plan.plan_id, "reason": "Should fail"},
    )
    assert response.status_code == 403


def test_cycle_history_visible_after_transfer(
    client,
    admin_headers,
    auth_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "History Plan A")
    plan_b = _create_plan(db_session, "History Plan B")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="History setup",
    )
    _create_active_version(db_session, plan_a.plan_id, admin_user.user_id)
    metric = _create_plan_metric(db_session, plan_a.plan_id)
    cycle = _create_cycle(db_session, plan_a.plan_id,
                          MonitoringCycleStatus.PENDING.value)
    db_session.commit()

    start_resp = client.post(
        f"/monitoring/cycles/{cycle.cycle_id}/start",
        headers=admin_headers,
    )
    assert start_resp.status_code == 200

    result = MonitoringResult(
        cycle_id=cycle.cycle_id,
        plan_metric_id=metric.metric_id,
        model_id=sample_model.model_id,
        numeric_value=0.9,
        calculated_outcome="GREEN",
        entered_by_user_id=admin_user.user_id,
    )
    db_session.add(result)
    db_session.commit()

    cycle.status = MonitoringCycleStatus.APPROVED.value
    db_session.commit()

    transfer_resp = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "Move for history"},
    )
    assert transfer_resp.status_code == 200

    timeline_resp = client.get(
        f"/models/{sample_model.model_id}/activity-timeline",
        headers=auth_headers,
    )
    assert timeline_resp.status_code == 200
    activities = timeline_resp.json().get("activities", [])
    cycle_ids = {activity.get("entity_id") for activity in activities}
    assert cycle.cycle_id in cycle_ids

    cycle_resp = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}",
        headers=auth_headers,
    )
    assert cycle_resp.status_code == 200
    scope_models = cycle_resp.json().get("scope_models", [])
    assert {m["model_id"] for m in scope_models} == {sample_model.model_id}

    results_resp = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}/results",
        headers=auth_headers,
    )
    assert results_resp.status_code == 200
    result_model_ids = {r["model_id"] for r in results_resp.json()}
    assert sample_model.model_id in result_model_ids


def test_new_cycles_respect_transfer_scope(
    client,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "Source Plan")
    plan_b = _create_plan(db_session, "Destination Plan")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Scope setup",
    )
    db_session.commit()

    transfer_resp = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "Move before cycles"},
    )
    assert transfer_resp.status_code == 200

    _create_active_version(db_session, plan_a.plan_id, admin_user.user_id)
    _create_active_version(db_session, plan_b.plan_id, admin_user.user_id)

    cycle_a = _create_cycle(db_session, plan_a.plan_id, MonitoringCycleStatus.PENDING.value)
    cycle_b = _create_cycle(db_session, plan_b.plan_id, MonitoringCycleStatus.PENDING.value)
    db_session.commit()

    start_a = client.post(
        f"/monitoring/cycles/{cycle_a.cycle_id}/start",
        headers=admin_headers,
    )
    assert start_a.status_code == 200
    assert start_a.json()["scope_models"] == []

    start_b = client.post(
        f"/monitoring/cycles/{cycle_b.cycle_id}/start",
        headers=admin_headers,
    )
    assert start_b.status_code == 200
    scope_b = {m["model_id"] for m in start_b.json()["scope_models"]}
    assert scope_b == {sample_model.model_id}


def test_scope_falls_back_to_version_snapshot(db_session, sample_model, admin_user):
    plan = _create_plan(db_session, "Snapshot Plan")
    version = _create_active_version(db_session, plan.plan_id, admin_user.user_id)
    db_session.add(MonitoringPlanModelSnapshot(
        version_id=version.version_id,
        model_id=sample_model.model_id,
        model_name=sample_model.model_name,
    ))
    cycle = _create_cycle(db_session, plan.plan_id, MonitoringCycleStatus.APPROVED.value)
    cycle.plan_version_id = version.version_id
    db_session.commit()

    scope = get_cycle_scope_models(db_session, cycle)
    assert {entry["model_id"] for entry in scope} == {sample_model.model_id}


def test_scope_falls_back_to_results(db_session, sample_model, admin_user):
    plan = _create_plan(db_session, "Results Plan")
    metric = _create_plan_metric(db_session, plan.plan_id)
    cycle = _create_cycle(db_session, plan.plan_id, MonitoringCycleStatus.APPROVED.value)
    cycle.plan_version_id = None
    db_session.commit()

    result = MonitoringResult(
        cycle_id=cycle.cycle_id,
        plan_metric_id=metric.metric_id,
        model_id=sample_model.model_id,
        numeric_value=0.2,
        calculated_outcome="RED",
        entered_by_user_id=admin_user.user_id,
    )
    db_session.add(result)
    db_session.commit()

    scope = get_cycle_scope_models(db_session, cycle)
    assert {entry["model_id"] for entry in scope} == {sample_model.model_id}


def test_scope_falls_back_to_active_membership(db_session, sample_model, admin_user):
    plan = _create_plan(db_session, "Membership Plan")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Membership fallback",
    )
    cycle = _create_cycle(db_session, plan.plan_id, MonitoringCycleStatus.APPROVED.value)
    cycle.plan_version_id = None
    db_session.commit()

    scope = get_cycle_scope_models(db_session, cycle)
    assert {entry["model_id"] for entry in scope} == {sample_model.model_id}


@pytest.mark.postgres
def test_transfer_waits_for_cycle_start_lock(postgres_db_session):
    lob = _create_lob_unit(postgres_db_session)
    usage_frequency = _create_usage_frequency(postgres_db_session)
    admin_user = _create_user(
        postgres_db_session,
        "admin@example.com",
        RoleCode.ADMIN.value,
        lob.lob_id,
    )
    model = _create_model(postgres_db_session, admin_user.user_id, usage_frequency.value_id)
    plan_a = _create_plan(postgres_db_session, "Concurrent Plan A")
    plan_b = _create_plan(postgres_db_session, "Concurrent Plan B")
    version = _create_active_version(postgres_db_session, plan_a.plan_id, admin_user.user_id)
    MonitoringMembershipService(postgres_db_session).replace_plan_models(
        plan_a.plan_id,
        [model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Concurrency setup",
    )
    cycle = _create_cycle(postgres_db_session, plan_a.plan_id, MonitoringCycleStatus.PENDING.value)
    postgres_db_session.commit()

    engine = postgres_db_session.get_bind()
    SessionLocal = sessionmaker(bind=engine)

    lock_acquired = threading.Event()
    release_lock = threading.Event()
    transfer_done = threading.Event()
    transfer_error = {}

    def start_cycle_worker():
        session = SessionLocal()
        try:
            session.begin()
            session.query(MonitoringPlan).filter(
                MonitoringPlan.plan_id == plan_a.plan_id
            ).with_for_update().one()
            memberships = session.query(MonitoringPlanMembership).filter(
                MonitoringPlanMembership.plan_id == plan_a.plan_id,
                MonitoringPlanMembership.effective_to.is_(None),
            ).order_by(MonitoringPlanMembership.model_id.asc()).with_for_update().all()
            locked_cycle = session.query(MonitoringCycle).filter(
                MonitoringCycle.cycle_id == cycle.cycle_id
            ).one()
            locked_cycle.plan_version_id = version.version_id
            locked_cycle.version_locked_at = utc_now()
            locked_cycle.version_locked_by_user_id = admin_user.user_id
            locked_cycle.status = MonitoringCycleStatus.DATA_COLLECTION.value
            materialize_cycle_scope(
                session,
                locked_cycle,
                memberships,
                locked_at=locked_cycle.version_locked_at,
                scope_source="membership_ledger",
                source_details={"plan_id": plan_a.plan_id, "plan_version_id": version.version_id},
            )
            lock_acquired.set()
            release_lock.wait(timeout=2)
            session.commit()
        finally:
            session.close()

    def transfer_worker():
        session = SessionLocal()
        try:
            lock_acquired.wait(timeout=2)
            try:
                MonitoringMembershipService(session).transfer_model(
                    model_id=model.model_id,
                    to_plan_id=plan_b.plan_id,
                    changed_by_user_id=admin_user.user_id,
                    reason="Concurrent transfer",
                )
                session.commit()
            except HTTPException as exc:
                transfer_error["status_code"] = exc.status_code
                session.rollback()
        finally:
            transfer_done.set()
            session.close()

    start_thread = threading.Thread(target=start_cycle_worker)
    transfer_thread = threading.Thread(target=transfer_worker)
    start_thread.start()
    transfer_thread.start()

    lock_acquired.wait(timeout=2)
    time.sleep(0.2)
    assert not transfer_done.is_set()

    release_lock.set()
    start_thread.join(timeout=2)
    transfer_thread.join(timeout=2)

    assert transfer_error.get("status_code") == 400

    postgres_db_session.expire_all()
    scope_rows = postgres_db_session.query(MonitoringCycleModelScope).filter(
        MonitoringCycleModelScope.cycle_id == cycle.cycle_id
    ).all()
    assert {row.model_id for row in scope_rows} == {model.model_id}

    active_membership = postgres_db_session.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.model_id == model.model_id,
        MonitoringPlanMembership.effective_to.is_(None),
    ).one()
    assert active_membership.plan_id == plan_a.plan_id
