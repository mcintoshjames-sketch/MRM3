"""Region API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Region as RegionModel, User, UserRole
from app.schemas.region import Region, RegionCreate, RegionUpdate

router = APIRouter()


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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if code already exists
    existing = db.query(RegionModel).filter(RegionModel.code == region_data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Region with code '{region_data.code}' already exists")

    region = RegionModel(**region_data.model_dump())
    db.add(region)
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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    region = db.query(RegionModel).filter(RegionModel.region_id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Check if new code conflicts with existing region
    if region_data.code and region_data.code != region.code:
        existing = db.query(RegionModel).filter(RegionModel.code == region_data.code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Region with code '{region_data.code}' already exists")

    # Update fields
    update_data = region_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(region, field, value)

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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    region = db.query(RegionModel).filter(RegionModel.region_id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    db.delete(region)
    db.commit()
    return None
