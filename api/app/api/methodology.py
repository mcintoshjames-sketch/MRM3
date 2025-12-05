"""Methodology library routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.methodology import MethodologyCategory, Methodology
from app.models.audit_log import AuditLog
from app.models.model import Model
from app.schemas.methodology import (
    MethodologyCategoryResponse,
    MethodologyCategoryCreate,
    MethodologyCategoryUpdate,
    MethodologyResponse,
    MethodologyCreate,
    MethodologyUpdate,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for methodology changes."""
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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================================
# READ ENDPOINTS - Available to all authenticated users
# ============================================================================

@router.get("/methodology-library/categories", response_model=List[MethodologyCategoryResponse])
def list_categories(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all methodology categories with their methodologies.

    Args:
        active_only: If True (default), only return active methodologies.
                     Set to False for admin UI to show all methodologies.
    """
    categories = db.query(MethodologyCategory).options(
        joinedload(MethodologyCategory.methodologies)
    ).order_by(MethodologyCategory.sort_order).all()

    # Filter methodologies based on active_only parameter
    result = []
    for category in categories:
        category_dict = {
            "category_id": category.category_id,
            "code": category.code,
            "name": category.name,
            "sort_order": category.sort_order,
            "methodologies": [
                {
                    "methodology_id": m.methodology_id,
                    "category_id": m.category_id,
                    "name": m.name,
                    "description": m.description,
                    "variants": m.variants,
                    "sort_order": m.sort_order,
                    "is_active": m.is_active,
                }
                for m in category.methodologies
                if not active_only or m.is_active
            ]
        }
        result.append(category_dict)

    return result


@router.get("/methodology-library/methodologies", response_model=List[MethodologyResponse])
def list_methodologies(
    search: Optional[str] = Query(None, description="Search by name or description"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only show active methodologies"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all methodologies with optional filtering.

    - search: Filter by name or description (case-insensitive)
    - category_id: Filter by methodology category
    - active_only: If True (default), only return active methodologies
    - limit/offset: Pagination controls
    """
    query = db.query(Methodology)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Methodology.name.ilike(search_filter),
                Methodology.description.ilike(search_filter)
            )
        )

    if category_id is not None:
        query = query.filter(Methodology.category_id == category_id)

    if active_only:
        query = query.filter(Methodology.is_active == True)

    methodologies = query.order_by(Methodology.sort_order).offset(offset).limit(limit).all()
    return methodologies


@router.get("/methodology-library/methodologies/{methodology_id}", response_model=MethodologyResponse)
def get_methodology(
    methodology_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific methodology by ID."""
    methodology = db.query(Methodology).filter(
        Methodology.methodology_id == methodology_id
    ).first()

    if not methodology:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Methodology not found"
        )

    return methodology


# ============================================================================
# ADMIN ENDPOINTS - Category Management
# ============================================================================

@router.post("/methodology-library/categories", response_model=MethodologyCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: MethodologyCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new methodology category (Admin only)."""
    # Check for duplicate code
    existing = db.query(MethodologyCategory).filter(
        MethodologyCategory.code == category.code
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with code '{category.code}' already exists"
        )

    new_category = MethodologyCategory(
        code=category.code,
        name=category.name,
        sort_order=category.sort_order
    )

    db.add(new_category)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="MethodologyCategory",
        entity_id=new_category.category_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"name": category.name, "code": category.code}
    )

    db.commit()
    db.refresh(new_category)

    # Load with methodologies relationship
    new_category = db.query(MethodologyCategory).options(
        joinedload(MethodologyCategory.methodologies)
    ).filter(MethodologyCategory.category_id == new_category.category_id).first()

    return new_category


