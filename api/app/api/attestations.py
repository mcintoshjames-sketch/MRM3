"""Attestation routes - Model Risk Attestation workflow."""
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.model import Model
from app.models.region import Region
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model_delegate import ModelDelegate
from app.models.model_pending_edit import ModelPendingEdit
from app.models.audit_log import AuditLog
from app.models.attestation import (
    AttestationCycle,
    AttestationCycleStatus,
    AttestationRecord,
    AttestationRecordStatus,
    AttestationResponse as AttestationResponseModel,
    AttestationEvidence,
    AttestationSchedulingRule,
    AttestationSchedulingRuleType,
    AttestationFrequency,
    AttestationChangeProposal,
    AttestationChangeType,
    AttestationChangeStatus,
    CoverageTarget,
    AttestationQuestionConfig,
    AttestationDecision,
    AttestationBulkSubmission,
    AttestationBulkSubmissionStatus,
)
from app.schemas.attestation import (
    # Cycle schemas
    AttestationCycleCreate,
    AttestationCycleUpdate,
    AttestationCycleResponse,
    AttestationCycleListResponse,
    # Record schemas
    AttestationSubmitRequest,
    AttestationReviewRequest,
    AttestationRecordResponse,
    AttestationRecordListResponse,
    MyAttestationResponse,
    # Question schemas
    AttestationQuestionResponse,
    AttestationQuestionUpdate,
    # Evidence schemas
    AttestationEvidenceCreate,
    AttestationEvidenceResponse,
    # Scheduling rule schemas
    AttestationSchedulingRuleCreate,
    AttestationSchedulingRuleUpdate,
    AttestationSchedulingRuleResponse,
    # Change proposal schemas
    AttestationChangeProposalCreate,
    AttestationChangeProposalDecision,
    AttestationChangeProposalResponse,
    # Coverage target schemas
    CoverageTargetCreate,
    CoverageTargetUpdate,
    CoverageTargetResponse,
    # Report schemas
    CoverageByTierResponse,
    CoverageReportResponse,
    TimelinessReportResponse,
    TimelinessItemResponse,
    # Dashboard schemas
    AttestationDashboardStats,
    CycleReminderResponse,
    OwnerAttestationWidgetResponse,
    CurrentCycleInfo,
    # Enums
    AttestationCycleStatusEnum,
    AttestationRecordStatusEnum,
    AttestationFrequencyEnum,
    AttestationDecisionEnum,
    # Bulk attestation schemas
    BulkAttestationStateResponse,
    BulkAttestationCycleInfo,
    BulkAttestationModel,
    BulkAttestationDraftInfo,
    BulkAttestationSummary,
    BulkAttestationDraftRequest,
    BulkAttestationDraftResponse,
    BulkAttestationSubmitRequest,
    BulkAttestationSubmitResponse,
    BulkAttestationDiscardResponse,
)

router = APIRouter()


# ============================================================================
# HELPERS
# ============================================================================

def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for attestation changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def is_clean_attestation(responses: list, decision_comment: Optional[str]) -> bool:
    """
    Check if an attestation is "clean" and should be auto-accepted.

    A clean attestation has:
    - All answers are "Yes" (True)
    - No comments on any response
    - No decision comment
    """
    # Check all answers are Yes
    all_yes = all(r.answer is True for r in responses)
    if not all_yes:
        return False

    # Check no response comments
    has_response_comments = any(r.comment and r.comment.strip() for r in responses)
    if has_response_comments:
        return False

    # Check no decision comment
    if decision_comment and decision_comment.strip():
        return False

    return True


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def can_attest_for_model(db: Session, user: User, model: Model) -> bool:
    """Check if user can attest for a model."""
    # Admin can always attest
    if user.role == UserRole.ADMIN:
        return True

    # Owner can attest
    if model.owner_id == user.user_id:
        return True

    # Delegate with can_attest permission
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model.model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.revoked_at == None,
        ModelDelegate.can_attest == True
    ).first()

    return delegate is not None


def get_attestation_questions(db: Session, frequency: Optional[str] = None) -> List[AttestationQuestionResponse]:
    """Get attestation questions from taxonomy with their configs."""
    # Find the "Attestation Question" taxonomy
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Attestation Question"
    ).first()

    if not taxonomy:
        return []

    # Get active values with their configs
    query = db.query(TaxonomyValue, AttestationQuestionConfig).outerjoin(
        AttestationQuestionConfig,
        AttestationQuestionConfig.question_value_id == TaxonomyValue.value_id
    ).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.is_active == True
    )

    # Filter by frequency if specified
    if frequency:
        query = query.filter(
            or_(
                AttestationQuestionConfig.frequency_scope == frequency,
                AttestationQuestionConfig.frequency_scope == "BOTH"
            )
        )

    results = query.order_by(TaxonomyValue.sort_order).all()

    questions = []
    for value, config in results:
        questions.append(AttestationQuestionResponse(
            value_id=value.value_id,
            code=value.code,
            label=value.label,
            description=value.description,
            sort_order=value.sort_order,
            is_active=value.is_active,
            frequency_scope=config.frequency_scope if config else "BOTH",
            requires_comment_if_no=config.requires_comment_if_no if config else False
        ))

    return questions


# ============================================================================
# CYCLE ENDPOINTS
# ============================================================================

@router.get("/cycles", response_model=List[AttestationCycleListResponse])
def list_cycles(
    status: Optional[AttestationCycleStatusEnum] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List attestation cycles. Admin/Validator can see all."""
    query = db.query(AttestationCycle)

    if status:
        query = query.filter(AttestationCycle.status == status.value)

    cycles = query.order_by(AttestationCycle.period_start_date.desc()).all()

    result = []
    for cycle in cycles:
        # Count records by status
        records = db.query(AttestationRecord).filter(
            AttestationRecord.cycle_id == cycle.cycle_id
        ).all()

        total = len(records)
        pending = len([r for r in records if r.status == AttestationRecordStatus.PENDING.value])
        submitted = len([r for r in records if r.status == AttestationRecordStatus.SUBMITTED.value])
        accepted = len([r for r in records if r.status == AttestationRecordStatus.ACCEPTED.value])

        coverage_pct = (accepted / total * 100) if total > 0 else 0

        result.append(AttestationCycleListResponse(
            cycle_id=cycle.cycle_id,
            cycle_name=cycle.cycle_name,
            period_start_date=cycle.period_start_date,
            period_end_date=cycle.period_end_date,
            submission_due_date=cycle.submission_due_date,
            status=AttestationCycleStatusEnum(cycle.status),
            total_records=total,
            pending_count=pending,
            submitted_count=submitted,
            accepted_count=accepted,
            coverage_pct=round(coverage_pct, 2)
        ))

    return result


@router.post("/cycles", response_model=AttestationCycleResponse)
def create_cycle(
    cycle_in: AttestationCycleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new attestation cycle. Admin only."""
    cycle = AttestationCycle(
        cycle_name=cycle_in.cycle_name,
        period_start_date=cycle_in.period_start_date,
        period_end_date=cycle_in.period_end_date,
        submission_due_date=cycle_in.submission_due_date,
        notes=cycle_in.notes,
        status=AttestationCycleStatus.PENDING.value
    )
    db.add(cycle)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="AttestationCycle",
        entity_id=cycle.cycle_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"cycle_name": cycle.cycle_name}
    )

    db.commit()
    db.refresh(cycle)

    return _build_cycle_response(cycle, db)


