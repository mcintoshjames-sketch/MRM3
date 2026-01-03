"""API endpoints for model decommissioning workflow."""
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.core.rls import can_submit_owner_actions
from app.models import (
    User, Model, ModelStatus, ModelVersion, ModelRegion, Region,
    Taxonomy, TaxonomyValue,
    DecommissioningRequest, DecommissioningStatusHistory, DecommissioningApproval,
    AuditLog
)
from app.core.roles import is_admin, is_validator, is_global_approver, is_regional_approver
from app.schemas.decommissioning import (
    DecommissioningRequestCreate,
    DecommissioningRequestUpdate,
    DecommissioningRequestResponse,
    DecommissioningRequestListItem,
    ValidatorReviewRequest,
    OwnerReviewRequest,
    ApprovalSubmitRequest,
    WithdrawRequest,
    ModelImplementationDateResponse,
    DecommissioningModelInfo,
    ReplacementModelInfo,
    DecommissioningApprovalResponse,
    DecommissioningStatusHistoryResponse,
    RegionBasic,
    REASONS_REQUIRING_REPLACEMENT
)
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/decommissioning", tags=["Decommissioning"])


# --- Helper Functions ---

def get_model_implementation_date(db: Session, model_id: int) -> Optional[date]:
    """Get the implementation date from the model's latest ACTIVE version."""
    version = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id,
        ModelVersion.status == "ACTIVE"
    ).order_by(ModelVersion.created_at.desc()).first()

    if version:
        return version.production_date or version.planned_production_date or version.actual_production_date
    return None


def get_model_status_id(db: Session, code: str) -> Optional[int]:
    """Get the status_id for a Model Status taxonomy value by code."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Model Status").first()
    if not taxonomy:
        return None
    value = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.code == code
    ).first()
    return value.value_id if value else None


def get_reason_code(db: Session, reason_id: int) -> Optional[str]:
    """Get the code for a decommission reason."""
    value = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == reason_id).first()
    return value.code if value else None


def create_status_history(
    db: Session, request_id: int, old_status: Optional[str],
    new_status: str, user_id: int, notes: Optional[str] = None
):
    """Create a status history entry."""
    history = DecommissioningStatusHistory(
        request_id=request_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=user_id,
        changed_at=utc_now(),
        notes=notes
    )
    db.add(history)


def create_approval_records(db: Session, request_id: int, model_id: int):
    """Create approval records for Global + Regional approvers based on model's regions."""
    # Always create Global approval
    global_approval = DecommissioningApproval(
        request_id=request_id,
        approver_type="GLOBAL",
        region_id=None
    )
    db.add(global_approval)

    # Create Regional approvals for each region the model is deployed in
    model_regions = db.query(ModelRegion).filter(ModelRegion.model_id == model_id).all()
    for mr in model_regions:
        regional_approval = DecommissioningApproval(
            request_id=request_id,
            approver_type="REGIONAL",
            region_id=mr.region_id
        )
        db.add(regional_approval)


def check_all_approvals_complete(db: Session, request_id: int) -> bool:
    """Check if all required approvals are complete."""
    pending = db.query(DecommissioningApproval).filter(
        DecommissioningApproval.request_id == request_id,
        DecommissioningApproval.is_approved.is_(None)
    ).count()
    return pending == 0


def check_any_rejection(db: Session, request_id: int) -> bool:
    """Check if any approval was rejected."""
    rejected = db.query(DecommissioningApproval).filter(
        DecommissioningApproval.request_id == request_id,
        DecommissioningApproval.is_approved == False
    ).count()
    return rejected > 0


def build_model_info(model: Model) -> DecommissioningModelInfo:
    """Build model info for response."""
    regions = [
        RegionBasic.model_validate(mr.region)
        for mr in (model.model_regions or [])
        if mr.region
    ]
    return DecommissioningModelInfo(
        model_id=model.model_id,
        model_name=model.model_name,
        owner_id=model.owner_id,
        owner_name=model.owner.full_name if model.owner else None,
        risk_tier=model.risk_tier.label if model.risk_tier else None,
        status=model.status_value.label if model.status_value else model.status,
        regions=regions
    )


def build_replacement_info(model: Model, db: Session) -> ReplacementModelInfo:
    """Build replacement model info for response."""
    impl_date = get_model_implementation_date(db, model.model_id)
    return ReplacementModelInfo(
        model_id=model.model_id,
        model_name=model.model_name,
        implementation_date=impl_date,
        status=model.status_value.label if model.status_value else model.status
    )


