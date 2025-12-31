"""API endpoints for Qualitative Risk Factor Configuration.

Admin-only endpoints for managing qualitative risk factors and their guidance.
"""
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.models.user import User
from app.core.roles import is_admin
from app.models.audit_log import AuditLog
from app.models.risk_assessment import (
    QualitativeRiskFactor,
    QualitativeFactorGuidance,
    QualitativeFactorAssessment,
)
from app.schemas.qualitative_factors import (
    FactorCreate,
    FactorUpdate,
    FactorResponse,
    WeightUpdate,
    GuidanceCreate,
    GuidanceUpdate,
    GuidanceResponse,
    WeightValidationResponse,
    ReorderRequest,
)

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an Admin."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def create_audit_log(
    db: Session, entity_type: str, entity_id: int,
    action: str, user_id: int, changes: dict = None
):
    """Create an audit log entry for factor/guidance changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def get_factor_or_404(db: Session, factor_id: int) -> QualitativeRiskFactor:
    """Get factor by ID or raise 404."""
    factor = (
        db.query(QualitativeRiskFactor)
        .options(joinedload(QualitativeRiskFactor.guidance))
        .filter(QualitativeRiskFactor.factor_id == factor_id)
        .first()
    )
    if not factor:
        raise HTTPException(status_code=404, detail="Factor not found")
    return factor


def get_guidance_or_404(db: Session, guidance_id: int) -> QualitativeFactorGuidance:
    """Get guidance by ID or raise 404."""
    guidance = (
        db.query(QualitativeFactorGuidance)
        .filter(QualitativeFactorGuidance.guidance_id == guidance_id)
        .first()
    )
    if not guidance:
        raise HTTPException(status_code=404, detail="Guidance not found")
    return guidance


def build_factor_response(factor: QualitativeRiskFactor) -> FactorResponse:
    """Build response with guidance sorted by sort_order."""
    sorted_guidance = sorted(factor.guidance, key=lambda g: g.sort_order)
    return FactorResponse(
        factor_id=factor.factor_id,
        code=factor.code,
        name=factor.name,
        description=factor.description,
        weight=float(factor.weight),
        sort_order=factor.sort_order,
        is_active=factor.is_active,
        guidance=[
            GuidanceResponse(
                guidance_id=g.guidance_id,
                factor_id=g.factor_id,
                rating=g.rating,
                points=g.points,
                description=g.description,
                sort_order=g.sort_order,
            )
            for g in sorted_guidance
        ],
        created_at=factor.created_at,
        updated_at=factor.updated_at,
    )


# ============================================================================
# Factor Endpoints
# ============================================================================

@router.get("/", response_model=List[FactorResponse])
def list_factors(
    include_inactive: bool = Query(False, description="Include inactive factors"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FactorResponse]:
    """List all qualitative risk factors with their guidance."""
    query = (
        db.query(QualitativeRiskFactor)
        .options(joinedload(QualitativeRiskFactor.guidance))
    )

    if not include_inactive:
        query = query.filter(QualitativeRiskFactor.is_active == True)

    factors = query.order_by(QualitativeRiskFactor.sort_order).all()
    return [build_factor_response(f) for f in factors]


@router.get("/{factor_id}", response_model=FactorResponse)
def get_factor(
    factor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FactorResponse:
    """Get a specific factor with its guidance."""
    factor = get_factor_or_404(db, factor_id)
    return build_factor_response(factor)


@router.post("/", response_model=FactorResponse, status_code=status.HTTP_201_CREATED)
def create_factor(
    data: FactorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> FactorResponse:
    """Create a new qualitative risk factor. Admin only."""
    # Check for duplicate code
    existing = (
        db.query(QualitativeRiskFactor)
        .filter(QualitativeRiskFactor.code == data.code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Factor with code '{data.code}' already exists"
        )

    # Create factor
    factor = QualitativeRiskFactor(
        code=data.code,
        name=data.name,
        description=data.description,
        weight=Decimal(str(data.weight)),
        sort_order=data.sort_order,
        is_active=True,
    )
    db.add(factor)
    db.flush()

    # Create guidance if provided
    if data.guidance:
        for g in data.guidance:
            guidance = QualitativeFactorGuidance(
                factor_id=factor.factor_id,
                rating=g.rating,
                points=g.points,
                description=g.description,
                sort_order=g.sort_order,
            )
            db.add(guidance)

    # Create audit log for factor creation
    create_audit_log(
        db=db,
        entity_type="QualitativeRiskFactor",
        entity_id=factor.factor_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "code": data.code,
            "name": data.name,
            "weight": float(data.weight),
            "sort_order": data.sort_order,
        }
    )

    db.commit()
    db.refresh(factor)

    # Reload with guidance
    factor = get_factor_or_404(db, factor.factor_id)
    return build_factor_response(factor)


@router.put("/{factor_id}", response_model=FactorResponse)
def update_factor(
    factor_id: int,
    data: FactorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> FactorResponse:
    """Update a factor. Admin only."""
    factor = get_factor_or_404(db, factor_id)

    # Check for duplicate code if being changed
    if data.code and data.code != factor.code:
        existing = (
            db.query(QualitativeRiskFactor)
            .filter(
                QualitativeRiskFactor.code == data.code,
                QualitativeRiskFactor.factor_id != factor_id
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Factor with code '{data.code}' already exists"
            )

    # Update fields
    if data.code is not None:
        factor.code = data.code
    if data.name is not None:
        factor.name = data.name
    if data.description is not None:
        factor.description = data.description
    if data.weight is not None:
        factor.weight = Decimal(str(data.weight))
    if data.sort_order is not None:
        factor.sort_order = data.sort_order
    if data.is_active is not None:
        factor.is_active = data.is_active

    factor.updated_at = utc_now()

    # Build changes dict with only provided fields
    changes = {}
    if data.code is not None:
        changes["code"] = data.code
    if data.name is not None:
        changes["name"] = data.name
    if data.description is not None:
        changes["description"] = data.description
    if data.weight is not None:
        changes["weight"] = float(data.weight)
    if data.sort_order is not None:
        changes["sort_order"] = data.sort_order
    if data.is_active is not None:
        changes["is_active"] = data.is_active

    # Create audit log for factor update
    create_audit_log(
        db=db,
        entity_type="QualitativeRiskFactor",
        entity_id=factor_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=changes
    )

    db.commit()
    db.refresh(factor)

    # Reload with guidance
    factor = get_factor_or_404(db, factor.factor_id)
    return build_factor_response(factor)


@router.patch("/{factor_id}/weight", response_model=FactorResponse)
def update_factor_weight(
    factor_id: int,
    data: WeightUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> FactorResponse:
    """Update only the weight of a factor. Admin only."""
    factor = get_factor_or_404(db, factor_id)
    old_weight = float(factor.weight)
    factor.weight = Decimal(str(data.weight))
    factor.updated_at = utc_now()

    # Create audit log for weight update
    create_audit_log(
        db=db,
        entity_type="QualitativeRiskFactor",
        entity_id=factor_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={
            "weight": {
                "old": old_weight,
                "new": float(data.weight)
            }
        }
    )

    db.commit()
    db.refresh(factor)

    # Reload with guidance
    factor = get_factor_or_404(db, factor.factor_id)
    return build_factor_response(factor)


@router.delete("/{factor_id}", response_model=FactorResponse)
def delete_factor(
    factor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> FactorResponse:
    """Soft-delete a factor (set is_active=False). Admin only.

    Cannot delete if factor is used in existing assessments.
    """
    factor = get_factor_or_404(db, factor_id)

    # Check if factor is in use
    in_use = (
        db.query(QualitativeFactorAssessment)
        .filter(QualitativeFactorAssessment.factor_id == factor_id)
        .first()
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete factor that is in use by existing assessments"
        )

    # Soft delete
    factor.is_active = False
    factor.updated_at = utc_now()
    db.commit()
    db.refresh(factor)

    # Reload with guidance
    factor = get_factor_or_404(db, factor.factor_id)
    return build_factor_response(factor)


# ============================================================================
# Weight Validation
# ============================================================================

@router.post("/validate-weights", response_model=WeightValidationResponse)
def validate_weights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightValidationResponse:
    """Validate that active factor weights sum to 1.0."""
    factors = (
        db.query(QualitativeRiskFactor)
        .filter(QualitativeRiskFactor.is_active == True)
        .all()
    )

    total = sum(float(f.weight) for f in factors)
    total_rounded = round(total, 4)
    is_valid = abs(total_rounded - 1.0) < 0.0001

    message = None
    if not is_valid:
        if total_rounded < 1.0:
            message = f"Weights sum to {total_rounded}, need to add {round(1.0 - total_rounded, 4)} more"
        else:
            message = f"Weights sum to {total_rounded}, need to reduce by {round(total_rounded - 1.0, 4)}"

    return WeightValidationResponse(
        valid=is_valid,
        total=total_rounded,
        message=message
    )


# ============================================================================
# Factor Reordering
# ============================================================================

@router.post("/reorder", response_model=List[FactorResponse])
def reorder_factors(
    data: ReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> List[FactorResponse]:
    """Reorder factors by providing new order of IDs. Admin only."""
    # Validate all IDs exist
    factors = (
        db.query(QualitativeRiskFactor)
        .filter(QualitativeRiskFactor.factor_id.in_(data.factor_ids))
        .all()
    )

    if len(factors) != len(data.factor_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more factor IDs not found"
        )

    # Update sort_order based on position in the list
    factor_map = {f.factor_id: f for f in factors}
    for idx, factor_id in enumerate(data.factor_ids):
        factor_map[factor_id].sort_order = idx + 1
        factor_map[factor_id].updated_at = utc_now()

    db.commit()

    # Return in new order
    return [build_factor_response(factor_map[fid]) for fid in data.factor_ids]


# ============================================================================
# Guidance Endpoints
# ============================================================================

@router.post("/{factor_id}/guidance", response_model=GuidanceResponse, status_code=status.HTTP_201_CREATED)
def add_guidance(
    factor_id: int,
    data: GuidanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> GuidanceResponse:
    """Add guidance to a factor. Admin only."""
    factor = get_factor_or_404(db, factor_id)

    # Check for duplicate rating
    existing = (
        db.query(QualitativeFactorGuidance)
        .filter(
            QualitativeFactorGuidance.factor_id == factor_id,
            QualitativeFactorGuidance.rating == data.rating
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Guidance for rating '{data.rating}' already exists for this factor"
        )

    guidance = QualitativeFactorGuidance(
        factor_id=factor_id,
        rating=data.rating,
        points=data.points,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(guidance)
    db.flush()

    # Create audit log for guidance creation
    create_audit_log(
        db=db,
        entity_type="QualitativeFactorGuidance",
        entity_id=guidance.guidance_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "factor_id": factor_id,
            "rating": data.rating,
            "points": data.points,
            "description": data.description,
        }
    )

    db.commit()
    db.refresh(guidance)

    return GuidanceResponse(
        guidance_id=guidance.guidance_id,
        factor_id=guidance.factor_id,
        rating=guidance.rating,
        points=guidance.points,
        description=guidance.description,
        sort_order=guidance.sort_order,
    )


@router.put("/guidance/{guidance_id}", response_model=GuidanceResponse)
def update_guidance(
    guidance_id: int,
    data: GuidanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> GuidanceResponse:
    """Update guidance text and/or points. Admin only."""
    guidance = get_guidance_or_404(db, guidance_id)

    # Build changes dict
    changes = {}
    if data.rating is not None:
        guidance.rating = data.rating
        changes["rating"] = data.rating
    if data.points is not None:
        guidance.points = data.points
        changes["points"] = data.points
    if data.description is not None:
        guidance.description = data.description
        changes["description"] = data.description
    if data.sort_order is not None:
        guidance.sort_order = data.sort_order
        changes["sort_order"] = data.sort_order

    # Create audit log for guidance update
    create_audit_log(
        db=db,
        entity_type="QualitativeFactorGuidance",
        entity_id=guidance_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=changes
    )

    db.commit()
    db.refresh(guidance)

    return GuidanceResponse(
        guidance_id=guidance.guidance_id,
        factor_id=guidance.factor_id,
        rating=guidance.rating,
        points=guidance.points,
        description=guidance.description,
        sort_order=guidance.sort_order,
    )


@router.delete("/guidance/{guidance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guidance(
    guidance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Delete guidance entry. Admin only."""
    guidance = get_guidance_or_404(db, guidance_id)

    # Create audit log for guidance deletion
    create_audit_log(
        db=db,
        entity_type="QualitativeFactorGuidance",
        entity_id=guidance_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "factor_id": guidance.factor_id,
            "rating": guidance.rating,
        }
    )

    db.delete(guidance)
    db.commit()
