"""Model Exceptions API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.core.exception_detection import (
    detect_type1_unmitigated_performance,
    detect_type1_persistent_red_for_model,
    detect_type2_outside_intended_purpose,
    detect_type3_use_prior_to_validation,
    acknowledge_exception,
    close_exception_manually,
    generate_exception_code,
)
from app.core.rls import apply_exception_rls, can_access_exception, can_access_model
from app.models.user import User
from app.core.roles import is_admin
from app.models.model import Model
from app.models.model_region import ModelRegion
from app.models.audit_log import AuditLog
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model_exception import ModelException, ModelExceptionStatusHistory
from app.schemas.model_exception import (
    ModelExceptionListResponse,
    ModelExceptionDetailResponse,
    ModelExceptionStatusHistoryResponse,
    AcknowledgeExceptionRequest,
    CloseExceptionRequest,
    CreateExceptionRequest,
    DetectionResponse,
    PaginatedExceptionResponse,
    ExceptionSummary,
    UserBrief,
    ModelBrief,
    TaxonomyValueBrief,
    EXCEPTION_TYPES,
    EXCEPTION_STATUSES,
)

router = APIRouter()

MAX_DETECT_ALL_MODELS = 200


# =============================================================================
# Helper Functions
# =============================================================================

def _build_exception_list_response(exc: ModelException) -> ModelExceptionListResponse:
    """Build list response from exception model."""
    return ModelExceptionListResponse(
        exception_id=exc.exception_id,
        exception_code=exc.exception_code,
        model_id=exc.model_id,
        model=ModelBrief(
            model_id=exc.model.model_id,
            model_name=exc.model.model_name,
            model_code=None,  # Model doesn't have model_code field
        ),
        exception_type=exc.exception_type,
        status=exc.status,
        description=exc.description,
        detected_at=exc.detected_at,
        auto_closed=exc.auto_closed,
        acknowledged_at=exc.acknowledged_at,
        closed_at=exc.closed_at,
        created_at=exc.created_at,
        updated_at=exc.updated_at,
    )


def _build_exception_detail_response(exc: ModelException) -> ModelExceptionDetailResponse:
    """Build detailed response from exception model."""
    # Build status history
    history_list = []
    for h in exc.status_history:
        history_list.append(ModelExceptionStatusHistoryResponse(
            history_id=h.history_id,
            exception_id=h.exception_id,
            old_status=h.old_status,
            new_status=h.new_status,
            changed_by_id=h.changed_by_id,
            changed_by=UserBrief(
                user_id=h.changed_by.user_id,
                email=h.changed_by.email,
                full_name=h.changed_by.full_name,
            ) if h.changed_by else None,
            changed_at=h.changed_at,
            notes=h.notes,
        ))

    return ModelExceptionDetailResponse(
        exception_id=exc.exception_id,
        exception_code=exc.exception_code,
        model_id=exc.model_id,
        model=ModelBrief(
            model_id=exc.model.model_id,
            model_name=exc.model.model_name,
            model_code=None,  # Model doesn't have model_code field
        ),
        exception_type=exc.exception_type,
        status=exc.status,
        description=exc.description,
        detected_at=exc.detected_at,
        auto_closed=exc.auto_closed,
        monitoring_result_id=exc.monitoring_result_id,
        attestation_response_id=exc.attestation_response_id,
        deployment_task_id=exc.deployment_task_id,
        acknowledged_by_id=exc.acknowledged_by_id,
        acknowledged_by=UserBrief(
            user_id=exc.acknowledged_by.user_id,
            email=exc.acknowledged_by.email,
            full_name=exc.acknowledged_by.full_name,
        ) if exc.acknowledged_by else None,
        acknowledged_at=exc.acknowledged_at,
        acknowledgment_notes=exc.acknowledgment_notes,
        closed_at=exc.closed_at,
        closed_by_id=exc.closed_by_id,
        closed_by=UserBrief(
            user_id=exc.closed_by.user_id,
            email=exc.closed_by.email,
            full_name=exc.closed_by.full_name,
        ) if exc.closed_by else None,
        closure_narrative=exc.closure_narrative,
        closure_reason_id=exc.closure_reason_id,
        closure_reason=TaxonomyValueBrief(
            value_id=exc.closure_reason.value_id,
            code=exc.closure_reason.code,
            label=exc.closure_reason.label,
        ) if exc.closure_reason else None,
        created_at=exc.created_at,
        updated_at=exc.updated_at,
        status_history=history_list,
    )


def _require_admin(user: User):
    """Raise 403 if user is not an Admin."""
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation",
        )


# =============================================================================
# Closure Reasons Endpoint (must be before /{exception_id} to avoid route conflict)
# =============================================================================

@router.get("/closure-reasons", response_model=List[TaxonomyValueBrief])
def get_closure_reasons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get available closure reasons from the Exception Closure Reason taxonomy."""
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Exception Closure Reason"
    ).first()

    if not taxonomy:
        return []

    values = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.is_active == True,
    ).order_by(TaxonomyValue.sort_order).all()

    return [
        TaxonomyValueBrief(
            value_id=v.value_id,
            code=v.code,
            label=v.label,
        )
        for v in values
    ]


