"""My Portfolio Report - Consolidated dashboard for model owners."""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from fpdf import FPDF

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.core.monitoring_constants import OUTCOME_YELLOW, OUTCOME_RED
from app.core.model_approval_status import compute_model_approval_status, get_status_label, ApprovalStatus
from app.api.validation_workflow import calculate_model_revalidation_status
from app.models.user import User
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.taxonomy import TaxonomyValue
from app.models.recommendation import Recommendation
from app.models.attestation import AttestationRecord, AttestationCycle
from app.models.validation import ValidationRequest, ValidationRequestModelVersion
from app.models.monitoring import (
    MonitoringResult,
    MonitoringCycle,
    MonitoringCycleStatus,
    MonitoringPlanMetric,
    monitoring_plan_models,
)
from app.models.model_exception import ModelException
from app.models.team import Team
from app.core.team_utils import get_models_team_map
from app.schemas.my_portfolio import (
    MyPortfolioResponse,
    PortfolioSummary,
    ActionItem,
    MonitoringAlert,
    ExceptionItem,
    CalendarItem,
    PortfolioModel,
)

router = APIRouter()


def get_owned_model_ids(db: Session, user: User) -> List[int]:
    """Get IDs of models the user owns (primary, shared, or delegated with can_submit_changes)."""
    # Primary owner
    primary_ids = db.query(Model.model_id).filter(
        Model.owner_id == user.user_id
    ).all()

    # Shared owner
    shared_ids = db.query(Model.model_id).filter(
        Model.shared_owner_id == user.user_id
    ).all()

    # Delegate with can_submit_changes permission
    delegate_ids = db.query(ModelDelegate.model_id).filter(
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.can_submit_changes == True,
        ModelDelegate.revoked_at.is_(None)
    ).all()

    # Combine and dedupe
    all_ids = set()
    for (model_id,) in primary_ids:
        all_ids.add(model_id)
    for (model_id,) in shared_ids:
        all_ids.add(model_id)
    for (model_id,) in delegate_ids:
        all_ids.add(model_id)

    return list(all_ids)


def get_ownership_type(model: Model, user: User, db: Session) -> str:
    """Determine how the user owns this model."""
    if model.owner_id == user.user_id:
        return "primary"
    if model.shared_owner_id == user.user_id:
        return "shared"
    # Check delegation
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model.model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.can_submit_changes == True,
        ModelDelegate.revoked_at.is_(None)
    ).first()
    if delegate:
        return "delegate"
    return "unknown"


def calculate_urgency(due_date: Optional[date], grace_end: Optional[date] = None) -> tuple[str, Optional[int]]:
    """Calculate urgency level and days until due."""
    if not due_date:
        return "unknown", None

    today = date.today()
    days_until_due = (due_date - today).days

    if days_until_due < 0:
        if grace_end and today <= grace_end:
            return "in_grace_period", days_until_due
        return "overdue", days_until_due
    elif days_until_due <= 30:
        return "due_soon", days_until_due
    else:
        return "upcoming", days_until_due