@router.patch("/methodology-library/categories/{category_id}", response_model=MethodologyCategoryResponse)
def update_category(
    category_id: int,
    update_data: MethodologyCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a methodology category (Admin only)."""
    category = db.query(MethodologyCategory).filter(
        MethodologyCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    changes = {}

    if update_data.code is not None:
        # Check for duplicate code
        existing = db.query(MethodologyCategory).filter(
            MethodologyCategory.code == update_data.code,
            MethodologyCategory.category_id != category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with code '{update_data.code}' already exists"
            )
        changes["code"] = {"old": category.code, "new": update_data.code}
        category.code = update_data.code

    if update_data.name is not None:
        changes["name"] = {"old": category.name, "new": update_data.name}
        category.name = update_data.name

    if update_data.sort_order is not None:
        changes["sort_order"] = {"old": category.sort_order, "new": update_data.sort_order}
        category.sort_order = update_data.sort_order

    if changes:
        create_audit_log(
            db=db,
            entity_type="MethodologyCategory",
            entity_id=category_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(category)

    # Load with methodologies relationship
    category = db.query(MethodologyCategory).options(
        joinedload(MethodologyCategory.methodologies)
    ).filter(MethodologyCategory.category_id == category_id).first()

    return category


@router.delete("/methodology-library/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    force: bool = Query(False, description="Force delete even if models reference methodologies in this category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a methodology category (Admin only). Cascades to associated methodologies.

    If models reference methodologies in this category, deletion will be blocked unless force=true.
    """
    category = db.query(MethodologyCategory).options(
        joinedload(MethodologyCategory.methodologies)
    ).filter(
        MethodologyCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if any models reference methodologies in this category
    methodology_ids = [m.methodology_id for m in category.methodologies]
    if methodology_ids:
        models_using = db.query(Model).filter(Model.methodology_id.in_(methodology_ids)).count()
        if models_using > 0 and not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete: {models_using} model(s) reference methodologies in this category. Use force=true to delete anyway."
            )

    create_audit_log(
        db=db,
        entity_type="MethodologyCategory",
        entity_id=category_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"name": category.name, "code": category.code}
    )

    db.delete(category)
    db.commit()

    return None


# ============================================================================
# ADMIN ENDPOINTS - Methodology Management
# ============================================================================

@router.post("/methodology-library/methodologies", response_model=MethodologyResponse, status_code=status.HTTP_201_CREATED)
def create_methodology(
    methodology: MethodologyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new methodology (Admin only)."""
    # Verify category exists
    category = db.query(MethodologyCategory).filter(
        MethodologyCategory.category_id == methodology.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    new_methodology = Methodology(
        category_id=methodology.category_id,
        name=methodology.name,
        description=methodology.description,
        variants=methodology.variants,
        sort_order=methodology.sort_order,
        is_active=methodology.is_active
    )

    db.add(new_methodology)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="Methodology",
        entity_id=new_methodology.methodology_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": methodology.name,
            "category_id": methodology.category_id,
            "is_active": methodology.is_active
        }
    )

    db.commit()
    db.refresh(new_methodology)

    return new_methodology


@router.patch("/methodology-library/methodologies/{methodology_id}", response_model=MethodologyResponse)
def update_methodology(
    methodology_id: int,
    update_data: MethodologyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a methodology (Admin only)."""
    methodology = db.query(Methodology).filter(
        Methodology.methodology_id == methodology_id
    ).first()

    if not methodology:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Methodology not found"
        )

    changes = {}

    if update_data.category_id is not None:
        # Verify category exists
        category = db.query(MethodologyCategory).filter(
            MethodologyCategory.category_id == update_data.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        changes["category_id"] = {"old": methodology.category_id, "new": update_data.category_id}
        methodology.category_id = update_data.category_id

    if update_data.name is not None:
        changes["name"] = {"old": methodology.name, "new": update_data.name}
        methodology.name = update_data.name

    if update_data.description is not None:
        changes["description"] = {"old": methodology.description, "new": update_data.description}
        methodology.description = update_data.description

    if update_data.variants is not None:
        changes["variants"] = {"old": methodology.variants, "new": update_data.variants}
        methodology.variants = update_data.variants

    if update_data.sort_order is not None:
        changes["sort_order"] = {"old": methodology.sort_order, "new": update_data.sort_order}
        methodology.sort_order = update_data.sort_order

    if update_data.is_active is not None:
        changes["is_active"] = {"old": methodology.is_active, "new": update_data.is_active}
        methodology.is_active = update_data.is_active

    if changes:
        create_audit_log(
            db=db,
            entity_type="Methodology",
            entity_id=methodology_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(methodology)

    return methodology


@router.delete("/methodology-library/methodologies/{methodology_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_methodology(
    methodology_id: int,
    force: bool = Query(False, description="Force delete even if models reference this methodology"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a methodology (Admin only).

    If models reference this methodology, deletion will be blocked unless force=true.
    """
    methodology = db.query(Methodology).filter(
        Methodology.methodology_id == methodology_id
    ).first()

    if not methodology:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Methodology not found"
        )

    # Check if any models reference this methodology
    models_using = db.query(Model).filter(Model.methodology_id == methodology_id).count()
    if models_using > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {models_using} model(s) use this methodology. Use force=true to delete anyway."
        )

    create_audit_log(
        db=db,
        entity_type="Methodology",
        entity_id=methodology_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "name": methodology.name,
            "category_id": methodology.category_id
        }
    )

    db.delete(methodology)
    db.commit()

    return None
