"""Tag routes for model categorization."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models.user import User
from app.models.model import Model
from app.models.tag import TagCategory, Tag, ModelTag, ModelTagHistory
from app.models.audit_log import AuditLog
from app.schemas.tag import (
    TagCategoryCreate,
    TagCategoryUpdate,
    TagCategoryResponse,
    TagCategoryWithTagsResponse,
    TagCreate,
    TagUpdate,
    TagResponse,
    TagWithCategoryResponse,
    TagListItem,
    ModelTagAssign,
    BulkTagAssign,
    BulkTagRemove,
    BulkTagResponse,
    ModelTagResponse,
    TagHistoryItem,
    ModelTagHistoryResponse,
    TagUsageStatistics,
    CategoryUsage,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict | None = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def require_admin(user: User, action: str = "perform this action"):
    """Require admin role for the operation."""
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin access required to {action}"
        )


def build_tag_list_item(tag: Tag) -> dict:
    """Build a TagListItem dict from a Tag model."""
    return {
        "tag_id": tag.tag_id,
        "name": tag.name,
        "color": tag.color,
        "effective_color": tag.effective_color,
        "category_id": tag.category_id,
        "category_name": tag.category.name,
        "category_color": tag.category.color,
    }


# ============================================================================
# Tag Category Endpoints
# ============================================================================

@router.get("/categories", response_model=List[TagCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tag categories with tag counts."""
    categories = db.query(TagCategory).order_by(
        TagCategory.sort_order, TagCategory.name
    ).all()

    # Get tag counts for each category
    tag_counts = dict(
        db.query(Tag.category_id, func.count(Tag.tag_id))
        .group_by(Tag.category_id)
        .all()
    )

    result = []
    for cat in categories:
        cat_dict = {
            "category_id": cat.category_id,
            "name": cat.name,
            "description": cat.description,
            "color": cat.color,
            "sort_order": cat.sort_order,
            "is_system": cat.is_system,
            "created_at": cat.created_at,
            "created_by_id": cat.created_by_id,
            "tag_count": tag_counts.get(cat.category_id, 0),
        }
        result.append(cat_dict)

    return result


@router.get("/categories/{category_id}", response_model=TagCategoryWithTagsResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a tag category with its tags."""
    category = db.query(TagCategory).options(
        joinedload(TagCategory.tags)
    ).filter(TagCategory.category_id == category_id).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag category not found"
        )

    # Get model counts for tags
    model_counts = dict(
        db.query(ModelTag.tag_id, func.count(ModelTag.model_id))
        .filter(ModelTag.tag_id.in_([t.tag_id for t in category.tags]))
        .group_by(ModelTag.tag_id)
        .all()
    )

    tags_data = []
    for tag in category.tags:
        tags_data.append({
            "tag_id": tag.tag_id,
            "category_id": tag.category_id,
            "name": tag.name,
            "description": tag.description,
            "color": tag.color,
            "sort_order": tag.sort_order,
            "is_active": tag.is_active,
            "created_at": tag.created_at,
            "created_by_id": tag.created_by_id,
            "effective_color": tag.effective_color,
            "model_count": model_counts.get(tag.tag_id, 0),
        })

    return {
        "category_id": category.category_id,
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "sort_order": category.sort_order,
        "is_system": category.is_system,
        "created_at": category.created_at,
        "created_by_id": category.created_by_id,
        "tag_count": len(category.tags),
        "tags": tags_data,
    }


@router.post("/categories", response_model=TagCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: TagCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag category (Admin only)."""
    require_admin(current_user, "create tag categories")

    # Check for duplicate name
    existing = db.query(TagCategory).filter(TagCategory.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag category with this name already exists"
        )

    category = TagCategory(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        sort_order=payload.sort_order,
        is_system=False,
        created_by_id=current_user.user_id,
    )
    db.add(category)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="TagCategory",
        entity_id=category.category_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"name": payload.name, "color": payload.color}
    )

    db.commit()
    db.refresh(category)

    return {
        "category_id": category.category_id,
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "sort_order": category.sort_order,
        "is_system": category.is_system,
        "created_at": category.created_at,
        "created_by_id": category.created_by_id,
        "tag_count": 0,
    }


