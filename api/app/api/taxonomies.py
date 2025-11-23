"""Taxonomy routes."""
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.audit_log import AuditLog
from app.schemas.taxonomy import (
    TaxonomyResponse,
    TaxonomyListResponse,
    TaxonomyCreate,
    TaxonomyUpdate,
    TaxonomyValueResponse,
    TaxonomyValueCreate,
    TaxonomyValueUpdate,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for taxonomy operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


@router.get("/", response_model=List[TaxonomyListResponse])
def list_taxonomies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all taxonomies."""
    taxonomies = db.query(Taxonomy).order_by(Taxonomy.name).all()
    return taxonomies


@router.get("/{taxonomy_id}", response_model=TaxonomyResponse)
def get_taxonomy(
    taxonomy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a taxonomy with its values."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.taxonomy_id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy not found"
        )
    return taxonomy


@router.post("/", response_model=TaxonomyResponse, status_code=status.HTTP_201_CREATED)
def create_taxonomy(
    taxonomy_data: TaxonomyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new taxonomy."""
    # Check if name already exists
    existing = db.query(Taxonomy).filter(Taxonomy.name == taxonomy_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Taxonomy with this name already exists"
        )

    taxonomy = Taxonomy(
        name=taxonomy_data.name,
        description=taxonomy_data.description,
        is_system=False
    )
    db.add(taxonomy)
    db.flush()  # Get taxonomy_id before creating audit log

    # Create audit log for new taxonomy
    create_audit_log(
        db=db,
        entity_type="Taxonomy",
        entity_id=taxonomy.taxonomy_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": taxonomy_data.name,
            "description": taxonomy_data.description
        }
    )

    db.commit()
    db.refresh(taxonomy)
    return taxonomy


@router.patch("/{taxonomy_id}", response_model=TaxonomyResponse)
def update_taxonomy(
    taxonomy_id: int,
    taxonomy_data: TaxonomyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a taxonomy."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.taxonomy_id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy not found"
        )

    update_data = taxonomy_data.model_dump(exclude_unset=True)

    # Check for name uniqueness if name is being updated
    if 'name' in update_data and update_data['name'] != taxonomy.name:
        existing = db.query(Taxonomy).filter(Taxonomy.name == update_data['name']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Taxonomy with this name already exists"
            )

    # Track changes for audit log
    changes = {}
    for field, value in update_data.items():
        old_value = getattr(taxonomy, field, None)
        if old_value != value:
            changes[field] = {
                "old": old_value,
                "new": value
            }
        setattr(taxonomy, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="Taxonomy",
            entity_id=taxonomy_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(taxonomy)
    return taxonomy


@router.delete("/{taxonomy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_taxonomy(
    taxonomy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a taxonomy."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.taxonomy_id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy not found"
        )

    if taxonomy.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system taxonomy"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="Taxonomy",
        entity_id=taxonomy_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "name": taxonomy.name,
            "description": taxonomy.description
        }
    )

    db.delete(taxonomy)
    db.commit()
    return None


# Taxonomy Value endpoints

@router.post("/{taxonomy_id}/values", response_model=TaxonomyValueResponse, status_code=status.HTTP_201_CREATED)
def create_taxonomy_value(
    taxonomy_id: int,
    value_data: TaxonomyValueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a value to a taxonomy."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.taxonomy_id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy not found"
        )

    # Check for duplicate code in this taxonomy
    existing = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy_id,
        TaxonomyValue.code == value_data.code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Value with this code already exists in this taxonomy"
        )

    value = TaxonomyValue(
        taxonomy_id=taxonomy_id,
        code=value_data.code,
        label=value_data.label,
        description=value_data.description,
        sort_order=value_data.sort_order,
        is_active=value_data.is_active
    )
    db.add(value)
    db.flush()  # Get value_id before creating audit log

    # Create audit log for new taxonomy value
    create_audit_log(
        db=db,
        entity_type="TaxonomyValue",
        entity_id=value.value_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "taxonomy_id": taxonomy_id,
            "taxonomy_name": taxonomy.name,
            "code": value_data.code,
            "label": value_data.label,
            "is_active": value_data.is_active
        }
    )

    db.commit()
    db.refresh(value)
    return value


@router.patch("/values/{value_id}", response_model=TaxonomyValueResponse)
def update_taxonomy_value(
    value_id: int,
    value_data: TaxonomyValueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a taxonomy value."""
    value = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == value_id).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy value not found"
        )

    update_data = value_data.model_dump(exclude_unset=True)

    # Prevent code changes for data integrity
    if 'code' in update_data and update_data['code'] != value.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code cannot be changed after creation to maintain data integrity. Please create a new value instead."
        )

    # Track changes for audit log
    changes = {}
    for field, val in update_data.items():
        old_value = getattr(value, field, None)
        if old_value != val:
            changes[field] = {
                "old": old_value,
                "new": val
            }
        setattr(value, field, val)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="TaxonomyValue",
            entity_id=value_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(value)
    return value


@router.delete("/values/{value_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_taxonomy_value(
    value_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a taxonomy value."""
    value = db.query(TaxonomyValue).options(
        joinedload(TaxonomyValue.taxonomy)
    ).filter(TaxonomyValue.value_id == value_id).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy value not found"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="TaxonomyValue",
        entity_id=value_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "taxonomy_name": value.taxonomy.name if value.taxonomy else None,
            "code": value.code,
            "label": value.label
        }
    )

    db.delete(value)
    db.commit()
    return None


@router.get("/export/csv")
def export_taxonomies_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all taxonomy values to CSV."""
    values = db.query(TaxonomyValue).options(
        joinedload(TaxonomyValue.taxonomy)
    ).order_by(TaxonomyValue.taxonomy_id, TaxonomyValue.sort_order).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Taxonomy",
        "Code",
        "Label",
        "Description",
        "Sort Order",
        "Active",
        "Created At"
    ])

    # Write data rows
    for value in values:
        writer.writerow([
            value.taxonomy.name if value.taxonomy else "",
            value.code,
            value.label,
            value.description or "",
            value.sort_order,
            "Yes" if value.is_active else "No",
            value.created_at.isoformat() if value.created_at else ""
        ])

    # Reset stream position
    output.seek(0)

    # Return as streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=taxonomies_export.csv"
        }
    )
