"""KPI Report API endpoint - computes model risk management metrics."""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, case

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.models import (
    Model,
    User,
    ValidationRequest,
    ValidationRequestModelVersion,
    TaxonomyValue,
    Recommendation,
    DecommissioningRequest,
)
from app.models.model_exception import ModelException
from app.models.region import Region
from app.models.model_region import ModelRegion
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringResult,
)
from app.models.attestation import (
    AttestationCycle,
    AttestationRecord,
)
from app.models.limitation import ModelLimitation
from app.models.residual_risk_map import ResidualRiskMapConfig
from app.models.methodology import Methodology
from app.schemas.kpi_report import (
    KPIDecomposition,
    KPIBreakdown,
    KPIMetric,
    KPIReportResponse,
)

router = APIRouter(prefix="/kpi-report", tags=["reports"])


# Metric definitions from METRICS.json (excluding 4.13, 4.15, 4.26; merging 4.7/4.28)
METRIC_DEFINITIONS = {
    "4.1": {
        "name": "Total Number of Active Models",
        "definition": "Total count of all models currently in use; tracks model inventory size and program scope.",
        "calculation": "Count of models with status = 'Active'",
        "category": "Model Inventory",
        "type": "count",
    },
    "4.2": {
        "name": "% of Models by Inherent Risk Tier",
        "definition": "Proportion of models by risk category (High, Medium, Low, Very Low); supports risk aggregation.",
        "calculation": "(# models per risk tier) / (Total models) × 100%",
        "category": "Model Inventory",
        "type": "breakdown",
    },
    "4.3": {
        "name": "% of Models by Business Line/Region",
        "definition": "Proportion of models allocated to each business line or geographic region; supports risk localization.",
        "calculation": "(# models in Business Line) / (Total models) × 100%",
        "category": "Model Inventory",
        "type": "breakdown",
    },
    "4.4": {
        "name": "% of Vendor/Third-Party Models",
        "definition": "Proportion of models sourced from external vendors; monitors third-party risk exposure.",
        "calculation": "(# vendor models) / (Total models) × 100%",
        "category": "Model Inventory",
        "type": "ratio",
    },
    "4.5": {
        "name": "% of AI/ML Models",
        "definition": "Proportion of models utilizing AI/ML techniques; supports monitoring of emerging risks.",
        "calculation": "(# AI/ML models) / (Total models) × 100%",
        "category": "Model Inventory",
        "type": "ratio",
    },
    "4.6": {
        "name": "% of Models Validated Within Required Cycle",
        "definition": "Percentage of models validated within their mandated review frequency; tracks compliance.",
        "calculation": "(# models validated on time) / (Total models requiring validation) × 100%",
        "category": "Validation",
        "type": "ratio",
    },
    "4.7": {
        "name": "KRI: % of Models Overdue for Validation",
        "definition": "Key risk indicator: proportion of models past their required validation or review date; monitors validation risk.",
        "calculation": "(# models overdue for validation) / (Total models) × 100%",
        "category": "Key Risk Indicators",
        "type": "ratio",
        "is_kri": True,
    },
    "4.8": {
        "name": "Average Time to Complete Model Validation by Risk Tier",
        "definition": "Mean time from model submission to validation approval, broken down by inherent risk tier; tracks process efficiency by risk level.",
        "calculation": "Avg. (Validation approval date – Submission date) per risk tier",
        "category": "Validation",
        "type": "breakdown",
    },
    "4.9": {
        "name": "Number of Models with Interim Approval",
        "definition": "Count of models in interim approval status; flags models in use before full validation.",
        "calculation": "Count of models with approval status = 'Interim Approved'",
        "category": "Validation",
        "type": "count",
    },
    "4.10": {
        "name": "% of Models with Timely Performance Monitoring Submission",
        "definition": "Percentage of models with on-schedule performance monitoring; tracks monitoring compliance.",
        "calculation": "(# timely submissions) / (Total required submissions) × 100%",
        "category": "Monitoring",
        "type": "ratio",
    },
    "4.11": {
        "name": "% of Models Breaching Performance Thresholds",
        "definition": "Percentage of models with red/yellow KPM breaches; highlights performance risk.",
        "calculation": "(# models with RED outcome) / (Total models monitored) × 100%",
        "category": "Monitoring",
        "type": "ratio",
    },
    "4.12": {
        "name": "% of Models with Open Performance Issues",
        "definition": "Proportion of models with unresolved performance-related issues (recommendations from monitoring); monitors ongoing risk.",
        "calculation": "(# models with open monitoring recommendations) / (Total models) × 100%",
        "category": "Monitoring",
        "type": "ratio",
    },
    "4.14": {
        "name": "% of Models with Critical Limitations",
        "definition": "Proportion of models with at least one critical limitation; aggregates model design and data risk.",
        "calculation": "(# models with ≥1 active critical limitation) / (Total models) × 100%",
        "category": "Model Risk",
        "type": "ratio",
    },
    "4.18": {
        "name": "Total Number of Open Recommendations",
        "definition": "Count of all open validation recommendations; aggregates remediation workload.",
        "calculation": "Count of recommendations with closed_at = NULL",
        "category": "Recommendations",
        "type": "count",
    },
    "4.19": {
        "name": "% of Recommendations Past Due",
        "definition": "Proportion of open recommendations past their due date; highlights overdue remediation.",
        "calculation": "(# past due recommendations) / (Total open recommendations) × 100%",
        "category": "Recommendations",
        "type": "ratio",
    },
    "4.20": {
        "name": "Average Time to Close Recommendations",
        "definition": "Mean days to close recommendations; tracks remediation efficiency.",
        "calculation": "Avg. (Date closed – Date issued)",
        "category": "Recommendations",
        "type": "duration",
    },
    "4.21": {
        "name": "% of Models with Open High-Priority Recommendations",
        "definition": "Proportion of models with unresolved high-priority issues; risk aggregation.",
        "calculation": "(# models with open high-priority recs) / (Total models) × 100%",
        "category": "Recommendations",
        "type": "ratio",
    },
    "4.22": {
        "name": "% of Required Attestations Received On Time",
        "definition": "Percentage of required attestations received by deadline; tracks governance adherence.",
        "calculation": "(# on-time attestations) / (Total required attestations) × 100%",
        "category": "Governance",
        "type": "ratio",
    },
    "4.23": {
        "name": "Number of Models Flagged for Decommissioning",
        "definition": "Count of models identified for decommission in the period; tracks model lifecycle.",
        "calculation": "Count of models with decommissioning status = 'PENDING'",
        "category": "Model Lifecycle",
        "type": "count",
    },
    "4.24": {
        "name": "Number of Models Decommissioned in Last 12 Months",
        "definition": "Total models formally decommissioned in past year; tracks inventory turnover.",
        "calculation": "Count with decommission status = 'APPROVED' in last 12 months",
        "category": "Model Lifecycle",
        "type": "count",
    },
    "4.27": {
        "name": "KRI: % of Models with High Residual Risk",
        "definition": "Key risk indicator: proportion of models flagged as high residual risk.",
        "calculation": "(# models with high residual risk) / (Total models with residual risk) × 100%",
        "category": "Key Risk Indicators",
        "type": "ratio",
        "is_kri": True,
    },
    "4.28": {
        "name": "KRI: % of Models with Open Exceptions",
        "definition": "Key risk indicator: proportion of active models with at least one open exception (unmitigated performance, out-of-scope usage, or pre-validation deployment).",
        "calculation": "(# models with open exceptions) / (Total active models) × 100%",
        "category": "Key Risk Indicators",
        "type": "ratio",
        "is_kri": True,
    },
}