def build_request_response(request: DecommissioningRequest, db: Session) -> DecommissioningRequestResponse:
    """Build full response for a decommissioning request."""
    # Calculate gap days if replacement exists
    gap_days = None
    if request.replacement_model_id:
        replacement_date = get_model_implementation_date(db, request.replacement_model_id)
        if replacement_date and request.last_production_date:
            gap_days = (replacement_date - request.last_production_date).days

    return DecommissioningRequestResponse(
        request_id=request.request_id,
        model_id=request.model_id,
        model=build_model_info(request.model) if request.model else None,
        status=request.status,
        reason_id=request.reason_id,
        reason=TaxonomyValueResponse.model_validate(request.reason) if request.reason else None,
        replacement_model_id=request.replacement_model_id,
        replacement_model=build_replacement_info(request.replacement_model, db) if request.replacement_model else None,
        last_production_date=request.last_production_date,
        gap_justification=request.gap_justification,
        gap_days=gap_days,
        archive_location=request.archive_location,
        downstream_impact_verified=request.downstream_impact_verified,
        created_at=request.created_at,
        created_by_id=request.created_by_id,
        created_by=UserResponse.model_validate(request.created_by) if request.created_by else None,
        validator_reviewed_by_id=request.validator_reviewed_by_id,
        validator_reviewed_by=(
            UserResponse.model_validate(request.validator_reviewed_by)
            if request.validator_reviewed_by
            else None
        ),
        validator_reviewed_at=request.validator_reviewed_at,
        validator_comment=request.validator_comment,
        owner_approval_required=request.owner_approval_required,
        owner_reviewed_by_id=request.owner_reviewed_by_id,
        owner_reviewed_by=(
            UserResponse.model_validate(request.owner_reviewed_by)
            if request.owner_reviewed_by
            else None
        ),
        owner_reviewed_at=request.owner_reviewed_at,
        owner_comment=request.owner_comment,
        final_reviewed_at=request.final_reviewed_at,
        rejection_reason=request.rejection_reason,
        status_history=[
            DecommissioningStatusHistoryResponse.model_validate(history)
            for history in (request.status_history or [])
        ],
        approvals=[
            DecommissioningApprovalResponse.model_validate(approval)
            for approval in (request.approvals or [])
        ]
    )


# --- Endpoints ---

