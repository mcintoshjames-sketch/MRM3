"""Regional Model Implementation API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import RegionalModelImplementation as RMIModel, Model, Region, User, UserRole
from app.schemas.regional_model_implementation import (
    RegionalModelImplementationResponse,
    RegionalModelImplementationCreate,
    RegionalModelImplementationUpdate
)

router = APIRouter()


@router.get("/models/{model_id}/regional-implementations", response_model=List[RegionalModelImplementationResponse])
def list_model_regional_implementations(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all regional implementations for a specific model."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    implementations = db.query(RMIModel).filter(
        RMIModel.model_id == model_id
    ).all()
    return implementations


@router.post("/models/{model_id}/regional-implementations", response_model=RegionalModelImplementationResponse, status_code=201)
def create_regional_implementation(
    model_id: int,
    rmi_data: RegionalModelImplementationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new regional implementation for a model."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Verify region exists
    region = db.query(Region).filter(Region.region_id == rmi_data.region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    # Verify regional implementation doesn't already exist for this model/region combo
    existing = db.query(RMIModel).filter(
        RMIModel.model_id == model_id,
        RMIModel.region_id == rmi_data.region_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Regional implementation already exists for model {model_id} in region {rmi_data.region_id}"
        )

    # Verify shared_model_owner if provided
    if rmi_data.shared_model_owner_id:
        owner = db.query(User).filter(User.user_id == rmi_data.shared_model_owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Shared model owner not found")

    # Create RMI
    rmi = RMIModel(**rmi_data.model_dump())
    db.add(rmi)
    db.commit()
    db.refresh(rmi)
    return rmi


@router.get("/regional-implementations/{rmi_id}", response_model=RegionalModelImplementationResponse)
def get_regional_implementation(
    rmi_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific regional implementation by ID."""
    rmi = db.query(RMIModel).filter(RMIModel.regional_model_impl_id == rmi_id).first()
    if not rmi:
        raise HTTPException(status_code=404, detail="Regional implementation not found")
    return rmi


@router.put("/regional-implementations/{rmi_id}", response_model=RegionalModelImplementationResponse)
def update_regional_implementation(
    rmi_id: int,
    rmi_data: RegionalModelImplementationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a regional implementation."""
    rmi = db.query(RMIModel).filter(RMIModel.regional_model_impl_id == rmi_id).first()
    if not rmi:
        raise HTTPException(status_code=404, detail="Regional implementation not found")

    # Verify shared_model_owner if being updated
    if rmi_data.shared_model_owner_id is not None:
        owner = db.query(User).filter(User.user_id == rmi_data.shared_model_owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Shared model owner not found")

    # Update fields
    update_data = rmi_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rmi, field, value)

    db.commit()
    db.refresh(rmi)
    return rmi


@router.delete("/regional-implementations/{rmi_id}", status_code=204)
def delete_regional_implementation(
    rmi_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a regional implementation (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    rmi = db.query(RMIModel).filter(RMIModel.regional_model_impl_id == rmi_id).first()
    if not rmi:
        raise HTTPException(status_code=404, detail="Regional implementation not found")

    db.delete(rmi)
    db.commit()
    return None
