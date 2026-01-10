"""Monitoring news feed regression tests."""
# Run (from api/): DATABASE_URL=sqlite:///:memory: SECRET_KEY=dev-test-key python3 -m pytest tests/test_dashboard_news_feed_monitoring.py
from datetime import date, timedelta

from app.core.monitoring_membership import MonitoringMembershipService
from app.core.time import utc_now
from app.models.kpm import KpmCategory, Kpm
from app.models.monitoring import (
    MonitoringPlan,
    MonitoringPlanMetric,
    MonitoringCycle,
    MonitoringCycleStatus,
    MonitoringResult,
    MonitoringFrequency,
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


def _create_metric(db_session, plan_id: int) -> MonitoringPlanMetric:
    category = KpmCategory(
        code=f"NF_{plan_id}",
        name="Performance",
        sort_order=1,
    )
    db_session.add(category)
    db_session.flush()

    kpm = Kpm(
        category_id=category.category_id,
        name="News Feed Metric",
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


def test_news_feed_retains_monitoring_cycle_after_transfer(
    client,
    auth_headers,
    admin_headers,
    admin_user,
    sample_model,
    db_session,
):
    plan_a = _create_plan(db_session, "News Feed Plan A")
    plan_b = _create_plan(db_session, "News Feed Plan B")
    MonitoringMembershipService(db_session).replace_plan_models(
        plan_a.plan_id,
        [sample_model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="News feed setup",
    )
    metric = _create_metric(db_session, plan_a.plan_id)
    cycle = MonitoringCycle(
        plan_id=plan_a.plan_id,
        period_start_date=date.today() - timedelta(days=90),
        period_end_date=date.today() - timedelta(days=1),
        submission_due_date=date.today(),
        report_due_date=date.today() + timedelta(days=7),
        status=MonitoringCycleStatus.APPROVED.value,
        completed_at=utc_now(),
        completed_by_user_id=admin_user.user_id,
    )
    db_session.add(cycle)
    db_session.flush()

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

    feed_before = client.get("/dashboard/news-feed", headers=auth_headers).json()
    assert any(
        item.get("entity_link") == f"/monitoring/cycles/{cycle.cycle_id}"
        for item in feed_before
    )

    transfer_resp = client.post(
        f"/models/{sample_model.model_id}/monitoring-plan-transfer",
        headers=admin_headers,
        json={"to_plan_id": plan_b.plan_id, "reason": "News feed transfer"},
    )
    assert transfer_resp.status_code == 200

    feed_after = client.get("/dashboard/news-feed", headers=auth_headers).json()
    assert any(
        item.get("entity_link") == f"/monitoring/cycles/{cycle.cycle_id}"
        for item in feed_after
    )
