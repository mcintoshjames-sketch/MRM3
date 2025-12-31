"""Model Limitations API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.core.roles import is_admin, is_validator
from app.models import (
    User, Model, ModelLimitation, ValidationRequest, ModelVersion,
    Recommendation, TaxonomyValue, Taxonomy, AuditLog, Region, ModelRegion
)


from app.schemas.limitation import (
    LimitationCreate, LimitationUpdate, LimitationRetire,
    LimitationResponse, LimitationListResponse,
    CriticalLimitationsReportResponse, CriticalLimitationReportItem
)


def require_admin_or_validator(current_user: User = Depends(get_current_user)) -> User:
    """Require Admin or Validator role for the current user."""
    if not (is_admin(current_user) or is_validator(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Validator role required"
        )
    return current_user


router = APIRouter()


def _get_limitation_with_relations(db: Session, limitation_id: int) -> ModelLimitation:
    """Fetch a limitation with all related entities."""
    limitation = db.query(ModelLimitation).options(
        joinedload(ModelLimitation.model),
        joinedload(ModelLimitation.validation_request),
        joinedload(ModelLimitation.model_version),
        joinedload(ModelLimitation.recommendation),
        joinedload(ModelLimitation.category),
        joinedload(ModelLimitation.created_by),
        joinedload(ModelLimitation.retired_by),
    ).filter(ModelLimitation.limitation_id == limitation_id).first()
    return limitation


def _validate_category_id(db: Session, category_id: int):
    """Validate that category_id belongs to Limitation Category taxonomy."""
    category = db.query(TaxonomyValue).join(Taxonomy).filter(
        TaxonomyValue.value_id == category_id,
        Taxonomy.name == "Limitation Category"
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category_id - must be a value from 'Limitation Category' taxonomy"
        )
    return category


def _log_audit(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: int,
    old_values: dict = None,
    new_values: dict = None
):
    """Create an audit log entry."""
    changes = {}
    if old_values:
        changes["old"] = old_values
    if new_values:
        changes["new"] = new_values

    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes if changes else None
    )
    db.add(audit_log)


# ==================== MODEL LIMITATIONS CRUD ====================

@router.get(
    "/models/{model_id}/limitations",
    response_model=List[LimitationListResponse],
    summary="List limitations for a model"
)
def list_model_limitations(
    model_id: int,
    include_retired: bool = Query(False, description="Include retired limitations"),
    significance: Optional[str] = Query(None, description="Filter by significance (Critical/Non-Critical)"),
    conclusion: Optional[str] = Query(None, description="Filter by conclusion (Mitigate/Accept)"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all limitations for a specific model."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    query = db.query(ModelLimitation).options(
        joinedload(ModelLimitation.category)
    ).filter(ModelLimitation.model_id == model_id)

    if not include_retired:
        query = query.filter(ModelLimitation.is_retired == False)

    if significance:
        query = query.filter(ModelLimitation.significance == significance)

    if conclusion:
        query = query.filter(ModelLimitation.conclusion == conclusion)

    if category_id:
        query = query.filter(ModelLimitation.category_id == category_id)

    limitations = query.order_by(ModelLimitation.created_at.desc()).all()
    return limitations


@router.post(
    "/models/{model_id}/limitations",
    response_model=LimitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a limitation for a model"
)
def create_limitation(
    model_id: int,
    payload: LimitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    """Create a new limitation for a model. Requires Validator or Admin role."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Validate category
    _validate_category_id(db, payload.category_id)

    # Validate validation_request_id if provided
    if payload.validation_request_id:
        validation_request = db.query(ValidationRequest).filter(
            ValidationRequest.request_id == payload.validation_request_id
        ).first()
        if not validation_request:
            raise HTTPException(status_code=400, detail="Invalid validation_request_id")

    # Validate model_version_id if provided
    if payload.model_version_id:
        model_version = db.query(ModelVersion).filter(
            ModelVersion.version_id == payload.model_version_id
        ).first()
        if not model_version:
            raise HTTPException(status_code=400, detail="Invalid model_version_id")

    # Validate recommendation_id if provided
    if payload.recommendation_id:
        recommendation = db.query(Recommendation).filter(
            Recommendation.recommendation_id == payload.recommendation_id
        ).first()
        if not recommendation:
            raise HTTPException(status_code=400, detail="Invalid recommendation_id")

    limitation = ModelLimitation(
        model_id=model_id,
        validation_request_id=payload.validation_request_id,
        model_version_id=payload.model_version_id,
        recommendation_id=payload.recommendation_id,
        significance=payload.significance,
        category_id=payload.category_id,
        description=payload.description,
        impact_assessment=payload.impact_assessment,
        conclusion=payload.conclusion,
        conclusion_rationale=payload.conclusion_rationale,
        user_awareness_description=payload.user_awareness_description,
        is_retired=False,
        created_by_id=current_user.user_id,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(limitation)
    db.flush()

    # Audit log
    _log_audit(
        db,
        entity_type="ModelLimitation",
        entity_id=limitation.limitation_id,
        action="CREATE",
        user_id=current_user.user_id,
        new_values={
            "model_id": model_id,
            "significance": payload.significance,
            "category_id": payload.category_id,
            "conclusion": payload.conclusion
        }
    )

    db.commit()

    return _get_limitation_with_relations(db, limitation.limitation_id)


@router.get(
    "/limitations/{limitation_id}",
    response_model=LimitationResponse,
    summary="Get limitation details"
)
def get_limitation(
    limitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific limitation."""
    limitation = _get_limitation_with_relations(db, limitation_id)
    if not limitation:
        raise HTTPException(status_code=404, detail="Limitation not found")
    return limitation


@router.patch(
    "/limitations/{limitation_id}",
    response_model=LimitationResponse,
    summary="Update a limitation"
)
def update_limitation(
    limitation_id: int,
    payload: LimitationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    """Update a limitation. Requires Validator or Admin role."""
    limitation = db.query(ModelLimitation).filter(
        ModelLimitation.limitation_id == limitation_id
    ).first()
    if not limitation:
        raise HTTPException(status_code=404, detail="Limitation not found")

    if limitation.is_retired:
        raise HTTPException(
            status_code=400,
            detail="Cannot update a retired limitation"
        )

    old_values = {}
    new_values = {}

    # Update fields if provided
    if payload.validation_request_id is not None:
        if payload.validation_request_id:
            validation_request = db.query(ValidationRequest).filter(
                ValidationRequest.request_id == payload.validation_request_id
            ).first()
            if not validation_request:
                raise HTTPException(status_code=400, detail="Invalid validation_request_id")
        old_values["validation_request_id"] = limitation.validation_request_id
        limitation.validation_request_id = payload.validation_request_id
        new_values["validation_request_id"] = payload.validation_request_id

    if payload.model_version_id is not None:
        if payload.model_version_id:
            model_version = db.query(ModelVersion).filter(
                ModelVersion.version_id == payload.model_version_id
            ).first()
            if not model_version:
                raise HTTPException(status_code=400, detail="Invalid model_version_id")
        old_values["model_version_id"] = limitation.model_version_id
        limitation.model_version_id = payload.model_version_id
        new_values["model_version_id"] = payload.model_version_id

    if payload.recommendation_id is not None:
        if payload.recommendation_id:
            recommendation = db.query(Recommendation).filter(
                Recommendation.recommendation_id == payload.recommendation_id
            ).first()
            if not recommendation:
                raise HTTPException(status_code=400, detail="Invalid recommendation_id")
        old_values["recommendation_id"] = limitation.recommendation_id
        limitation.recommendation_id = payload.recommendation_id
        new_values["recommendation_id"] = payload.recommendation_id

    if payload.significance is not None:
        old_values["significance"] = limitation.significance
        limitation.significance = payload.significance
        new_values["significance"] = payload.significance

    if payload.category_id is not None:
        _validate_category_id(db, payload.category_id)
        old_values["category_id"] = limitation.category_id
        limitation.category_id = payload.category_id
        new_values["category_id"] = payload.category_id

    if payload.description is not None:
        old_values["description"] = limitation.description[:100] + "..." if len(limitation.description) > 100 else limitation.description
        limitation.description = payload.description
        new_values["description"] = payload.description[:100] + "..." if len(payload.description) > 100 else payload.description

    if payload.impact_assessment is not None:
        old_values["impact_assessment"] = limitation.impact_assessment[:100] + "..." if len(limitation.impact_assessment) > 100 else limitation.impact_assessment
        limitation.impact_assessment = payload.impact_assessment
        new_values["impact_assessment"] = payload.impact_assessment[:100] + "..." if len(payload.impact_assessment) > 100 else payload.impact_assessment

    if payload.conclusion is not None:
        old_values["conclusion"] = limitation.conclusion
        limitation.conclusion = payload.conclusion
        new_values["conclusion"] = payload.conclusion

    if payload.conclusion_rationale is not None:
        old_values["conclusion_rationale"] = limitation.conclusion_rationale[:100] + "..." if len(limitation.conclusion_rationale) > 100 else limitation.conclusion_rationale
        limitation.conclusion_rationale = payload.conclusion_rationale
        new_values["conclusion_rationale"] = payload.conclusion_rationale[:100] + "..." if len(payload.conclusion_rationale) > 100 else payload.conclusion_rationale

    if payload.user_awareness_description is not None:
        old_val = limitation.user_awareness_description
        old_values["user_awareness_description"] = (old_val[:100] + "...") if old_val and len(old_val) > 100 else old_val
        limitation.user_awareness_description = payload.user_awareness_description
        new_val = payload.user_awareness_description
        new_values["user_awareness_description"] = (new_val[:100] + "...") if new_val and len(new_val) > 100 else new_val

    # Validate that critical limitations have user_awareness_description
    if limitation.significance == "Critical" and not limitation.user_awareness_description:
        raise HTTPException(
            status_code=400,
            detail="User awareness description is required for Critical limitations"
        )

    limitation.updated_at = utc_now()

    # Audit log
    if new_values:
        _log_audit(
            db,
            entity_type="ModelLimitation",
            entity_id=limitation_id,
            action="UPDATE",
            user_id=current_user.user_id,
            old_values=old_values,
            new_values=new_values
        )

    db.commit()

    return _get_limitation_with_relations(db, limitation_id)


@router.post(
    "/limitations/{limitation_id}/retire",
    response_model=LimitationResponse,
    summary="Retire a limitation"
)
def retire_limitation(
    limitation_id: int,
    payload: LimitationRetire,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    """Retire a limitation with commentary. Requires Validator or Admin role."""
    limitation = db.query(ModelLimitation).filter(
        ModelLimitation.limitation_id == limitation_id
    ).first()
    if not limitation:
        raise HTTPException(status_code=404, detail="Limitation not found")

    if limitation.is_retired:
        raise HTTPException(
            status_code=400,
            detail="Limitation is already retired"
        )

    limitation.is_retired = True
    limitation.retirement_date = utc_now()
    limitation.retirement_reason = payload.retirement_reason
    limitation.retired_by_id = current_user.user_id
    limitation.updated_at = utc_now()

    # Audit log
    _log_audit(
        db,
        entity_type="ModelLimitation",
        entity_id=limitation_id,
        action="RETIRE",
        user_id=current_user.user_id,
        new_values={
            "retirement_reason": payload.retirement_reason
        }
    )

    db.commit()

    return _get_limitation_with_relations(db, limitation_id)


# ==================== CRITICAL LIMITATIONS REPORT ====================

@router.get(
    "/reports/critical-limitations",
    response_model=CriticalLimitationsReportResponse,
    summary="Critical Limitations Report"
)
def get_critical_limitations_report(
    region_id: Optional[int] = Query(None, description="Filter by region"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a report of all critical limitations, optionally filtered by region.

    The region filter checks for models deployed to the specified region
    via the model_regions table.
    """
    # Base query for critical, non-retired limitations
    query = db.query(ModelLimitation).options(
        joinedload(ModelLimitation.model),
        joinedload(ModelLimitation.validation_request),
        joinedload(ModelLimitation.category),
    ).filter(
        ModelLimitation.significance == "Critical",
        ModelLimitation.is_retired == False
    )

    # If filtering by region, join with model_regions
    if region_id:
        # Verify region exists
        region = db.query(Region).filter(Region.region_id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")

        # Get model IDs that are deployed to this region
        model_ids_in_region = db.query(ModelRegion.model_id).filter(
            ModelRegion.region_id == region_id
        ).subquery()

        query = query.filter(ModelLimitation.model_id.in_(model_ids_in_region))

    limitations = query.order_by(ModelLimitation.created_at.desc()).all()

    # Build report items
    items = []
    for lim in limitations:
        # Get region name if model has regions
        region_name = None
        if lim.model and lim.model.model_regions:
            region_names = [mr.region.name for mr in lim.model.model_regions if mr.region]
            region_name = ", ".join(region_names) if region_names else None

        # Get originating validation name
        originating_validation = None
        if lim.validation_request:
            # Use validation type label if available
            if lim.validation_request.validation_type:
                originating_validation = f"Request #{lim.validation_request.request_id} - {lim.validation_request.validation_type.label}"
            else:
                originating_validation = f"Request #{lim.validation_request.request_id}"

        items.append(CriticalLimitationReportItem(
            limitation_id=lim.limitation_id,
            model_id=lim.model_id,
            model_name=lim.model.model_name if lim.model else "Unknown",
            region_name=region_name,
            category_label=lim.category.label if lim.category else "Unknown",
            description=lim.description,
            impact_assessment=lim.impact_assessment,
            conclusion=lim.conclusion,
            conclusion_rationale=lim.conclusion_rationale,
            user_awareness_description=lim.user_awareness_description or "",
            originating_validation=originating_validation,
            created_at=lim.created_at
        ))

    return CriticalLimitationsReportResponse(
        filters_applied={"region_id": region_id} if region_id else {},
        total_count=len(items),
        items=items
    )


# ==================== VALIDATION REQUEST LIMITATIONS ====================

@router.get(
    "/validation-requests/{request_id}/limitations",
    response_model=List[LimitationListResponse],
    summary="List limitations for a validation request"
)
def list_validation_request_limitations(
    request_id: int,
    include_retired: bool = Query(False, description="Include retired limitations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all limitations associated with a specific validation request.

    Returns limitations that were documented during this validation (i.e., have
    their validation_request_id set to this request).
    """
    # Verify validation request exists
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    query = db.query(ModelLimitation).options(
        joinedload(ModelLimitation.category),
        joinedload(ModelLimitation.model)
    ).filter(ModelLimitation.validation_request_id == request_id)

    if not include_retired:
        query = query.filter(ModelLimitation.is_retired == False)

    limitations = query.order_by(ModelLimitation.created_at.desc()).all()
    return limitations
