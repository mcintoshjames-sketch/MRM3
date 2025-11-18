"""Model change taxonomy routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model_change_taxonomy import ModelChangeCategory, ModelChangeType
from app.schemas.model_change_taxonomy import (
    ModelChangeCategoryResponse,
    ModelChangeTypeResponse,
)

router = APIRouter()


@router.get("/change-taxonomy/categories", response_model=List[ModelChangeCategoryResponse])
def list_change_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all model change categories with their types."""
    categories = db.query(ModelChangeCategory).options(
        joinedload(ModelChangeCategory.change_types)
    ).order_by(ModelChangeCategory.sort_order).all()

    # Filter to only active change types
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
                if ct.is_active  # Only include active types
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
