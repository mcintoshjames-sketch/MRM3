"""Model-Region API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rls import can_manage_model_region
from app.models import ModelRegion as ModelRegionModel, Model, Region, User
from app.core.roles import is_admin
from app.models.audit_log import AuditLog
from app.schemas.model_region import ModelRegion, ModelRegionCreate, ModelRegionUpdate

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)
    # Note: commit happens with the main transaction


@router.get("/models/{model_id}/regions", response_model=List[ModelRegion])
def get_model_regions(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all regional metadata for a specific model."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model_regions = db.query(ModelRegionModel).filter(
        ModelRegionModel.model_id == model_id
    ).all()
    return model_regions


@router.post("/models/{model_id}/regions", response_model=ModelRegion, status_code=201)
def create_model_region(
    model_id: int,
    region_data: ModelRegionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a model-region link for regional metadata."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Permission check: Admin, model owner, or delegate with can_manage_regional permission
    if not can_manage_model_region(model_id, current_user, db):
        raise HTTPException(
            status_code=403,
            detail="Only the model owner, Admin, or a delegate with regional management permission can create model regions"
        )

    # Verify region exists
    region = db.query(Region).filter(Region.region_id == region_data.region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Check if link already exists
    existing = db.query(ModelRegionModel).filter(
        ModelRegionModel.model_id == model_id,
        ModelRegionModel.region_id == region_data.region_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Model-region link already exists for model {model_id} in region {region_data.region_id}"
        )

    # Verify shared_model_owner if provided
    if region_data.shared_model_owner_id:
        owner = db.query(User).filter(User.user_id == region_data.shared_model_owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Shared model owner not found")

    # Create model-region link
    model_region = ModelRegionModel(
        model_id=model_id,
        **region_data.model_dump()
    )
    db.add(model_region)

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ModelRegion",
        entity_id=model_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "region_id": region_data.region_id,
            "shared_model_owner_id": region_data.shared_model_owner_id,
            "regional_risk_level": region_data.regional_risk_level,
            "notes": region_data.notes
        }
    )

    db.commit()
    db.refresh(model_region)
    return model_region


@router.put("/model-regions/{id}", response_model=ModelRegion)
def update_model_region(
    id: int,
    region_data: ModelRegionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a model-region link."""
    model_region = db.query(ModelRegionModel).filter(ModelRegionModel.id == id).first()
    if not model_region:
        raise HTTPException(status_code=404, detail="Model-region link not found")

    # Permission check: Admin, model owner, or delegate with can_manage_regional permission
    if not can_manage_model_region(model_region.model_id, current_user, db):
        raise HTTPException(
            status_code=403,
            detail="Only the model owner, Admin, or a delegate with regional management permission can update model regions"
        )

    # Verify shared_model_owner if being updated
    if region_data.shared_model_owner_id is not None:
        owner = db.query(User).filter(User.user_id == region_data.shared_model_owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Shared model owner not found")

    # Update fields
    update_data = region_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model_region, field, value)

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ModelRegion",
        entity_id=model_region.model_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=update_data
    )

    db.commit()
    db.refresh(model_region)
    return model_region


@router.delete("/model-regions/{id}", status_code=204)
def delete_model_region(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a model-region link (Admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    model_region = db.query(ModelRegionModel).filter(ModelRegionModel.id == id).first()
    if not model_region:
        raise HTTPException(status_code=404, detail="Model-region link not found")

    # Store model_id before deletion
    model_id = model_region.model_id
    region_id = model_region.region_id

    db.delete(model_region)

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ModelRegion",
        entity_id=model_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"region_id": region_id}
    )

    db.commit()
    return None