@router.patch("/categories/{category_id}", response_model=TagCategoryResponse)
def update_category(
    category_id: int,
    payload: TagCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a tag category (Admin only)."""
    require_admin(current_user, "update tag categories")

    category = db.query(TagCategory).filter(TagCategory.category_id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag category not found"
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate name if name is being changed
    if 'name' in update_data and update_data['name'] != category.name:
        existing = db.query(TagCategory).filter(TagCategory.name == update_data['name']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag category with this name already exists"
            )

    changes = {}
    for field, value in update_data.items():
        old_value = getattr(category, field, None)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
        setattr(category, field, value)

    if changes:
        create_audit_log(
            db=db,
            entity_type="TagCategory",
            entity_id=category_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(category)

    tag_count = db.query(func.count(Tag.tag_id)).filter(Tag.category_id == category_id).scalar() or 0

    return {
        "category_id": category.category_id,
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "sort_order": category.sort_order,
        "is_system": category.is_system,
        "created_at": category.created_at,
        "created_by_id": category.created_by_id,
        "tag_count": tag_count,
    }


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a tag category (Admin only). Fails if tags are in use."""
    require_admin(current_user, "delete tag categories")

    category = db.query(TagCategory).filter(TagCategory.category_id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag category not found"
        )

    if category.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system tag category"
        )

    # Check if any tags in this category are in use
    tags_in_use = db.query(Tag.tag_id).filter(
        Tag.category_id == category_id
    ).join(ModelTag, Tag.tag_id == ModelTag.tag_id).count()

    if tags_in_use > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category: {tags_in_use} tag(s) are assigned to models"
        )

    create_audit_log(
        db=db,
        entity_type="TagCategory",
        entity_id=category_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"name": category.name}
    )

    db.delete(category)
    db.commit()
    return None


# ============================================================================
# Tag Endpoints
# ============================================================================

