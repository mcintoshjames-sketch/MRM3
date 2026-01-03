"""Model type taxonomy routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.roles import is_admin
from app.models.model_type_taxonomy import ModelTypeCategory, ModelType
from app.models.audit_log import AuditLog
from app.schemas.model_type_taxonomy import (
    ModelTypeCategoryResponse,
    ModelTypeResponse,
    ModelTypeUpdate,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict | None = None):
    """Create an audit log entry for taxonomy changes."""
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


@router.get("/model-types/categories", response_model=List[ModelTypeCategoryResponse])
def list_model_type_categories(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all model type categories with their types.

    Args:
        active_only: If True (default), only return active model types.
                     Set to False for admin UI to show all types.
    """
    categories = db.query(ModelTypeCategory).options(
        joinedload(ModelTypeCategory.model_types)
    ).order_by(ModelTypeCategory.sort_order).all()

    # Filter model types based on active_only parameter
    result = []
    for category in categories:
        category_dict = {
            "category_id": category.category_id,
            "name": category.name,
            "description": category.description,
            "sort_order": category.sort_order,
            "model_types": [
                {
                    "type_id": mt.type_id,
                    "category_id": mt.category_id,
                    "name": mt.name,
                    "description": mt.description,
                    "sort_order": mt.sort_order,
                    "is_active": mt.is_active,
                }
                for mt in category.model_types
                if not active_only or mt.is_active  # Filter based on parameter
            ]
        }
        result.append(category_dict)

    return result


@router.get("/model-types/types", response_model=List[ModelTypeResponse])
def list_model_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True
):
    """List all model types (optionally filtered to active only)."""
    query = db.query(ModelType)

    if active_only:
        query = query.filter(ModelType.is_active == True)

    types = query.order_by(ModelType.sort_order).all()

    return types


@router.get("/model-types/types/{type_id}", response_model=ModelTypeResponse)
def get_model_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific model type by ID."""
    model_type = db.query(ModelType).filter(
        ModelType.type_id == type_id
    ).first()

    if not model_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model type not found"
        )

    return model_type


# ============================================================================
# ADMIN ENDPOINTS - Category Management
# ============================================================================

@router.post("/model-types/categories", response_model=ModelTypeCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    name: str,
    description: str | None = None,
    sort_order: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new model type category (Admin only)."""
    # Check for duplicate name
    existing = db.query(ModelTypeCategory).filter(
        ModelTypeCategory.name == name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{name}' already exists"
        )

    category = ModelTypeCategory(
        name=name,
        description=description,
        sort_order=sort_order
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    # Load with model_types relationship
    category = db.query(ModelTypeCategory).options(
        joinedload(ModelTypeCategory.model_types)
    ).filter(ModelTypeCategory.category_id == category.category_id).first()

    return category


@router.patch("/model-types/categories/{category_id}", response_model=ModelTypeCategoryResponse)
def update_category(
    category_id: int,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a model type category (Admin only)."""
    category = db.query(ModelTypeCategory).filter(
        ModelTypeCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Update fields
    if name is not None:
        # Check for duplicate name
        existing = db.query(ModelTypeCategory).filter(
            ModelTypeCategory.name == name,
            ModelTypeCategory.category_id != category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{name}' already exists"
            )
        category.name = name

    if description is not None:
        category.description = description

    if sort_order is not None:
        category.sort_order = sort_order

    db.commit()
    db.refresh(category)

    # Load with model_types relationship
    category = db.query(ModelTypeCategory).options(
        joinedload(ModelTypeCategory.model_types)
    ).filter(ModelTypeCategory.category_id == category_id).first()

    return category


@router.delete("/model-types/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a model type category (Admin only). Cascades to associated model types."""
    category = db.query(ModelTypeCategory).filter(
        ModelTypeCategory.category_id == category_id
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
# ADMIN ENDPOINTS - Model Type Management
# ============================================================================

@router.post("/model-types/types", response_model=ModelTypeResponse, status_code=status.HTTP_201_CREATED)
def create_model_type(
    category_id: int,
    name: str,
    description: str | None = None,
    sort_order: int = 0,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new model type (Admin only)."""
    # Verify category exists
    category = db.query(ModelTypeCategory).filter(
        ModelTypeCategory.category_id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check for duplicate name within category? Or globally?
    # Let's check globally for simplicity, or within category.
    # Usually names should be unique.
    existing = db.query(ModelType).filter(
        ModelType.name == name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model type with name '{name}' already exists"
        )

    model_type = ModelType(
        category_id=category_id,
        name=name,
        description=description,
        sort_order=sort_order,
        is_active=is_active
    )

    db.add(model_type)
    db.flush()  # Get the type_id before creating audit log

    # Create audit log for new model type
    create_audit_log(
        db=db,
        entity_type="ModelType",
        entity_id=model_type.type_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": name,
            "is_active": is_active
        }
    )

    db.commit()
    db.refresh(model_type)

    return model_type


@router.patch("/model-types/types/{type_id}", response_model=ModelTypeResponse)
def update_model_type(
    type_id: int,
    update_data: ModelTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a model type (Admin only)."""
    model_type = db.query(ModelType).filter(
        ModelType.type_id == type_id
    ).first()

    if not model_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model type not found"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.category_id is not None:
        # Verify category exists
        category = db.query(ModelTypeCategory).filter(
            ModelTypeCategory.category_id == update_data.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        changes["category_id"] = {
            "old": model_type.category_id, "new": update_data.category_id}
        model_type.category_id = update_data.category_id

    if update_data.name is not None:
        # Check for duplicate name
        existing = db.query(ModelType).filter(
            ModelType.name == update_data.name,
            ModelType.type_id != type_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model type with name '{update_data.name}' already exists"
            )
        changes["name"] = {"old": model_type.name, "new": update_data.name}
        model_type.name = update_data.name

    if update_data.description is not None:
        changes["description"] = {
            "old": model_type.description, "new": update_data.description}
        model_type.description = update_data.description

    if update_data.sort_order is not None:
        changes["sort_order"] = {
            "old": model_type.sort_order, "new": update_data.sort_order}
        model_type.sort_order = update_data.sort_order

    if update_data.is_active is not None:
        changes["is_active"] = {
            "old": model_type.is_active, "new": update_data.is_active}
        model_type.is_active = update_data.is_active

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="ModelType",
            entity_id=type_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(model_type)

    return model_type


@router.delete("/model-types/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_type(
    type_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a model type (Admin only).

    Will fail if model type is referenced by models unless force=True.
    Recommend deactivating instead of deleting to preserve historical data.
    """
    from app.models.model import Model

    model_type = db.query(ModelType).filter(
        ModelType.type_id == type_id
    ).first()

    if not model_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model type not found"
        )

    # Check for references in models
    model_count = db.query(Model).filter(
        Model.model_type_id == type_id
    ).count()

    if model_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete model type: {model_count} model(s) reference this type. "
                   f"Consider deactivating instead to preserve historical data, or use force=true to delete anyway."
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="ModelType",
        entity_id=type_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "name": model_type.name,
            "force_deleted": force,
            "affected_models": model_count
        }
    )

    db.delete(model_type)
    db.commit()

    return None