# =============================================================================
# List & Detail Endpoints
# =============================================================================

@router.get("/", response_model=PaginatedExceptionResponse)
def list_exceptions(
    model_id: Optional[int] = Query(None, description="Filter by model ID"),
    exception_type: Optional[str] = Query(None, description="Filter by type: UNMITIGATED_PERFORMANCE, OUTSIDE_INTENDED_PURPOSE, USE_PRIOR_TO_VALIDATION"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN, ACKNOWLEDGED, CLOSED"),
    region_id: Optional[int] = Query(None, description="Filter by region ID (models deployed to this region)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List model exceptions with optional filters.

    Available filters:
    - model_id: Get exceptions for a specific model
    - exception_type: UNMITIGATED_PERFORMANCE | OUTSIDE_INTENDED_PURPOSE | USE_PRIOR_TO_VALIDATION
    - status: OPEN | ACKNOWLEDGED | CLOSED
    - region_id: Get exceptions for models deployed to a specific region

    Access Control:
    - Admin/Validator/Global Approver/Regional Approver: See all exceptions
    - User role: Only see exceptions for models they own/develop/delegate
    """
    query = db.query(ModelException).options(
        joinedload(ModelException.model)
    )

    # Apply Row-Level Security - users only see exceptions for models they have access to
    query = apply_exception_rls(query, current_user, db)

    if model_id:
        query = query.filter(ModelException.model_id == model_id)
    if exception_type:
        query = query.filter(ModelException.exception_type == exception_type)
    if status_filter:
        query = query.filter(ModelException.status == status_filter)
    if region_id:
        # Join through Model -> ModelRegion to filter by region
        # Note: Model join may already exist from RLS, but SQLAlchemy handles duplicates
        query = query.join(Model, ModelException.model_id == Model.model_id, isouter=True).join(
            ModelRegion, Model.model_id == ModelRegion.model_id
        ).filter(ModelRegion.region_id == region_id)

    # Get total count
    total = query.count()

    # Get paginated results
    exceptions = query.order_by(
        ModelException.detected_at.desc()
    ).offset(skip).limit(limit).all()

    items = [_build_exception_list_response(exc) for exc in exceptions]

    return PaginatedExceptionResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=ModelExceptionDetailResponse)
def create_exception(
    request: CreateExceptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually create an exception (Admin only).

    Use this for exceptions discovered outside the automated detection system,
    such as audit findings or historical documentation.

    - exception_type: UNMITIGATED_PERFORMANCE | OUTSIDE_INTENDED_PURPOSE | USE_PRIOR_TO_VALIDATION
    - initial_status: OPEN (default) or ACKNOWLEDGED
    """
    _require_admin(current_user)

    # Validate exception type
    if request.exception_type not in EXCEPTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception_type. Must be one of: {EXCEPTION_TYPES}",
        )

    # Validate initial status
    if request.initial_status not in ["OPEN", "ACKNOWLEDGED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="initial_status must be 'OPEN' or 'ACKNOWLEDGED'",
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == request.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {request.model_id} not found",
        )

    # Generate exception code
    exception_code = generate_exception_code(db)
    now = utc_now()

    # Create the exception
    exception = ModelException(
        exception_code=exception_code,
        model_id=request.model_id,
        exception_type=request.exception_type,
        status=request.initial_status,
        description=request.description,
        detected_at=now,
        auto_closed=False,
    )

    # If creating in ACKNOWLEDGED status, set acknowledgment fields
    if request.initial_status == "ACKNOWLEDGED":
        exception.acknowledged_by_id = current_user.user_id
        exception.acknowledged_at = now
        exception.acknowledgment_notes = request.acknowledgment_notes

    db.add(exception)
    db.flush()

    # Create initial status history record
    history = ModelExceptionStatusHistory(
        exception_id=exception.exception_id,
        old_status=None,
        new_status=request.initial_status,
        changed_by_id=current_user.user_id,
        changed_at=now,
        notes=f"Manually created by admin. {request.acknowledgment_notes or ''}".strip(),
    )
    db.add(history)

    # Log audit
    db.add(AuditLog(
        entity_type="ModelException",
        entity_id=exception.exception_id,
        action="CREATED",
        user_id=current_user.user_id,
        changes={
            "model_id": request.model_id,
            "exception_type": request.exception_type,
            "initial_status": request.initial_status,
            "description": request.description[:100] + "..." if len(request.description) > 100 else request.description,
            "manually_created": True,
        },
    ))
    db.commit()

    # Reload with relationships
    exception = db.query(ModelException).options(
        joinedload(ModelException.model),
        joinedload(ModelException.acknowledged_by),
        joinedload(ModelException.closed_by),
        joinedload(ModelException.closure_reason),
        joinedload(ModelException.status_history).joinedload(ModelExceptionStatusHistory.changed_by),
    ).filter(ModelException.exception_id == exception.exception_id).first()

    if not exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exception not found after creation",
        )

    return _build_exception_detail_response(exception)


@router.get("/summary", response_model=ExceptionSummary)
def get_exception_summary(
    model_id: Optional[int] = Query(None, description="Filter by model ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get summary statistics for exceptions.

    Access Control:
    - Admin/Validator/Global Approver/Regional Approver: See summary for all models
    - User role: Only see summary for models they own/develop/delegate
    """
    query = db.query(ModelException)

    # Apply Row-Level Security - users only see summary for models they have access to
    query = apply_exception_rls(query, current_user, db)

    if model_id:
        query = query.filter(ModelException.model_id == model_id)

    # Count by status (need to apply status filter to the RLS-filtered query)
    total_open = query.filter(ModelException.status == "OPEN").count()
    total_acknowledged = query.filter(ModelException.status == "ACKNOWLEDGED").count()
    total_closed = query.filter(ModelException.status == "CLOSED").count()

    # Count by type
    by_type = {}
    for exc_type in ["UNMITIGATED_PERFORMANCE", "OUTSIDE_INTENDED_PURPOSE", "USE_PRIOR_TO_VALIDATION"]:
        by_type[exc_type] = query.filter(ModelException.exception_type == exc_type).count()

    return ExceptionSummary(
        total_open=total_open,
        total_acknowledged=total_acknowledged,
        total_closed=total_closed,
        by_type=by_type,
    )


@router.get("/{exception_id}", response_model=ModelExceptionDetailResponse)
def get_exception(
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed exception information including status history.

    Access Control:
    - Admin/Validator/Global Approver/Regional Approver: Can view any exception
    - User role: Can only view exceptions for models they own/develop/delegate
    """
    exc = db.query(ModelException).options(
        joinedload(ModelException.model),
        joinedload(ModelException.acknowledged_by),
        joinedload(ModelException.closed_by),
        joinedload(ModelException.closure_reason),
        joinedload(ModelException.status_history).joinedload(ModelExceptionStatusHistory.changed_by),
    ).filter(ModelException.exception_id == exception_id).first()

    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    # Check access - user must have access to the exception's model
    if not can_access_exception(exception_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this exception",
        )

    return _build_exception_detail_response(exc)


# =============================================================================
# Status Transition Endpoints
# =============================================================================

@router.post("/{exception_id}/acknowledge", response_model=ModelExceptionDetailResponse)
def acknowledge_exception_endpoint(
    exception_id: int,
    request: AcknowledgeExceptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Acknowledge an exception (Admin only).

    Transitions: OPEN -> ACKNOWLEDGED
    """
    _require_admin(current_user)

    exc = db.query(ModelException).filter(
        ModelException.exception_id == exception_id
    ).first()

    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    if exc.status != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only acknowledge OPEN exceptions. Current status: {exc.status}",
        )

    # Perform acknowledgment
    acknowledge_exception(db, exc, current_user.user_id, request.notes)
    db.commit()
    db.refresh(exc)

    # Log audit
    db.add(AuditLog(
        entity_type="ModelException",
        entity_id=exc.exception_id,
        action="ACKNOWLEDGED",
        user_id=current_user.user_id,
        changes={"old_status": "OPEN", "new_status": "ACKNOWLEDGED", "notes": request.notes},
    ))
    db.commit()

    # Reload with relationships
    exc = db.query(ModelException).options(
        joinedload(ModelException.model),
        joinedload(ModelException.acknowledged_by),
        joinedload(ModelException.closed_by),
        joinedload(ModelException.closure_reason),
        joinedload(ModelException.status_history).joinedload(ModelExceptionStatusHistory.changed_by),
    ).filter(ModelException.exception_id == exception_id).first()

    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    return _build_exception_detail_response(exc)


@router.post("/{exception_id}/close", response_model=ModelExceptionDetailResponse)
def close_exception_endpoint(
    exception_id: int,
    request: CloseExceptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Close an exception with required narrative and reason (Admin only).

    Can close from OPEN or ACKNOWLEDGED status.
    """
    _require_admin(current_user)

    exc = db.query(ModelException).filter(
        ModelException.exception_id == exception_id
    ).first()

    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    if exc.status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exception is already closed",
        )

    # Validate closure reason exists and is from correct taxonomy
    closure_reason = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request.closure_reason_id
    ).first()

    if not closure_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid closure_reason_id: {request.closure_reason_id}",
        )

    # Check it's from the Exception Closure Reason taxonomy
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.taxonomy_id == closure_reason.taxonomy_id,
        Taxonomy.name == "Exception Closure Reason"
    ).first()

    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="closure_reason_id must be from 'Exception Closure Reason' taxonomy",
        )

    old_status = exc.status

    # Perform closure
    close_exception_manually(
        db=db,
        exception=exc,
        user_id=current_user.user_id,
        closure_narrative=request.closure_narrative,
        closure_reason_id=request.closure_reason_id,
    )
    db.commit()
    db.refresh(exc)

    # Log audit
    db.add(AuditLog(
        entity_type="ModelException",
        entity_id=exc.exception_id,
        action="CLOSED",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status,
            "new_status": "CLOSED",
            "closure_narrative": request.closure_narrative,
            "closure_reason_id": request.closure_reason_id,
        },
    ))
    db.commit()

    # Reload with relationships
    exc = db.query(ModelException).options(
        joinedload(ModelException.model),
        joinedload(ModelException.acknowledged_by),
        joinedload(ModelException.closed_by),
        joinedload(ModelException.closure_reason),
        joinedload(ModelException.status_history).joinedload(ModelExceptionStatusHistory.changed_by),
    ).filter(ModelException.exception_id == exception_id).first()

    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )

    return _build_exception_detail_response(exc)


