"""Model change taxonomy routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.roles import is_admin
from app.models.model_change_taxonomy import ModelChangeCategory, ModelChangeType
from app.models.audit_log import AuditLog
from app.schemas.model_change_taxonomy import (
    ModelChangeCategoryResponse,
    ModelChangeTypeResponse,
    ModelChangeTypeUpdate,
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
    code: str | None = None,
    name: str | None = None,
    sort_order: int | None = None,
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
    description: str | None = None,
    mv_activity: str | None = None,
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
    db.flush()  # Get the change_type_id before creating audit log

    # Create audit log for new change type
    create_audit_log(
        db=db,
        entity_type="ModelChangeType",
        entity_id=change_type.change_type_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": name,
            "code": code,
            "requires_mv_approval": requires_mv_approval,
            "is_active": is_active
        }
    )

    db.commit()
    db.refresh(change_type)

    return change_type


@router.patch("/change-taxonomy/types/{change_type_id}", response_model=ModelChangeTypeResponse)
def update_change_type(
    change_type_id: int,
    update_data: ModelChangeTypeUpdate,
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

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.category_id is not None:
        # Verify category exists
        category = db.query(ModelChangeCategory).filter(
            ModelChangeCategory.category_id == update_data.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        changes["category_id"] = {
            "old": change_type.category_id, "new": update_data.category_id}
        change_type.category_id = update_data.category_id

    if update_data.code is not None:
        # Check for duplicate code
        existing = db.query(ModelChangeType).filter(
            ModelChangeType.code == update_data.code,
            ModelChangeType.change_type_id != change_type_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Change type with code {update_data.code} already exists"
            )
        changes["code"] = {"old": change_type.code, "new": update_data.code}
        change_type.code = update_data.code

    if update_data.name is not None:
        changes["name"] = {"old": change_type.name, "new": update_data.name}
        change_type.name = update_data.name

    if update_data.description is not None:
        changes["description"] = {
            "old": change_type.description, "new": update_data.description}
        change_type.description = update_data.description

    if update_data.mv_activity is not None:
        changes["mv_activity"] = {
            "old": change_type.mv_activity, "new": update_data.mv_activity}
        change_type.mv_activity = update_data.mv_activity

    if update_data.requires_mv_approval is not None:
        # CRITICAL: Track changes to approval requirements for compliance audit trail
        changes["requires_mv_approval"] = {
            "old": change_type.requires_mv_approval,
            "new": update_data.requires_mv_approval
        }
        change_type.requires_mv_approval = update_data.requires_mv_approval

    if update_data.sort_order is not None:
        changes["sort_order"] = {
            "old": change_type.sort_order, "new": update_data.sort_order}
        change_type.sort_order = update_data.sort_order

    if update_data.is_active is not None:
        changes["is_active"] = {
            "old": change_type.is_active, "new": update_data.is_active}
        change_type.is_active = update_data.is_active

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="ModelChangeType",
            entity_id=change_type_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

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

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="ModelChangeType",
        entity_id=change_type_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "name": change_type.name,
            "code": change_type.code,
            "requires_mv_approval": change_type.requires_mv_approval,
            "force_deleted": force,
            "affected_versions": version_count
        }
    )

    db.delete(change_type)
    db.commit()

    return None
