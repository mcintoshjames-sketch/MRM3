"""Tests for monitoring outcome backfill logic."""
from datetime import date, timedelta

from app.core.monitoring_backfill import (
    backfill_monitoring_results_outcomes,
    backfill_monitoring_cycle_versions,
)
from app.core.monitoring_membership import MonitoringMembershipService
from app.core.time import utc_now
from app.models.kpm import Kpm, KpmCategory
from app.models.model import Model
from app.models.model_exception import ModelException
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringPlan,
    MonitoringPlanMetric,
    MonitoringPlanMetricSnapshot,
    MonitoringPlanVersion,
    MonitoringFrequency,
    MonitoringResult,
)
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.core.exception_detection import EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE, STATUS_OPEN


def _ensure_outcome_taxonomy(db_session):
    taxonomy = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Qualitative Outcome"
    ).first()
    if taxonomy:
        values = db_session.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id
        ).all()
        return {v.code: v for v in values}

    taxonomy = Taxonomy(
        name="Qualitative Outcome",
        description="Outcome values for KPMs",
        is_system=True,
        taxonomy_type="standard"
    )
    db_session.add(taxonomy)
    db_session.flush()

    values = {}
    for code, label in [("GREEN", "Green"), ("YELLOW", "Yellow"), ("RED", "Red")]:
        value = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code=code,
            label=label,
            is_active=True
        )
        db_session.add(value)
        values[code] = value
    db_session.commit()
    return values


def _ensure_exception_closure_taxonomy(db_session):
    taxonomy = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Exception Closure Reason"
    ).first()
    if taxonomy:
        return taxonomy

    taxonomy = Taxonomy(
        name="Exception Closure Reason",
        is_system=True
    )
    db_session.add(taxonomy)
    db_session.flush()

    db_session.add_all([
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="NO_LONGER_EXCEPTION",
            label="No longer an exception",
            sort_order=1
        ),
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="EXCEPTION_OVERRIDDEN",
            label="Exception overridden",
            sort_order=2
        )
    ])
    db_session.commit()
    return taxonomy


def _setup_versioned_cycle(db_session, admin_user, usage_frequency):
    outcome_values = _ensure_outcome_taxonomy(db_session)
    _ensure_exception_closure_taxonomy(db_session)

    model = Model(
        model_name="Backfill Model",
        description="Model for backfill tests",
        owner_id=admin_user.user_id,
        development_type="In-House",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.flush()

    category = KpmCategory(
        code="BF_CAT",
        name="Backfill Category",
        description="Backfill category",
        sort_order=1
    )
    db_session.add(category)
    db_session.flush()

    kpm = Kpm(
        category_id=category.category_id,
        name="Backfill Metric",
        evaluation_type="Quantitative",
        sort_order=1
    )
    db_session.add(kpm)
    db_session.flush()

    plan = MonitoringPlan(
        name="Backfill Plan",
        description="Plan for backfill tests",
        frequency=MonitoringFrequency.QUARTERLY,
        reporting_lead_days=10,
        data_submission_lead_days=5
    )
    db_session.add(plan)
    db_session.flush()
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [model.model_id],
        changed_by_user_id=admin_user.user_id,
        reason="Backfill test setup",
    )

    metric = MonitoringPlanMetric(
        plan_id=plan.plan_id,
        kpm_id=kpm.kpm_id,
        yellow_min=0.8,
        red_min=0.6,
        sort_order=1,
        is_active=True
    )
    db_session.add(metric)
    db_session.flush()

    version = MonitoringPlanVersion(
        plan_id=plan.plan_id,
        version_number=1,
        version_name="v1",
        effective_date=date.today(),
        published_by_user_id=admin_user.user_id,
        published_at=utc_now(),
        is_active=True
    )
    db_session.add(version)
    db_session.flush()

    snapshot = MonitoringPlanMetricSnapshot(
        version_id=version.version_id,
        original_metric_id=metric.metric_id,
        kpm_id=kpm.kpm_id,
        yellow_min=metric.yellow_min,
        red_min=metric.red_min,
        yellow_max=None,
        red_max=None,
        qualitative_guidance=None,
        sort_order=metric.sort_order,
        is_active=True,
        kpm_name=kpm.name,
        kpm_category_name=category.name,
        evaluation_type="Quantitative"
    )
    db_session.add(snapshot)
    db_session.flush()

    period_end = date.today() - timedelta(days=1)
    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=period_end - timedelta(days=90),
        period_end_date=period_end,
        submission_due_date=period_end + timedelta(days=5),
        report_due_date=period_end + timedelta(days=15),
        status="APPROVED",
        plan_version_id=version.version_id
    )
    db_session.add(cycle)
    db_session.commit()

    return {
        "model": model,
        "metric": metric,
        "cycle": cycle,
        "outcomes": outcome_values
    }