# =============================================================================
# Detection Endpoints
# =============================================================================

@router.post("/detect/{model_id}", response_model=DetectionResponse)
def detect_exceptions_for_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger exception detection for a specific model (Admin only).

    Runs all three detection types and creates any new exceptions found.
    """
    _require_admin(current_user)

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )

    all_created = []

    # Type 1: Unmitigated Performance (RED without recommendation)
    type1_no_rec = detect_type1_unmitigated_performance(db, model_id)
    all_created.extend(type1_no_rec)

    # Type 1: Persistent RED across cycles
    type1_persistent = detect_type1_persistent_red_for_model(db, model_id)
    all_created.extend(type1_persistent)

    # Type 2: Outside Intended Purpose
    type2 = detect_type2_outside_intended_purpose(db, model_id)
    all_created.extend(type2)

    # Type 3: Use Prior to Validation
    type3 = detect_type3_use_prior_to_validation(db, model_id)
    all_created.extend(type3)

    db.commit()

    # Categorize counts
    type1_count = sum(1 for e in all_created if e.exception_type == "UNMITIGATED_PERFORMANCE")
    type2_count = sum(1 for e in all_created if e.exception_type == "OUTSIDE_INTENDED_PURPOSE")
    type3_count = sum(1 for e in all_created if e.exception_type == "USE_PRIOR_TO_VALIDATION")

    # Log audit for detection run
    if all_created:
        db.add(AuditLog(
            entity_type="ModelException",
            entity_id=model_id,
            action="DETECTION_RUN",
            user_id=current_user.user_id,
            changes={
                "model_id": model_id,
                "exceptions_created": len(all_created),
                "type1_count": type1_count,
                "type2_count": type2_count,
                "type3_count": type3_count,
            },
        ))
        db.commit()

    # Build response
    exception_responses = []
    for exc in all_created:
        # Refresh to get model relationship
        db.refresh(exc)
        exception_responses.append(_build_exception_list_response(exc))

    return DetectionResponse(
        type1_count=type1_count,
        type2_count=type2_count,
        type3_count=type3_count,
        total_created=len(all_created),
        exceptions=exception_responses,
    )


@router.post("/detect-all", response_model=DetectionResponse)
def detect_exceptions_all_models(
    limit: int = Query(MAX_DETECT_ALL_MODELS, ge=1, le=MAX_DETECT_ALL_MODELS),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger exception detection for ALL active models (Admin only).

    This is a batch operation that runs all detection types across the entire inventory.
    Use with caution in large deployments.
    """
    _require_admin(current_user)

    models = db.query(Model).filter(
        Model.status == "Active"
    ).order_by(Model.model_id).offset(offset).limit(limit).all()

    all_created: List[ModelException] = []
    type1_count = 0
    type2_count = 0
    type3_count = 0
    models_scanned = 0
    current_model_id: Optional[int] = None

    try:
        for model in models:
            current_model_id = model.model_id

            # Type 1: Unmitigated Performance
            type1_no_rec = detect_type1_unmitigated_performance(db, current_model_id)
            type1_persistent = detect_type1_persistent_red_for_model(db, current_model_id)

            # Type 2: Outside Intended Purpose
            type2 = detect_type2_outside_intended_purpose(db, current_model_id)

            # Type 3: Use Prior to Validation
            type3 = detect_type3_use_prior_to_validation(db, current_model_id)

            model_created = type1_no_rec + type1_persistent + type2 + type3
            db.commit()

            models_scanned += 1
            for exc in model_created:
                if exc.exception_type == "UNMITIGATED_PERFORMANCE":
                    type1_count += 1
                elif exc.exception_type == "OUTSIDE_INTENDED_PURPOSE":
                    type2_count += 1
                elif exc.exception_type == "USE_PRIOR_TO_VALIDATION":
                    type3_count += 1
            all_created.extend(model_created)
    except Exception as exc:
        db.rollback()
        db.add(AuditLog(
            entity_type="ModelException",
            entity_id=0,
            action="BATCH_DETECTION_RUN",
            user_id=current_user.user_id,
            changes={
                "models_scanned": models_scanned,
                "exceptions_created": len(all_created),
                "type1_count": type1_count,
                "type2_count": type2_count,
                "type3_count": type3_count,
                "limit": limit,
                "offset": offset,
                "failed_model_id": current_model_id,
                "error": str(exc),
            },
        ))
        db.commit()
        raise

    # Log audit for batch detection run (always, for traceability)
    db.add(AuditLog(
        entity_type="ModelException",
        entity_id=0,  # Batch operation, no specific entity
        action="BATCH_DETECTION_RUN",
        user_id=current_user.user_id,
        changes={
            "models_scanned": models_scanned,
            "exceptions_created": len(all_created),
            "type1_count": type1_count,
            "type2_count": type2_count,
            "type3_count": type3_count,
            "limit": limit,
            "offset": offset,
        },
    ))
    db.commit()

    # Build response (limit to first 100 for performance)
    exception_responses = []
    for exc in all_created[:100]:
        db.refresh(exc)
        exception_responses.append(_build_exception_list_response(exc))

    return DetectionResponse(
        type1_count=type1_count,
        type2_count=type2_count,
        type3_count=type3_count,
        total_created=len(all_created),
        exceptions=exception_responses,
    )