@router.get("/", response_model=List[TagWithCategoryResponse])
def list_tags(
    category_id: Optional[int] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tags with optional filters."""
    query = db.query(Tag).options(joinedload(Tag.category))

    if category_id is not None:
        query = query.filter(Tag.category_id == category_id)
    if is_active is not None:
        query = query.filter(Tag.is_active == is_active)

    tags = query.order_by(Tag.category_id, Tag.sort_order, Tag.name).all()

    # Get model counts
    model_counts = dict(
        db.query(ModelTag.tag_id, func.count(ModelTag.model_id))
        .group_by(ModelTag.tag_id)
        .all()
    )

    result = []
    for tag in tags:
        result.append({
            "tag_id": tag.tag_id,
            "category_id": tag.category_id,
            "name": tag.name,
            "description": tag.description,
            "color": tag.color,
            "sort_order": tag.sort_order,
            "is_active": tag.is_active,
            "created_at": tag.created_at,
            "created_by_id": tag.created_by_id,
            "effective_color": tag.effective_color,
            "model_count": model_counts.get(tag.tag_id, 0),
            "category": {
                "category_id": tag.category.category_id,
                "name": tag.category.name,
                "description": tag.category.description,
                "color": tag.category.color,
                "sort_order": tag.category.sort_order,
                "is_system": tag.category.is_system,
                "created_at": tag.category.created_at,
                "created_by_id": tag.category.created_by_id,
                "tag_count": 0,  # Not computing nested count
            }
        })

    return result


@router.get("/usage-statistics", response_model=TagUsageStatistics)
def get_tag_usage_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tag usage statistics."""
    total_tags = db.query(func.count(Tag.tag_id)).scalar() or 0
    total_active_tags = db.query(func.count(Tag.tag_id)).filter(Tag.is_active == True).scalar() or 0
    total_categories = db.query(func.count(TagCategory.category_id)).scalar() or 0
    total_model_associations = db.query(func.count(ModelTag.model_id)).scalar() or 0

    # Get stats by category
    category_stats = db.query(
        TagCategory.category_id,
        TagCategory.name,
        TagCategory.color,
        func.count(Tag.tag_id).label('tag_count'),
    ).outerjoin(Tag, TagCategory.category_id == Tag.category_id).group_by(
        TagCategory.category_id, TagCategory.name, TagCategory.color
    ).all()

    # Get model associations by category
    association_counts = dict(
        db.query(Tag.category_id, func.count(ModelTag.model_id))
        .join(ModelTag, Tag.tag_id == ModelTag.tag_id)
        .group_by(Tag.category_id)
        .all()
    )

    tags_by_category = []
    for cat_id, cat_name, cat_color, tag_count in category_stats:
        tags_by_category.append(CategoryUsage(
            category_id=cat_id,
            category_name=cat_name,
            category_color=cat_color,
            tag_count=tag_count,
            model_associations=association_counts.get(cat_id, 0),
        ))

    return TagUsageStatistics(
        total_tags=total_tags,
        total_active_tags=total_active_tags,
        total_categories=total_categories,
        total_model_associations=total_model_associations,
        tags_by_category=tags_by_category,
    )


@router.get("/{tag_id}", response_model=TagWithCategoryResponse)
def get_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a tag by ID."""
    tag = db.query(Tag).options(joinedload(Tag.category)).filter(Tag.tag_id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    model_count = db.query(func.count(ModelTag.model_id)).filter(ModelTag.tag_id == tag_id).scalar() or 0

    return {
        "tag_id": tag.tag_id,
        "category_id": tag.category_id,
        "name": tag.name,
        "description": tag.description,
        "color": tag.color,
        "sort_order": tag.sort_order,
        "is_active": tag.is_active,
        "created_at": tag.created_at,
        "created_by_id": tag.created_by_id,
        "effective_color": tag.effective_color,
        "model_count": model_count,
        "category": {
            "category_id": tag.category.category_id,
            "name": tag.category.name,
            "description": tag.category.description,
            "color": tag.category.color,
            "sort_order": tag.category.sort_order,
            "is_system": tag.category.is_system,
            "created_at": tag.category.created_at,
            "created_by_id": tag.category.created_by_id,
            "tag_count": 0,
        }
    }


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag (Admin only)."""
    require_admin(current_user, "create tags")

    # Verify category exists
    category = db.query(TagCategory).filter(TagCategory.category_id == payload.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag category not found"
        )

    # Check for duplicate name within category
    existing = db.query(Tag).filter(
        Tag.category_id == payload.category_id,
        Tag.name == payload.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists in this category"
        )

    tag = Tag(
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        color=payload.color,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        created_by_id=current_user.user_id,
    )
    db.add(tag)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="Tag",
        entity_id=tag.tag_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": payload.name,
            "category_id": payload.category_id,
            "category_name": category.name,
        }
    )

    db.commit()
    db.refresh(tag)

    return {
        "tag_id": tag.tag_id,
        "category_id": tag.category_id,
        "name": tag.name,
        "description": tag.description,
        "color": tag.color,
        "sort_order": tag.sort_order,
        "is_active": tag.is_active,
        "created_at": tag.created_at,
        "created_by_id": tag.created_by_id,
        "effective_color": tag.color if tag.color else category.color,
        "model_count": 0,
    }


