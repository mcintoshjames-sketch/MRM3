"""Export Views routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.export_view import ExportView
from app.schemas.export_view import ExportViewCreate, ExportViewUpdate, ExportViewResponse

router = APIRouter()


@router.get("/", response_model=List[ExportViewResponse])
def list_export_views(
    entity_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all export views accessible to the current user.
    Returns user's own views plus all public views.
    Optionally filter by entity_type (e.g., 'models', 'validations').
    """
    query = db.query(ExportView).filter(
        or_(
            ExportView.user_id == current_user.user_id,
            ExportView.is_public == True
        )
    )

    if entity_type:
        query = query.filter(ExportView.entity_type == entity_type)

    views = query.order_by(
        ExportView.is_public.desc(),  # Public views first
        ExportView.view_name
    ).all()

    return views


@router.post("/", response_model=ExportViewResponse, status_code=status.HTTP_201_CREATED)
def create_export_view(
    view_data: ExportViewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new export view."""
    # Check for duplicate name for this user and entity type
    existing = db.query(ExportView).filter(
        ExportView.user_id == current_user.user_id,
        ExportView.entity_type == view_data.entity_type,
        ExportView.view_name == view_data.view_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have a view named '{view_data.view_name}' for {view_data.entity_type}"
        )

    view = ExportView(
        **view_data.model_dump(),
        user_id=current_user.user_id
    )

    db.add(view)
    db.commit()
    db.refresh(view)
    return view


@router.get("/{view_id}", response_model=ExportViewResponse)
def get_export_view(
    view_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific export view."""
    view = db.query(ExportView).filter(ExportView.view_id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export view not found"
        )

    # Check access: must be owner or view must be public
    if view.user_id != current_user.user_id and not view.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this view"
        )

    return view


@router.patch("/{view_id}", response_model=ExportViewResponse)
def update_export_view(
    view_id: int,
    view_data: ExportViewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an export view. Only the owner can update their view."""
    view = db.query(ExportView).filter(ExportView.view_id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export view not found"
        )

    # Only owner can update
    if view.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own views"
        )

    # Check for duplicate name if updating name
    update_data = view_data.model_dump(exclude_unset=True)
    if "view_name" in update_data and update_data["view_name"] != view.view_name:
        existing = db.query(ExportView).filter(
            ExportView.user_id == current_user.user_id,
            ExportView.entity_type == view.entity_type,
            ExportView.view_name == update_data["view_name"]
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have a view named '{update_data['view_name']}'"
            )

    for field, value in update_data.items():
        setattr(view, field, value)

    db.commit()
    db.refresh(view)
    return view


@router.delete("/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_export_view(
    view_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an export view. Only the owner can delete their view."""
    view = db.query(ExportView).filter(ExportView.view_id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export view not found"
        )

    # Only owner can delete
    if view.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own views"
        )

    db.delete(view)
    db.commit()
    return None