@router.get("/cycles/reminder", response_model=CycleReminderResponse)
def get_cycle_reminder(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Check if a cycle reminder should be shown. Admin only."""
    today = date.today()

    # Check if we're in the first 2 weeks of a quarter
    quarter_starts = [
        date(today.year, 1, 1),
        date(today.year, 4, 1),
        date(today.year, 7, 1),
        date(today.year, 10, 1)
    ]

    current_quarter_start = None
    for qs in quarter_starts:
        if qs <= today < qs + timedelta(days=14):
            current_quarter_start = qs
            break

    if not current_quarter_start:
        return CycleReminderResponse(should_show_reminder=False)

    # Check if there's an OPEN cycle for this quarter
    quarter_end = current_quarter_start + timedelta(days=90)  # Approximate
    open_cycle = db.query(AttestationCycle).filter(
        AttestationCycle.status == AttestationCycleStatus.OPEN.value,
        AttestationCycle.period_start_date >= current_quarter_start,
        AttestationCycle.period_start_date < quarter_end
    ).first()

    if open_cycle:
        return CycleReminderResponse(should_show_reminder=False)

    # Get last closed cycle
    last_cycle = db.query(AttestationCycle).filter(
        AttestationCycle.status == AttestationCycleStatus.CLOSED.value
    ).order_by(AttestationCycle.period_end_date.desc()).first()

    quarter_names = {1: "Q1", 4: "Q2", 7: "Q3", 10: "Q4"}
    suggested_name = f"{quarter_names[current_quarter_start.month]} {current_quarter_start.year} Attestation Cycle"

    return CycleReminderResponse(
        should_show_reminder=True,
        suggested_cycle_name=suggested_name,
        last_cycle_end_date=last_cycle.period_end_date if last_cycle else None,
        message=f"It's time to open a new attestation cycle for {suggested_name}."
    )


@router.get("/cycles/{cycle_id}", response_model=AttestationCycleResponse)
def get_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific attestation cycle."""
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    return _build_cycle_response(cycle, db)


@router.patch("/cycles/{cycle_id}", response_model=AttestationCycleResponse)
def update_cycle(
    cycle_id: int,
    cycle_in: AttestationCycleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update an attestation cycle. Admin only. Cannot update after OPEN."""
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    if cycle.status != AttestationCycleStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot update cycle after it has been opened"
        )

    update_data = cycle_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cycle, field, value)

    create_audit_log(
        db=db,
        entity_type="AttestationCycle",
        entity_id=cycle.cycle_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=update_data
    )

    db.commit()
    db.refresh(cycle)

    return _build_cycle_response(cycle, db)


@router.post("/cycles/{cycle_id}/open", response_model=AttestationCycleResponse)
def open_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Open an attestation cycle and generate attestation records. Admin only."""
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    if cycle.status != AttestationCycleStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot open cycle in status {cycle.status}"
        )

    # Generate attestation records for all active, approved models
    models = db.query(Model).filter(
        Model.row_approval_status == None,  # Approved (NULL = approved in workflow)
        Model.status == "Active"  # Only active models (not In Development or Retired)
    ).all()

    records_created = 0
    for model in models:
        # Check if model is due in this cycle based on scheduling rules
        frequency = _resolve_attestation_frequency(db, model.model_id, model.owner_id)

        if _is_model_due_in_cycle(db, model, frequency, cycle):
            record = AttestationRecord(
                cycle_id=cycle.cycle_id,
                model_id=model.model_id,
                attesting_user_id=model.owner_id,
                due_date=cycle.submission_due_date,
                status=AttestationRecordStatus.PENDING.value
            )
            db.add(record)
            records_created += 1

    # Update cycle status
    cycle.status = AttestationCycleStatus.OPEN.value
    cycle.opened_at = utc_now()
    cycle.opened_by_user_id = current_user.user_id

    create_audit_log(
        db=db,
        entity_type="AttestationCycle",
        entity_id=cycle.cycle_id,
        action="OPEN",
        user_id=current_user.user_id,
        changes={"records_created": records_created}
    )

    db.commit()
    db.refresh(cycle)

    return _build_cycle_response(cycle, db)


@router.post("/cycles/{cycle_id}/close", response_model=AttestationCycleResponse)
def close_cycle(
    cycle_id: int,
    force: bool = Query(False, description="Force close even if blocking targets not met"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Close an attestation cycle. May be blocked if coverage targets not met."""
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    if cycle.status not in [AttestationCycleStatus.OPEN.value, AttestationCycleStatus.UNDER_REVIEW.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close cycle in status {cycle.status}"
        )

    # Check coverage targets unless forcing
    if not force:
        blocking_gaps = _check_blocking_targets(db, cycle.cycle_id)
        if blocking_gaps:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot close cycle: {'; '.join(blocking_gaps)}"
            )

    # Clean up any draft bulk submissions for this cycle
    draft_submissions = db.query(AttestationBulkSubmission).filter(
        AttestationBulkSubmission.cycle_id == cycle_id,
        AttestationBulkSubmission.status == AttestationBulkSubmissionStatus.DRAFT.value
    ).all()

    draft_count = len(draft_submissions)
    for draft in draft_submissions:
        db.delete(draft)

    # Reset is_excluded flags on PENDING records (they were never submitted)
    pending_records = db.query(AttestationRecord).filter(
        AttestationRecord.cycle_id == cycle_id,
        AttestationRecord.status == AttestationRecordStatus.PENDING.value
    ).all()

    for record in pending_records:
        if record.is_excluded:
            record.is_excluded = False

    # Update cycle status
    cycle.status = AttestationCycleStatus.CLOSED.value
    cycle.closed_at = utc_now()
    cycle.closed_by_user_id = current_user.user_id

    create_audit_log(
        db=db,
        entity_type="AttestationCycle",
        entity_id=cycle.cycle_id,
        action="CLOSE",
        user_id=current_user.user_id,
        changes={"forced": force, "drafts_cleaned_up": draft_count}
    )

    db.commit()
    db.refresh(cycle)

    return _build_cycle_response(cycle, db)


def _build_cycle_response(cycle: AttestationCycle, db: Session) -> AttestationCycleResponse:
    """Build full cycle response with counts."""
    records = db.query(AttestationRecord).filter(
        AttestationRecord.cycle_id == cycle.cycle_id
    ).all()

    total = len(records)
    pending = len([r for r in records if r.status == AttestationRecordStatus.PENDING.value])
    submitted = len([r for r in records if r.status == AttestationRecordStatus.SUBMITTED.value])
    accepted = len([r for r in records if r.status == AttestationRecordStatus.ACCEPTED.value])
    rejected = len([r for r in records if r.status == AttestationRecordStatus.REJECTED.value])

    opened_by = None
    if cycle.opened_by_user_id:
        user = db.query(User).filter(User.user_id == cycle.opened_by_user_id).first()
        if user:
            opened_by = {"user_id": user.user_id, "email": user.email, "full_name": user.full_name}

    closed_by = None
    if cycle.closed_by_user_id:
        user = db.query(User).filter(User.user_id == cycle.closed_by_user_id).first()
        if user:
            closed_by = {"user_id": user.user_id, "email": user.email, "full_name": user.full_name}

    return AttestationCycleResponse(
        cycle_id=cycle.cycle_id,
        cycle_name=cycle.cycle_name,
        period_start_date=cycle.period_start_date,
        period_end_date=cycle.period_end_date,
        submission_due_date=cycle.submission_due_date,
        notes=cycle.notes,
        status=AttestationCycleStatusEnum(cycle.status),
        opened_at=cycle.opened_at,
        opened_by=opened_by,
        closed_at=cycle.closed_at,
        closed_by=closed_by,
        created_at=cycle.created_at,
        updated_at=cycle.updated_at,
        total_records=total,
        pending_count=pending,
        submitted_count=submitted,
        accepted_count=accepted,
        rejected_count=rejected
    )


# ============================================================================
# RECORD ENDPOINTS
# ============================================================================

@router.get("/my-attestations", response_model=List[MyAttestationResponse])
def get_my_attestations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's attestations for OPEN cycles (all statuses)."""
    today = date.today()

    # Get all attestations for OPEN cycles where user is owner or delegate
    # Now includes all statuses to show pending, submitted, accepted, rejected
    query = db.query(AttestationRecord).join(
        AttestationCycle, AttestationCycle.cycle_id == AttestationRecord.cycle_id
    ).join(
        Model, Model.model_id == AttestationRecord.model_id
    ).filter(
        AttestationCycle.status == AttestationCycleStatus.OPEN.value
    )

    records = query.all()

    result = []
    for record in records:
        model = record.model
        cycle = record.cycle

        # Check if user can attest for this model
        if not can_attest_for_model(db, current_user, model):
            continue

        days_until_due = (record.due_date - today).days
        is_overdue = days_until_due < 0 and record.status == AttestationRecordStatus.PENDING.value

        # Get risk tier info
        risk_tier_code = None
        risk_tier_label = None
        if model.risk_tier_id:
            tier = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == model.risk_tier_id
            ).first()
            if tier:
                risk_tier_code = tier.code
                risk_tier_label = tier.label

        # Determine if user can submit (only PENDING or REJECTED)
        can_submit = record.status in [
            AttestationRecordStatus.PENDING.value,
            AttestationRecordStatus.REJECTED.value
        ]

        # Get rejection reason if rejected
        rejection_reason = None
        if record.status == AttestationRecordStatus.REJECTED.value:
            rejection_reason = record.review_comment

        # Get decision enum if submitted
        decision = None
        if record.decision:
            try:
                decision = AttestationDecisionEnum(record.decision)
            except ValueError:
                pass

        result.append(MyAttestationResponse(
            attestation_id=record.attestation_id,
            cycle_id=cycle.cycle_id,
            cycle_name=cycle.cycle_name,
            model_id=model.model_id,
            model_name=model.model_name,
            model_risk_tier=risk_tier_label or risk_tier_code,
            risk_tier_code=risk_tier_code,
            due_date=record.due_date,
            status=AttestationRecordStatusEnum(record.status),
            attested_at=record.attested_at,
            decision=decision,
            rejection_reason=rejection_reason,
            days_until_due=days_until_due,
            is_overdue=is_overdue,
            can_submit=can_submit,
            is_excluded=record.is_excluded
        ))

    # Sort: pending (overdue first, then by due date), then submitted/accepted/rejected
    def sort_key(x):
        if x.status == AttestationRecordStatusEnum.PENDING:
            return (0, not x.is_overdue, x.due_date)
        elif x.status == AttestationRecordStatusEnum.REJECTED:
            return (1, False, x.due_date)  # Rejected need attention
        elif x.status == AttestationRecordStatusEnum.SUBMITTED:
            return (2, False, x.due_date)
        else:
            return (3, False, x.due_date)  # Accepted last

    result.sort(key=sort_key)

    return result


@router.get("/my-upcoming", response_model=OwnerAttestationWidgetResponse)
def get_my_upcoming_attestations(
    days_ahead: int = Query(14, description="Days ahead to look for upcoming attestations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get owner's upcoming (14 days) and past-due attestations for dashboard widget."""
    today = date.today()
    cutoff_date = today + timedelta(days=days_ahead)

    all_attestations = get_my_attestations(db=db, current_user=current_user)

    upcoming = []
    past_due = []

    for att in all_attestations:
        if att.is_overdue:
            past_due.append(att)
        elif att.due_date <= cutoff_date:
            upcoming.append(att)

    # Find current cycle info from user's pending attestations
    current_cycle_info = None
    pending_attestations = [a for a in all_attestations if a.status == "PENDING"]
    overdue_attestations = [a for a in pending_attestations if a.is_overdue]

    if pending_attestations:
        # Get cycle info from the first pending attestation
        first_att = pending_attestations[0]
        cycle = db.query(AttestationCycle).filter(
            AttestationCycle.cycle_id == first_att.cycle_id
        ).first()
        if cycle:
            current_cycle_info = CurrentCycleInfo(
                cycle_id=cycle.cycle_id,
                cycle_name=cycle.cycle_name,
                submission_due_date=cycle.submission_due_date,
                status=cycle.status.value if hasattr(cycle.status, 'value') else str(cycle.status)
            )

    # Calculate days until due (use first pending attestation's due date)
    days_until_due = None
    if pending_attestations:
        first_due = min(a.due_date for a in pending_attestations)
        days_until_due = (first_due - today).days

    return OwnerAttestationWidgetResponse(
        # New fields expected by frontend
        current_cycle=current_cycle_info,
        attestations=pending_attestations,
        pending_count=len(pending_attestations),
        overdue_count=len(overdue_attestations),
        days_until_due=days_until_due,
        # Legacy fields
        upcoming_attestations=upcoming,
        past_due_attestations=past_due,
        total_upcoming=len(upcoming),
        total_past_due=len(past_due)
    )


@router.get("/records", response_model=List[AttestationRecordListResponse])
def list_records(
    cycle_id: Optional[int] = None,
    status: Optional[AttestationRecordStatusEnum] = None,
    overdue: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List attestation records. Admin/Validator can see all."""
    if current_user.role not in [UserRole.ADMIN, UserRole.VALIDATOR]:
        raise HTTPException(
            status_code=403,
            detail="Admin or Validator access required"
        )

    query = db.query(AttestationRecord).join(
        AttestationCycle, AttestationCycle.cycle_id == AttestationRecord.cycle_id
    ).join(
        Model, Model.model_id == AttestationRecord.model_id
    ).join(
        User, User.user_id == AttestationRecord.attesting_user_id
    )

    if cycle_id:
        query = query.filter(AttestationRecord.cycle_id == cycle_id)

    if status:
        query = query.filter(AttestationRecord.status == status.value)

    records = query.order_by(AttestationRecord.due_date).all()

    today = date.today()
    result = []

    for record in records:
        model = record.model
        cycle = record.cycle
        attesting_user = record.attesting_user

        days_overdue = (today - record.due_date).days if today > record.due_date else 0
        is_overdue = days_overdue > 0 and record.status == AttestationRecordStatus.PENDING.value

        if overdue is not None:
            if overdue and not is_overdue:
                continue
            if not overdue and is_overdue:
                continue

        # Get owner
        owner = db.query(User).filter(User.user_id == model.owner_id).first()

        # Get risk tier code
        risk_tier_code = None
        if model.risk_tier_id:
            tier = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == model.risk_tier_id
            ).first()
            if tier:
                risk_tier_code = tier.code

        result.append(AttestationRecordListResponse(
            attestation_id=record.attestation_id,
            cycle_id=cycle.cycle_id,
            cycle_name=cycle.cycle_name,
            model_id=model.model_id,
            model_name=model.model_name,
            risk_tier_code=risk_tier_code,
            owner_name=owner.full_name if owner else "Unknown",
            attesting_user_name=attesting_user.full_name,
            due_date=record.due_date,
            status=AttestationRecordStatusEnum(record.status),
            decision=record.decision,
            attested_at=record.attested_at,
            is_overdue=is_overdue,
            days_overdue=days_overdue
        ))

    return result


@router.get("/records/{attestation_id}", response_model=AttestationRecordResponse)
def get_record(
    attestation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific attestation record with full details."""
    record = db.query(AttestationRecord).options(
        joinedload(AttestationRecord.responses),
        joinedload(AttestationRecord.evidence),
        joinedload(AttestationRecord.change_proposals)
    ).filter(
        AttestationRecord.attestation_id == attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    # Check permission
    model = record.model
    if current_user.role not in [UserRole.ADMIN, UserRole.VALIDATOR]:
        if not can_attest_for_model(db, current_user, model):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this attestation"
            )

    return _build_record_response(record, db)


@router.post("/records/{attestation_id}/submit", response_model=AttestationRecordResponse)
def submit_attestation(
    attestation_id: int,
    submission: AttestationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit an attestation."""
    record = db.query(AttestationRecord).filter(
        AttestationRecord.attestation_id == attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    # Check permission
    model = record.model
    if not can_attest_for_model(db, current_user, model):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to submit this attestation"
        )

    # Check cycle is open
    cycle = record.cycle
    if cycle.status != AttestationCycleStatus.OPEN.value:
        raise HTTPException(
            status_code=400,
            detail="Cycle is not open for submissions"
        )

    # Check record status
    if record.status != AttestationRecordStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit attestation in status {record.status}"
        )

    # Validate decision
    if submission.decision != AttestationDecision.I_ATTEST.value and not submission.decision_comment:
        raise HTTPException(
            status_code=400,
            detail="Comment required for decision other than 'I Attest'"
        )

    # Determine the attestation frequency for this model/owner to filter questions
    model_frequency = _resolve_attestation_frequency(db, model.model_id, model.owner_id)

    # Validate question responses - filter by frequency
    questions = get_attestation_questions(db, model_frequency)
    question_ids = {q.value_id for q in questions}
    submitted_question_ids = {r.question_id for r in submission.responses}

    if submitted_question_ids != question_ids:
        raise HTTPException(
            status_code=400,
            detail="All questions must be answered"
        )

    # Validate comments for "No" answers
    question_map = {q.value_id: q for q in questions}
    for response in submission.responses:
        question = question_map.get(response.question_id)
        if question and not response.answer and question.requires_comment_if_no and not response.comment:
            raise HTTPException(
                status_code=400,
                detail=f"Comment required when answering 'No' to question: {question.code}"
            )

    # Check if this is a clean attestation (auto-accept)
    auto_accept = is_clean_attestation(submission.responses, submission.decision_comment)

    # Update record
    record.decision = submission.decision
    record.decision_comment = submission.decision_comment
    if auto_accept:
        record.status = AttestationRecordStatus.ACCEPTED.value
        record.reviewed_at = utc_now()
        record.reviewed_by_user_id = current_user.user_id  # Self-accepted
    else:
        record.status = AttestationRecordStatus.SUBMITTED.value
    record.attested_at = utc_now()
    record.attesting_user_id = current_user.user_id
    # Clear excluded flag since record is now submitted
    record.is_excluded = False

    # Save responses
    for response_data in submission.responses:
        response = AttestationResponseModel(
            attestation_id=attestation_id,
            question_id=response_data.question_id,
            answer=response_data.answer,
            comment=response_data.comment
        )
        db.add(response)

    # Save evidence (optional)
    for evidence_data in submission.evidence:
        evidence = AttestationEvidence(
            attestation_id=attestation_id,
            evidence_type=evidence_data.evidence_type,
            url=evidence_data.url,
            description=evidence_data.description,
            added_by_user_id=current_user.user_id
        )
        db.add(evidence)

    create_audit_log(
        db=db,
        entity_type="AttestationRecord",
        entity_id=attestation_id,
        action="AUTO_ACCEPT" if auto_accept else "SUBMIT",
        user_id=current_user.user_id,
        changes={
            "decision": submission.decision,
            "response_count": len(submission.responses),
            "auto_accepted": auto_accept
        }
    )

    # Clean up bulk submission draft if this was an excluded model
    bulk_submission = db.query(AttestationBulkSubmission).filter(
        AttestationBulkSubmission.cycle_id == record.cycle_id,
        AttestationBulkSubmission.user_id == current_user.user_id,
        AttestationBulkSubmission.status == AttestationBulkSubmissionStatus.DRAFT.value
    ).first()

    if bulk_submission and bulk_submission.excluded_model_ids:
        # Remove this model from excluded list
        if model.model_id in bulk_submission.excluded_model_ids:
            bulk_submission.excluded_model_ids = [
                m_id for m_id in bulk_submission.excluded_model_ids
                if m_id != model.model_id
            ]
            bulk_submission.updated_at = utc_now()

        # Check if user has any remaining PENDING records
        remaining_pending = db.query(AttestationRecord).join(
            Model, Model.model_id == AttestationRecord.model_id
        ).filter(
            AttestationRecord.cycle_id == record.cycle_id,
            AttestationRecord.status == AttestationRecordStatus.PENDING.value
        ).all()

        # Filter to records this user can attest
        user_pending = [r for r in remaining_pending if can_attest_for_model(db, current_user, r.model)]

        # If no remaining pending records, delete the draft
        if not user_pending:
            db.delete(bulk_submission)

    db.commit()
    db.refresh(record)

    return _build_record_response(record, db)


@router.post("/records/{attestation_id}/accept", response_model=AttestationRecordResponse)
def accept_attestation(
    attestation_id: int,
    review: AttestationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Accept a submitted attestation. Admin only."""
    record = db.query(AttestationRecord).filter(
        AttestationRecord.attestation_id == attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    if record.status != AttestationRecordStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot accept attestation in status {record.status}"
        )

    record.status = AttestationRecordStatus.ACCEPTED.value
    record.reviewed_by_user_id = current_user.user_id
    record.reviewed_at = utc_now()
    record.review_comment = review.review_comment

    create_audit_log(
        db=db,
        entity_type="AttestationRecord",
        entity_id=attestation_id,
        action="ACCEPT",
        user_id=current_user.user_id,
        changes={"review_comment": review.review_comment}
    )

    db.commit()
    db.refresh(record)

    return _build_record_response(record, db)


@router.post("/records/{attestation_id}/reject", response_model=AttestationRecordResponse)
def reject_attestation(
    attestation_id: int,
    review: AttestationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Reject a submitted attestation. Admin only."""
    record = db.query(AttestationRecord).filter(
        AttestationRecord.attestation_id == attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    if record.status != AttestationRecordStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject attestation in status {record.status}"
        )

    if not review.review_comment:
        raise HTTPException(
            status_code=400,
            detail="Review comment required when rejecting"
        )

    record.status = AttestationRecordStatus.REJECTED.value
    record.reviewed_by_user_id = current_user.user_id
    record.reviewed_at = utc_now()
    record.review_comment = review.review_comment

    create_audit_log(
        db=db,
        entity_type="AttestationRecord",
        entity_id=attestation_id,
        action="REJECT",
        user_id=current_user.user_id,
        changes={"review_comment": review.review_comment}
    )

    db.commit()
    db.refresh(record)

    return _build_record_response(record, db)


# ============================================================================
# EVIDENCE ENDPOINTS
# ============================================================================

@router.post("/records/{attestation_id}/evidence", response_model=AttestationEvidenceResponse)
def add_evidence(
    attestation_id: int,
    evidence_in: AttestationEvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add evidence to an attestation record."""
    record = db.query(AttestationRecord).filter(
        AttestationRecord.attestation_id == attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    # Check permission
    model = record.model
    if current_user.role not in [UserRole.ADMIN, UserRole.VALIDATOR]:
        if not can_attest_for_model(db, current_user, model):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to add evidence to this attestation"
            )

    # Check record status - can add evidence until accepted
    if record.status == AttestationRecordStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot add evidence to an accepted attestation"
        )

    evidence = AttestationEvidence(
        attestation_id=attestation_id,
        evidence_type=evidence_in.evidence_type,
        url=evidence_in.url,
        description=evidence_in.description,
        added_by_user_id=current_user.user_id
    )
    db.add(evidence)

    create_audit_log(
        db=db,
        entity_type="AttestationEvidence",
        entity_id=attestation_id,
        action="ADD_EVIDENCE",
        user_id=current_user.user_id,
        changes={"url": evidence_in.url, "evidence_type": evidence_in.evidence_type}
    )

    db.commit()
    db.refresh(evidence)

    added_by = db.query(User).filter(User.user_id == evidence.added_by_user_id).first()

    return AttestationEvidenceResponse(
        evidence_id=evidence.evidence_id,
        attestation_id=evidence.attestation_id,
        evidence_type=evidence.evidence_type,
        url=evidence.url,
        description=evidence.description,
        added_by={"user_id": added_by.user_id, "email": added_by.email, "full_name": added_by.full_name} if added_by else None,
        added_at=evidence.added_at
    )


@router.delete("/evidence/{evidence_id}")
def remove_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove evidence from an attestation record."""
    evidence = db.query(AttestationEvidence).filter(
        AttestationEvidence.evidence_id == evidence_id
    ).first()

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    record = db.query(AttestationRecord).filter(
        AttestationRecord.attestation_id == evidence.attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    # Check permission - only admin or the person who added it can remove
    if current_user.role != UserRole.ADMIN and evidence.added_by_user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to remove this evidence"
        )

    # Check record status - cannot remove from accepted attestation
    if record.status == AttestationRecordStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove evidence from an accepted attestation"
        )

    create_audit_log(
        db=db,
        entity_type="AttestationEvidence",
        entity_id=evidence.attestation_id,
        action="REMOVE_EVIDENCE",
        user_id=current_user.user_id,
        changes={"evidence_id": evidence_id, "url": evidence.url}
    )

    db.delete(evidence)
    db.commit()

    return {"message": "Evidence removed successfully"}


def _build_record_response(record: AttestationRecord, db: Session) -> AttestationRecordResponse:
    """Build full record response."""
    model = record.model
    attesting_user = record.attesting_user
    today = date.today()

    days_overdue = (today - record.due_date).days if today > record.due_date else 0
    is_overdue = days_overdue > 0 and record.status == AttestationRecordStatus.PENDING.value

    # Get owner and risk tier
    owner = db.query(User).filter(User.user_id == model.owner_id).first()
    risk_tier_code = None
    risk_tier_label = None
    if model.risk_tier_id:
        tier = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == model.risk_tier_id
        ).first()
        if tier:
            risk_tier_code = tier.code
            risk_tier_label = tier.label

    model_ref = {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "risk_tier_code": risk_tier_code,
        "risk_tier_label": risk_tier_label,
        "owner_id": model.owner_id,
        "owner_name": owner.full_name if owner else None
    }

    attesting_user_ref = {
        "user_id": attesting_user.user_id,
        "email": attesting_user.email,
        "full_name": attesting_user.full_name
    }

    reviewed_by_ref = None
    if record.reviewed_by_user_id:
        reviewer = db.query(User).filter(User.user_id == record.reviewed_by_user_id).first()
        if reviewer:
            reviewed_by_ref = {
                "user_id": reviewer.user_id,
                "email": reviewer.email,
                "full_name": reviewer.full_name
            }

    # Build responses
    responses = []
    for resp in record.responses:
        question = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == resp.question_id
        ).first()
        config = db.query(AttestationQuestionConfig).filter(
            AttestationQuestionConfig.question_value_id == resp.question_id
        ).first()

        responses.append({
            "response_id": resp.response_id,
            "attestation_id": resp.attestation_id,
            "question_id": resp.question_id,
            "answer": resp.answer,
            "comment": resp.comment,
            "created_at": resp.created_at,
            "question": {
                "value_id": question.value_id,
                "code": question.code,
                "label": question.label,
                "description": question.description,
                "sort_order": question.sort_order,
                "is_active": question.is_active,
                "frequency_scope": config.frequency_scope if config else "BOTH",
                "requires_comment_if_no": config.requires_comment_if_no if config else False
            } if question else None
        })

    # Build evidence
    evidence = []
    for ev in record.evidence:
        added_by = db.query(User).filter(User.user_id == ev.added_by_user_id).first()
        evidence.append({
            "evidence_id": ev.evidence_id,
            "attestation_id": ev.attestation_id,
            "evidence_type": ev.evidence_type,
            "url": ev.url,
            "description": ev.description,
            "added_by": {
                "user_id": added_by.user_id,
                "email": added_by.email,
                "full_name": added_by.full_name
            } if added_by else None,
            "added_at": ev.added_at
        })

    # Build change proposals
    change_proposals = []
    for proposal in record.change_proposals:
        proposal_model_ref = None
        if proposal.model_id:
            target_model = db.query(Model).filter(Model.model_id == proposal.model_id).first()
            if target_model:
                proposal_model_ref = {
                    "model_id": target_model.model_id,
                    "model_name": target_model.model_name
                }

        decided_by_ref = None
        if proposal.decided_by_user_id:
            decided_by = db.query(User).filter(User.user_id == proposal.decided_by_user_id).first()
            if decided_by:
                decided_by_ref = {
                    "user_id": decided_by.user_id,
                    "email": decided_by.email,
                    "full_name": decided_by.full_name
                }

        change_proposals.append({
            "proposal_id": proposal.proposal_id,
            "attestation_id": proposal.attestation_id,
            "pending_edit_id": proposal.pending_edit_id,
            "change_type": proposal.change_type,
            "model_id": proposal.model_id,
            "proposed_data": proposal.proposed_data,
            "status": proposal.status,
            "admin_comment": proposal.admin_comment,
            "decided_by": decided_by_ref,
            "decided_at": proposal.decided_at,
            "created_at": proposal.created_at,
            "model": proposal_model_ref
        })

    return AttestationRecordResponse(
        attestation_id=record.attestation_id,
        cycle_id=record.cycle_id,
        model=model_ref,
        attesting_user=attesting_user_ref,
        due_date=record.due_date,
        status=AttestationRecordStatusEnum(record.status),
        attested_at=record.attested_at,
        decision=record.decision,
        decision_comment=record.decision_comment,
        reviewed_by=reviewed_by_ref,
        reviewed_at=record.reviewed_at,
        review_comment=record.review_comment,
        responses=responses,
        evidence=evidence,
        change_proposals=change_proposals,
        created_at=record.created_at,
        updated_at=record.updated_at,
        days_overdue=days_overdue,
        is_overdue=is_overdue
    )


# ============================================================================
# QUESTIONS ENDPOINT
# ============================================================================

@router.get("/questions", response_model=List[AttestationQuestionResponse])
def list_questions(
    frequency: Optional[AttestationFrequencyEnum] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List attestation questions, optionally filtered by frequency."""
    return get_attestation_questions(db, frequency.value if frequency else None)


@router.get("/questions/all", response_model=List[AttestationQuestionResponse])
def list_all_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all attestation questions including inactive ones. Admin only."""
    # Find the "Attestation Question" taxonomy
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Attestation Question"
    ).first()

    if not taxonomy:
        return []

    # Get ALL values with their configs (including inactive)
    results = db.query(TaxonomyValue, AttestationQuestionConfig).outerjoin(
        AttestationQuestionConfig,
        AttestationQuestionConfig.question_value_id == TaxonomyValue.value_id
    ).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id
    ).order_by(TaxonomyValue.sort_order).all()

    questions = []
    for value, config in results:
        questions.append(AttestationQuestionResponse(
            value_id=value.value_id,
            code=value.code,
            label=value.label,
            description=value.description,
            sort_order=value.sort_order,
            is_active=value.is_active,
            frequency_scope=config.frequency_scope if config else "BOTH",
            requires_comment_if_no=config.requires_comment_if_no if config else False
        ))

    return questions


@router.patch("/questions/{value_id}", response_model=AttestationQuestionResponse)
def update_question(
    value_id: int,
    question_in: AttestationQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update an attestation question. Admin only."""
    # Find the "Attestation Question" taxonomy
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Attestation Question"
    ).first()

    if not taxonomy:
        raise HTTPException(status_code=404, detail="Attestation Question taxonomy not found")

    # Find the value
    value = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == value_id,
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id
    ).first()

    if not value:
        raise HTTPException(status_code=404, detail="Question not found")

    update_data = question_in.model_dump(exclude_unset=True)
    old_values = {}

    # Update taxonomy value fields
    taxonomy_fields = ['label', 'description', 'sort_order', 'is_active']
    for field in taxonomy_fields:
        if field in update_data:
            old_values[field] = getattr(value, field)
            setattr(value, field, update_data[field])

    # Update or create config
    config = db.query(AttestationQuestionConfig).filter(
        AttestationQuestionConfig.question_value_id == value_id
    ).first()

    config_fields = ['frequency_scope', 'requires_comment_if_no']
    config_updates = {k: v for k, v in update_data.items() if k in config_fields}

    if config_updates:
        if config:
            # Update existing config
            for field, new_value in config_updates.items():
                old_values[field] = getattr(config, field)
                setattr(config, field, new_value)
        else:
            # Create new config with defaults
            config = AttestationQuestionConfig(
                question_value_id=value_id,
                frequency_scope=config_updates.get('frequency_scope', 'BOTH'),
                requires_comment_if_no=config_updates.get('requires_comment_if_no', False)
            )
            db.add(config)

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="AttestationQuestion",
        entity_id=value_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={"old": old_values, "new": update_data}
    )

    db.commit()
    db.refresh(value)
    if config:
        db.refresh(config)

    return AttestationQuestionResponse(
        value_id=value.value_id,
        code=value.code,
        label=value.label,
        description=value.description,
        sort_order=value.sort_order,
        is_active=value.is_active,
        frequency_scope=config.frequency_scope if config else "BOTH",
        requires_comment_if_no=config.requires_comment_if_no if config else False
    )


# ============================================================================
# SCHEDULING RULES ENDPOINTS
# ============================================================================

@router.get("/rules", response_model=List[AttestationSchedulingRuleResponse])
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List attestation scheduling rules. Admin only."""
    rules = db.query(AttestationSchedulingRule).order_by(
        AttestationSchedulingRule.priority.desc()
    ).all()

    return [_build_rule_response(rule, db) for rule in rules]


@router.post("/rules", response_model=AttestationSchedulingRuleResponse)
def create_rule(
    rule_in: AttestationSchedulingRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a scheduling rule. Admin only."""
    # Validate OWNER_THRESHOLD rules have at least one criterion
    if rule_in.rule_type == AttestationSchedulingRuleType.OWNER_THRESHOLD:
        if rule_in.owner_model_count_min is None and not rule_in.owner_high_fluctuation_flag:
            raise HTTPException(
                status_code=400,
                detail="OWNER_THRESHOLD rules must have at least one criterion (owner_model_count_min or owner_high_fluctuation_flag)"
            )

    # Validate only one active GLOBAL_DEFAULT rule exists
    if rule_in.rule_type == AttestationSchedulingRuleType.GLOBAL_DEFAULT:
        existing = db.query(AttestationSchedulingRule).filter(
            AttestationSchedulingRule.rule_type == AttestationSchedulingRuleType.GLOBAL_DEFAULT,
            AttestationSchedulingRule.is_active == True
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"An active GLOBAL_DEFAULT rule already exists: '{existing.rule_name}'. Deactivate it first or edit the existing rule."
            )

    rule = AttestationSchedulingRule(
        **rule_in.model_dump(),
        created_by_user_id=current_user.user_id
    )
    db.add(rule)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="AttestationSchedulingRule",
        entity_id=rule.rule_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes=rule_in.model_dump(mode='json')  # mode='json' serializes dates to strings
    )

    db.commit()
    db.refresh(rule)

    return _build_rule_response(rule, db)


@router.patch("/rules/{rule_id}", response_model=AttestationSchedulingRuleResponse)
def update_rule(
    rule_id: int,
    rule_in: AttestationSchedulingRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a scheduling rule. Admin only."""
    rule = db.query(AttestationSchedulingRule).filter(
        AttestationSchedulingRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_in.model_dump(exclude_unset=True)

    # Validate OWNER_THRESHOLD rules won't become criterion-less after update
    if rule.rule_type == AttestationSchedulingRuleType.OWNER_THRESHOLD:
        new_count = update_data.get('owner_model_count_min', rule.owner_model_count_min)
        new_flag = update_data.get('owner_high_fluctuation_flag', rule.owner_high_fluctuation_flag)
        if new_count is None and not new_flag:
            raise HTTPException(
                status_code=400,
                detail="OWNER_THRESHOLD rules must have at least one criterion (owner_model_count_min or owner_high_fluctuation_flag)"
            )

    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_by_user_id = current_user.user_id

    # Use mode='json' for audit log to serialize dates to strings
    audit_changes = rule_in.model_dump(exclude_unset=True, mode='json')
    create_audit_log(
        db=db,
        entity_type="AttestationSchedulingRule",
        entity_id=rule.rule_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=audit_changes
    )

    db.commit()
    db.refresh(rule)

    return _build_rule_response(rule, db)


@router.delete("/rules/{rule_id}")
def deactivate_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deactivate a scheduling rule. Admin only."""
    rule = db.query(AttestationSchedulingRule).filter(
        AttestationSchedulingRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = False
    rule.updated_by_user_id = current_user.user_id

    create_audit_log(
        db=db,
        entity_type="AttestationSchedulingRule",
        entity_id=rule.rule_id,
        action="DEACTIVATE",
        user_id=current_user.user_id,
        changes={}
    )

    db.commit()

    return {"message": "Rule deactivated"}


def _build_rule_response(rule: AttestationSchedulingRule, db: Session) -> AttestationSchedulingRuleResponse:
    """Build rule response."""
    model_ref = None
    if rule.model_id:
        model = db.query(Model).filter(Model.model_id == rule.model_id).first()
        if model:
            model_ref = {"model_id": model.model_id, "model_name": model.model_name}

    region_ref = None
    if rule.region_id:
        region = db.query(Region).filter(Region.region_id == rule.region_id).first()
        if region:
            region_ref = {"region_id": region.region_id, "region_name": region.name, "region_code": region.code}

    created_by = db.query(User).filter(User.user_id == rule.created_by_user_id).first()
    updated_by = None
    if rule.updated_by_user_id:
        updated_by = db.query(User).filter(User.user_id == rule.updated_by_user_id).first()

    return AttestationSchedulingRuleResponse(
        rule_id=rule.rule_id,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        frequency=rule.frequency,
        priority=rule.priority,
        is_active=rule.is_active,
        owner_model_count_min=rule.owner_model_count_min,
        owner_high_fluctuation_flag=rule.owner_high_fluctuation_flag,
        model_id=rule.model_id,
        region_id=rule.region_id,
        effective_date=rule.effective_date,
        end_date=rule.end_date,
        model=model_ref,
        region=region_ref,
        created_by={"user_id": created_by.user_id, "email": created_by.email, "full_name": created_by.full_name} if created_by else None,
        updated_by={"user_id": updated_by.user_id, "email": updated_by.email, "full_name": updated_by.full_name} if updated_by else None,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


# ============================================================================
# COVERAGE TARGETS ENDPOINTS
# ============================================================================

@router.get("/targets", response_model=List[CoverageTargetResponse])
def list_targets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List coverage targets."""
    targets = db.query(CoverageTarget).filter(
        or_(CoverageTarget.end_date == None, CoverageTarget.end_date >= date.today())
    ).all()

    return [_build_target_response(target, db) for target in targets]


@router.patch("/targets/{tier_id}", response_model=CoverageTargetResponse)
def update_target(
    tier_id: int,
    target_in: CoverageTargetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a coverage target. Admin only."""
    target = db.query(CoverageTarget).filter(
        CoverageTarget.risk_tier_id == tier_id,
        or_(CoverageTarget.end_date == None, CoverageTarget.end_date >= date.today())
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found for this tier")

    update_data = target_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(target, field, value)

    create_audit_log(
        db=db,
        entity_type="CoverageTarget",
        entity_id=target.target_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=update_data
    )

    db.commit()
    db.refresh(target)

    return _build_target_response(target, db)


def _build_target_response(target: CoverageTarget, db: Session) -> CoverageTargetResponse:
    """Build target response."""
    tier = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == target.risk_tier_id
    ).first()

    created_by = db.query(User).filter(User.user_id == target.created_by_user_id).first()

    return CoverageTargetResponse(
        target_id=target.target_id,
        risk_tier_id=target.risk_tier_id,
        target_percentage=target.target_percentage,
        is_blocking=target.is_blocking,
        effective_date=target.effective_date,
        end_date=target.end_date,
        risk_tier={"value_id": tier.value_id, "code": tier.code, "label": tier.label} if tier else None,
        created_by={"user_id": created_by.user_id, "email": created_by.email, "full_name": created_by.full_name} if created_by else None,
        created_at=target.created_at,
        updated_at=target.updated_at
    )


# ============================================================================
# REPORTS ENDPOINTS
# ============================================================================

@router.get("/reports/coverage", response_model=CoverageReportResponse)
def get_coverage_report(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get coverage report for a cycle."""
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    # Get all tiers
    tier_taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Model Risk Tier").first()
    if not tier_taxonomy:
        raise HTTPException(status_code=500, detail="Model Risk Tier taxonomy not found")

    tiers = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == tier_taxonomy.taxonomy_id,
        TaxonomyValue.is_active == True
    ).all()

    # Get targets
    targets = db.query(CoverageTarget).filter(
        CoverageTarget.effective_date <= date.today(),
        or_(CoverageTarget.end_date == None, CoverageTarget.end_date >= date.today())
    ).all()
    target_map = {t.risk_tier_id: t for t in targets}

    coverage_by_tier = []
    total_models = 0
    total_attested = 0
    blocking_gaps = []
    models_not_attested = []

    for tier in tiers:
        # Count models for this tier in cycle
        records = db.query(AttestationRecord).join(
            Model, Model.model_id == AttestationRecord.model_id
        ).filter(
            AttestationRecord.cycle_id == cycle_id,
            Model.risk_tier_id == tier.value_id
        ).all()

        tier_total = len(records)
        tier_attested = len([r for r in records if r.status in [
            AttestationRecordStatus.ACCEPTED.value,
            AttestationRecordStatus.SUBMITTED.value
        ]])

        total_models += tier_total
        total_attested += tier_attested

        coverage_pct = (tier_attested / tier_total * 100) if tier_total > 0 else 100

        target = target_map.get(tier.value_id)
        target_pct = float(target.target_percentage) if target else 100
        is_blocking = target.is_blocking if target else False
        meets_target = coverage_pct >= target_pct

        if not meets_target and is_blocking:
            blocking_gaps.append(f"{tier.label}: {tier_total - tier_attested} models missing (blocking)")

        # Collect non-attested models
        for record in records:
            if record.status == AttestationRecordStatus.PENDING.value:
                model = record.model
                owner = db.query(User).filter(User.user_id == model.owner_id).first()
                models_not_attested.append({
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "risk_tier_code": tier.code,
                    "owner_name": owner.full_name if owner else "Unknown"
                })

        coverage_by_tier.append(CoverageByTierResponse(
            risk_tier_code=tier.code,
            risk_tier_label=tier.label,
            total_models=tier_total,
            attested_count=tier_attested,
            coverage_pct=round(coverage_pct, 2),
            target_pct=target_pct,
            is_blocking=is_blocking,
            meets_target=meets_target,
            gap=tier_total - tier_attested
        ))

    overall_coverage_pct = (total_attested / total_models * 100) if total_models > 0 else 100

    # Build cycle summary
    cycle_summary = AttestationCycleListResponse(
        cycle_id=cycle.cycle_id,
        cycle_name=cycle.cycle_name,
        period_start_date=cycle.period_start_date,
        period_end_date=cycle.period_end_date,
        submission_due_date=cycle.submission_due_date,
        status=AttestationCycleStatusEnum(cycle.status),
        total_records=total_models,
        pending_count=0,
        submitted_count=0,
        accepted_count=total_attested,
        coverage_pct=round(overall_coverage_pct, 2)
    )

    return CoverageReportResponse(
        cycle=cycle_summary,
        coverage_by_tier=coverage_by_tier,
        overall_coverage={
            "total_models": total_models,
            "attested_count": total_attested,
            "coverage_pct": round(overall_coverage_pct, 2)
        },
        can_close_cycle=len(blocking_gaps) == 0,
        blocking_gaps=blocking_gaps,
        models_not_attested=models_not_attested
    )


@router.get("/reports/timeliness", response_model=TimelinessReportResponse)
def get_timeliness_report(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get timeliness report for a cycle."""
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    records = db.query(AttestationRecord).filter(
        AttestationRecord.cycle_id == cycle_id
    ).all()

    today = date.today()
    total_due = len(records)
    submitted_on_time = 0
    submitted_late = 0
    still_pending = 0
    total_days_to_submit = 0
    submitted_count = 0
    past_due_items = []

    for record in records:
        if record.status == AttestationRecordStatus.PENDING.value:
            still_pending += 1
            if today > record.due_date:
                model = record.model
                owner = db.query(User).filter(User.user_id == model.owner_id).first()
                tier = db.query(TaxonomyValue).filter(
                    TaxonomyValue.value_id == model.risk_tier_id
                ).first() if model.risk_tier_id else None

                past_due_items.append(TimelinessItemResponse(
                    attestation_id=record.attestation_id,
                    model_id=model.model_id,
                    model_name=model.model_name,
                    owner_name=owner.full_name if owner else "Unknown",
                    due_date=record.due_date,
                    days_overdue=(today - record.due_date).days,
                    risk_tier=tier.code if tier else "Unknown"
                ))
        else:
            submitted_count += 1
            if record.attested_at:
                attested_date = record.attested_at.date()
                if attested_date <= record.due_date:
                    submitted_on_time += 1
                else:
                    submitted_late += 1
                # Calculate days from cycle open to submission
                if cycle.opened_at:
                    days = (record.attested_at - cycle.opened_at).days
                    total_days_to_submit += days

    on_time_rate_pct = (submitted_on_time / submitted_count * 100) if submitted_count > 0 else 0
    avg_days_to_submit = (total_days_to_submit / submitted_count) if submitted_count > 0 else 0

    # Build cycle summary
    cycle_summary = AttestationCycleListResponse(
        cycle_id=cycle.cycle_id,
        cycle_name=cycle.cycle_name,
        period_start_date=cycle.period_start_date,
        period_end_date=cycle.period_end_date,
        submission_due_date=cycle.submission_due_date,
        status=AttestationCycleStatusEnum(cycle.status),
        total_records=total_due,
        pending_count=still_pending,
        submitted_count=submitted_count,
        accepted_count=0,
        coverage_pct=0
    )

    return TimelinessReportResponse(
        cycle=cycle_summary,
        timeliness_summary={
            "total_due": total_due,
            "submitted_on_time": submitted_on_time,
            "submitted_late": submitted_late,
            "still_pending": still_pending,
            "on_time_rate_pct": round(on_time_rate_pct, 2),
            "avg_days_to_submit": round(avg_days_to_submit, 1)
        },
        past_due_items=past_due_items
    )


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/stats", response_model=AttestationDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get attestation dashboard stats. Admin only."""
    today = date.today()

    # Active cycles
    active_cycles = db.query(AttestationCycle).filter(
        AttestationCycle.status == AttestationCycleStatus.OPEN.value
    ).count()

    # Pending (not submitted)
    pending_count = db.query(AttestationRecord).join(
        AttestationCycle
    ).filter(
        AttestationCycle.status == AttestationCycleStatus.OPEN.value,
        AttestationRecord.status == AttestationRecordStatus.PENDING.value
    ).count()

    # Submitted (awaiting review)
    submitted_count = db.query(AttestationRecord).join(
        AttestationCycle
    ).filter(
        AttestationCycle.status == AttestationCycleStatus.OPEN.value,
        AttestationRecord.status == AttestationRecordStatus.SUBMITTED.value
    ).count()

    # Overdue
    overdue_count = db.query(AttestationRecord).join(
        AttestationCycle
    ).filter(
        AttestationCycle.status == AttestationCycleStatus.OPEN.value,
        AttestationRecord.status == AttestationRecordStatus.PENDING.value,
        AttestationRecord.due_date < today
    ).count()

    # Pending changes
    pending_changes = db.query(AttestationChangeProposal).filter(
        AttestationChangeProposal.status == AttestationChangeStatus.PENDING.value
    ).count()

    return AttestationDashboardStats(
        pending_count=pending_count,
        submitted_count=submitted_count,
        overdue_count=overdue_count,
        pending_changes=pending_changes,
        active_cycles=active_cycles
    )


# ============================================================================
# SCHEDULING RULE HELPERS
# ============================================================================

def _resolve_attestation_frequency(db: Session, model_id: int, owner_id: int) -> str:
    """Resolve the effective attestation frequency for a model."""
    today = date.today()

    # Get model and owner
    model = db.query(Model).filter(Model.model_id == model_id).first()
    owner = db.query(User).filter(User.user_id == owner_id).first()

    if not model or not owner:
        return AttestationFrequency.ANNUAL.value

    # Get all active rules, ordered by priority DESC
    rules = db.query(AttestationSchedulingRule).filter(
        AttestationSchedulingRule.is_active == True,
        AttestationSchedulingRule.effective_date <= today,
        or_(
            AttestationSchedulingRule.end_date == None,
            AttestationSchedulingRule.end_date >= today
        )
    ).order_by(AttestationSchedulingRule.priority.desc()).all()

    for rule in rules:
        if _rule_applies(db, rule, model, owner):
            return rule.frequency

    return AttestationFrequency.ANNUAL.value


def _rule_applies(db: Session, rule: AttestationSchedulingRule, model: Model, owner: User) -> bool:
    """Check if a scheduling rule applies to a model/owner."""
    if rule.rule_type == AttestationSchedulingRuleType.MODEL_OVERRIDE.value:
        return rule.model_id == model.model_id

    if rule.rule_type == AttestationSchedulingRuleType.REGIONAL_OVERRIDE.value:
        # Check if model is deployed to this region via model_regions
        from app.models.model_region import ModelRegion
        region_deployment = db.query(ModelRegion).filter(
            ModelRegion.model_id == model.model_id,
            ModelRegion.region_id == rule.region_id
        ).first()
        return region_deployment is not None

    if rule.rule_type == AttestationSchedulingRuleType.OWNER_THRESHOLD.value:
        # Count owner's models
        owner_model_count = db.query(Model).filter(
            Model.owner_id == owner.user_id,
            Model.row_approval_status == None  # Approved
        ).count()

        if rule.owner_model_count_min and owner_model_count >= rule.owner_model_count_min:
            return True
        if rule.owner_high_fluctuation_flag and getattr(owner, 'high_fluctuation_flag', False):
            return True
        return False

    if rule.rule_type == AttestationSchedulingRuleType.GLOBAL_DEFAULT.value:
        return True

    return False


def _is_model_due_in_cycle(db: Session, model: Model, frequency: str, cycle: AttestationCycle) -> bool:
    """Determine if a model needs attestation in this cycle."""
    # Quarterly models are always due
    if frequency == AttestationFrequency.QUARTERLY.value:
        return True

    # For annual, check last accepted attestation
    last_attestation = db.query(AttestationRecord).filter(
        AttestationRecord.model_id == model.model_id,
        AttestationRecord.status == AttestationRecordStatus.ACCEPTED.value
    ).order_by(AttestationRecord.attested_at.desc()).first()

    if not last_attestation:
        return True  # Never attested

    if not last_attestation.attested_at:
        return True

    # Check if last attestation was more than 12 months ago
    months_since = (cycle.period_start_date.year - last_attestation.attested_at.year) * 12 + \
                   (cycle.period_start_date.month - last_attestation.attested_at.month)

    return months_since >= 12


def _check_blocking_targets(db: Session, cycle_id: int) -> List[str]:
    """Check if any blocking coverage targets are not met."""
    # Get coverage report data
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        return ["Cycle not found"]

    # Get all tiers
    tier_taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Model Risk Tier").first()
    if not tier_taxonomy:
        return []

    tiers = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == tier_taxonomy.taxonomy_id,
        TaxonomyValue.is_active == True
    ).all()

    # Get targets
    targets = db.query(CoverageTarget).filter(
        CoverageTarget.effective_date <= date.today(),
        or_(CoverageTarget.end_date == None, CoverageTarget.end_date >= date.today())
    ).all()
    target_map = {t.risk_tier_id: t for t in targets}

    blocking_gaps = []

    for tier in tiers:
        records = db.query(AttestationRecord).join(
            Model, Model.model_id == AttestationRecord.model_id
        ).filter(
            AttestationRecord.cycle_id == cycle_id,
            Model.risk_tier_id == tier.value_id
        ).all()

        tier_total = len(records)
        tier_attested = len([r for r in records if r.status in [
            AttestationRecordStatus.ACCEPTED.value,
            AttestationRecordStatus.SUBMITTED.value
        ]])

        coverage_pct = (tier_attested / tier_total * 100) if tier_total > 0 else 100

        target = target_map.get(tier.value_id)
        if target and target.is_blocking:
            target_pct = float(target.target_percentage)
            if coverage_pct < target_pct:
                blocking_gaps.append(
                    f"{tier.label}: {tier_total - tier_attested} models missing "
                    f"({coverage_pct:.1f}% < {target_pct:.1f}% target)"
                )

    return blocking_gaps


# ============================================================================
# CHANGE PROPOSAL ENDPOINTS
# ============================================================================

@router.post("/records/{attestation_id}/changes", response_model=AttestationChangeProposalResponse)
def create_change_proposal(
    attestation_id: int,
    proposal_in: AttestationChangeProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Propose an inventory change during attestation.

    Change types:
    - UPDATE_EXISTING: Modify an existing model (creates ModelPendingEdit)
    - NEW_MODEL: Register a new model (stored in proposed_data)
    - DECOMMISSION: Propose model decommissioning (stored in proposed_data)
    """
    # Get attestation record
    record = db.query(AttestationRecord).filter(
        AttestationRecord.attestation_id == attestation_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Attestation record not found")

    # Check permission
    model = record.model
    if current_user.role not in [UserRole.ADMIN, UserRole.VALIDATOR]:
        if not can_attest_for_model(db, current_user, model):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to propose changes for this attestation"
            )

    # Check attestation status - can only add changes before acceptance
    if record.status == AttestationRecordStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot add change proposals to an accepted attestation"
        )

    # Validate change type and required fields
    pending_edit_id = None

    if proposal_in.change_type == AttestationChangeType.UPDATE_EXISTING.value:
        # Must have model_id and proposed_data
        if not proposal_in.model_id:
            raise HTTPException(status_code=400, detail="model_id required for UPDATE_EXISTING")
        if not proposal_in.proposed_data:
            raise HTTPException(status_code=400, detail="proposed_data required for UPDATE_EXISTING")

        # Verify model exists
        target_model = db.query(Model).filter(Model.model_id == proposal_in.model_id).first()
        if not target_model:
            raise HTTPException(status_code=404, detail="Target model not found")

        # Create ModelPendingEdit for the change
        original_values = {}
        for field in proposal_in.proposed_data.keys():
            original_values[field] = getattr(target_model, field, None)

        pending_edit = ModelPendingEdit(
            model_id=proposal_in.model_id,
            requested_by_id=current_user.user_id,
            proposed_changes=proposal_in.proposed_data,
            original_values=original_values,
            status="pending"
        )
        db.add(pending_edit)
        db.flush()
        pending_edit_id = pending_edit.pending_edit_id

    elif proposal_in.change_type == AttestationChangeType.NEW_MODEL.value:
        # Must have proposed_data with model details
        if not proposal_in.proposed_data:
            raise HTTPException(status_code=400, detail="proposed_data required for NEW_MODEL")
        if 'model_name' not in proposal_in.proposed_data:
            raise HTTPException(status_code=400, detail="model_name required in proposed_data for NEW_MODEL")

    elif proposal_in.change_type == AttestationChangeType.DECOMMISSION.value:
        # Must have model_id
        if not proposal_in.model_id:
            raise HTTPException(status_code=400, detail="model_id required for DECOMMISSION")

        # Verify model exists
        target_model = db.query(Model).filter(Model.model_id == proposal_in.model_id).first()
        if not target_model:
            raise HTTPException(status_code=404, detail="Target model not found")

    # Create change proposal
    proposal = AttestationChangeProposal(
        attestation_id=attestation_id,
        pending_edit_id=pending_edit_id,
        change_type=proposal_in.change_type,
        model_id=proposal_in.model_id,
        proposed_data=proposal_in.proposed_data,
        status=AttestationChangeStatus.PENDING.value
    )
    db.add(proposal)

    create_audit_log(
        db=db,
        entity_type="AttestationChangeProposal",
        entity_id=attestation_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "change_type": proposal_in.change_type,
            "model_id": proposal_in.model_id,
            "proposed_data": proposal_in.proposed_data
        }
    )

    db.commit()
    db.refresh(proposal)

    return _build_proposal_response(proposal, db)


@router.get("/changes", response_model=List[AttestationChangeProposalResponse])
def list_change_proposals(
    status: Optional[str] = None,
    cycle_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all change proposals. Admin only."""
    query = db.query(AttestationChangeProposal).join(
        AttestationRecord, AttestationRecord.attestation_id == AttestationChangeProposal.attestation_id
    )

    if status:
        query = query.filter(AttestationChangeProposal.status == status)

    if cycle_id:
        query = query.filter(AttestationRecord.cycle_id == cycle_id)

    proposals = query.order_by(AttestationChangeProposal.created_at.desc()).all()

    return [_build_proposal_response(p, db) for p in proposals]


@router.get("/changes/{proposal_id}", response_model=AttestationChangeProposalResponse)
def get_change_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get change proposal details."""
    proposal = db.query(AttestationChangeProposal).filter(
        AttestationChangeProposal.proposal_id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Change proposal not found")

    # Check permission - admin/validator can see all, others only their own
    if current_user.role not in [UserRole.ADMIN, UserRole.VALIDATOR]:
        record = proposal.attestation
        model = record.model
        if not can_attest_for_model(db, current_user, model):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this change proposal"
            )

    return _build_proposal_response(proposal, db)


@router.post("/changes/{proposal_id}/accept", response_model=AttestationChangeProposalResponse)
def accept_change_proposal(
    proposal_id: int,
    decision: AttestationChangeProposalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Accept a change proposal. Admin only.

    For UPDATE_EXISTING: Applies the pending edit to the model.
    For NEW_MODEL: Creates the new model.
    For DECOMMISSION: Initiates decommissioning workflow.
    """
    proposal = db.query(AttestationChangeProposal).filter(
        AttestationChangeProposal.proposal_id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Change proposal not found")

    if proposal.status != AttestationChangeStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot accept proposal with status {proposal.status}"
        )

    # Process based on change type
    if proposal.change_type == AttestationChangeType.UPDATE_EXISTING.value:
        # Apply the pending edit
        if proposal.pending_edit_id:
            pending_edit = db.query(ModelPendingEdit).filter(
                ModelPendingEdit.pending_edit_id == proposal.pending_edit_id
            ).first()

            if pending_edit and pending_edit.status == "pending":
                # Apply changes to model
                target_model = db.query(Model).filter(
                    Model.model_id == pending_edit.model_id
                ).first()

                if target_model:
                    for field, value in pending_edit.proposed_changes.items():
                        if hasattr(target_model, field):
                            setattr(target_model, field, value)

                    pending_edit.status = "approved"
                    pending_edit.reviewed_by_id = current_user.user_id
                    pending_edit.reviewed_at = utc_now()
                    pending_edit.review_comment = decision.admin_comment

                    create_audit_log(
                        db=db,
                        entity_type="Model",
                        entity_id=target_model.model_id,
                        action="UPDATE",
                        user_id=current_user.user_id,
                        changes=pending_edit.proposed_changes
                    )

    elif proposal.change_type == AttestationChangeType.NEW_MODEL.value:
        # Create new model from proposed_data
        if proposal.proposed_data:
            new_model_data = proposal.proposed_data.copy()

            # Set required defaults if not provided
            if 'owner_id' not in new_model_data:
                new_model_data['owner_id'] = proposal.attestation.attesting_user_id
            if 'development_type' not in new_model_data:
                new_model_data['development_type'] = 'In-House'

            # Create the model
            new_model = Model(**new_model_data)
            new_model.row_approval_status = None  # Approved by Admin accepting this proposal
            db.add(new_model)
            db.flush()

            create_audit_log(
                db=db,
                entity_type="Model",
                entity_id=new_model.model_id,
                action="CREATE",
                user_id=current_user.user_id,
                changes={"source": "attestation_change_proposal", "proposal_id": proposal_id}
            )

    elif proposal.change_type == AttestationChangeType.DECOMMISSION.value:
        # Mark model for decommissioning (simplified - would normally trigger full workflow)
        if proposal.model_id:
            target_model = db.query(Model).filter(
                Model.model_id == proposal.model_id
            ).first()

            if target_model:
                # Update status to indicate pending decommission
                target_model.status = "Pending Decommission"

                create_audit_log(
                    db=db,
                    entity_type="Model",
                    entity_id=target_model.model_id,
                    action="DECOMMISSION_REQUESTED",
                    user_id=current_user.user_id,
                    changes={"source": "attestation_change_proposal", "proposal_id": proposal_id}
                )

    # Update proposal status
    proposal.status = AttestationChangeStatus.ACCEPTED.value
    proposal.admin_comment = decision.admin_comment
    proposal.decided_by_user_id = current_user.user_id
    proposal.decided_at = utc_now()

    create_audit_log(
        db=db,
        entity_type="AttestationChangeProposal",
        entity_id=proposal_id,
        action="ACCEPT",
        user_id=current_user.user_id,
        changes={"admin_comment": decision.admin_comment}
    )

    db.commit()
    db.refresh(proposal)

    return _build_proposal_response(proposal, db)


@router.post("/changes/{proposal_id}/reject", response_model=AttestationChangeProposalResponse)
def reject_change_proposal(
    proposal_id: int,
    decision: AttestationChangeProposalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Reject a change proposal. Admin only. Comment required."""
    if not decision.admin_comment:
        raise HTTPException(status_code=400, detail="Comment required when rejecting a change proposal")

    proposal = db.query(AttestationChangeProposal).filter(
        AttestationChangeProposal.proposal_id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Change proposal not found")

    if proposal.status != AttestationChangeStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject proposal with status {proposal.status}"
        )

    # If there's a linked pending edit, reject it too
    if proposal.pending_edit_id:
        pending_edit = db.query(ModelPendingEdit).filter(
            ModelPendingEdit.pending_edit_id == proposal.pending_edit_id
        ).first()

        if pending_edit and pending_edit.status == "pending":
            pending_edit.status = "rejected"
            pending_edit.reviewed_by_id = current_user.user_id
            pending_edit.reviewed_at = utc_now()
            pending_edit.review_comment = decision.admin_comment

    # Update proposal status
    proposal.status = AttestationChangeStatus.REJECTED.value
    proposal.admin_comment = decision.admin_comment
    proposal.decided_by_user_id = current_user.user_id
    proposal.decided_at = utc_now()

    create_audit_log(
        db=db,
        entity_type="AttestationChangeProposal",
        entity_id=proposal_id,
        action="REJECT",
        user_id=current_user.user_id,
        changes={"admin_comment": decision.admin_comment}
    )

    db.commit()
    db.refresh(proposal)

    return _build_proposal_response(proposal, db)


def _build_proposal_response(proposal: AttestationChangeProposal, db: Session) -> AttestationChangeProposalResponse:
    """Build full change proposal response."""
    model_ref = None
    if proposal.model_id:
        target_model = db.query(Model).filter(Model.model_id == proposal.model_id).first()
        if target_model:
            model_ref = {"model_id": target_model.model_id, "model_name": target_model.model_name}

    decided_by_ref = None
    if proposal.decided_by_user_id:
        decided_by = db.query(User).filter(User.user_id == proposal.decided_by_user_id).first()
        if decided_by:
            decided_by_ref = {
                "user_id": decided_by.user_id,
                "email": decided_by.email,
                "full_name": decided_by.full_name
            }

    return AttestationChangeProposalResponse(
        proposal_id=proposal.proposal_id,
        attestation_id=proposal.attestation_id,
        pending_edit_id=proposal.pending_edit_id,
        change_type=proposal.change_type,
        model_id=proposal.model_id,
        proposed_data=proposal.proposed_data,
        status=proposal.status,
        admin_comment=proposal.admin_comment,
        decided_by=decided_by_ref,
        decided_at=proposal.decided_at,
        created_at=proposal.created_at,
        model=model_ref
    )


# ============================================================================
# BULK ATTESTATION ENDPOINTS
# ============================================================================

def _get_user_attestable_records(
    db: Session,
    user: User,
    cycle_id: int
) -> List[AttestationRecord]:
    """Get all attestation records the user can attest for in a cycle."""
    # Get all records for the cycle
    records = db.query(AttestationRecord).join(
        Model, Model.model_id == AttestationRecord.model_id
    ).filter(
        AttestationRecord.cycle_id == cycle_id
    ).all()

    # Filter to records user can attest for
    attestable = []
    for record in records:
        if can_attest_for_model(db, user, record.model):
            attestable.append(record)

    return attestable


@router.get("/bulk/{cycle_id}", response_model=BulkAttestationStateResponse)
def get_bulk_attestation_state(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get bulk attestation state for current user.

    Returns models available for bulk attestation, draft state if any,
    attestation questions, and summary statistics.

    This endpoint can be called at any time to view the user's attestation
    state, including after all records have been submitted.
    """
    # Get cycle
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    # Allow viewing state for OPEN, CLOSED, and UNDER_REVIEW cycles
    # Only PENDING (not yet opened) cycles should be blocked
    if cycle.status == AttestationCycleStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Cycle is still pending - not yet open for attestations"
        )

    # Get attestable records for this user
    records = _get_user_attestable_records(db, current_user, cycle_id)

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No attestation records found for you in this cycle"
        )

    today = date.today()
    days_until_due = (cycle.submission_due_date - today).days

    # Build cycle info
    cycle_info = BulkAttestationCycleInfo(
        cycle_id=cycle.cycle_id,
        cycle_name=cycle.cycle_name,
        submission_due_date=cycle.submission_due_date,
        status=AttestationCycleStatusEnum(cycle.status),
        days_until_due=days_until_due
    )

    # Build models list
    models_list = []
    pending_count = 0
    excluded_count = 0
    submitted_count = 0
    accepted_count = 0
    rejected_count = 0

    for record in records:
        model = record.model

        # Get risk tier info
        risk_tier_code = None
        risk_tier_label = None
        if model.risk_tier_id:
            tier = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == model.risk_tier_id
            ).first()
            if tier:
                risk_tier_code = tier.code
                risk_tier_label = tier.label

        # Get last attested date
        last_attestation = db.query(AttestationRecord).filter(
            AttestationRecord.model_id == model.model_id,
            AttestationRecord.status == AttestationRecordStatus.ACCEPTED.value
        ).order_by(AttestationRecord.attested_at.desc()).first()
        last_attested_date = last_attestation.attested_at.date() if last_attestation and last_attestation.attested_at else None

        models_list.append(BulkAttestationModel(
            attestation_id=record.attestation_id,
            model_id=model.model_id,
            model_name=model.model_name,
            risk_tier_code=risk_tier_code,
            risk_tier_label=risk_tier_label,
            model_status=model.status,
            last_attested_date=last_attested_date,
            attestation_status=AttestationRecordStatusEnum(record.status),
            is_excluded=record.is_excluded
        ))

        # Count by status
        if record.status == AttestationRecordStatus.PENDING.value:
            if record.is_excluded:
                excluded_count += 1
            else:
                pending_count += 1
        elif record.status == AttestationRecordStatus.SUBMITTED.value:
            submitted_count += 1
        elif record.status == AttestationRecordStatus.ACCEPTED.value:
            accepted_count += 1
        elif record.status == AttestationRecordStatus.REJECTED.value:
            rejected_count += 1

    # Get draft if exists
    bulk_submission = db.query(AttestationBulkSubmission).filter(
        AttestationBulkSubmission.cycle_id == cycle_id,
        AttestationBulkSubmission.user_id == current_user.user_id
    ).first()

    draft_info = BulkAttestationDraftInfo(
        exists=bulk_submission is not None and bulk_submission.status == AttestationBulkSubmissionStatus.DRAFT.value,
        bulk_submission_id=bulk_submission.bulk_submission_id if bulk_submission else None,
        selected_model_ids=bulk_submission.selected_model_ids or [] if bulk_submission else [],
        excluded_model_ids=bulk_submission.excluded_model_ids or [] if bulk_submission else [],
        responses=bulk_submission.draft_responses or [] if bulk_submission else [],
        comment=bulk_submission.draft_comment if bulk_submission else None,
        last_saved=bulk_submission.updated_at if bulk_submission else None
    )

    # Get questions
    questions = get_attestation_questions(db)

    # Build summary
    summary = BulkAttestationSummary(
        total_models=len(records),
        pending_count=pending_count,
        excluded_count=excluded_count,
        submitted_count=submitted_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count
    )

    return BulkAttestationStateResponse(
        cycle=cycle_info,
        models=models_list,
        draft=draft_info,
        questions=questions,
        summary=summary
    )


@router.post("/bulk/{cycle_id}/draft", response_model=BulkAttestationDraftResponse)
def save_bulk_attestation_draft(
    cycle_id: int,
    draft_in: BulkAttestationDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save bulk attestation draft.

    Saves current progress (selected models, answers, comments) for later completion.
    Creates a new draft or updates existing one.
    """
    # Verify cycle is open
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    if cycle.status != AttestationCycleStatus.OPEN.value:
        raise HTTPException(
            status_code=400,
            detail="Cycle is not open for attestations"
        )

    # Get attestable records for this user and build validation set
    records = _get_user_attestable_records(db, current_user, cycle_id)
    records_by_model = {r.model_id: r for r in records}

    # Get model IDs that are in PENDING status (can be selected/excluded)
    pending_model_ids = {
        model_id for model_id, record in records_by_model.items()
        if record.status == AttestationRecordStatus.PENDING.value
    }

    # Validate selected_model_ids - must be pending records for this user
    invalid_selected = set(draft_in.selected_model_ids) - pending_model_ids
    if invalid_selected:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid selected model IDs (not available for attestation): {sorted(invalid_selected)}"
        )

    # Validate excluded_model_ids - must be pending records for this user
    invalid_excluded = set(draft_in.excluded_model_ids) - pending_model_ids
    if invalid_excluded:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid excluded model IDs (not available for attestation): {sorted(invalid_excluded)}"
        )

    # Ensure no overlap between selected and excluded
    overlap = set(draft_in.selected_model_ids) & set(draft_in.excluded_model_ids)
    if overlap:
        raise HTTPException(
            status_code=400,
            detail=f"Model IDs cannot be both selected and excluded: {sorted(overlap)}"
        )

    # Get or create bulk submission record
    bulk_submission = db.query(AttestationBulkSubmission).filter(
        AttestationBulkSubmission.cycle_id == cycle_id,
        AttestationBulkSubmission.user_id == current_user.user_id
    ).first()

    if bulk_submission:
        # Check if already submitted
        if bulk_submission.status == AttestationBulkSubmissionStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=400,
                detail="Bulk attestation already submitted for this cycle"
            )
        # Update existing draft
        bulk_submission.selected_model_ids = draft_in.selected_model_ids
        bulk_submission.excluded_model_ids = draft_in.excluded_model_ids
        bulk_submission.draft_responses = [r.model_dump() for r in draft_in.responses]
        bulk_submission.draft_comment = draft_in.comment
        bulk_submission.updated_at = utc_now()
    else:
        # Create new draft
        bulk_submission = AttestationBulkSubmission(
            cycle_id=cycle_id,
            user_id=current_user.user_id,
            status=AttestationBulkSubmissionStatus.DRAFT.value,
            selected_model_ids=draft_in.selected_model_ids,
            excluded_model_ids=draft_in.excluded_model_ids,
            draft_responses=[r.model_dump() for r in draft_in.responses],
            draft_comment=draft_in.comment
        )
        db.add(bulk_submission)

    # Update excluded flags on attestation records (only for PENDING records)
    for model_id, record in records_by_model.items():
        if record.status == AttestationRecordStatus.PENDING.value:
            record.is_excluded = model_id in draft_in.excluded_model_ids

    db.commit()
    db.refresh(bulk_submission)

    return BulkAttestationDraftResponse(
        success=True,
        bulk_submission_id=bulk_submission.bulk_submission_id,
        last_saved=bulk_submission.updated_at,
        message="Draft saved successfully"
    )


@router.post("/bulk/{cycle_id}/submit", response_model=BulkAttestationSubmitResponse)
def submit_bulk_attestation(
    cycle_id: int,
    submit_in: BulkAttestationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit bulk attestation.

    Creates AttestationRecord submissions for all selected models with the same
    responses. Models not in selected_model_ids are marked as excluded.
    """
    # Verify cycle is open
    cycle = db.query(AttestationCycle).filter(
        AttestationCycle.cycle_id == cycle_id
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    if cycle.status != AttestationCycleStatus.OPEN.value:
        raise HTTPException(
            status_code=400,
            detail="Cycle is not open for attestations"
        )

    # Validate at least one model selected
    if not submit_in.selected_model_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one model must be selected for bulk attestation"
        )

    # Get attestable records for this user
    records = _get_user_attestable_records(db, current_user, cycle_id)
    records_by_model = {r.model_id: r for r in records}

    # Validate all selected models belong to user's attestable records
    for model_id in submit_in.selected_model_ids:
        if model_id not in records_by_model:
            raise HTTPException(
                status_code=400,
                detail=f"Model {model_id} is not available for attestation in this cycle"
            )
        record = records_by_model[model_id]
        if record.status != AttestationRecordStatus.PENDING.value:
            raise HTTPException(
                status_code=400,
                detail=f"Model {record.model.model_name} is not in PENDING status"
            )

    # Validate questions
    questions = get_attestation_questions(db)
    question_ids = {q.value_id for q in questions}
    submitted_question_ids = {r.question_id for r in submit_in.responses}

    if submitted_question_ids != question_ids:
        raise HTTPException(
            status_code=400,
            detail="All questions must be answered"
        )

    # Validate all answers are boolean (not null)
    for response in submit_in.responses:
        if response.answer is None:
            raise HTTPException(
                status_code=400,
                detail="All questions must have a Yes or No answer"
            )

    # Validate comments for "No" answers
    question_map = {q.value_id: q for q in questions}
    for response in submit_in.responses:
        question = question_map.get(response.question_id)
        if question and not response.answer and question.requires_comment_if_no and not response.comment:
            raise HTTPException(
                status_code=400,
                detail=f"Comment required when answering 'No' to question: {question.code}"
            )

    # Determine decision based on answers
    all_yes = all(r.answer for r in submit_in.responses)
    decision = AttestationDecision.I_ATTEST.value if all_yes else AttestationDecision.I_ATTEST_WITH_UPDATES.value

    # Get or create bulk submission record
    bulk_submission = db.query(AttestationBulkSubmission).filter(
        AttestationBulkSubmission.cycle_id == cycle_id,
        AttestationBulkSubmission.user_id == current_user.user_id
    ).first()

    if bulk_submission:
        if bulk_submission.status == AttestationBulkSubmissionStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=400,
                detail="Bulk attestation already submitted for this cycle"
            )
    else:
        bulk_submission = AttestationBulkSubmission(
            cycle_id=cycle_id,
            user_id=current_user.user_id
        )
        db.add(bulk_submission)
        db.flush()

    # Check if this is a clean attestation (auto-accept)
    auto_accept = is_clean_attestation(submit_in.responses, submit_in.decision_comment)

    # Update bulk submission
    bulk_submission.status = AttestationBulkSubmissionStatus.SUBMITTED.value
    bulk_submission.selected_model_ids = submit_in.selected_model_ids
    bulk_submission.excluded_model_ids = [
        m_id for m_id in records_by_model.keys()
        if m_id not in submit_in.selected_model_ids
    ]
    bulk_submission.draft_responses = [r.model_dump() for r in submit_in.responses]
    bulk_submission.draft_comment = submit_in.decision_comment
    bulk_submission.submitted_at = utc_now()
    bulk_submission.attestation_count = len(submit_in.selected_model_ids)

    # Submit each selected record
    attestation_ids = []
    for model_id in submit_in.selected_model_ids:
        record = records_by_model[model_id]

        # Update record
        record.decision = decision
        record.decision_comment = submit_in.decision_comment
        if auto_accept:
            record.status = AttestationRecordStatus.ACCEPTED.value
            record.reviewed_at = utc_now()
            record.reviewed_by_user_id = current_user.user_id  # Self-accepted
        else:
            record.status = AttestationRecordStatus.SUBMITTED.value
        record.attested_at = utc_now()
        record.attesting_user_id = current_user.user_id
        record.bulk_submission_id = bulk_submission.bulk_submission_id
        record.is_excluded = False

        # Clone responses for this record
        for response_data in submit_in.responses:
            response = AttestationResponseModel(
                attestation_id=record.attestation_id,
                question_id=response_data.question_id,
                answer=response_data.answer,
                comment=response_data.comment
            )
            db.add(response)

        attestation_ids.append(record.attestation_id)

    # Mark excluded records
    excluded_count = 0
    for model_id, record in records_by_model.items():
        if model_id not in submit_in.selected_model_ids:
            if record.status == AttestationRecordStatus.PENDING.value:
                record.is_excluded = True
                excluded_count += 1

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="AttestationBulkSubmission",
        entity_id=bulk_submission.bulk_submission_id,
        action="AUTO_ACCEPT" if auto_accept else "SUBMIT",
        user_id=current_user.user_id,
        changes={
            "submitted_count": len(submit_in.selected_model_ids),
            "excluded_count": excluded_count,
            "decision": decision,
            "auto_accepted": auto_accept
        }
    )

    db.commit()

    # Build response message
    count = len(submit_in.selected_model_ids)
    if auto_accept:
        msg = f"Successfully submitted and auto-accepted {count} attestation{'s' if count != 1 else ''}."
    else:
        msg = f"Successfully submitted {count} attestation{'s' if count != 1 else ''}."
    if excluded_count > 0:
        msg += f" {excluded_count} model{'s' if excluded_count != 1 else ''} require{'s' if excluded_count == 1 else ''} individual attestation."

    return BulkAttestationSubmitResponse(
        success=True,
        bulk_submission_id=bulk_submission.bulk_submission_id,
        submitted_count=len(submit_in.selected_model_ids),
        excluded_count=excluded_count,
        attestation_ids=attestation_ids,
        message=msg
    )


@router.delete("/bulk/{cycle_id}/draft", response_model=BulkAttestationDiscardResponse)
def discard_bulk_attestation_draft(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Discard bulk attestation draft.

    Deletes the draft and resets any excluded flags on attestation records.
    """
    # Get bulk submission
    bulk_submission = db.query(AttestationBulkSubmission).filter(
        AttestationBulkSubmission.cycle_id == cycle_id,
        AttestationBulkSubmission.user_id == current_user.user_id
    ).first()

    if not bulk_submission:
        raise HTTPException(status_code=404, detail="No draft found for this cycle")

    if bulk_submission.status == AttestationBulkSubmissionStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot discard a submitted bulk attestation"
        )

    # Reset excluded flags on records
    records = _get_user_attestable_records(db, current_user, cycle_id)
    for record in records:
        if record.status == AttestationRecordStatus.PENDING.value:
            record.is_excluded = False

    # Delete the bulk submission
    db.delete(bulk_submission)

    create_audit_log(
        db=db,
        entity_type="AttestationBulkSubmission",
        entity_id=bulk_submission.bulk_submission_id,
        action="DISCARD_DRAFT",
        user_id=current_user.user_id,
        changes={}
    )

    db.commit()

    return BulkAttestationDiscardResponse(
        success=True,
        message="Draft discarded successfully"
    )
