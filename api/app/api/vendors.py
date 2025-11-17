"""Vendors routes."""
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.vendor import Vendor
from app.models.model import Model
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from app.schemas.model import ModelDetailResponse

router = APIRouter()


@router.get("/", response_model=List[VendorResponse])
def list_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all vendors."""
    vendors = db.query(Vendor).all()
    return vendors


@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new vendor."""
    # Check for duplicate name
    existing = db.query(Vendor).filter(Vendor.name == vendor_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor with this name already exists"
        )

    vendor = Vendor(**vendor_data.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific vendor."""
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    return vendor


@router.get("/{vendor_id}/models", response_model=List[ModelDetailResponse])
def get_vendor_models(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all models for a specific vendor."""
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(Model.vendor_id == vendor_id).all()

    return models


@router.patch("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a vendor."""
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # Check for duplicate name if updating name
    update_data = vendor_data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != vendor.name:
        existing = db.query(Vendor).filter(Vendor.name == update_data["name"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor with this name already exists"
            )

    for field, value in update_data.items():
        setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a vendor."""
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    db.delete(vendor)
    db.commit()
    return None


@router.get("/export/csv")
def export_vendors_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all vendors to CSV."""
    vendors = db.query(Vendor).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Vendor ID",
        "Name",
        "Contact Info",
        "Created At"
    ])

    # Write data rows
    for vendor in vendors:
        writer.writerow([
            vendor.vendor_id,
            vendor.name,
            vendor.contact_info or "",
            vendor.created_at.isoformat() if vendor.created_at else ""
        ])

    # Reset stream position
    output.seek(0)

    # Return as streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=vendors_export.csv"
        }
    )