@router.post("/", response_model=DecommissioningRequestResponse, status_code=status.HTTP_201_CREATED)
def create_decommissioning_request(
    data: DecommissioningRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new decommissioning request.

    Business Rules:
    - Reasons REPLACEMENT and CONSOLIDATION require a replacement_model_id
    - If replacement model has no implementation date, replacement_implementation_date must be provided
    - If gap exists between dates, gap_justification is required
    - downstream_impact_verified must be True
    """
    # Validate model exists
    model = db.query(Model).options(
        joinedload(Model.model_regions).joinedload(ModelRegion.region)
    ).filter(Model.model_id == data.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Check no pending decommissioning request exists for this model
    existing = db.query(DecommissioningRequest).filter(
        DecommissioningRequest.model_id == data.model_id,
        DecommissioningRequest.status.in_(["PENDING", "VALIDATOR_APPROVED"])
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Model already has a pending decommissioning request (ID: {existing.request_id})"
        )

    # Validate reason is from correct taxonomy
    reason = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == data.reason_id).first()
    if not reason:
        raise HTTPException(status_code=400, detail="Invalid reason_id")

    taxonomy = db.query(Taxonomy).filter(Taxonomy.taxonomy_id == reason.taxonomy_id).first()
    if not taxonomy or taxonomy.name != "Model Decommission Reason":
        raise HTTPException(status_code=400, detail="reason_id must be from 'Model Decommission Reason' taxonomy")

    # Check if reason requires replacement
    reason_code = reason.code
    requires_replacement = reason_code in REASONS_REQUIRING_REPLACEMENT

    if requires_replacement and not data.replacement_model_id:
        raise HTTPException(
            status_code=400,
            detail=f"Reason '{reason.label}' requires a replacement model"
        )

    replacement_impl_date = None
    if data.replacement_model_id:
        # Validate replacement model exists
        replacement = db.query(Model).filter(Model.model_id == data.replacement_model_id).first()
        if not replacement:
            raise HTTPException(status_code=400, detail="Replacement model not found")

        if data.replacement_model_id == data.model_id:
            raise HTTPException(status_code=400, detail="Model cannot be its own replacement")

        # Check replacement model's implementation date
        replacement_impl_date = get_model_implementation_date(db, data.replacement_model_id)

        if not replacement_impl_date:
            # Need to create a version with the provided date
            if not data.replacement_implementation_date:
                raise HTTPException(
                    status_code=400,
                    detail="Replacement model has no implementation date. Please provide replacement_implementation_date."
                )

            # Create a new version for the replacement model
            new_version = ModelVersion(
                model_id=data.replacement_model_id,
                version_number="1.0",
                change_type="INITIAL",
                change_description="Implementation date set during decommissioning workflow",
                created_by_id=current_user.user_id,
                production_date=data.replacement_implementation_date,
                planned_production_date=data.replacement_implementation_date,
                status="DRAFT",
                scope="GLOBAL"
            )
            db.add(new_version)
            db.flush()
            replacement_impl_date = data.replacement_implementation_date

        # Gap analysis
        if replacement_impl_date > data.last_production_date:
            # Gap exists
            if not data.gap_justification or not data.gap_justification.strip():
                gap_days = (replacement_impl_date - data.last_production_date).days
                raise HTTPException(
                    status_code=400,
                    detail=f"There is a {gap_days}-day gap between the retirement date and replacement implementation. gap_justification is required."
                )

    # Validate downstream impact verified
    if not data.downstream_impact_verified:
        raise HTTPException(
            status_code=400,
            detail="You must verify downstream impact before submitting (downstream_impact_verified must be true)"
        )

    # Determine if owner approval is required (requestor is not the model owner)
    owner_approval_required = current_user.user_id != model.owner_id

    # Create the request
    decom_request = DecommissioningRequest(
        model_id=data.model_id,
        status="PENDING",
        reason_id=data.reason_id,
        replacement_model_id=data.replacement_model_id,
        last_production_date=data.last_production_date,
        gap_justification=data.gap_justification,
        archive_location=data.archive_location,
        downstream_impact_verified=data.downstream_impact_verified,
        created_at=utc_now(),
        created_by_id=current_user.user_id,
        owner_approval_required=owner_approval_required
    )
    db.add(decom_request)
    db.flush()

    # Create status history
    create_status_history(db, decom_request.request_id, None, "PENDING", current_user.user_id, "Request created")

    # Update model status to DECOMMISSIONING
    decommissioning_status_id = get_model_status_id(db, "DECOMMISSIONING")
    if decommissioning_status_id:
        model.status_id = decommissioning_status_id
    model.status = ModelStatus.PENDING_DECOMMISSION

    # Create audit log
    audit_log = AuditLog(
        entity_type="DecommissioningRequest",
        entity_id=decom_request.request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "model_id": data.model_id,
            "model_name": model.model_name,
            "reason": reason.label,
            "replacement_model_id": data.replacement_model_id,
            "last_production_date": str(data.last_production_date),
            "owner_approval_required": owner_approval_required
        }
    )
    db.add(audit_log)

    db.commit()

    # Reload with relationships
    db.refresh(decom_request)
    request_with_rels = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model).joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(DecommissioningRequest.model).joinedload(Model.owner),
        joinedload(DecommissioningRequest.model).joinedload(Model.risk_tier),
        joinedload(DecommissioningRequest.model).joinedload(Model.status_value),
        joinedload(DecommissioningRequest.replacement_model),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.created_by),
        joinedload(DecommissioningRequest.status_history).joinedload(DecommissioningStatusHistory.changed_by),
        joinedload(DecommissioningRequest.approvals).joinedload(DecommissioningApproval.region),
    ).filter(DecommissioningRequest.request_id == decom_request.request_id).first()

    if not request_with_rels:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    return build_request_response(request_with_rels, db)


@router.get("/", response_model=List[DecommissioningRequestListItem])
def list_decommissioning_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    model_id: Optional[int] = Query(None, description="Filter by model"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all decommissioning requests with optional filters."""
    query = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model),
        joinedload(DecommissioningRequest.replacement_model),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.created_by)
    )

    if status:
        query = query.filter(DecommissioningRequest.status == status)
    if model_id:
        query = query.filter(DecommissioningRequest.model_id == model_id)

    requests = query.order_by(DecommissioningRequest.created_at.desc()).all()

    return [
        DecommissioningRequestListItem(
            request_id=r.request_id,
            model_id=r.model_id,
            model_name=r.model.model_name if r.model else "Unknown",
            status=r.status,
            reason=r.reason.label if r.reason else None,
            replacement_model_id=r.replacement_model_id,
            replacement_model_name=r.replacement_model.model_name if r.replacement_model else None,
            last_production_date=r.last_production_date,
            created_at=r.created_at,
            created_by_name=r.created_by.full_name if r.created_by else None
        )
        for r in requests
    ]


