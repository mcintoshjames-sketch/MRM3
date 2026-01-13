"""Tag schemas for model categorization."""
import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')


def validate_hex_color(value: Optional[str]) -> Optional[str]:
    """Validate that a value is a valid hex color code."""
    if value is None:
        return None
    if not HEX_COLOR_PATTERN.match(value):
        raise ValueError(
            'Invalid hex color format. Must be #RRGGBB (e.g., #DC2626)')
    return value.upper()  # Normalize to uppercase


# ============================================================================
# Tag Category Schemas
# ============================================================================

class TagCategoryBase(BaseModel):
    """Base schema for tag categories."""
    name: str
    description: Optional[str] = None
    color: str = "#6B7280"
    sort_order: int = 0

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        result = validate_hex_color(v)
        if result is None:
            raise ValueError('Color is required')
        return result


class TagCategoryCreate(TagCategoryBase):
    """Schema for creating a tag category."""
    pass


class TagCategoryUpdate(BaseModel):
    """Schema for updating a tag category."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        return validate_hex_color(v)


class TagCategoryResponse(TagCategoryBase):
    """Response schema for a tag category."""
    category_id: int
    is_system: bool
    created_at: datetime
    created_by_id: Optional[int] = None
    tag_count: int = 0  # Number of tags in this category

    model_config = ConfigDict(from_attributes=True)


class TagCategoryWithTagsResponse(TagCategoryResponse):
    """Response schema for a tag category with its tags."""
    tags: List["TagResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Tag Schemas
# ============================================================================

class TagBase(BaseModel):
    """Base schema for tags."""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        return validate_hex_color(v)


class TagCreate(TagBase):
    """Schema for creating a tag."""
    category_id: int


class TagUpdate(BaseModel):
    """Schema for updating a tag."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        return validate_hex_color(v)


class TagResponse(TagBase):
    """Response schema for a tag."""
    tag_id: int
    category_id: int
    created_at: datetime
    created_by_id: Optional[int] = None
    effective_color: str  # Computed: tag color or category color
    model_count: int = 0  # Number of models with this tag

    model_config = ConfigDict(from_attributes=True)


class TagWithCategoryResponse(TagResponse):
    """Response schema for a tag with its category."""
    category: TagCategoryResponse

    model_config = ConfigDict(from_attributes=True)


class TagListItem(BaseModel):
    """Lightweight tag info for list views and model associations."""
    tag_id: int
    name: str
    color: Optional[str] = None
    effective_color: str
    category_id: int
    category_name: str
    category_color: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Model Tag Association Schemas
# ============================================================================

class ModelTagAssign(BaseModel):
    """Schema for assigning tags to a model."""
    tag_ids: List[int]


class ModelTagRemove(BaseModel):
    """Schema for removing a tag from a model."""
    tag_id: int


class BulkTagAssign(BaseModel):
    """Schema for bulk assigning a tag to multiple models."""
    tag_id: int
    model_ids: List[int]


class BulkTagRemove(BaseModel):
    """Schema for bulk removing a tag from multiple models."""
    tag_id: int
    model_ids: List[int]


class BulkTagResponse(BaseModel):
    """Response for bulk tag operations."""
    tag_id: int
    total_requested: int
    total_modified: int
    already_had_tag: int = 0  # For assign
    did_not_have_tag: int = 0  # For remove


class ModelTagResponse(BaseModel):
    """Response schema for a model's tags."""
    model_id: int
    tags: List[TagListItem]


# ============================================================================
# Tag History Schemas
# ============================================================================

class TagHistoryItem(BaseModel):
    """Response schema for a single tag history entry."""
    history_id: int
    model_id: int
    tag_id: int
    tag_name: str
    category_name: str
    action: str  # 'ADDED' or 'REMOVED'
    performed_at: datetime
    performed_by_id: Optional[int] = None
    performed_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModelTagHistoryResponse(BaseModel):
    """Response schema for a model's tag history."""
    model_id: int
    total_count: int
    history: List[TagHistoryItem]


# ============================================================================
# Tag Usage Statistics
# ============================================================================

class CategoryUsage(BaseModel):
    """Usage statistics for a category."""
    category_id: int
    category_name: str
    category_color: str
    tag_count: int
    model_associations: int


class TagUsageStatistics(BaseModel):
    """Response schema for tag usage statistics."""
    total_tags: int
    total_active_tags: int
    total_categories: int
    total_model_associations: int
    tags_by_category: List[CategoryUsage]


# Forward references
TagCategoryWithTagsResponse.model_rebuild()
