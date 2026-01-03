"""Region API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Region as RegionModel, User
from app.core.roles import is_admin
from app.models.audit_log import AuditLog
from app.schemas.region import Region, RegionCreate, RegionUpdate

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict | None = None):
    """Create an audit log entry for region management operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


@router.get("/", response_model=List[Region])
def list_regions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all regions."""
    regions = db.query(RegionModel).order_by(RegionModel.name).all()
    return regions


@router.get("/{region_id}", response_model=Region)
def get_region(
    region_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific region by ID."""
    region = db.query(RegionModel).filter(RegionModel.region_id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region


@router.post("/", response_model=Region, status_code=201)
def create_region(
    region_data: RegionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new region (Admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if code already exists
    existing = db.query(RegionModel).filter(RegionModel.code == region_data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Region with code '{region_data.code}' already exists")

    region = RegionModel(**region_data.model_dump())
    db.add(region)
    db.flush()  # Get region_id before creating audit log

    # Create audit log for new region
    create_audit_log(
        db=db,
        entity_type="Region",
        entity_id=region.region_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "code": region_data.code,
            "name": region_data.name
        }
    )

    db.commit()
    db.refresh(region)
    return region


@router.put("/{region_id}", response_model=Region)
def update_region(
    region_id: int,
    region_data: RegionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a region (Admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    region = db.query(RegionModel).filter(RegionModel.region_id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Check if new code conflicts with existing region
    if region_data.code and region_data.code != region.code:
        existing = db.query(RegionModel).filter(RegionModel.code == region_data.code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Region with code '{region_data.code}' already exists")

    # Track changes for audit log
    changes = {}
    update_data = region_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        old_value = getattr(region, field, None)
        if old_value != value:
            changes[field] = {
                "old": old_value,
                "new": value
            }
        setattr(region, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="Region",
            entity_id=region_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(region)
    return region


@router.delete("/{region_id}", status_code=204)
def delete_region(
    region_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a region (Admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    region = db.query(RegionModel).filter(RegionModel.region_id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="Region",
        entity_id=region_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "code": region.code,
            "name": region.name
        }
    )

    db.delete(region)
    db.commit()
    return None