@router.get("/pending-validator-review", response_model=List[DecommissioningRequestListItem])
def get_pending_validator_review(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get decommissioning requests pending validator review (for Validator dashboard)."""
    if not (is_admin(current_user) or is_validator(current_user)):
        raise HTTPException(status_code=403, detail="Only Validators and Admins can view this")

    requests = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.created_by)
    ).filter(
        DecommissioningRequest.status == "PENDING"
    ).order_by(DecommissioningRequest.created_at.asc()).all()

    return [
        DecommissioningRequestListItem(
            request_id=r.request_id,
            model_id=r.model_id,
            model_name=r.model.model_name if r.model else "Unknown",
            status=r.status,
            reason=r.reason.label if r.reason else None,
            replacement_model_id=r.replacement_model_id,
            replacement_model_name=None,
            last_production_date=r.last_production_date,
            created_at=r.created_at,
            created_by_name=r.created_by.full_name if r.created_by else None
        )
        for r in requests
    ]


@router.get("/my-pending-approvals", response_model=List[DecommissioningRequestListItem])
def get_my_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get decommissioning requests pending approval by current user (Global/Regional approver)."""
    # Build filter based on user role
    if is_admin(current_user):
        # Admin can see all pending approvals
        pending_requests = db.query(DecommissioningRequest).options(
            joinedload(DecommissioningRequest.model),
            joinedload(DecommissioningRequest.reason),
            joinedload(DecommissioningRequest.created_by),
            joinedload(DecommissioningRequest.approvals)
        ).filter(
            DecommissioningRequest.status == "VALIDATOR_APPROVED"
        ).all()

        # Filter to those with pending approvals
        requests = [r for r in pending_requests if any(a.is_approved is None for a in r.approvals)]

    elif is_global_approver(current_user):
        # Can approve GLOBAL approvals
        requests = db.query(DecommissioningRequest).join(
            DecommissioningApproval
        ).options(
            joinedload(DecommissioningRequest.model),
            joinedload(DecommissioningRequest.reason),
            joinedload(DecommissioningRequest.created_by)
        ).filter(
            DecommissioningRequest.status == "VALIDATOR_APPROVED",
            DecommissioningApproval.approver_type == "GLOBAL",
            DecommissioningApproval.is_approved.is_(None)
        ).all()

    elif is_regional_approver(current_user):
        # Can approve REGIONAL approvals for their regions
        user_region_ids = [r.region_id for r in current_user.regions]
        requests = db.query(DecommissioningRequest).join(
            DecommissioningApproval
        ).options(
            joinedload(DecommissioningRequest.model),
            joinedload(DecommissioningRequest.reason),
            joinedload(DecommissioningRequest.created_by)
        ).filter(
            DecommissioningRequest.status == "VALIDATOR_APPROVED",
            DecommissioningApproval.approver_type == "REGIONAL",
            DecommissioningApproval.region_id.in_(user_region_ids),
            DecommissioningApproval.is_approved.is_(None)
        ).all()

    else:
        requests = []

    return [
        DecommissioningRequestListItem(
            request_id=r.request_id,
            model_id=r.model_id,
            model_name=r.model.model_name if r.model else "Unknown",
            status=r.status,
            reason=r.reason.label if r.reason else None,
            replacement_model_id=r.replacement_model_id,
            replacement_model_name=None,
            last_production_date=r.last_production_date,
            created_at=r.created_at,
            created_by_name=r.created_by.full_name if r.created_by else None
        )
        for r in requests
    ]


@router.get("/my-pending-owner-reviews", response_model=List[DecommissioningRequestListItem])
def get_my_pending_owner_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get decommissioning requests pending owner review by current user.

    Returns requests where:
    - Current user is the model owner
    - owner_approval_required is True
    - Owner has not yet reviewed (owner_reviewed_at is NULL)
    - Status is PENDING
    """
    requests = db.query(DecommissioningRequest).join(
        Model, DecommissioningRequest.model_id == Model.model_id
    ).options(
        joinedload(DecommissioningRequest.model),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.created_by)
    ).filter(
        Model.owner_id == current_user.user_id,
        DecommissioningRequest.owner_approval_required == True,
        DecommissioningRequest.owner_reviewed_at.is_(None),
        DecommissioningRequest.status == "PENDING"
    ).order_by(DecommissioningRequest.created_at.asc()).all()

    return [
        DecommissioningRequestListItem(
            request_id=r.request_id,
            model_id=r.model_id,
            model_name=r.model.model_name if r.model else "Unknown",
            status=r.status,
            reason=r.reason.label if r.reason else None,
            replacement_model_id=r.replacement_model_id,
            replacement_model_name=None,
            last_production_date=r.last_production_date,
            created_at=r.created_at,
            created_by_name=r.created_by.full_name if r.created_by else None
        )
        for r in requests
    ]


@router.get("/{request_id}", response_model=DecommissioningRequestResponse)
def get_decommissioning_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a decommissioning request by ID with full details."""
    request = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model).joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(DecommissioningRequest.model).joinedload(Model.owner),
        joinedload(DecommissioningRequest.model).joinedload(Model.risk_tier),
        joinedload(DecommissioningRequest.model).joinedload(Model.status_value),
        joinedload(DecommissioningRequest.replacement_model),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.created_by),
        joinedload(DecommissioningRequest.validator_reviewed_by),
        joinedload(DecommissioningRequest.owner_reviewed_by),
        joinedload(DecommissioningRequest.status_history).joinedload(DecommissioningStatusHistory.changed_by),
        joinedload(DecommissioningRequest.approvals).joinedload(DecommissioningApproval.region),
        joinedload(DecommissioningRequest.approvals).joinedload(DecommissioningApproval.approved_by),
    ).filter(DecommissioningRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    return build_request_response(request, db)


@router.patch("/{request_id}", response_model=DecommissioningRequestResponse)
def update_decommissioning_request(
    request_id: int,
    data: DecommissioningRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a decommissioning request.

    Restrictions:
    - Only allowed while status is PENDING (before any approvals)
    - Only the request creator or Admin can update
    - All validation rules from create apply (e.g., gap justification if gap exists)
    """
    request = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model).joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(DecommissioningRequest.model).joinedload(Model.owner),
        joinedload(DecommissioningRequest.replacement_model),
        joinedload(DecommissioningRequest.reason),
    ).filter(DecommissioningRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    # Check status - only PENDING requests can be updated
    if request.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update request in status '{request.status}'. Updates only allowed while PENDING."
        )

    # Permission check - only creator or Admin
    if not is_admin(current_user) and current_user.user_id != request.created_by_id:
        raise HTTPException(
            status_code=403,
            detail="Only the request creator or Admin can update this request"
        )

    # Track changes for audit log
    changes = {}

    # Update reason_id if provided
    if data.reason_id is not None and data.reason_id != request.reason_id:
        reason = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == data.reason_id).first()
        if not reason:
            raise HTTPException(status_code=400, detail="Invalid reason_id")

        taxonomy = db.query(Taxonomy).filter(Taxonomy.taxonomy_id == reason.taxonomy_id).first()
        if not taxonomy or taxonomy.name != "Model Decommission Reason":
            raise HTTPException(status_code=400, detail="reason_id must be from 'Model Decommission Reason' taxonomy")

        old_reason = request.reason.label if request.reason else None
        changes["reason"] = {"old": old_reason, "new": reason.label}
        request.reason_id = data.reason_id

    # Determine the effective reason code for replacement validation
    effective_reason_code = get_reason_code(db, request.reason_id)
    requires_replacement = effective_reason_code in REASONS_REQUIRING_REPLACEMENT

    # Update replacement_model_id if provided
    if data.replacement_model_id is not None:
        if data.replacement_model_id != request.replacement_model_id:
            if data.replacement_model_id == request.model_id:
                raise HTTPException(status_code=400, detail="Model cannot be its own replacement")

            replacement = db.query(Model).filter(Model.model_id == data.replacement_model_id).first()
            if not replacement:
                raise HTTPException(status_code=400, detail="Replacement model not found")

            old_replacement = request.replacement_model.model_name if request.replacement_model else None
            changes["replacement_model"] = {"old": old_replacement, "new": replacement.model_name}
            request.replacement_model_id = data.replacement_model_id

    # After reason/replacement changes, validate replacement requirement
    if requires_replacement and not request.replacement_model_id:
        reason_label = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == request.reason_id).first()
        raise HTTPException(
            status_code=400,
            detail=f"Reason '{reason_label.label if reason_label else effective_reason_code}' requires a replacement model"
        )

    # Update last_production_date if provided
    if data.last_production_date is not None and data.last_production_date != request.last_production_date:
        changes["last_production_date"] = {
            "old": str(request.last_production_date),
            "new": str(data.last_production_date)
        }
        request.last_production_date = data.last_production_date

    # Handle replacement implementation date
    if data.replacement_implementation_date is not None and request.replacement_model_id:
        replacement_impl_date = get_model_implementation_date(db, request.replacement_model_id)

        if not replacement_impl_date:
            # Create a new version for the replacement model with the provided date
            new_version = ModelVersion(
                model_id=request.replacement_model_id,
                version_number="1.0",
                change_type="INITIAL",
                change_description="Implementation date set during decommissioning workflow update",
                created_by_id=current_user.user_id,
                production_date=data.replacement_implementation_date,
                planned_production_date=data.replacement_implementation_date,
                status="DRAFT",
                scope="GLOBAL"
            )
            db.add(new_version)
            db.flush()
            changes["replacement_implementation_date"] = {"old": None, "new": str(data.replacement_implementation_date)}

    # Gap analysis after updates
    if request.replacement_model_id and request.last_production_date:
        replacement_impl_date = get_model_implementation_date(db, request.replacement_model_id)
        if replacement_impl_date and replacement_impl_date > request.last_production_date:
            # Gap exists - check if gap_justification is provided or already exists
            effective_justification = data.gap_justification if data.gap_justification is not None else request.gap_justification
            if not effective_justification or not effective_justification.strip():
                gap_days = (replacement_impl_date - request.last_production_date).days
                raise HTTPException(
                    status_code=400,
                    detail=f"There is a {gap_days}-day gap between the retirement date and replacement implementation. gap_justification is required."
                )

    # Update gap_justification if provided
    if data.gap_justification is not None and data.gap_justification != request.gap_justification:
        changes["gap_justification"] = {
            "old": request.gap_justification,
            "new": data.gap_justification
        }
        request.gap_justification = data.gap_justification

    # Update archive_location if provided
    if data.archive_location is not None and data.archive_location != request.archive_location:
        changes["archive_location"] = {
            "old": request.archive_location,
            "new": data.archive_location
        }
        request.archive_location = data.archive_location

    # Only create audit log if there were actual changes
    if changes:
        audit_log = AuditLog(
            entity_type="DecommissioningRequest",
            entity_id=request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes={
                "model_name": request.model.model_name if request.model else None,
                "fields_changed": changes
            }
        )
        db.add(audit_log)

    db.commit()

    # Reload with all relationships
    request_with_rels = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model).joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(DecommissioningRequest.model).joinedload(Model.owner),
        joinedload(DecommissioningRequest.model).joinedload(Model.risk_tier),
        joinedload(DecommissioningRequest.model).joinedload(Model.status_value),
        joinedload(DecommissioningRequest.replacement_model),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.created_by),
        joinedload(DecommissioningRequest.validator_reviewed_by),
        joinedload(DecommissioningRequest.owner_reviewed_by),
        joinedload(DecommissioningRequest.status_history).joinedload(DecommissioningStatusHistory.changed_by),
        joinedload(DecommissioningRequest.approvals).joinedload(DecommissioningApproval.region),
        joinedload(DecommissioningRequest.approvals).joinedload(DecommissioningApproval.approved_by),
    ).filter(DecommissioningRequest.request_id == request_id).first()

    if not request_with_rels:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    return build_request_response(request_with_rels, db)


@router.post("/{request_id}/validator-review")
def submit_validator_review(
    request_id: int,
    review: ValidatorReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit validator review (Stage 1).

    Only Validators and Admins can review.
    Request must be in PENDING status and not yet reviewed by validator.

    Dual Approval Logic:
    - If owner_approval_required is True AND owner hasn't approved yet:
      - Validator approval is recorded, but status stays PENDING
    - Otherwise (owner not required OR owner already approved):
      - Status moves to VALIDATOR_APPROVED and Stage 2 approvals are created
    """
    if not (is_admin(current_user) or is_validator(current_user)):
        raise HTTPException(status_code=403, detail="Only Validators and Admins can review decommissioning requests")

    request = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model).joinedload(Model.model_regions)
    ).filter(DecommissioningRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is not pending review (current status: {request.status})")

    if request.validator_reviewed_at is not None:
        raise HTTPException(status_code=400, detail="Validator has already reviewed this request")

    old_status = request.status
    request.validator_reviewed_by_id = current_user.user_id
    request.validator_reviewed_at = utc_now()
    request.validator_comment = review.comment

    if review.approved:
        # Check if we can proceed to VALIDATOR_APPROVED or need to wait for owner
        owner_pending = request.owner_approval_required and request.owner_reviewed_at is None

        if owner_pending:
            # Owner approval still needed - stay in PENDING, just record validator approval
            create_status_history(
                db, request_id, old_status, "PENDING",
                current_user.user_id, f"Validator approved. Awaiting model owner approval. Comment: {review.comment}"
            )
        else:
            # Owner not required OR owner already approved - proceed to Stage 2
            request.status = "VALIDATOR_APPROVED"
            create_approval_records(db, request_id, request.model_id)
            create_status_history(db, request_id, old_status, "VALIDATOR_APPROVED", current_user.user_id, review.comment)
    else:
        request.status = "REJECTED"
        request.rejection_reason = review.comment
        request.final_reviewed_at = utc_now()
        create_status_history(db, request_id, old_status, "REJECTED", current_user.user_id, review.comment)

        # Revert model status (remove DECOMMISSIONING)
        model = request.model
        active_status_id = get_model_status_id(db, "ACTIVE")
        if active_status_id:
            model.status_id = active_status_id
        model.status = ModelStatus.ACTIVE

    # Create audit log
    audit_log = AuditLog(
        entity_type="DecommissioningRequest",
        entity_id=request_id,
        action="VALIDATOR_REVIEW",
        user_id=current_user.user_id,
        changes={
            "decision": "Approved" if review.approved else "Rejected",
            "comment": review.comment,
            "old_status": old_status,
            "new_status": request.status,
            "model_name": request.model.model_name if request.model else None
        }
    )
    db.add(audit_log)

    db.commit()

    return {
        "message": f"Validator review submitted: {'Approved' if review.approved else 'Rejected'}",
        "status": request.status
    }


@router.post("/{request_id}/owner-review")
def submit_owner_review(
    request_id: int,
    review: OwnerReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit model owner review (Stage 1 - parallel with validator if owner != requestor).

    Only the model owner or Admin can submit owner review.
    Request must be in PENDING status, owner_approval_required must be True,
    and owner must not have already reviewed.

    Dual Approval Logic:
    - If rejected: Status moves to REJECTED (terminates workflow)
    - If approved AND validator hasn't approved yet:
      - Owner approval is recorded, but status stays PENDING
    - If approved AND validator already approved:
      - Status moves to VALIDATOR_APPROVED and Stage 2 approvals are created
    """
    request = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.model).joinedload(Model.model_regions)
    ).filter(DecommissioningRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    # Check owner_approval_required
    if not request.owner_approval_required:
        raise HTTPException(
            status_code=400,
            detail="Owner approval is not required for this request (requestor is the model owner)"
        )

    # Permission check: Admin, model owner, or delegate with can_submit_changes permission
    model_id = request.model.model_id if request.model else None
    if not model_id or not can_submit_owner_actions(model_id, current_user, db):
        raise HTTPException(
            status_code=403,
            detail="Only the model owner, Admin, or a delegate with change submission permission can submit owner review"
        )

    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is not pending review (current status: {request.status})")

    if request.owner_reviewed_at is not None:
        raise HTTPException(status_code=400, detail="Owner has already reviewed this request")

    old_status = request.status
    request.owner_reviewed_by_id = current_user.user_id
    request.owner_reviewed_at = utc_now()
    request.owner_comment = review.comment

    if review.approved:
        # Check if validator has already approved
        validator_approved = request.validator_reviewed_at is not None

        if not validator_approved:
            # Validator approval still needed - stay in PENDING, just record owner approval
            create_status_history(
                db, request_id, old_status, "PENDING",
                current_user.user_id, f"Model owner approved. Awaiting validator approval. Comment: {review.comment}"
            )
        else:
            # Validator already approved - proceed to Stage 2
            request.status = "VALIDATOR_APPROVED"
            create_approval_records(db, request_id, request.model_id)
            create_status_history(
                db, request_id, old_status, "VALIDATOR_APPROVED",
                current_user.user_id, f"Model owner approved (validator already approved). Comment: {review.comment}"
            )
    else:
        # Rejection - terminate the workflow
        request.status = "REJECTED"
        request.rejection_reason = review.comment
        request.final_reviewed_at = utc_now()
        create_status_history(db, request_id, old_status, "REJECTED", current_user.user_id, review.comment)

        # Revert model status (remove DECOMMISSIONING)
        model = request.model
        active_status_id = get_model_status_id(db, "ACTIVE")
        if active_status_id:
            model.status_id = active_status_id
        model.status = ModelStatus.ACTIVE

    # Create audit log
    audit_log = AuditLog(
        entity_type="DecommissioningRequest",
        entity_id=request_id,
        action="OWNER_REVIEW",
        user_id=current_user.user_id,
        changes={
            "decision": "Approved" if review.approved else "Rejected",
            "comment": review.comment,
            "old_status": old_status,
            "new_status": request.status,
            "model_name": request.model.model_name if request.model else None
        }
    )
    db.add(audit_log)

    db.commit()

    return {
        "message": f"Owner review submitted: {'Approved' if review.approved else 'Rejected'}",
        "status": request.status
    }


@router.post("/{request_id}/approvals/{approval_id}")
def submit_approval(
    request_id: int,
    approval_id: int,
    data: ApprovalSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit Global/Regional approval (Stage 2).

    - Admins can approve any approval
    - Global Approvers can approve GLOBAL approvals
    - Regional Approvers can approve REGIONAL approvals for their regions
    """
    request = db.query(DecommissioningRequest).filter(
        DecommissioningRequest.request_id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    if request.status != "VALIDATOR_APPROVED":
        raise HTTPException(status_code=400, detail=f"Request is not pending management approval (current status: {request.status})")

    approval = db.query(DecommissioningApproval).filter(
        DecommissioningApproval.approval_id == approval_id,
        DecommissioningApproval.request_id == request_id
    ).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval record not found")

    if approval.is_approved is not None:
        raise HTTPException(status_code=400, detail="This approval has already been submitted")

    # Permission check
    can_approve = False
    if is_admin(current_user):
        can_approve = True
    elif approval.approver_type == "GLOBAL" and is_global_approver(current_user):
        can_approve = True
    elif approval.approver_type == "REGIONAL" and is_regional_approver(current_user):
        user_region_ids = [r.region_id for r in current_user.regions]
        can_approve = approval.region_id in user_region_ids

    if not can_approve:
        raise HTTPException(status_code=403, detail="You do not have permission to submit this approval")

    # Submit approval
    approval.approved_by_id = current_user.user_id
    approval.approved_at = utc_now()
    approval.is_approved = data.is_approved
    approval.comment = data.comment

    if not data.is_approved:
        # Rejection - fail the entire request
        old_status = request.status
        request.status = "REJECTED"
        request.rejection_reason = data.comment or f"Rejected by {approval.approver_type} approver"
        request.final_reviewed_at = utc_now()
        create_status_history(db, request_id, old_status, "REJECTED", current_user.user_id, data.comment)

        # Revert model status
        model = db.query(Model).filter(Model.model_id == request.model_id).first()
        active_status_id = get_model_status_id(db, "ACTIVE")
        if active_status_id and model:
            model.status_id = active_status_id
            model.status = ModelStatus.ACTIVE
    else:
        # Check if all approvals are now complete
        if check_all_approvals_complete(db, request_id):
            old_status = request.status
            request.status = "APPROVED"
            request.final_reviewed_at = utc_now()
            create_status_history(db, request_id, old_status, "APPROVED", current_user.user_id, "All approvals complete")

            # Update model status to RETIRED
            model = db.query(Model).filter(Model.model_id == request.model_id).first()
            retired_status_id = get_model_status_id(db, "RETIRED")
            if retired_status_id and model:
                model.status_id = retired_status_id
            if model:
                model.status = ModelStatus.RETIRED

    # Get model name for audit log
    model_for_audit = db.query(Model).filter(Model.model_id == request.model_id).first()

    # Get region name for regional approvals
    region_name = None
    if approval.approver_type == "REGIONAL" and approval.region_id:
        region = db.query(Region).filter(Region.region_id == approval.region_id).first()
        region_name = region.name if region else None

    # Create audit log
    audit_log = AuditLog(
        entity_type="DecommissioningRequest",
        entity_id=request_id,
        action="STAGE2_APPROVAL",
        user_id=current_user.user_id,
        changes={
            "decision": "Approved" if data.is_approved else "Rejected",
            "approver_type": approval.approver_type,
            "region": region_name,
            "comment": data.comment,
            "new_status": request.status,
            "model_name": model_for_audit.model_name if model_for_audit else None
        }
    )
    db.add(audit_log)

    db.commit()

    return {
        "message": f"Approval submitted: {'Approved' if data.is_approved else 'Rejected'}",
        "request_status": request.status
    }


@router.post("/{request_id}/withdraw")
def withdraw_request(
    request_id: int,
    data: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Withdraw a decommissioning request.

    - Only the creator or Admin can withdraw
    - Can only withdraw if status is PENDING or VALIDATOR_APPROVED
    """
    request = db.query(DecommissioningRequest).filter(
        DecommissioningRequest.request_id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Decommissioning request not found")

    # Permission check
    if not is_admin(current_user) and current_user.user_id != request.created_by_id:
        raise HTTPException(status_code=403, detail="Only the creator or Admin can withdraw this request")

    if request.status not in ["PENDING", "VALIDATOR_APPROVED"]:
        raise HTTPException(status_code=400, detail=f"Cannot withdraw request in status: {request.status}")

    old_status = request.status
    request.status = "WITHDRAWN"
    request.final_reviewed_at = utc_now()
    create_status_history(db, request_id, old_status, "WITHDRAWN", current_user.user_id, data.reason)

    # Revert model status
    model = db.query(Model).filter(Model.model_id == request.model_id).first()
    active_status_id = get_model_status_id(db, "ACTIVE")
    if active_status_id and model:
        model.status_id = active_status_id
        model.status = ModelStatus.ACTIVE

    # Create audit log
    audit_log = AuditLog(
        entity_type="DecommissioningRequest",
        entity_id=request_id,
        action="WITHDRAW",
        user_id=current_user.user_id,
        changes={
            "reason": data.reason,
            "old_status": old_status,
            "new_status": "WITHDRAWN",
            "model_name": model.model_name if model else None
        }
    )
    db.add(audit_log)

    db.commit()

    return {"message": "Request withdrawn", "status": request.status}


# --- Helper endpoint for frontend ---

@router.get("/models/{model_id}/implementation-date", response_model=ModelImplementationDateResponse)
def get_model_implementation_date_endpoint(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a model's implementation date from its latest ACTIVE version."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get latest version
    latest_version = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id
    ).order_by(ModelVersion.created_at.desc()).first()

    impl_date = None
    if latest_version:
        impl_date = latest_version.production_date or latest_version.planned_production_date or latest_version.actual_production_date

    return ModelImplementationDateResponse(
        model_id=model.model_id,
        model_name=model.model_name,
        has_implementation_date=impl_date is not None,
        implementation_date=impl_date,
        latest_version_id=latest_version.version_id if latest_version else None,
        latest_version_status=latest_version.status if latest_version else None
    )