@router.patch("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a tag (Admin only)."""
    require_admin(current_user, "update tags")

    tag = db.query(Tag).options(joinedload(Tag.category)).filter(Tag.tag_id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    update_data = payload.model_dump(exclude_unset=True)

    # If changing category, verify new category exists
    if 'category_id' in update_data and update_data['category_id'] != tag.category_id:
        new_category = db.query(TagCategory).filter(
            TagCategory.category_id == update_data['category_id']
        ).first()
        if not new_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New tag category not found"
            )

    # Check for duplicate name if name or category is changing
    new_category_id = update_data.get('category_id', tag.category_id)
    new_name = update_data.get('name', tag.name)
    if new_name != tag.name or new_category_id != tag.category_id:
        existing = db.query(Tag).filter(
            Tag.category_id == new_category_id,
            Tag.name == new_name,
            Tag.tag_id != tag_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists in this category"
            )

    changes = {}
    for field, value in update_data.items():
        old_value = getattr(tag, field, None)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
        setattr(tag, field, value)

    if changes:
        create_audit_log(
            db=db,
            entity_type="Tag",
            entity_id=tag_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(tag)

    model_count = db.query(func.count(ModelTag.model_id)).filter(ModelTag.tag_id == tag_id).scalar() or 0

    return {
        "tag_id": tag.tag_id,
        "category_id": tag.category_id,
        "name": tag.name,
        "description": tag.description,
        "color": tag.color,
        "sort_order": tag.sort_order,
        "is_active": tag.is_active,
        "created_at": tag.created_at,
        "created_by_id": tag.created_by_id,
        "effective_color": tag.effective_color,
        "model_count": model_count,
    }


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a tag (Admin only). Fails if tag is in use."""
    require_admin(current_user, "delete tags")

    tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    # Check if tag is in use
    model_count = db.query(func.count(ModelTag.model_id)).filter(ModelTag.tag_id == tag_id).scalar() or 0
    if model_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete tag: it is assigned to {model_count} model(s)"
        )

    create_audit_log(
        db=db,
        entity_type="Tag",
        entity_id=tag_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"name": tag.name, "category_id": tag.category_id}
    )

    db.delete(tag)
    db.commit()
    return None


# ============================================================================
# Model Tag Assignment Endpoints
# ============================================================================

@router.get("/models/{model_id}/tags", response_model=ModelTagResponse)
def get_model_tags(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tags assigned to a model."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model_tags = db.query(ModelTag).options(
        joinedload(ModelTag.tag).joinedload(Tag.category)
    ).filter(ModelTag.model_id == model_id).all()

    tags = [build_tag_list_item(mt.tag) for mt in model_tags]

    return {"model_id": model_id, "tags": tags}


@router.post("/models/{model_id}/tags", response_model=ModelTagResponse)
def add_model_tags(
    model_id: int,
    payload: ModelTagAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add tags to a model (Admin only)."""
    require_admin(current_user, "assign tags to models")

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify all tags exist and are active
    tags = db.query(Tag).options(joinedload(Tag.category)).filter(
        Tag.tag_id.in_(payload.tag_ids),
        Tag.is_active == True
    ).all()

    found_ids = {t.tag_id for t in tags}
    missing_ids = set(payload.tag_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tags not found or inactive: {list(missing_ids)}"
        )

    # Get existing tags for this model
    existing = db.query(ModelTag.tag_id).filter(
        ModelTag.model_id == model_id,
        ModelTag.tag_id.in_(payload.tag_ids)
    ).all()
    existing_ids = {r[0] for r in existing}

    # Add new tags
    tags_to_add = [t for t in tags if t.tag_id not in existing_ids]
    for tag in tags_to_add:
        model_tag = ModelTag(
            model_id=model_id,
            tag_id=tag.tag_id,
            added_by_id=current_user.user_id,
        )
        db.add(model_tag)

        # Add history record
        history = ModelTagHistory(
            model_id=model_id,
            tag_id=tag.tag_id,
            action="ADDED",
            performed_by_id=current_user.user_id,
        )
        db.add(history)

    if tags_to_add:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="TAGS_ADDED",
            user_id=current_user.user_id,
            changes={"tags_added": [t.name for t in tags_to_add]}
        )

    db.commit()

    # Fetch updated tags
    model_tags = db.query(ModelTag).options(
        joinedload(ModelTag.tag).joinedload(Tag.category)
    ).filter(ModelTag.model_id == model_id).all()

    return {"model_id": model_id, "tags": [build_tag_list_item(mt.tag) for mt in model_tags]}


@router.delete("/models/{model_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_model_tag(
    model_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a tag from a model (Admin only)."""
    require_admin(current_user, "remove tags from models")

    model_tag = db.query(ModelTag).filter(
        ModelTag.model_id == model_id,
        ModelTag.tag_id == tag_id
    ).first()

    if not model_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not assigned to this model"
        )

    # Get tag name for audit
    tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
    tag_name = tag.name if tag else f"tag_id={tag_id}"

    # Add history record
    history = ModelTagHistory(
        model_id=model_id,
        tag_id=tag_id,
        action="REMOVED",
        performed_by_id=current_user.user_id,
    )
    db.add(history)

    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="TAG_REMOVED",
        user_id=current_user.user_id,
        changes={"tag_removed": tag_name}
    )

    db.delete(model_tag)
    db.commit()
    return None


# ============================================================================
# Bulk Tag Operations
# ============================================================================

@router.post("/bulk-assign", response_model=BulkTagResponse)
def bulk_assign_tag(
    payload: BulkTagAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk assign a tag to multiple models (Admin only). Idempotent."""
    require_admin(current_user, "bulk assign tags")

    # Verify tag exists and is active
    tag = db.query(Tag).filter(Tag.tag_id == payload.tag_id, Tag.is_active == True).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found or inactive"
        )

    # Verify models exist
    models = db.query(Model.model_id).filter(Model.model_id.in_(payload.model_ids)).all()
    found_model_ids = {m[0] for m in models}
    missing_model_ids = set(payload.model_ids) - found_model_ids
    if missing_model_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Models not found: {list(missing_model_ids)}"
        )

    # Get existing assignments
    existing = db.query(ModelTag.model_id).filter(
        ModelTag.tag_id == payload.tag_id,
        ModelTag.model_id.in_(payload.model_ids)
    ).all()
    existing_model_ids = {r[0] for r in existing}

    # Add new assignments
    models_to_add = found_model_ids - existing_model_ids
    for model_id in models_to_add:
        model_tag = ModelTag(
            model_id=model_id,
            tag_id=payload.tag_id,
            added_by_id=current_user.user_id,
        )
        db.add(model_tag)

        history = ModelTagHistory(
            model_id=model_id,
            tag_id=payload.tag_id,
            action="ADDED",
            performed_by_id=current_user.user_id,
        )
        db.add(history)

    if models_to_add:
        create_audit_log(
            db=db,
            entity_type="Tag",
            entity_id=payload.tag_id,
            action="BULK_ASSIGN",
            user_id=current_user.user_id,
            changes={
                "tag_name": tag.name,
                "models_added": len(models_to_add),
                "model_ids": list(models_to_add),
            }
        )

    db.commit()

    return BulkTagResponse(
        tag_id=payload.tag_id,
        total_requested=len(payload.model_ids),
        total_modified=len(models_to_add),
        already_had_tag=len(existing_model_ids),
    )