# =============================================================================
# Model-Specific Endpoint
# =============================================================================

@router.get("/model/{model_id}", response_model=List[ModelExceptionListResponse])
def get_model_exceptions(
    model_id: int,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN, ACKNOWLEDGED, CLOSED"),
    include_closed: bool = Query(False, description="Include closed exceptions (deprecated, use status param)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all exceptions for a specific model.

    Filtering:
    - status: Filter to specific status (OPEN, ACKNOWLEDGED, CLOSED)
    - include_closed: Legacy param - if true, includes all statuses (deprecated, use status param)

    Default behavior (no params): Returns only OPEN and ACKNOWLEDGED exceptions.

    Access Control:
    - Admin/Validator/Global Approver/Regional Approver: Can view any model's exceptions
    - User role: Can only view exceptions for models they own/develop/delegate
    """
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )

    # Check access - user must have access to the model
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view exceptions for this model",
        )

    query = db.query(ModelException).options(
        joinedload(ModelException.model)
    ).filter(ModelException.model_id == model_id)

    # New status filter takes precedence over legacy include_closed
    if status_filter:
        # Validate status value
        if status_filter not in EXCEPTION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {EXCEPTION_STATUSES}",
            )
        query = query.filter(ModelException.status == status_filter)
    elif not include_closed:
        # Legacy behavior: exclude closed by default
        query = query.filter(ModelException.status != "CLOSED")

    exceptions = query.order_by(ModelException.detected_at.desc()).all()

    return [_build_exception_list_response(exc) for exc in exceptions]
