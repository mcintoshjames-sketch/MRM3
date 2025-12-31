"""KPM (Key Performance Metrics) routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.roles import is_admin
from app.models.kpm import KpmCategory, Kpm
from app.models.audit_log import AuditLog
from app.schemas.kpm import (
    KpmCategoryResponse,
    KpmCategoryCreate,
    KpmCategoryUpdate,
    KpmResponse,
    KpmCreate,
    KpmUpdate,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for KPM changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to require admin role."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================================
# READ ENDPOINTS - Available to all authenticated users
# ============================================================================

@router.get("/kpm/categories", response_model=List[KpmCategoryResponse])
def list_kpm_categories(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all KPM categories with their KPMs.

    Args:
        active_only: If True (default), only return active KPMs.
                     Set to False for admin UI to show all KPMs.
    """
    categories = db.query(KpmCategory).options(
        joinedload(KpmCategory.kpms)
    ).order_by(KpmCategory.sort_order).all()

    # Filter KPMs based on active_only parameter
    result = []
    for category in categories:
        category_dict = {
            "category_id": category.category_id,
            "code": category.code,
            "name": category.name,
            "description": category.description,
            "sort_order": category.sort_order,
            "category_type": category.category_type,
            "kpms": [
                {
                    "kpm_id": kpm.kpm_id,
                    "category_id": kpm.category_id,
                    "name": kpm.name,
                    "description": kpm.description,
                    "calculation": kpm.calculation,
                    "interpretation": kpm.interpretation,
                    "sort_order": kpm.sort_order,
                    "is_active": kpm.is_active,
                    "evaluation_type": kpm.evaluation_type,
                }
                for kpm in category.kpms
                if not active_only or kpm.is_active
            ]
        }
        result.append(category_dict)

    return result


@router.get("/kpm/kpms", response_model=List[KpmResponse])
def list_kpms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True
):
    """List all KPMs (optionally filtered to active only)."""
    query = db.query(Kpm)

    if active_only:
        query = query.filter(Kpm.is_active == True)

    kpms = query.order_by(Kpm.sort_order).all()

    return kpms