def test_backfill_closes_exception_on_improvement(db_session, admin_user, usage_frequency):
    setup = _setup_versioned_cycle(db_session, admin_user, usage_frequency)
    model = setup["model"]
    metric = setup["metric"]
    cycle = setup["cycle"]
    outcomes = setup["outcomes"]

    result = MonitoringResult(
        cycle_id=cycle.cycle_id,
        plan_metric_id=metric.metric_id,
        model_id=model.model_id,
        numeric_value=0.85,
        calculated_outcome="RED",
        outcome_value_id=outcomes["RED"].value_id,
        entered_by_user_id=admin_user.user_id
    )
    db_session.add(result)
    db_session.flush()

    exception = ModelException(
        exception_code="EXC-2025-99999",
        model_id=model.model_id,
        exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
        status=STATUS_OPEN,
        description="Backfill exception test",
        detected_at=utc_now(),
        monitoring_result_id=result.result_id
    )
    db_session.add(exception)
    db_session.commit()

    summary = backfill_monitoring_results_outcomes(db_session, dry_run=False)

    db_session.refresh(result)
    db_session.refresh(exception)

    assert result.calculated_outcome == "GREEN"
    assert result.outcome_value_id == outcomes["GREEN"].value_id
    assert exception.status == "CLOSED"
    assert summary["exceptions_closed"] == 1


def test_backfill_creates_exception_on_degradation(db_session, admin_user, usage_frequency):
    setup = _setup_versioned_cycle(db_session, admin_user, usage_frequency)
    model = setup["model"]
    metric = setup["metric"]
    cycle = setup["cycle"]
    outcomes = setup["outcomes"]

    result = MonitoringResult(
        cycle_id=cycle.cycle_id,
        plan_metric_id=metric.metric_id,
        model_id=model.model_id,
        numeric_value=0.5,
        calculated_outcome="GREEN",
        outcome_value_id=outcomes["GREEN"].value_id,
        entered_by_user_id=admin_user.user_id
    )
    db_session.add(result)
    db_session.commit()

    summary = backfill_monitoring_results_outcomes(db_session, dry_run=False)

    db_session.refresh(result)
    exceptions = db_session.query(ModelException).filter(
        ModelException.monitoring_result_id == result.result_id
    ).all()

    assert result.calculated_outcome == "RED"
    assert result.outcome_value_id == outcomes["RED"].value_id
    assert len(exceptions) == 1
    assert exceptions[0].status == STATUS_OPEN
    assert summary["exceptions_created"] == 1


def test_backfill_assigns_version_to_cycle(db_session, admin_user):
    plan = MonitoringPlan(
        name="Version Backfill Plan",
        description="Plan for version backfill tests",
        frequency=MonitoringFrequency.QUARTERLY,
        reporting_lead_days=10,
        data_submission_lead_days=5
    )
    db_session.add(plan)
    db_session.flush()

    version1 = MonitoringPlanVersion(
        plan_id=plan.plan_id,
        version_number=1,
        version_name="v1",
        effective_date=date(2024, 1, 1),
        published_by_user_id=admin_user.user_id,
        published_at=utc_now(),
        is_active=False
    )
    version2 = MonitoringPlanVersion(
        plan_id=plan.plan_id,
        version_number=2,
        version_name="v2",
        effective_date=date(2024, 6, 1),
        published_by_user_id=admin_user.user_id,
        published_at=utc_now(),
        is_active=True
    )
    db_session.add_all([version1, version2])
    db_session.flush()

    period_end = date(2024, 7, 1)
    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=period_end - timedelta(days=90),
        period_end_date=period_end,
        submission_due_date=period_end + timedelta(days=5),
        report_due_date=period_end + timedelta(days=15),
        status="APPROVED",
        plan_version_id=None
    )
    db_session.add(cycle)
    db_session.commit()

    summary = backfill_monitoring_cycle_versions(db_session, dry_run=False)
    db_session.refresh(cycle)

    assert summary["updated"] == 1
    assert cycle.plan_version_id == version2.version_id