def _create_metric(
    metric_id: str,
    count_value: Optional[int] = None,
    ratio_value: Optional[KPIDecomposition] = None,
    duration_value: Optional[float] = None,
    breakdown_value: Optional[List[KPIBreakdown]] = None,
) -> KPIMetric:
    """Helper to create a KPIMetric from definitions."""
    defn = METRIC_DEFINITIONS[metric_id]
    return KPIMetric(
        metric_id=metric_id,
        metric_name=defn["name"],
        category=defn["category"],
        metric_type=defn["type"],
        count_value=count_value,
        ratio_value=ratio_value,
        duration_value=duration_value,
        breakdown_value=breakdown_value,
        definition=defn["definition"],
        calculation=defn["calculation"],
        is_kri=defn.get("is_kri", False),
    )


def _safe_percentage(numerator: int, denominator: int) -> float:
    """Calculate percentage safely, returning 0 if denominator is 0."""
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _compute_metric_4_1(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.1 - Total Number of Active Models"""
    return _create_metric("4.1", count_value=len(active_models))


def _compute_metric_4_2(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.2 - % of Models by Inherent Risk Tier"""
    total = len(active_models)
    breakdown_dict: Dict[str, int] = {}

    for model in active_models:
        tier_name = "Unassigned"
        if model.risk_tier:
            tier_name = model.risk_tier.label or model.risk_tier.code
        breakdown_dict[tier_name] = breakdown_dict.get(tier_name, 0) + 1

    breakdown = [
        KPIBreakdown(
            category=tier,
            count=count,
            percentage=_safe_percentage(count, total)
        )
        for tier, count in sorted(breakdown_dict.items())
    ]

    return _create_metric("4.2", breakdown_value=breakdown)


def _compute_metric_4_3(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.3 - % of Models by Business Line (using owner's LOB rolled up to LOB4)"""
    total = len(active_models)
    breakdown_dict: Dict[str, int] = {}

    for model in active_models:
        bl_name = model.business_line_name or "Unassigned"
        breakdown_dict[bl_name] = breakdown_dict.get(bl_name, 0) + 1

    breakdown = [
        KPIBreakdown(
            category=bl,
            count=count,
            percentage=_safe_percentage(count, total)
        )
        for bl, count in sorted(breakdown_dict.items())
    ]

    return _create_metric("4.3", breakdown_value=breakdown)


def _compute_metric_4_4(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.4 - % of Vendor/Third-Party Models"""
    total = len(active_models)
    third_party_models = [m for m in active_models if m.development_type == "Third-Party"]
    third_party_ids = [m.model_id for m in third_party_models]

    return _create_metric("4.4", ratio_value=KPIDecomposition(
        numerator=len(third_party_models),
        denominator=total,
        percentage=_safe_percentage(len(third_party_models), total),
        numerator_label="third-party",
        denominator_label="total active models",
        numerator_model_ids=third_party_ids if third_party_ids else None
    ))


def _compute_metric_4_5(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.5 - % of AI/ML Models"""
    total = len(active_models)
    aiml_models = [m for m in active_models if m.is_aiml is True]
    aiml_ids = [m.model_id for m in aiml_models]

    return _create_metric("4.5", ratio_value=KPIDecomposition(
        numerator=len(aiml_models),
        denominator=total,
        percentage=_safe_percentage(len(aiml_models), total),
        numerator_label="AI/ML",
        denominator_label="total active models",
        numerator_model_ids=aiml_ids if aiml_ids else None
    ))


def _compute_validation_metrics(
    db: Session,
    active_models: List[Model]
) -> Dict[str, Any]:
    """Compute validation-related metrics (4.6, 4.7, 4.8, 4.9)."""
    from app.api.validation_workflow import calculate_model_revalidation_status
    from app.core.model_approval_status import compute_model_approval_status, ApprovalStatus

    total_models = len(active_models)
    on_time_count = 0
    overdue_count = 0
    interim_count = 0
    on_time_model_ids: List[int] = []
    overdue_model_ids: List[int] = []

    for model in active_models:
        # Revalidation status for 4.6 and 4.7
        reval_status = calculate_model_revalidation_status(model, db)
        status_str = reval_status.get("status", "")

        overdue_statuses = [
            "Submission Overdue",
            "Validation Overdue",
            "Revalidation Overdue",
            "Should Create Request",
            "INTERIM Expired",
        ]

        if any(s in status_str for s in overdue_statuses):
            overdue_count += 1
            overdue_model_ids.append(model.model_id)
        elif "On Track" in status_str or status_str == "Approved":
            on_time_count += 1
            on_time_model_ids.append(model.model_id)

        # Approval status for 4.9
        approval_status, _ = compute_model_approval_status(model, db)
        if approval_status == ApprovalStatus.INTERIM_APPROVED:
            interim_count += 1

    # Metric 4.8 - Average time to complete validation BY RISK TIER
    completed_validations = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.validated_risk_tier)
    ).filter(
        ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED"),
        ValidationRequest.completion_date.isnot(None),
        ValidationRequest.created_at.isnot(None),
    ).all()

    # Group by risk tier
    tier_data: Dict[str, List[int]] = {}  # tier label -> list of days
    for vr in completed_validations:
        if vr.completion_date and vr.created_at:
            tier_name = "Unassigned"
            if vr.validated_risk_tier:
                tier_name = vr.validated_risk_tier.label or vr.validated_risk_tier.code or "Unassigned"
            if tier_name not in tier_data:
                tier_data[tier_name] = []
            delta = (vr.completion_date.date() - vr.created_at.date()).days
            tier_data[tier_name].append(delta)

    total_count = sum(len(days) for days in tier_data.values())
    breakdown_4_8 = [
        KPIBreakdown(
            category=tier,
            count=len(days),
            percentage=_safe_percentage(len(days), total_count),
            avg_days=round(sum(days) / len(days), 1) if days else None
        )
        for tier, days in sorted(tier_data.items())
    ]

    return {
        "4.6": _create_metric("4.6", ratio_value=KPIDecomposition(
            numerator=on_time_count,
            denominator=total_models,
            percentage=_safe_percentage(on_time_count, total_models),
            numerator_label="on time",
            denominator_label="total active models",
            numerator_model_ids=on_time_model_ids if on_time_model_ids else None
        )),
        "4.7": _create_metric("4.7", ratio_value=KPIDecomposition(
            numerator=overdue_count,
            denominator=total_models,
            percentage=_safe_percentage(overdue_count, total_models),
            numerator_label="overdue",
            denominator_label="total active models",
            numerator_model_ids=overdue_model_ids if overdue_model_ids else None
        )),
        "4.8": _create_metric("4.8", breakdown_value=breakdown_4_8 if breakdown_4_8 else None),
        "4.9": _create_metric("4.9", count_value=interim_count),
    }


def _compute_monitoring_metrics(
    db: Session,
    active_models: List[Model]
) -> Dict[str, Any]:
    """Compute monitoring-related metrics (4.10, 4.11, 4.12)."""
    total_models = len(active_models)
    model_ids = [m.model_id for m in active_models]

    # Get most recent approved cycle for each monitored plan
    # For timely submission (4.10), check cycles where status = APPROVED
    approved_cycles = db.query(MonitoringCycle).filter(
        MonitoringCycle.status == "APPROVED"
    ).all()

    timely_count = 0
    total_submissions = 0
    for cycle in approved_cycles:
        total_submissions += 1
        # Check if submitted on time
        if cycle.submitted_at and cycle.submission_due_date:
            if cycle.submitted_at.date() <= cycle.submission_due_date:
                timely_count += 1

    # For threshold breaches (4.11), get models with RED outcomes in their latest cycle
    # This requires checking the most recent cycle's results per model
    models_with_red = set()
    models_monitored = set()

    # Get distinct model_ids from monitoring plans using the association table
    from app.models.monitoring import monitoring_plan_models, MonitoringPlan
    monitored_model_ids = db.query(monitoring_plan_models.c.model_id).distinct().all()
    monitored_model_ids = [mid[0] for mid in monitored_model_ids if mid[0] in model_ids]

    for model_id in monitored_model_ids:
        models_monitored.add(model_id)
        # Get the latest monitoring result for this model
        # A model can be in multiple plans, get latest cycle across all plans containing this model
        latest_result = db.query(MonitoringResult).join(
            MonitoringCycle
        ).join(
            MonitoringPlan
        ).join(
            monitoring_plan_models,
            and_(
                monitoring_plan_models.c.plan_id == MonitoringPlan.plan_id,
                monitoring_plan_models.c.model_id == model_id
            )
        ).order_by(MonitoringCycle.period_end_date.desc()).first()

        if latest_result and latest_result.calculated_outcome == "RED":
            models_with_red.add(model_id)

    # For open performance issues (4.12), get models with open recs from monitoring
    models_with_monitoring_recs_query = db.query(Recommendation.model_id).filter(
        Recommendation.model_id.in_(model_ids),
        Recommendation.monitoring_cycle_id.isnot(None),
        Recommendation.closed_at.is_(None)
    ).distinct().all()
    models_with_monitoring_recs_ids = [m[0] for m in models_with_monitoring_recs_query]

    return {
        "4.10": _create_metric("4.10", ratio_value=KPIDecomposition(
            numerator=timely_count,
            denominator=total_submissions,
            percentage=_safe_percentage(timely_count, total_submissions),
            numerator_label="timely submissions",
            denominator_label="total required submissions"
        )),
        "4.11": _create_metric("4.11", ratio_value=KPIDecomposition(
            numerator=len(models_with_red),
            denominator=len(models_monitored),
            percentage=_safe_percentage(len(models_with_red), len(models_monitored)),
            numerator_label="with RED breaches",
            denominator_label="monitored models",
            numerator_model_ids=list(models_with_red) if models_with_red else None
        )),
        "4.12": _create_metric("4.12", ratio_value=KPIDecomposition(
            numerator=len(models_with_monitoring_recs_ids),
            denominator=total_models,
            percentage=_safe_percentage(len(models_with_monitoring_recs_ids), total_models),
            numerator_label="with open monitoring issues",
            denominator_label="total active models",
            numerator_model_ids=models_with_monitoring_recs_ids if models_with_monitoring_recs_ids else None
        )),
    }


def _compute_metric_4_14(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.14 - % of Models with Critical Limitations"""
    total = len(active_models)
    model_ids = [m.model_id for m in active_models]

    models_with_critical_query = db.query(ModelLimitation.model_id).filter(
        ModelLimitation.model_id.in_(model_ids),
        ModelLimitation.significance == "Critical",
        ModelLimitation.is_retired == False
    ).distinct().all()
    models_with_critical_ids = [m[0] for m in models_with_critical_query]

    return _create_metric("4.14", ratio_value=KPIDecomposition(
        numerator=len(models_with_critical_ids),
        denominator=total,
        percentage=_safe_percentage(len(models_with_critical_ids), total),
        numerator_label="with critical limitations",
        denominator_label="total active models",
        numerator_model_ids=models_with_critical_ids if models_with_critical_ids else None
    ))


def _compute_recommendation_metrics(
    db: Session,
    active_models: List[Model]
) -> Dict[str, Any]:
    """Compute recommendation-related metrics (4.18, 4.19, 4.20, 4.21)."""
    total_models = len(active_models)
    model_ids = [m.model_id for m in active_models]
    today = date.today()

    # 4.18 - Total open recommendations
    open_recs_count = db.query(Recommendation).filter(
        Recommendation.closed_at.is_(None)
    ).count()

    # 4.19 - % of recommendations past due
    past_due_recs = db.query(Recommendation).filter(
        Recommendation.closed_at.is_(None),
        Recommendation.current_target_date < today
    ).count()

    # 4.20 - Average time to close recommendations
    closed_recs = db.query(Recommendation).filter(
        Recommendation.closed_at.isnot(None),
        Recommendation.created_at.isnot(None)
    ).all()

    avg_close_days = None
    if closed_recs:
        total_days = 0
        count = 0
        for rec in closed_recs:
            if rec.closed_at and rec.created_at:
                delta = rec.closed_at - rec.created_at
                total_days += delta.days
                count += 1
        if count > 0:
            avg_close_days = round(total_days / count, 1)

    # 4.21 - % of models with open high-priority recommendations
    # Get high priority taxonomy value
    high_priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "HIGH"
    ).first()

    models_with_high_priority_ids: List[int] = []
    if high_priority:
        models_with_high_priority_query = db.query(Recommendation.model_id).filter(
            Recommendation.model_id.in_(model_ids),
            Recommendation.closed_at.is_(None),
            Recommendation.priority_id == high_priority.value_id
        ).distinct().all()
        models_with_high_priority_ids = [m[0] for m in models_with_high_priority_query]

    return {
        "4.18": _create_metric("4.18", count_value=open_recs_count),
        "4.19": _create_metric("4.19", ratio_value=KPIDecomposition(
            numerator=past_due_recs,
            denominator=open_recs_count,
            percentage=_safe_percentage(past_due_recs, open_recs_count),
            numerator_label="past due",
            denominator_label="open recommendations"
        )),
        "4.20": _create_metric("4.20", duration_value=avg_close_days),
        "4.21": _create_metric("4.21", ratio_value=KPIDecomposition(
            numerator=len(models_with_high_priority_ids),
            denominator=total_models,
            percentage=_safe_percentage(len(models_with_high_priority_ids), total_models),
            numerator_label="with open high-priority recs",
            denominator_label="total active models",
            numerator_model_ids=models_with_high_priority_ids if models_with_high_priority_ids else None
        )),
    }


def _compute_metric_4_22(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.22 - % of Required Attestations Received On Time"""
    # Get the most recently closed attestation cycle
    latest_closed_cycle = db.query(AttestationCycle).filter(
        AttestationCycle.status == "CLOSED"
    ).order_by(AttestationCycle.period_end_date.desc()).first()

    if not latest_closed_cycle:
        return _create_metric("4.22", ratio_value=KPIDecomposition(
            numerator=0,
            denominator=0,
            percentage=0.0,
            numerator_label="on time",
            denominator_label="required attestations"
        ))

    # Get all attestation records for this cycle
    records = db.query(AttestationRecord).filter(
        AttestationRecord.cycle_id == latest_closed_cycle.cycle_id
    ).all()

    total_required = len(records)
    on_time_count = 0

    for record in records:
        if record.attested_at and record.due_date:
            if record.attested_at.date() <= record.due_date:
                on_time_count += 1

    return _create_metric("4.22", ratio_value=KPIDecomposition(
        numerator=on_time_count,
        denominator=total_required,
        percentage=_safe_percentage(on_time_count, total_required),
        numerator_label="on time",
        denominator_label="required attestations"
    ))


def _compute_decommissioning_metrics(db: Session) -> Dict[str, Any]:
    """Compute decommissioning metrics (4.23, 4.24)."""
    # 4.23 - Models flagged for decommissioning (PENDING status)
    pending_count = db.query(DecommissioningRequest).filter(
        DecommissioningRequest.status == "PENDING"
    ).count()

    # 4.24 - Models decommissioned in last 12 months
    one_year_ago = utc_now() - timedelta(days=365)

    decommissioned_count = db.query(DecommissioningRequest).filter(
        DecommissioningRequest.status == "APPROVED",
        DecommissioningRequest.final_reviewed_at >= one_year_ago
    ).count()

    return {
        "4.23": _create_metric("4.23", count_value=pending_count),
        "4.24": _create_metric("4.24", count_value=decommissioned_count),
    }


def _compute_metric_4_27(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.27 - KRI: % of Models with High Residual Risk"""
    # Get the active residual risk map configuration
    config = db.query(ResidualRiskMapConfig).filter(
        ResidualRiskMapConfig.is_active == True
    ).first()

    if not config or not config.matrix_config:
        # No config means we can't compute residual risk
        return _create_metric("4.27", ratio_value=KPIDecomposition(
            numerator=0,
            denominator=0,
            percentage=0.0,
            numerator_label="high residual risk",
            denominator_label="models with residual risk assessed"
        ))

    matrix = config.matrix_config.get("matrix", {})

    # Mapping for risk tier labels to matrix keys
    tier_mapping = {
        "High Inherent Risk": "High",
        "Medium Inherent Risk": "Medium",
        "Low Inherent Risk": "Low",
        "Very Low Inherent Risk": "Very Low",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
        "Very Low": "Very Low",
    }

    models_with_residual = 0
    high_residual_count = 0
    high_residual_model_ids: List[int] = []

    for model in active_models:
        # Get the model's latest approved validation
        latest_approved = db.query(ValidationRequest).join(
            ValidationRequestModelVersion
        ).filter(
            ValidationRequestModelVersion.model_id == model.model_id,
            ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED")
        ).order_by(
            ValidationRequest.completion_date.desc().nullslast()
        ).first()

        if latest_approved and latest_approved.validated_risk_tier and latest_approved.scorecard_overall_rating:
            # Get the risk tier label and normalize it
            risk_tier_label = latest_approved.validated_risk_tier.label
            normalized_tier = tier_mapping.get(risk_tier_label)

            if normalized_tier:
                scorecard_outcome = latest_approved.scorecard_overall_rating
                tier_row = matrix.get(normalized_tier, {})
                residual_risk = tier_row.get(scorecard_outcome)

                if residual_risk:
                    models_with_residual += 1
                    if residual_risk == "High":
                        high_residual_count += 1
                        high_residual_model_ids.append(model.model_id)

    return _create_metric("4.27", ratio_value=KPIDecomposition(
        numerator=high_residual_count,
        denominator=models_with_residual,
        percentage=_safe_percentage(high_residual_count, models_with_residual),
        numerator_label="high residual risk",
        denominator_label="models with residual risk assessed",
        numerator_model_ids=high_residual_model_ids if high_residual_model_ids else None
    ))


def _compute_metric_4_28(db: Session, active_models: List[Model]) -> KPIMetric:
    """4.28 - KRI: % of Models with Open Exceptions"""
    total = len(active_models)
    model_ids = [m.model_id for m in active_models]

    # Get distinct model_ids that have open exceptions (status = OPEN or ACKNOWLEDGED)
    models_with_open_exceptions_query = db.query(ModelException.model_id).filter(
        ModelException.model_id.in_(model_ids),
        ModelException.status.in_(["OPEN", "ACKNOWLEDGED"])
    ).distinct().all()
    models_with_open_exceptions_ids = [m[0] for m in models_with_open_exceptions_query]

    return _create_metric("4.28", ratio_value=KPIDecomposition(
        numerator=len(models_with_open_exceptions_ids),
        denominator=total,
        percentage=_safe_percentage(len(models_with_open_exceptions_ids), total),
        numerator_label="with open exceptions",
        denominator_label="total active models",
        numerator_model_ids=models_with_open_exceptions_ids if models_with_open_exceptions_ids else None
    ))


@router.get("/", response_model=KPIReportResponse)
def get_kpi_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    region_id: Optional[int] = Query(None, description="Filter metrics by region (models deployed to this region)"),
):
    """
    Generate the KPI Report with all model risk management metrics.

    This endpoint computes 21 metrics from METRICS.json, providing:
    - Count metrics (simple integer counts)
    - Ratio metrics (with numerator/denominator decomposition)
    - Duration metrics (average days)
    - Breakdown metrics (distribution by category)

    Two metrics are flagged as Key Risk Indicators (KRI): 4.7 and 4.27.

    Optionally filter by region_id to scope metrics to models deployed in that region.
    """
    # Handle region filtering
    region_name = "All Regions"
    region_model_subquery = None

    if region_id is not None:
        # Validate region exists
        region = db.query(Region).filter(Region.region_id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        region_name = region.name

        # Create subquery for model IDs deployed to this region
        region_model_subquery = db.query(ModelRegion.model_id).filter(
            ModelRegion.region_id == region_id
        ).distinct().scalar_subquery()

    # Get all active models with necessary relationships
    active_models_query = db.query(Model).options(
        joinedload(Model.risk_tier),
        joinedload(Model.methodology).joinedload(Methodology.category),
        joinedload(Model.owner),
    ).filter(
        Model.status == "Active"
    )

    # Apply region filter if specified
    if region_model_subquery is not None:
        active_models_query = active_models_query.filter(
            Model.model_id.in_(region_model_subquery)
        )

    active_models = active_models_query.all()

    metrics: List[KPIMetric] = []

    # Model Inventory metrics
    metrics.append(_compute_metric_4_1(db, active_models))
    metrics.append(_compute_metric_4_2(db, active_models))
    metrics.append(_compute_metric_4_3(db, active_models))
    metrics.append(_compute_metric_4_4(db, active_models))
    metrics.append(_compute_metric_4_5(db, active_models))

    # Validation metrics (4.6, 4.7, 4.8, 4.9)
    validation_metrics = _compute_validation_metrics(db, active_models)
    metrics.extend([
        validation_metrics["4.6"],
        validation_metrics["4.7"],
        validation_metrics["4.8"],
        validation_metrics["4.9"],
    ])

    # Monitoring metrics (4.10, 4.11, 4.12)
    monitoring_metrics = _compute_monitoring_metrics(db, active_models)
    metrics.extend([
        monitoring_metrics["4.10"],
        monitoring_metrics["4.11"],
        monitoring_metrics["4.12"],
    ])

    # Model Risk metric (4.14)
    metrics.append(_compute_metric_4_14(db, active_models))

    # Recommendation metrics (4.18, 4.19, 4.20, 4.21)
    rec_metrics = _compute_recommendation_metrics(db, active_models)
    metrics.extend([
        rec_metrics["4.18"],
        rec_metrics["4.19"],
        rec_metrics["4.20"],
        rec_metrics["4.21"],
    ])

    # Governance metric (4.22)
    metrics.append(_compute_metric_4_22(db, active_models))

    # Model Lifecycle metrics (4.23, 4.24)
    decom_metrics = _compute_decommissioning_metrics(db)
    metrics.extend([
        decom_metrics["4.23"],
        decom_metrics["4.24"],
    ])

    # Key Risk Indicator (4.27)
    metrics.append(_compute_metric_4_27(db, active_models))

    # Key Risk Indicator (4.28) - Models with Open Exceptions
    metrics.append(_compute_metric_4_28(db, active_models))

    return KPIReportResponse(
        report_generated_at=utc_now(),
        as_of_date=date.today(),
        metrics=metrics,
        total_active_models=len(active_models),
        region_id=region_id,
        region_name=region_name,
    )
