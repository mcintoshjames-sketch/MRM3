"""Taxonomy routes."""
import csv
import io
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
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


def require_admin_for_bucket_taxonomy(user: User, taxonomy: Taxonomy, action: str = "modify"):
    """Require admin role for bucket taxonomy modifications.

    Args:
        user: The current user
        taxonomy: The taxonomy being modified
        action: Description of the action (for error message)

    Raises:
        HTTPException: If user is not admin and taxonomy is a bucket type
    """
    if taxonomy.taxonomy_type == "bucket" and user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only administrators can {action} bucket taxonomy values"
        )


def validate_bucket_taxonomy_values(
    values: List[TaxonomyValue],
    new_value: Optional[TaxonomyValueCreate] = None,
    updating_value_id: Optional[int] = None,
    updated_min_days: Optional[int] = None,
    updated_max_days: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that bucket taxonomy values form a contiguous range with no gaps or overlaps.

    Rules:
    1. Exactly one bucket must have min_days=None (the lower unbounded bucket)
    2. Exactly one bucket must have max_days=None (the upper unbounded bucket)
    3. Buckets must be contiguous: max_days of one bucket + 1 = min_days of next bucket
    4. No overlapping ranges

    Args:
        values: Existing taxonomy values (excluding the one being updated if applicable)
        new_value: New value being created (if applicable)
        updating_value_id: ID of value being updated (if applicable)
        updated_min_days: New min_days for the value being updated
        updated_max_days: New max_days for the value being updated

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Build list of all buckets to validate
    buckets = []
    for v in values:
        if updating_value_id and v.value_id == updating_value_id:
            # Use updated values
            buckets.append({
                "label": v.label,
                "min_days": updated_min_days,
                "max_days": updated_max_days,
            })
        else:
            buckets.append({
                "label": v.label,
                "min_days": v.min_days,
                "max_days": v.max_days,
            })

    if new_value:
        buckets.append({
            "label": new_value.label,
            "min_days": new_value.min_days,
            "max_days": new_value.max_days,
        })

    if len(buckets) == 0:
        return True, None

    if len(buckets) == 1:
        # Single bucket should be unbounded on both ends
        b = buckets[0]
        if b["min_days"] is not None or b["max_days"] is not None:
            return False, "A single bucket must have both min_days and max_days as null (unbounded)"
        return True, None

    # Sort buckets by their effective min_days (None = negative infinity = -inf)
    def sort_key(b):
        if b["min_days"] is None:
            return float('-inf')
        return b["min_days"]

    sorted_buckets = sorted(buckets, key=sort_key)

    # Validate first bucket has min_days=None
    if sorted_buckets[0]["min_days"] is not None:
        return False, f"The lowest bucket ('{sorted_buckets[0]['label']}') must have min_days=null (unbounded lower bound)"

    # Validate last bucket has max_days=None
    if sorted_buckets[-1]["max_days"] is not None:
        return False, f"The highest bucket ('{sorted_buckets[-1]['label']}') must have max_days=null (unbounded upper bound)"

    # Validate no other bucket has null min_days or max_days
    for i, b in enumerate(sorted_buckets):
        if i > 0 and b["min_days"] is None:
            return False, f"Only the lowest bucket can have min_days=null. Bucket '{b['label']}' has invalid null min_days"
        if i < len(sorted_buckets) - 1 and b["max_days"] is None:
            return False, f"Only the highest bucket can have max_days=null. Bucket '{b['label']}' has invalid null max_days"

    # Validate contiguity and no overlaps
    for i in range(len(sorted_buckets) - 1):
        current = sorted_buckets[i]
        next_bucket = sorted_buckets[i + 1]

        current_max = current["max_days"]
        next_min = next_bucket["min_days"]

        if current_max is None:
            # Current is the unbounded upper bucket but it's not last - this is an error
            return False, f"Bucket '{current['label']}' has max_days=null but is not the last bucket"

        if next_min is None:
            # Next has unbounded lower but it's not first - this is an error
            return False, f"Bucket '{next_bucket['label']}' has min_days=null but is not the first bucket"

        # Check for gap
        if next_min > current_max + 1:
            return False, f"Gap detected between buckets '{current['label']}' (max={current_max}) and '{next_bucket['label']}' (min={next_min}). Expected min_days={current_max + 1}"

        # Check for overlap
        if next_min <= current_max:
            return False, f"Overlap detected between buckets '{current['label']}' (max={current_max}) and '{next_bucket['label']}' (min={next_min}). Buckets must not overlap"

    return True, None


@router.get("/", response_model=List[TaxonomyListResponse])
def list_taxonomies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all taxonomies."""
    taxonomies = db.query(Taxonomy).order_by(Taxonomy.name).all()
    return taxonomies


@router.get("/by-names/", response_model=List[TaxonomyResponse])
def get_taxonomies_by_names(
    names: List[str] = Query(..., description="List of taxonomy names to fetch"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch multiple taxonomies by name with their values in a single call.

    This endpoint is optimized for fetching specific taxonomies needed for
    dropdowns/filters, reducing N+1 queries to a single request.
    """
    taxonomies = db.query(Taxonomy).options(
        joinedload(Taxonomy.values)
    ).filter(Taxonomy.name.in_(names)).order_by(Taxonomy.name).all()
    return taxonomies


@router.get("/{taxonomy_id}", response_model=TaxonomyResponse)
def get_taxonomy(
    taxonomy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a taxonomy with its values."""
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.taxonomy_id == taxonomy_id).first()
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
    existing = db.query(Taxonomy).filter(
        Taxonomy.name == taxonomy_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Taxonomy with this name already exists"
        )

    # Validate taxonomy_type
    if taxonomy_data.taxonomy_type not in ("standard", "bucket"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="taxonomy_type must be 'standard' or 'bucket'"
        )

    taxonomy = Taxonomy(
        name=taxonomy_data.name,
        description=taxonomy_data.description,
        taxonomy_type=taxonomy_data.taxonomy_type,
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
            "description": taxonomy_data.description,
            "taxonomy_type": taxonomy_data.taxonomy_type
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
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.taxonomy_id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy not found"
        )

    update_data = taxonomy_data.model_dump(exclude_unset=True)

    # Require admin role when changing taxonomy_type to or from 'bucket'
    if 'taxonomy_type' in update_data:
        new_type = update_data['taxonomy_type']
        if (new_type == 'bucket' or taxonomy.taxonomy_type == 'bucket') and current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can change taxonomy type to or from 'bucket'"
            )

    # Check for name uniqueness if name is being updated
    if 'name' in update_data and update_data['name'] != taxonomy.name:
        existing = db.query(Taxonomy).filter(
            Taxonomy.name == update_data['name']).first()
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
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.taxonomy_id == taxonomy_id).first()
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
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.taxonomy_id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy not found"
        )

    # Require admin role for bucket taxonomy modifications
    require_admin_for_bucket_taxonomy(current_user, taxonomy, "create values in")

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

    # Validate bucket constraints if this is a bucket taxonomy
    if taxonomy.taxonomy_type == "bucket":
        existing_values = db.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == taxonomy_id
        ).all()
        is_valid, error_msg = validate_bucket_taxonomy_values(
            existing_values, new_value=value_data
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bucket validation failed: {error_msg}"
            )

    value = TaxonomyValue(
        taxonomy_id=taxonomy_id,
        code=value_data.code,
        label=value_data.label,
        description=value_data.description,
        sort_order=value_data.sort_order,
        is_active=value_data.is_active,
        min_days=value_data.min_days if taxonomy.taxonomy_type == "bucket" else None,
        max_days=value_data.max_days if taxonomy.taxonomy_type == "bucket" else None,
    )
    db.add(value)
    db.flush()  # Get value_id before creating audit log

    # Create audit log for new taxonomy value
    changes = {
        "taxonomy_id": taxonomy_id,
        "taxonomy_name": taxonomy.name,
        "code": value_data.code,
        "label": value_data.label,
        "is_active": value_data.is_active
    }
    if taxonomy.taxonomy_type == "bucket":
        changes["min_days"] = value_data.min_days
        changes["max_days"] = value_data.max_days

    create_audit_log(
        db=db,
        entity_type="TaxonomyValue",
        entity_id=value.value_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes=changes
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
    value = db.query(TaxonomyValue).options(
        joinedload(TaxonomyValue.taxonomy)
    ).filter(TaxonomyValue.value_id == value_id).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy value not found"
        )

    update_data = value_data.model_dump(exclude_unset=True)

    # Require admin role for bucket taxonomy modifications
    # Check if updating bucket fields or if taxonomy is a bucket type
    taxonomy = value.taxonomy
    if taxonomy.taxonomy_type == "bucket" and ('min_days' in update_data or 'max_days' in update_data):
        require_admin_for_bucket_taxonomy(current_user, taxonomy, "modify range values in")

    # Prevent code changes for data integrity
    if 'code' in update_data and update_data['code'] != value.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code cannot be changed after creation to maintain data integrity. Please create a new value instead."
        )

    # Validate bucket constraints if this is a bucket taxonomy and bucket fields are being updated
    if taxonomy.taxonomy_type == "bucket" and ('min_days' in update_data or 'max_days' in update_data):
        # Get all values for this taxonomy
        all_values = db.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id
        ).all()

        # Determine the new min/max values
        new_min = update_data.get('min_days', value.min_days)
        new_max = update_data.get('max_days', value.max_days)

        is_valid, error_msg = validate_bucket_taxonomy_values(
            all_values,
            updating_value_id=value_id,
            updated_min_days=new_min,
            updated_max_days=new_max,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bucket validation failed: {error_msg}"
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

    # Require admin role for bucket taxonomy modifications
    taxonomy = value.taxonomy
    require_admin_for_bucket_taxonomy(current_user, taxonomy, "delete values from")

    # For bucket taxonomies, validate that deletion won't create gaps
    if taxonomy.taxonomy_type == "bucket":
        # Get all values except the one being deleted
        remaining_values = db.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
            TaxonomyValue.value_id != value_id
        ).all()

        if len(remaining_values) > 0:
            is_valid, error_msg = validate_bucket_taxonomy_values(
                remaining_values)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete this bucket: deletion would create an invalid range. {error_msg}"
                )

    # Create audit log before deletion
    delete_changes = {
        "taxonomy_name": value.taxonomy.name if value.taxonomy else None,
        "code": value.code,
        "label": value.label
    }
    # Include bucket fields for bucket taxonomies
    if taxonomy.taxonomy_type == "bucket":
        delete_changes["min_days"] = value.min_days
        delete_changes["max_days"] = value.max_days

    create_audit_log(
        db=db,
        entity_type="TaxonomyValue",
        entity_id=value_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes=delete_changes
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
        "Taxonomy Type",
        "Code",
        "Label",
        "Description",
        "Sort Order",
        "Active",
        "Min Days",
        "Max Days",
        "Created At"
    ])

    # Write data rows
    for value in values:
        writer.writerow([
            value.taxonomy.name if value.taxonomy else "",
            value.taxonomy.taxonomy_type if value.taxonomy else "",
            value.code,
            value.label,
            value.description or "",
            value.sort_order,
            "Yes" if value.is_active else "No",
            value.min_days if value.min_days is not None else "",
            value.max_days if value.max_days is not None else "",
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