@router.post("/bulk-remove", response_model=BulkTagResponse)
def bulk_remove_tag(
    payload: BulkTagRemove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk remove a tag from multiple models (Admin only)."""
    require_admin(current_user, "bulk remove tags")

    # Verify tag exists
    tag = db.query(Tag).filter(Tag.tag_id == payload.tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    # Get existing assignments
    existing_tags = db.query(ModelTag).filter(
        ModelTag.tag_id == payload.tag_id,
        ModelTag.model_id.in_(payload.model_ids)
    ).all()

    existing_model_ids = {mt.model_id for mt in existing_tags}
    not_assigned = set(payload.model_ids) - existing_model_ids

    # Remove assignments and add history
    for mt in existing_tags:
        history = ModelTagHistory(
            model_id=mt.model_id,
            tag_id=payload.tag_id,
            action="REMOVED",
            performed_by_id=current_user.user_id,
        )
        db.add(history)
        db.delete(mt)

    if existing_tags:
        create_audit_log(
            db=db,
            entity_type="Tag",
            entity_id=payload.tag_id,
            action="BULK_REMOVE",
            user_id=current_user.user_id,
            changes={
                "tag_name": tag.name,
                "models_removed": len(existing_tags),
                "model_ids": list(existing_model_ids),
            }
        )

    db.commit()

    return BulkTagResponse(
        tag_id=payload.tag_id,
        total_requested=len(payload.model_ids),
        total_modified=len(existing_tags),
        did_not_have_tag=len(not_assigned),
    )


# ============================================================================
# Tag History and Statistics
# ============================================================================

@router.get("/models/{model_id}/tags/history", response_model=ModelTagHistoryResponse)
def get_model_tag_history(
    model_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tag change history for a model."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    history_records = db.query(ModelTagHistory).options(
        joinedload(ModelTagHistory.tag).joinedload(Tag.category),
        joinedload(ModelTagHistory.performed_by)
    ).filter(
        ModelTagHistory.model_id == model_id
    ).order_by(ModelTagHistory.performed_at.desc()).limit(limit).all()

    total_count = db.query(func.count(ModelTagHistory.history_id)).filter(
        ModelTagHistory.model_id == model_id
    ).scalar() or 0

    history_items = []
    for h in history_records:
        history_items.append({
            "history_id": h.history_id,
            "model_id": h.model_id,
            "tag_id": h.tag_id,
            "tag_name": h.tag.name if h.tag else "Unknown",
            "category_name": h.tag.category.name if h.tag and h.tag.category else "Unknown",
            "action": h.action,
            "performed_at": h.performed_at,
            "performed_by_id": h.performed_by_id,
            "performed_by_name": h.performed_by.full_name if h.performed_by else None,
        })

    return {
        "model_id": model_id,
        "total_count": total_count,
        "history": history_items,
    }
