"""Saved Queries routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.saved_query import SavedQuery
from app.schemas.saved_query import SavedQueryCreate, SavedQueryUpdate, SavedQueryResponse

router = APIRouter()


@router.get("/", response_model=List[SavedQueryResponse])
def list_saved_queries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all saved queries accessible to the current user.
    Returns user's own queries plus all public queries.
    """
    queries = db.query(SavedQuery).filter(
        or_(
            SavedQuery.user_id == current_user.user_id,
            SavedQuery.is_public == True
        )
    ).order_by(
        SavedQuery.is_public.desc(),  # Public queries first
        SavedQuery.query_name
    ).all()

    return queries


@router.post("/", response_model=SavedQueryResponse, status_code=status.HTTP_201_CREATED)
def create_saved_query(
    query_data: SavedQueryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new saved query."""
    # Check for duplicate name for this user
    existing = db.query(SavedQuery).filter(
        SavedQuery.user_id == current_user.user_id,
        SavedQuery.query_name == query_data.query_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have a query named '{query_data.query_name}'"
        )

    query = SavedQuery(
        **query_data.model_dump(),
        user_id=current_user.user_id
    )

    db.add(query)
    db.commit()
    db.refresh(query)
    return query


@router.get("/{query_id}", response_model=SavedQueryResponse)
def get_saved_query(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific saved query."""
    query = db.query(SavedQuery).filter(SavedQuery.query_id == query_id).first()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved query not found"
        )

    # Check access: must be owner or query must be public
    if query.user_id != current_user.user_id and not query.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this query"
        )

    return query


@router.patch("/{query_id}", response_model=SavedQueryResponse)
def update_saved_query(
    query_id: int,
    query_data: SavedQueryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a saved query. Only the owner can update their query."""
    query = db.query(SavedQuery).filter(SavedQuery.query_id == query_id).first()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved query not found"
        )

    # Only owner can update
    if query.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own queries"
        )

    # Check for duplicate name if updating name
    update_data = query_data.model_dump(exclude_unset=True)
    if "query_name" in update_data and update_data["query_name"] != query.query_name:
        existing = db.query(SavedQuery).filter(
            SavedQuery.user_id == current_user.user_id,
            SavedQuery.query_name == update_data["query_name"]
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have a query named '{update_data['query_name']}'"
            )

    for field, value in update_data.items():
        setattr(query, field, value)

    db.commit()
    db.refresh(query)
    return query


@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_query(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a saved query. Only the owner can delete their query."""
    query = db.query(SavedQuery).filter(SavedQuery.query_id == query_id).first()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved query not found"
        )

    # Only owner can delete
    if query.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own queries"
        )

    db.delete(query)
    db.commit()
    return None
