"""Model change taxonomy routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.model_change_taxonomy import ModelChangeCategory, ModelChangeType
from app.schemas.model_change_taxonomy import (
    ModelChangeCategoryResponse,
    ModelChangeTypeResponse,
)

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/change-taxonomy/categories", response_model=List[ModelChangeCategoryResponse])
def list_change_categories(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all model change categories with their types.

    Args:
        active_only: If True (default), only return active change types.
                     Set to False for admin UI to show all types.
    """
    categories = db.query(ModelChangeCategory).options(
        joinedload(ModelChangeCategory.change_types)
    ).order_by(ModelChangeCategory.sort_order).all()

    # Filter change types based on active_only parameter
    result = []
    for category in categories:
        category_dict = {
            "category_id": category.category_id,
            "code": category.code,
            "name": category.name,
            "sort_order": category.sort_order,
            "change_types": [
                {
                    "change_type_id": ct.change_type_id,
                    "category_id": ct.category_id,
                    "code": ct.code,
                    "name": ct.name,
                    "description": ct.description,
                    "mv_activity": ct.mv_activity,
                    "requires_mv_approval": ct.requires_mv_approval,
                    "sort_order": ct.sort_order,
                    "is_active": ct.is_active,
                }
                for ct in category.change_types
                if not active_only or ct.is_active  # Filter based on parameter
            ]
        }
        result.append(category_dict)

    return result


@router.get("/change-taxonomy/types", response_model=List[ModelChangeTypeResponse])
def list_change_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True
):
    """List all model change types (optionally filtered to active only)."""
    query = db.query(ModelChangeType)

    if active_only:
        query = query.filter(ModelChangeType.is_active == True)

    types = query.order_by(ModelChangeType.sort_order).all()

    return types


@router.get("/change-taxonomy/types/{change_type_id}", response_model=ModelChangeTypeResponse)
def get_change_type(
    change_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific change type by ID."""
    change_type = db.query(ModelChangeType).filter(
        ModelChangeType.change_type_id == change_type_id
    ).first()

    if not change_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change type not found"
        )

    return change_type


# ============================================================================
# ADMIN ENDPOINTS - Category Management
# ============================================================================

@router.post("/change-taxonomy/categories", response_model=ModelChangeCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    code: str,
    name: str,
    sort_order: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new change category (Admin only)."""
    # Check for duplicate code
    existing = db.query(ModelChangeCategory).filter(
        ModelChangeCategory.code == code
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with code '{code}' already exists"
        )

    category = ModelChangeCategory(
        code=code,
        name=name,
        sort_order=sort_order
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    # Load with change_types relationship
    category = db.query(ModelChangeCategory).options(
        joinedload(ModelChangeCategory.change_types)
    ).filter(ModelChangeCategory.category_id == category.category_id).first()

    return category


@router.patch("/change-taxonomy/categories/{category_id}", response_model=ModelChangeCategoryResponse)
def update_category(
    category_id: int,
    code: str = None,
    name: str = None,
    sort_order: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a change category (Admin only)."""
    category = db.query(ModelChangeCategory).filter(
        ModelChangeCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Update fields
    if code is not None:
        # Check for duplicate code
        existing = db.query(ModelChangeCategory).filter(
            ModelChangeCategory.code == code,
            ModelChangeCategory.category_id != category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with code '{code}' already exists"
            )
        category.code = code

    if name is not None:
        category.name = name

    if sort_order is not None:
        category.sort_order = sort_order

    db.commit()
    db.refresh(category)

    # Load with change_types relationship
    category = db.query(ModelChangeCategory).options(
        joinedload(ModelChangeCategory.change_types)
    ).filter(ModelChangeCategory.category_id == category_id).first()

    return category


@router.delete("/change-taxonomy/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a change category (Admin only). Cascades to associated change types."""
    category = db.query(ModelChangeCategory).filter(
        ModelChangeCategory.category_id == category_id
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
# ADMIN ENDPOINTS - Change Type Management
# ============================================================================

@router.post("/change-taxonomy/types", response_model=ModelChangeTypeResponse, status_code=status.HTTP_201_CREATED)
def create_change_type(
    category_id: int,
    code: int,
    name: str,
    description: str = None,
    mv_activity: str = None,
    requires_mv_approval: bool = False,
    sort_order: int = 0,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new change type (Admin only)."""
    # Verify category exists
    category = db.query(ModelChangeCategory).filter(
        ModelChangeCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check for duplicate code
    existing = db.query(ModelChangeType).filter(
        ModelChangeType.code == code
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Change type with code {code} already exists"
        )

    change_type = ModelChangeType(
        category_id=category_id,
        code=code,
        name=name,
        description=description,
        mv_activity=mv_activity,
        requires_mv_approval=requires_mv_approval,
        sort_order=sort_order,
        is_active=is_active
    )

    db.add(change_type)
    db.commit()
    db.refresh(change_type)

    return change_type


@router.patch("/change-taxonomy/types/{change_type_id}", response_model=ModelChangeTypeResponse)
def update_change_type(
    change_type_id: int,
    category_id: int = None,
    code: int = None,
    name: str = None,
    description: str = None,
    mv_activity: str = None,
    requires_mv_approval: bool = None,
    sort_order: int = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a change type (Admin only)."""
    change_type = db.query(ModelChangeType).filter(
        ModelChangeType.change_type_id == change_type_id
    ).first()

    if not change_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change type not found"
        )

    # Update fields
    if category_id is not None:
        # Verify category exists
        category = db.query(ModelChangeCategory).filter(
            ModelChangeCategory.category_id == category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        change_type.category_id = category_id

    if code is not None:
        # Check for duplicate code
        existing = db.query(ModelChangeType).filter(
            ModelChangeType.code == code,
            ModelChangeType.change_type_id != change_type_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Change type with code {code} already exists"
            )
        change_type.code = code

    if name is not None:
        change_type.name = name

    if description is not None:
        change_type.description = description

    if mv_activity is not None:
        change_type.mv_activity = mv_activity

    if requires_mv_approval is not None:
        change_type.requires_mv_approval = requires_mv_approval

    if sort_order is not None:
        change_type.sort_order = sort_order

    if is_active is not None:
        change_type.is_active = is_active

    db.commit()
    db.refresh(change_type)

    return change_type


@router.delete("/change-taxonomy/types/{change_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_change_type(
    change_type_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a change type (Admin only).

    Will fail if change type is referenced by model versions unless force=True.
    Recommend deactivating instead of deleting to preserve historical data.
    """
    from app.models.model_version import ModelVersion

    change_type = db.query(ModelChangeType).filter(
        ModelChangeType.change_type_id == change_type_id
    ).first()

    if not change_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change type not found"
        )

    # Check for references in model_versions
    version_count = db.query(ModelVersion).filter(
        ModelVersion.change_type_id == change_type_id
    ).count()

    if version_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete change type: {version_count} model version(s) reference this change type. "
                   f"Consider deactivating instead to preserve historical data, or use force=true to delete anyway."
        )

    db.delete(change_type)
    db.commit()

    return None