@router.get("/kpm/kpms/{kpm_id}", response_model=KpmResponse)
def get_kpm(
    kpm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific KPM by ID."""
    kpm = db.query(Kpm).filter(Kpm.kpm_id == kpm_id).first()

    if not kpm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPM not found"
        )

    return kpm


# ============================================================================
# ADMIN ENDPOINTS - Category Management
# ============================================================================

@router.post("/kpm/categories", response_model=KpmCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: KpmCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new KPM category (Admin only)."""
    # Check for duplicate code
    existing = db.query(KpmCategory).filter(
        KpmCategory.code == category_data.code
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with code '{category_data.code}' already exists"
        )

    category = KpmCategory(
        code=category_data.code,
        name=category_data.name,
        description=category_data.description,
        sort_order=category_data.sort_order,
        category_type=category_data.category_type.value if category_data.category_type else "Quantitative"
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    # Load with kpms relationship
    category = db.query(KpmCategory).options(
        joinedload(KpmCategory.kpms)
    ).filter(KpmCategory.category_id == category.category_id).first()

    return category


@router.patch("/kpm/categories/{category_id}", response_model=KpmCategoryResponse)
def update_category(
    category_id: int,
    update_data: KpmCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a KPM category (Admin only)."""
    category = db.query(KpmCategory).filter(
        KpmCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Update fields
    if update_data.code is not None:
        # Check for duplicate code
        existing = db.query(KpmCategory).filter(
            KpmCategory.code == update_data.code,
            KpmCategory.category_id != category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with code '{update_data.code}' already exists"
            )
        category.code = update_data.code

    if update_data.name is not None:
        category.name = update_data.name

    if update_data.description is not None:
        category.description = update_data.description

    if update_data.sort_order is not None:
        category.sort_order = update_data.sort_order

    if update_data.category_type is not None:
        category.category_type = update_data.category_type.value

    db.commit()
    db.refresh(category)

    # Load with kpms relationship
    category = db.query(KpmCategory).options(
        joinedload(KpmCategory.kpms)
    ).filter(KpmCategory.category_id == category_id).first()

    return category


@router.delete("/kpm/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a KPM category (Admin only). Cascades to associated KPMs."""
    category = db.query(KpmCategory).filter(
        KpmCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    db.delete(category)
    db.commit()

    return None


# ============================================================================
# ADMIN ENDPOINTS - KPM Management
# ============================================================================

@router.post("/kpm/kpms", response_model=KpmResponse, status_code=status.HTTP_201_CREATED)
def create_kpm(
    kpm_data: KpmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new KPM (Admin only)."""
    # Verify category exists
    category = db.query(KpmCategory).filter(
        KpmCategory.category_id == kpm_data.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check for duplicate name
    existing = db.query(Kpm).filter(
        Kpm.name == kpm_data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"KPM with name '{kpm_data.name}' already exists"
        )

    kpm = Kpm(
        category_id=kpm_data.category_id,
        name=kpm_data.name,
        description=kpm_data.description,
        calculation=kpm_data.calculation,
        interpretation=kpm_data.interpretation,
        sort_order=kpm_data.sort_order,
        is_active=kpm_data.is_active,
        evaluation_type=kpm_data.evaluation_type.value if kpm_data.evaluation_type else "Quantitative"
    )

    db.add(kpm)
    db.flush()

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="Kpm",
        entity_id=kpm.kpm_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": kpm_data.name,
            "is_active": kpm_data.is_active
        }
    )

    db.commit()
    db.refresh(kpm)

    return kpm


@router.patch("/kpm/kpms/{kpm_id}", response_model=KpmResponse)
def update_kpm(
    kpm_id: int,
    update_data: KpmUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a KPM (Admin only)."""
    kpm = db.query(Kpm).filter(Kpm.kpm_id == kpm_id).first()

    if not kpm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPM not found"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.category_id is not None:
        # Verify category exists
        category = db.query(KpmCategory).filter(
            KpmCategory.category_id == update_data.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        changes["category_id"] = {
            "old": kpm.category_id, "new": update_data.category_id}
        kpm.category_id = update_data.category_id

    if update_data.name is not None:
        # Check for duplicate name
        existing = db.query(Kpm).filter(
            Kpm.name == update_data.name,
            Kpm.kpm_id != kpm_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"KPM with name '{update_data.name}' already exists"
            )
        changes["name"] = {"old": kpm.name, "new": update_data.name}
        kpm.name = update_data.name

    if update_data.description is not None:
        changes["description"] = {
            "old": kpm.description, "new": update_data.description}
        kpm.description = update_data.description

    if update_data.calculation is not None:
        changes["calculation"] = {
            "old": kpm.calculation, "new": update_data.calculation}
        kpm.calculation = update_data.calculation

    if update_data.interpretation is not None:
        changes["interpretation"] = {
            "old": kpm.interpretation, "new": update_data.interpretation}
        kpm.interpretation = update_data.interpretation

    if update_data.sort_order is not None:
        changes["sort_order"] = {
            "old": kpm.sort_order, "new": update_data.sort_order}
        kpm.sort_order = update_data.sort_order

    if update_data.is_active is not None:
        changes["is_active"] = {
            "old": kpm.is_active, "new": update_data.is_active}
        kpm.is_active = update_data.is_active

    if update_data.evaluation_type is not None:
        changes["evaluation_type"] = {
            "old": kpm.evaluation_type, "new": update_data.evaluation_type.value}
        kpm.evaluation_type = update_data.evaluation_type.value

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="Kpm",
            entity_id=kpm_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(kpm)

    return kpm


@router.delete("/kpm/kpms/{kpm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kpm(
    kpm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a KPM (Admin only).

    Recommend deactivating instead of deleting to preserve historical data.
    """
    kpm = db.query(Kpm).filter(Kpm.kpm_id == kpm_id).first()

    if not kpm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPM not found"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="Kpm",
        entity_id=kpm_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"name": kpm.name}
    )

    db.delete(kpm)
    db.commit()

    return None
