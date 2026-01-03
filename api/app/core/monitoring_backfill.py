"""Backfill utilities for monitoring result outcomes."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.time import utc_now
from app.core.exception_detection import (
    close_type1_exception_for_result,
    ensure_type1_exception_for_result,
)
from app.models.audit_log import AuditLog
from app.models.kpm import Kpm
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringPlanMetric,
    MonitoringPlanMetricSnapshot,
    MonitoringPlanVersion,
    MonitoringResult,
)
from app.api.monitoring import calculate_outcome, resolve_outcome_value_id


def backfill_monitoring_results_outcomes(
    db: Session,
    dry_run: bool = True,
    user_id: Optional[int] = None,
    cycle_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> dict:
    """Recalculate monitoring result outcomes using versioned thresholds."""
    summary = {
        "processed": 0,
        "updated": 0,
        "skipped_no_snapshot": 0,
        "exceptions_closed": 0,
        "exceptions_created": 0,
        "dry_run": dry_run,
    }

    query = db.query(MonitoringResult).join(
        MonitoringCycle
    ).join(
        MonitoringPlanMetric, MonitoringPlanMetric.metric_id == MonitoringResult.plan_metric_id
    ).join(
        Kpm, Kpm.kpm_id == MonitoringPlanMetric.kpm_id
    ).options(
        joinedload(MonitoringResult.cycle),
        joinedload(MonitoringResult.plan_metric).joinedload(MonitoringPlanMetric.kpm)
    ).filter(
        MonitoringResult.numeric_value.isnot(None),
        MonitoringCycle.plan_version_id.isnot(None),
        Kpm.evaluation_type == "Quantitative",
    )

    if cycle_id:
        query = query.filter(MonitoringResult.cycle_id == cycle_id)

    if limit:
        query = query.limit(limit)

    results = query.all()
    if not results:
        return summary

    version_ids = {r.cycle.plan_version_id for r in results if r.cycle and r.cycle.plan_version_id}
    metric_ids = {r.plan_metric_id for r in results}

    snapshots = db.query(MonitoringPlanMetricSnapshot).filter(
        MonitoringPlanMetricSnapshot.version_id.in_(version_ids),
        MonitoringPlanMetricSnapshot.original_metric_id.in_(metric_ids)
    ).all()
    snapshot_map = {
        (s.version_id, s.original_metric_id): s
        for s in snapshots
        if s.original_metric_id is not None
    }

    cycle_update_counts: dict[int, int] = {}

    for result in results:
        summary["processed"] += 1
        cycle = result.cycle
        if not cycle or not cycle.plan_version_id:
            summary["skipped_no_snapshot"] += 1
            continue

        snapshot = snapshot_map.get((cycle.plan_version_id, result.plan_metric_id))
        if not snapshot:
            summary["skipped_no_snapshot"] += 1
            continue

        if result.numeric_value is None:
            continue
        new_outcome = calculate_outcome(result.numeric_value, snapshot)
        old_outcome = result.calculated_outcome

        if new_outcome == old_outcome:
            continue

        summary["updated"] += 1
        cycle_update_counts[cycle.cycle_id] = cycle_update_counts.get(cycle.cycle_id, 0) + 1

        if dry_run:
            continue

        result.calculated_outcome = new_outcome
        result.outcome_value_id = resolve_outcome_value_id(db, new_outcome)
        result.updated_at = utc_now()

        if old_outcome == "RED" and new_outcome in ("GREEN", "YELLOW"):
            summary["exceptions_closed"] += close_type1_exception_for_result(db, result, new_outcome)
        elif new_outcome == "RED" and old_outcome != "RED":
            exception = ensure_type1_exception_for_result(db, result)
            if exception:
                summary["exceptions_created"] += 1

    if not dry_run:
        if user_id:
            for cycle_id_key, count in cycle_update_counts.items():
                db.add(AuditLog(
                    entity_type="MonitoringCycle",
                    entity_id=cycle_id_key,
                    action="BACKFILL_OUTCOMES",
                    user_id=user_id,
                    changes={"updated_results": count}
                ))
        db.commit()

    return summary


def backfill_monitoring_cycle_versions(
    db: Session,
    dry_run: bool = True,
    user_id: Optional[int] = None,
    plan_id: Optional[int] = None,
    cycle_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> dict:
    """Assign plan versions to cycles missing plan_version_id."""
    summary = {
        "processed": 0,
        "updated": 0,
        "skipped_no_versions": 0,
        "dry_run": dry_run,
    }

    query = db.query(MonitoringCycle).filter(MonitoringCycle.plan_version_id.is_(None))
    if plan_id:
        query = query.filter(MonitoringCycle.plan_id == plan_id)
    if cycle_id:
        query = query.filter(MonitoringCycle.cycle_id == cycle_id)
    if limit:
        query = query.limit(limit)

    cycles = query.all()
    if not cycles:
        return summary

    plan_ids = {cycle.plan_id for cycle in cycles}
    versions = db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id.in_(plan_ids)
    ).order_by(
        MonitoringPlanVersion.effective_date.asc(),
        MonitoringPlanVersion.version_number.asc()
    ).all()

    versions_by_plan: dict[int, list[MonitoringPlanVersion]] = {}
    for version in versions:
        versions_by_plan.setdefault(version.plan_id, []).append(version)

    for cycle in cycles:
        summary["processed"] += 1
        plan_versions = versions_by_plan.get(cycle.plan_id, [])
        if not plan_versions:
            summary["skipped_no_versions"] += 1
            continue

        selected_version = None
        for version in reversed(plan_versions):
            if version.effective_date and version.effective_date <= cycle.period_end_date:
                selected_version = version
                break

        if selected_version is None:
            selected_version = plan_versions[0]

        summary["updated"] += 1

        if dry_run:
            continue

        cycle.plan_version_id = selected_version.version_id
        cycle.version_locked_at = cycle.version_locked_at or cycle.created_at or utc_now()
        if user_id:
            cycle.version_locked_by_user_id = user_id
        cycle.updated_at = utc_now()

        if user_id:
            db.add(AuditLog(
                entity_type="MonitoringCycle",
                entity_id=cycle.cycle_id,
                action="BACKFILL_VERSION",
                user_id=user_id,
                changes={
                    "plan_version_id": selected_version.version_id,
                    "version_number": selected_version.version_number,
                }
            ))

    if not dry_run:
        db.commit()

    return summary