@router.get("/reports/my-portfolio", response_model=MyPortfolioResponse)
def get_my_portfolio(
    team_id: Optional[int] = Query(None, description="Filter portfolio by team ID (0 = Unassigned)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get consolidated portfolio report for the current user.

    Shows:
    - Summary statistics (models, action items, compliance, alerts)
    - Action items requiring attention (attestations, recommendations, validation submissions)
    - Monitoring alerts (yellow/red results from recent cycles)
    - Calendar items for deadline tracking
    - Full model portfolio with status details
    """
    today = date.today()
    ninety_days_ago = today - timedelta(days=90)
    ninety_days_out = today + timedelta(days=90)

    # Get models owned by this user (Option C: primary + shared + delegate with can_submit_changes)
    owned_model_ids = get_owned_model_ids(db, current_user)

    team_name = "All Teams"
    if team_id is not None and owned_model_ids:
        model_team_map = get_models_team_map(db, owned_model_ids)
        if team_id == 0:
            owned_model_ids = [
                model_id for model_id in owned_model_ids
                if model_team_map.get(model_id) is None
            ]
            team_name = "Unassigned"
        else:
            owned_model_ids = [
                model_id for model_id in owned_model_ids
                if (team_entry := model_team_map.get(model_id))
                and team_entry.get("team_id") == team_id
            ]
            team = db.query(Team).filter(Team.team_id == team_id).first()
            team_name = team.name if team else f"Team {team_id}"

    if not owned_model_ids:
        # Return empty portfolio
        return MyPortfolioResponse(
            report_generated_at=utc_now(),
            as_of_date=today,
            team_id=team_id,
            team_name=team_name,
            summary=PortfolioSummary(
                total_models=0,
                action_items_count=0,
                overdue_count=0,
                compliant_percentage=100.0,
                models_compliant=0,
                models_non_compliant=0,
                yellow_alerts=0,
                red_alerts=0,
                open_exceptions_count=0,
            ),
            action_items=[],
            monitoring_alerts=[],
            open_exceptions=[],
            calendar_items=[],
            models=[],
        )

    # Load owned models with relationships
    owned_models = db.query(Model).options(
        joinedload(Model.risk_tier),
    ).filter(Model.model_id.in_(owned_model_ids)).all()

    # --- ATTESTATIONS ---
    attestation_items: List[ActionItem] = []
    attestation_calendar: List[CalendarItem] = []

    attestations = db.query(AttestationRecord).join(
        AttestationCycle
    ).options(
        joinedload(AttestationRecord.model),
        joinedload(AttestationRecord.cycle),
    ).filter(
        AttestationRecord.model_id.in_(owned_model_ids),
        AttestationRecord.status.in_(["pending", "rejected"]),
        AttestationCycle.status.in_(["PENDING", "OPEN"]),
    ).all()

    for att in attestations:
        model = att.model
        if not model:
            continue

        due_date = att.due_date
        urgency, days_until_due = calculate_urgency(due_date)

        action_desc = "Resubmit attestation" if att.status == "rejected" else "Submit attestation"

        attestation_items.append(ActionItem(
            type="attestation",
            urgency=urgency,
            model_id=model.model_id,
            model_name=model.model_name,
            item_id=att.attestation_id,
            item_code=None,
            title=f"Attestation - {model.model_name}",
            action_description=action_desc,
            due_date=due_date,
            days_until_due=days_until_due,
            link=f"/attestations"
        ))

        if due_date:
            attestation_calendar.append(CalendarItem(
                due_date=due_date,
                type="attestation",
                model_id=model.model_id,
                model_name=model.model_name,
                item_id=att.attestation_id,
                item_code=None,
                title=f"Attestation Due",
                is_overdue=(urgency == "overdue")
            ))

    # --- RECOMMENDATIONS ---
    recommendation_items: List[ActionItem] = []
    recommendation_calendar: List[CalendarItem] = []

    # Get recommendations assigned to the user where action is needed
    developer_action_statuses = [
        "REC_PENDING_RESPONSE",
        "REC_PENDING_ACKNOWLEDGEMENT",
        "REC_OPEN",
        "REC_REWORK_REQUIRED",
        "REC_PENDING_ACTION_PLAN"
    ]

    recommendations = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.current_status),
    ).join(
        TaxonomyValue, Recommendation.current_status_id == TaxonomyValue.value_id
    ).filter(
        Recommendation.model_id.in_(owned_model_ids),
        TaxonomyValue.code.in_(developer_action_statuses)
    ).all()

    for rec in recommendations:
        model = rec.model
        if not model:
            continue

        due_date = rec.current_target_date
        urgency, days_until_due = calculate_urgency(due_date)

        # Determine action based on status
        status_code = rec.current_status.code if rec.current_status else ""
        if status_code == "REC_PENDING_RESPONSE":
            action_desc = "Submit action plan or rebuttal"
        elif status_code == "REC_PENDING_ACKNOWLEDGEMENT":
            action_desc = "Acknowledge recommendation"
        elif status_code == "REC_REWORK_REQUIRED":
            action_desc = "Address feedback and resubmit"
        elif status_code == "REC_PENDING_ACTION_PLAN":
            action_desc = "Submit action plan"
        else:
            action_desc = "Review recommendation"

        rec_code = rec.recommendation_code or f"REC-{rec.recommendation_id}"

        recommendation_items.append(ActionItem(
            type="recommendation",
            urgency=urgency,
            model_id=model.model_id,
            model_name=model.model_name,
            item_id=rec.recommendation_id,
            item_code=rec_code,
            title=f"Recommendation {rec_code}",
            action_description=action_desc,
            due_date=due_date,
            days_until_due=days_until_due,
            link=f"/recommendations/{rec.recommendation_id}"
        ))

        if due_date:
            recommendation_calendar.append(CalendarItem(
                due_date=due_date,
                type="recommendation",
                model_id=model.model_id,
                model_name=model.model_name,
                item_id=rec.recommendation_id,
                item_code=rec_code,
                title=f"Recommendation Due",
                is_overdue=(urgency == "overdue")
            ))

    # --- VALIDATION SUBMISSIONS ---
    validation_items: List[ActionItem] = []
    validation_calendar: List[CalendarItem] = []

    # Get pending validation submissions for owned models
    pending_requests = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).join(
        Model
    ).filter(
        Model.model_id.in_(owned_model_ids),
        ValidationRequest.validation_type.has(TaxonomyValue.code == "COMPREHENSIVE"),
        ValidationRequest.submission_received_date.is_(None),
        ValidationRequest.current_status.has(TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
    ).all()

    for req in pending_requests:
        # Get model from request
        if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
            model_assoc = req.model_versions_assoc[0]
            model = model_assoc.model
        else:
            continue

        due_date = req.submission_due_date
        grace_end = req.submission_grace_period_end
        urgency, days_until_due = calculate_urgency(due_date, grace_end)

        validation_items.append(ActionItem(
            type="validation_submission",
            urgency=urgency,
            model_id=model.model_id,
            model_name=model.model_name,
            item_id=req.request_id,
            item_code=None,
            title=f"Validation Submission - {model.model_name}",
            action_description="Submit revalidation documentation",
            due_date=due_date,
            days_until_due=days_until_due,
            link=f"/validation-workflow/{req.request_id}"
        ))

        if due_date:
            validation_calendar.append(CalendarItem(
                due_date=due_date,
                type="validation_submission",
                model_id=model.model_id,
                model_name=model.model_name,
                item_id=req.request_id,
                item_code=None,
                title=f"Validation Submission Due",
                is_overdue=(urgency == "overdue")
            ))

    # --- MONITORING ALERTS (Yellow/Red from last 90 days) ---
    monitoring_alerts: List[MonitoringAlert] = []

    # Query monitoring results with yellow/red outcomes for owned models
    # Join through plan to get models, then filter by calculated_outcome
    # Only include alerts from cycles that have been reviewed/finalized
    # (matching the Performance Summary logic for consistency)
    reviewed_statuses = [
        MonitoringCycleStatus.APPROVED.value,
        MonitoringCycleStatus.PENDING_APPROVAL.value,
        MonitoringCycleStatus.UNDER_REVIEW.value,
    ]
    results = db.query(MonitoringResult).join(
        MonitoringCycle
    ).join(
        MonitoringPlanMetric
    ).filter(
        MonitoringResult.model_id.in_(owned_model_ids),
        MonitoringResult.calculated_outcome.in_([OUTCOME_YELLOW, OUTCOME_RED]),
        MonitoringCycle.period_end_date >= ninety_days_ago,
        MonitoringCycle.status.in_(reviewed_statuses),
    ).options(
        joinedload(MonitoringResult.model),
        joinedload(MonitoringResult.cycle),
        joinedload(MonitoringResult.plan_metric).joinedload(MonitoringPlanMetric.kpm),
        joinedload(MonitoringResult.outcome_value),
    ).order_by(
        MonitoringResult.calculated_outcome.desc(),  # RED first
        MonitoringCycle.period_end_date.desc()
    ).limit(50).all()

    for result in results:
        model = result.model
        cycle = result.cycle
        metric = result.plan_metric
        kpm = metric.kpm if metric else None

        if not model or not cycle:
            continue

        # Build cycle name from period dates
        cycle_name = f"{cycle.period_start_date.strftime('%b %Y')}"

        monitoring_alerts.append(MonitoringAlert(
            model_id=model.model_id,
            model_name=model.model_name,
            metric_name=kpm.name if kpm else "Unknown Metric",
            metric_value=result.numeric_value,
            qualitative_outcome=result.outcome_value.label if result.outcome_value else None,
            outcome=result.calculated_outcome or "UNKNOWN",
            cycle_name=cycle_name,
            cycle_id=cycle.cycle_id,
            plan_id=cycle.plan_id,
            result_date=cycle.period_end_date,
        ))

    # --- OPEN MODEL EXCEPTIONS ---
    open_exception_items: List[ExceptionItem] = []

    # Get exception type labels
    exception_type_labels = {
        "UNMITIGATED_PERFORMANCE": "Unmitigated Performance Problem",
        "OUTSIDE_INTENDED_PURPOSE": "Model Used Outside Intended Purpose",
        "USE_PRIOR_TO_VALIDATION": "Model In Use Prior to Full Validation",
    }

    # Query open exceptions for owned models
    open_exceptions = db.query(ModelException).options(
        joinedload(ModelException.model),
    ).filter(
        ModelException.model_id.in_(owned_model_ids),
        ModelException.status.in_(["OPEN", "ACKNOWLEDGED"]),
    ).order_by(
        ModelException.detected_at.desc()
    ).all()

    for exc in open_exceptions:
        model = exc.model
        if not model:
            continue

        open_exception_items.append(ExceptionItem(
            exception_id=exc.exception_id,
            exception_code=exc.exception_code,
            exception_type=exc.exception_type,
            exception_type_label=exception_type_labels.get(exc.exception_type, exc.exception_type),
            model_id=model.model_id,
            model_name=model.model_name,
            status=exc.status,
            description=exc.description or "",
            detected_at=exc.detected_at,
            acknowledged_at=exc.acknowledged_at,
            link=f"/models/{model.model_id}",
        ))

    # --- COMBINE AND SORT ACTION ITEMS ---
    all_action_items = attestation_items + recommendation_items + validation_items

    # Sort by urgency (overdue first, then in_grace_period, due_soon, upcoming)
    urgency_order = {"overdue": 0, "in_grace_period": 1, "due_soon": 2, "upcoming": 3, "unknown": 4}
    all_action_items.sort(key=lambda x: (
        urgency_order.get(x.urgency, 4),
        x.days_until_due if x.days_until_due is not None else 9999
    ))

    # --- COMBINE CALENDAR ITEMS ---
    all_calendar_items = attestation_calendar + recommendation_calendar + validation_calendar
    all_calendar_items.sort(key=lambda x: x.due_date)

    # --- BUILD MODEL PORTFOLIO ---
    model_portfolio: List[PortfolioModel] = []
    model_overdue_map = {}  # Track which models have overdue items
    model_yellow_map = {}   # Yellow alerts by model
    model_red_map = {}      # Red alerts by model

    # Count alerts per model
    for alert in monitoring_alerts:
        if alert.outcome == OUTCOME_YELLOW:
            model_yellow_map[alert.model_id] = model_yellow_map.get(alert.model_id, 0) + 1
        elif alert.outcome == OUTCOME_RED:
            model_red_map[alert.model_id] = model_red_map.get(alert.model_id, 0) + 1

    # Count open exceptions per model
    model_exceptions_map = {}
    for exc in open_exception_items:
        model_exceptions_map[exc.model_id] = model_exceptions_map.get(exc.model_id, 0) + 1

    # Track overdue items per model
    for item in all_action_items:
        if item.urgency == "overdue":
            model_overdue_map[item.model_id] = True

    # Count open recommendations per model
    open_rec_statuses = [
        "REC_PENDING_RESPONSE", "REC_PENDING_ACKNOWLEDGEMENT", "REC_OPEN",
        "REC_REWORK_REQUIRED", "REC_PENDING_ACTION_PLAN", "REC_IN_PROGRESS"
    ]
    open_recs_by_model = db.query(
        Recommendation.model_id,
        func.count(Recommendation.recommendation_id).label("count")
    ).join(
        TaxonomyValue, Recommendation.current_status_id == TaxonomyValue.value_id
    ).filter(
        Recommendation.model_id.in_(owned_model_ids),
        TaxonomyValue.code.in_(open_rec_statuses)
    ).group_by(Recommendation.model_id).all()

    open_recs_map = {model_id: count for model_id, count in open_recs_by_model}

    for model in owned_models:
        # Calculate revalidation status to get all key dates
        reval_status = calculate_model_revalidation_status(model, db)

        last_val_date = reval_status.get("last_validation_date")
        next_submission_due = reval_status.get("next_submission_due")
        next_val_due = reval_status.get("next_validation_due")
        days_until_submission = reval_status.get("days_until_submission_due")
        days_until_val = reval_status.get("days_until_validation_due")

        # Get pending attestation status
        attestation_status = None
        pending_att = db.query(AttestationRecord).join(
            AttestationCycle
        ).filter(
            AttestationRecord.model_id == model.model_id,
            AttestationCycle.status.in_(["PENDING", "OPEN"]),
        ).first()
        if pending_att:
            attestation_status = pending_att.status.capitalize() if pending_att.status else None

        # Compute model approval status (validation-based)
        model_approval_status_code, _ = compute_model_approval_status(model, db)
        model_approval_status_label = get_status_label(model_approval_status_code)

        model_portfolio.append(PortfolioModel(
            model_id=model.model_id,
            model_name=model.model_name,
            risk_tier=model.risk_tier.label if model.risk_tier else None,
            risk_tier_code=model.risk_tier.code if model.risk_tier else None,
            approval_status=model_approval_status_label,
            approval_status_code=model_approval_status_code,
            last_validation_date=last_val_date,
            next_submission_due=next_submission_due,
            next_validation_due=next_val_due,
            days_until_submission_due=days_until_submission,
            days_until_validation_due=days_until_val,
            open_recommendations=open_recs_map.get(model.model_id, 0),
            attestation_status=attestation_status,
            yellow_alerts=model_yellow_map.get(model.model_id, 0),
            red_alerts=model_red_map.get(model.model_id, 0),
            open_exceptions=model_exceptions_map.get(model.model_id, 0),
            has_overdue_items=model_overdue_map.get(model.model_id, False),
            ownership_type=get_ownership_type(model, current_user, db),
        ))

    # Sort portfolio: overdue first, then by name
    model_portfolio.sort(key=lambda m: (not m.has_overdue_items, m.model_name))

    # --- CALCULATE SUMMARY ---
    total_models = len(owned_models)
    overdue_count = sum(1 for item in all_action_items if item.urgency == "overdue")
    action_items_count = len(all_action_items)

    # Compliance: model is compliant if no overdue items and approved (or interim approved)
    compliant_count = sum(
        1 for m in model_portfolio
        if not m.has_overdue_items and m.approval_status_code in (ApprovalStatus.APPROVED, ApprovalStatus.INTERIM_APPROVED)
    )
    non_compliant_count = total_models - compliant_count
    compliant_percentage = (compliant_count / total_models * 100) if total_models > 0 else 100.0

    yellow_count = sum(1 for a in monitoring_alerts if a.outcome == OUTCOME_YELLOW)
    red_count = sum(1 for a in monitoring_alerts if a.outcome == OUTCOME_RED)

    summary = PortfolioSummary(
        total_models=total_models,
        action_items_count=action_items_count,
        overdue_count=overdue_count,
        compliant_percentage=round(compliant_percentage, 1),
        models_compliant=compliant_count,
        models_non_compliant=non_compliant_count,
        yellow_alerts=yellow_count,
        red_alerts=red_count,
        open_exceptions_count=len(open_exception_items),
    )

    return MyPortfolioResponse(
        report_generated_at=utc_now(),
        as_of_date=today,
        team_id=team_id,
        team_name=team_name,
        summary=summary,
        action_items=all_action_items,
        monitoring_alerts=monitoring_alerts,
        open_exceptions=open_exception_items,
        calendar_items=all_calendar_items,
        models=model_portfolio,
    )


# =============================================================================
# PDF Export for My Portfolio Report
# =============================================================================

# Color constants for PDF
BG_GREEN = (220, 252, 231)
BG_YELLOW = (254, 249, 195)
BG_RED = (254, 226, 226)
BG_GRAY = (243, 244, 246)
BG_BLUE = (219, 234, 254)
BG_PURPLE = (243, 232, 255)

HEADER_BG = (31, 41, 55)
HEADER_TEXT = (255, 255, 255)
SECTION_BG = (243, 244, 246)
SECTION_TEXT = (31, 41, 55)


class MyPortfolioPDF(FPDF):
    """PDF generator for My Portfolio Report."""

    def __init__(self, report_data: dict, user_name: str):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.report_data = report_data
        self.user_name = user_name
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)

    def header(self):
        """Page header - adapts to portrait or landscape orientation."""
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(*SECTION_TEXT)
        self.cell(0, 8, 'My Model Portfolio Report', align='L')
        self.set_font('helvetica', '', 8)
        self.cell(0, 8, f'Owner: {self.user_name}', align='R', ln=True)
        self.set_draw_color(200, 200, 200)
        # Dynamically set line width based on page orientation
        page_width = self.w - 30  # Total width minus margins (15mm each side)
        self.line(15, self.get_y(), 15 + page_width, self.get_y())
        self.ln(5)

    def footer(self):
        """Page footer."""
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f'Page {self.page_no()}/{{nb}}', align='C')

    def add_section_header(self, title: str):
        """Add a styled section header."""
        self.set_fill_color(*SECTION_BG)
        self.set_text_color(*SECTION_TEXT)
        self.set_font('helvetica', 'B', 11)
        self.cell(0, 8, title, border=0, fill=True, ln=True)
        self.ln(2)

    def add_cover_page(self):
        """Add cover page with summary."""
        self.add_page()
        summary = self.report_data.get('summary', {})
        as_of_date = self.report_data.get('as_of_date', '')

        # Title
        self.set_font('helvetica', 'B', 24)
        self.set_text_color(*SECTION_TEXT)
        self.ln(20)
        self.cell(0, 15, 'My Model Portfolio', align='C', ln=True)
        self.ln(5)

        # Subtitle
        self.set_font('helvetica', '', 14)
        self.cell(0, 10, f'Report for: {self.user_name}', align='C', ln=True)
        self.set_font('helvetica', '', 11)
        self.cell(0, 8, f'As of: {as_of_date}', align='C', ln=True)
        self.ln(15)

        # Summary cards - 2x2 grid
        card_width = 85
        card_height = 25
        start_x = 20
        start_y = self.get_y()

        cards = [
            ('Models in Scope', str(summary.get('total_models', 0)), BG_BLUE),
            ('Action Items', str(summary.get('action_items_count', 0)), BG_YELLOW),
            ('Compliant', f"{summary.get('compliant_percentage', 0):.0f}%", BG_GREEN),
            ('Overdue Items', str(summary.get('overdue_count', 0)), BG_RED),
        ]

        for i, (label, value, color) in enumerate(cards):
            col = i % 2
            row = i // 2
            x = start_x + col * (card_width + 5)
            y = start_y + row * (card_height + 5)

            self.set_xy(x, y)
            self.set_fill_color(*color)
            self.rect(x, y, card_width, card_height, 'F')
            self.set_draw_color(180, 180, 180)
            self.rect(x, y, card_width, card_height, 'D')

            # Value
            self.set_xy(x, y + 3)
            self.set_font('helvetica', 'B', 18)
            self.set_text_color(*SECTION_TEXT)
            self.cell(card_width, 10, value, align='C')

            # Label
            self.set_xy(x, y + 14)
            self.set_font('helvetica', '', 9)
            self.cell(card_width, 6, label, align='C')

        self.set_y(start_y + 2 * (card_height + 5) + 10)

        # Alert summary
        self.ln(5)
        yellow = summary.get('yellow_alerts', 0)
        red = summary.get('red_alerts', 0)
        self.set_font('helvetica', '', 10)
        self.cell(0, 6, f'Monitoring Alerts: {yellow} Yellow, {red} Red', align='C', ln=True)

    def add_action_items(self):
        """Add action items section."""
        action_items = self.report_data.get('action_items', [])

        if not action_items:
            self.add_section_header('ACTION ITEMS')
            self.set_font('helvetica', 'I', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, 'No action items pending - you\'re all caught up!', ln=True)
            self.ln(5)
            return

        self.add_section_header(f'ACTION ITEMS ({len(action_items)} pending)')

        # Group by urgency
        urgency_groups = {
            'overdue': [],
            'in_grace_period': [],
            'due_soon': [],
            'upcoming': [],
        }
        for item in action_items:
            urgency = item.get('urgency', 'upcoming')
            if urgency in urgency_groups:
                urgency_groups[urgency].append(item)
            else:
                urgency_groups['upcoming'].append(item)

        urgency_config = [
            ('overdue', 'OVERDUE', BG_RED),
            ('in_grace_period', 'IN GRACE PERIOD', BG_YELLOW),
            ('due_soon', 'DUE SOON', BG_YELLOW),
            ('upcoming', 'UPCOMING', BG_BLUE),
        ]

        for urgency_key, label, color in urgency_config:
            items = urgency_groups.get(urgency_key, [])
            if not items:
                continue

            # Check page break
            if self.get_y() > 240:
                self.add_page()

            # Urgency header
            self.set_fill_color(*color)
            self.set_font('helvetica', 'B', 9)
            self.set_text_color(*SECTION_TEXT)
            self.cell(0, 6, f'{label} ({len(items)})', fill=True, ln=True)

            # Items table
            self.set_font('helvetica', '', 8)
            for item in items[:10]:  # Limit per group
                if self.get_y() > 270:
                    self.add_page()

                item_type = item.get('type', '').replace('_', ' ').title()
                model = item.get('model_name', '')[:25]
                title = item.get('title', '')[:35]
                due = item.get('due_date', '-') or '-'
                days = item.get('days_until_due')
                days_str = f"{days}d" if days is not None else '-'

                self.cell(25, 5, item_type, border='B')
                self.cell(50, 5, model, border='B')
                self.cell(70, 5, title, border='B')
                self.cell(20, 5, str(due), border='B')
                self.cell(15, 5, days_str, border='B', ln=True)

            if len(items) > 10:
                self.set_font('helvetica', 'I', 8)
                self.cell(0, 5, f'... and {len(items) - 10} more', ln=True)

            self.ln(3)

    def add_monitoring_alerts(self):
        """Add monitoring alerts section."""
        alerts = self.report_data.get('monitoring_alerts', [])
        summary = self.report_data.get('summary', {})

        self.add_section_header('MONITORING ALERTS')

        yellow = summary.get('yellow_alerts', 0)
        red = summary.get('red_alerts', 0)
        self.set_font('helvetica', '', 9)
        self.cell(0, 5, f'Yellow: {yellow}  |  Red: {red}  |  (Last 90 days)', ln=True)
        self.ln(2)

        if not alerts:
            self.set_font('helvetica', 'I', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, 'No yellow or red monitoring alerts in the last 90 days', ln=True)
            self.set_text_color(*SECTION_TEXT)
            return

        # Table header
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*HEADER_TEXT)
        self.set_font('helvetica', 'B', 8)
        self.cell(15, 6, 'Status', 1, 0, 'C', True)
        self.cell(50, 6, 'Model', 1, 0, 'C', True)
        self.cell(50, 6, 'Metric', 1, 0, 'C', True)
        self.cell(25, 6, 'Value', 1, 0, 'C', True)
        self.cell(25, 6, 'Cycle', 1, 0, 'C', True)
        self.cell(20, 6, 'Date', 1, 1, 'C', True)

        self.set_font('helvetica', '', 8)
        self.set_text_color(*SECTION_TEXT)

        for alert in alerts[:20]:  # Limit to 20
            if self.get_y() > 270:
                self.add_page()
                # Repeat header
                self.set_fill_color(*HEADER_BG)
                self.set_text_color(*HEADER_TEXT)
                self.set_font('helvetica', 'B', 8)
                self.cell(15, 6, 'Status', 1, 0, 'C', True)
                self.cell(50, 6, 'Model', 1, 0, 'C', True)
                self.cell(50, 6, 'Metric', 1, 0, 'C', True)
                self.cell(25, 6, 'Value', 1, 0, 'C', True)
                self.cell(25, 6, 'Cycle', 1, 0, 'C', True)
                self.cell(20, 6, 'Date', 1, 1, 'C', True)
                self.set_font('helvetica', '', 8)
                self.set_text_color(*SECTION_TEXT)

            outcome = alert.get('outcome', '')
            color = BG_RED if outcome == 'RED' else BG_YELLOW
            self.set_fill_color(*color)

            self.cell(15, 5, outcome, 1, 0, 'C', True)
            self.set_fill_color(255, 255, 255)
            self.cell(50, 5, alert.get('model_name', '')[:30], 1, 0)
            self.cell(50, 5, alert.get('metric_name', '')[:30], 1, 0)

            value = alert.get('metric_value')
            if value is not None:
                value_str = f"{value:.3f}" if isinstance(value, float) else str(value)
            else:
                value_str = alert.get('qualitative_outcome', '-') or '-'
            self.cell(25, 5, value_str[:12], 1, 0, 'R')

            self.cell(25, 5, alert.get('cycle_name', '-')[:15], 1, 0, 'C')
            result_date = alert.get('result_date', '')
            date_str = str(result_date)[:10] if result_date else '-'
            self.cell(20, 5, date_str, 1, 1, 'C')

        if len(alerts) > 20:
            self.set_font('helvetica', 'I', 8)
            self.cell(0, 5, f'... and {len(alerts) - 20} more alerts', ln=True)

        self.ln(5)

    def add_model_portfolio(self):
        """Add model portfolio table in landscape orientation."""
        models = self.report_data.get('models', [])

        # Add landscape page for portfolio table
        self.add_page('L')  # 'L' for landscape
        self.add_section_header(f'MODEL PORTFOLIO ({len(models)} models)')

        if not models:
            self.set_font('helvetica', 'I', 10)
            self.cell(0, 8, 'No models in portfolio', ln=True)
            return

        # Column widths for landscape (total usable width ~267mm with 15mm margins on A4 landscape)
        col_widths = {
            'id': 12,        # Model ID
            'name': 55,      # Model Name
            'tier': 16,      # Risk Tier
            'status': 24,    # Status
            'last_val': 24,  # Last Validation
            'sub_due': 26,   # Next Submission Due
            'val_due': 26,   # Next Validation Due
            'recs': 12,      # Open Recs
            'alerts': 24,    # Monitoring Alerts
            'role': 18,      # Role
        }

        # Table header
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*HEADER_TEXT)
        self.set_font('helvetica', 'B', 7)
        self.cell(col_widths['id'], 6, 'ID', 1, 0, 'C', True)
        self.cell(col_widths['name'], 6, 'Model', 1, 0, 'C', True)
        self.cell(col_widths['tier'], 6, 'Risk Tier', 1, 0, 'C', True)
        self.cell(col_widths['status'], 6, 'Status', 1, 0, 'C', True)
        self.cell(col_widths['last_val'], 6, 'Last Val', 1, 0, 'C', True)
        self.cell(col_widths['sub_due'], 6, 'Next Sub Due', 1, 0, 'C', True)
        self.cell(col_widths['val_due'], 6, 'Next Val Due', 1, 0, 'C', True)
        self.cell(col_widths['recs'], 6, 'Recs', 1, 0, 'C', True)
        self.cell(col_widths['alerts'], 6, 'Mon. Alerts', 1, 0, 'C', True)
        self.cell(col_widths['role'], 6, 'Role', 1, 1, 'C', True)

        self.set_font('helvetica', '', 7)
        self.set_text_color(*SECTION_TEXT)

        for model in models:
            if self.get_y() > 180:  # Landscape has less vertical space
                self.add_page('L')
                # Repeat header
                self.set_fill_color(*HEADER_BG)
                self.set_text_color(*HEADER_TEXT)
                self.set_font('helvetica', 'B', 7)
                self.cell(col_widths['id'], 6, 'ID', 1, 0, 'C', True)
                self.cell(col_widths['name'], 6, 'Model', 1, 0, 'C', True)
                self.cell(col_widths['tier'], 6, 'Risk Tier', 1, 0, 'C', True)
                self.cell(col_widths['status'], 6, 'Status', 1, 0, 'C', True)
                self.cell(col_widths['last_val'], 6, 'Last Val', 1, 0, 'C', True)
                self.cell(col_widths['sub_due'], 6, 'Next Sub Due', 1, 0, 'C', True)
                self.cell(col_widths['val_due'], 6, 'Next Val Due', 1, 0, 'C', True)
                self.cell(col_widths['recs'], 6, 'Recs', 1, 0, 'C', True)
                self.cell(col_widths['alerts'], 6, 'Mon. Alerts', 1, 0, 'C', True)
                self.cell(col_widths['role'], 6, 'Role', 1, 1, 'C', True)
                self.set_font('helvetica', '', 7)
                self.set_text_color(*SECTION_TEXT)

            # Row color based on overdue status
            if model.get('has_overdue_items'):
                self.set_fill_color(*BG_RED)
            else:
                self.set_fill_color(255, 255, 255)

            model_name = model.get('model_name', '')[:35]
            if model.get('has_overdue_items'):
                model_name = '! ' + model_name[:33]

            # Model ID
            model_id = model.get('model_id', '')
            self.cell(col_widths['id'], 5, str(model_id), 1, 0, 'C', fill=model.get('has_overdue_items', False))

            # Model Name
            self.cell(col_widths['name'], 5, model_name, 1, 0, fill=model.get('has_overdue_items', False))

            # Risk tier with color
            tier_code = model.get('risk_tier_code', '')
            tier_label = model.get('risk_tier', '-') or '-'
            if tier_code == 'TIER_1':
                self.set_fill_color(*BG_RED)
            elif tier_code == 'TIER_2':
                self.set_fill_color(*BG_YELLOW)
            else:
                self.set_fill_color(*BG_GREEN)
            self.cell(col_widths['tier'], 5, tier_label[:10], 1, 0, 'C', True)
            self.set_fill_color(255, 255, 255)

            self.cell(col_widths['status'], 5, (model.get('approval_status', '-') or '-')[:14], 1, 0, 'C')

            last_val = model.get('last_validation_date', '')
            self.cell(col_widths['last_val'], 5, str(last_val)[:10] if last_val else '-', 1, 0, 'C')

            # Next Submission Due
            next_sub = model.get('next_submission_due', '')
            self.cell(col_widths['sub_due'], 5, str(next_sub)[:10] if next_sub else '-', 1, 0, 'C')

            # Next Validation Due
            next_val = model.get('next_validation_due', '')
            self.cell(col_widths['val_due'], 5, str(next_val)[:10] if next_val else '-', 1, 0, 'C')

            open_recs = model.get('open_recommendations', 0)
            self.cell(col_widths['recs'], 5, str(open_recs) if open_recs else '-', 1, 0, 'C')

            # Monitoring Alerts
            yellow = model.get('yellow_alerts', 0)
            red = model.get('red_alerts', 0)
            if red > 0 or yellow > 0:
                alert_str = ''
                if red > 0:
                    alert_str += f'R:{red} '
                if yellow > 0:
                    alert_str += f'Y:{yellow}'
            else:
                alert_str = '-'
            self.cell(col_widths['alerts'], 5, alert_str.strip(), 1, 0, 'C')

            # Ownership type
            ownership = model.get('ownership_type', '')
            if ownership == 'primary':
                role = 'Primary'
            elif ownership == 'shared':
                role = 'Shared'
            elif ownership == 'delegate':
                role = 'Delegate'
            else:
                role = '-'
            self.cell(col_widths['role'], 5, role, 1, 1, 'C')

        self.ln(5)

    def generate(self) -> bytes:
        """Generate the complete PDF report."""
        self.alias_nb_pages()

        # Add sections
        self.add_cover_page()
        self.add_action_items()
        self.add_monitoring_alerts()
        self.add_model_portfolio()

        return bytes(self.output())


@router.get("/reports/my-portfolio/pdf")
def export_my_portfolio_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export My Portfolio Report as a professional PDF document.

    Generates a clean PDF report containing:
    - Summary statistics
    - Action items by urgency
    - Monitoring alerts
    - Full model portfolio table
    """
    # Get the portfolio data using the existing endpoint logic
    portfolio = get_my_portfolio(db=db, current_user=current_user)

    # Convert to dict for PDF generation
    report_data = {
        'as_of_date': str(portfolio.as_of_date),
        'report_generated_at': str(portfolio.report_generated_at),
        'summary': {
            'total_models': portfolio.summary.total_models,
            'action_items_count': portfolio.summary.action_items_count,
            'overdue_count': portfolio.summary.overdue_count,
            'compliant_percentage': portfolio.summary.compliant_percentage,
            'models_compliant': portfolio.summary.models_compliant,
            'models_non_compliant': portfolio.summary.models_non_compliant,
            'yellow_alerts': portfolio.summary.yellow_alerts,
            'red_alerts': portfolio.summary.red_alerts,
        },
        'action_items': [
            {
                'type': item.type,
                'urgency': item.urgency,
                'model_id': item.model_id,
                'model_name': item.model_name,
                'item_id': item.item_id,
                'item_code': item.item_code,
                'title': item.title,
                'action_description': item.action_description,
                'due_date': str(item.due_date) if item.due_date else None,
                'days_until_due': item.days_until_due,
                'link': item.link,
            }
            for item in portfolio.action_items
        ],
        'monitoring_alerts': [
            {
                'model_id': alert.model_id,
                'model_name': alert.model_name,
                'metric_name': alert.metric_name,
                'metric_value': alert.metric_value,
                'qualitative_outcome': alert.qualitative_outcome,
                'outcome': alert.outcome,
                'cycle_name': alert.cycle_name,
                'cycle_id': alert.cycle_id,
                'plan_id': alert.plan_id,
                'result_date': str(alert.result_date) if alert.result_date else None,
            }
            for alert in portfolio.monitoring_alerts
        ],
        'models': [
            {
                'model_id': m.model_id,
                'model_name': m.model_name,
                'risk_tier': m.risk_tier,
                'risk_tier_code': m.risk_tier_code,
                'approval_status': m.approval_status,
                'last_validation_date': str(m.last_validation_date) if m.last_validation_date else None,
                'next_submission_due': str(m.next_submission_due) if m.next_submission_due else None,
                'next_validation_due': str(m.next_validation_due) if m.next_validation_due else None,
                'days_until_submission_due': m.days_until_submission_due,
                'days_until_validation_due': m.days_until_validation_due,
                'open_recommendations': m.open_recommendations,
                'attestation_status': m.attestation_status,
                'yellow_alerts': m.yellow_alerts,
                'red_alerts': m.red_alerts,
                'has_overdue_items': m.has_overdue_items,
                'ownership_type': m.ownership_type,
            }
            for m in portfolio.models
        ],
    }

    # Generate PDF
    user_name = current_user.full_name or current_user.email
    pdf = MyPortfolioPDF(report_data, user_name)
    pdf_bytes = pdf.generate()

    # Return as downloadable PDF
    filename = f"my_portfolio_{portfolio.as_of_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
