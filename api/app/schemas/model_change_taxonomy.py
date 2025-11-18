"""Model change taxonomy schemas."""
from typing import Optional, List
from pydantic import BaseModel


class ModelChangeTypeBase(BaseModel):
    """Base schema for model change type."""
    code: int
    name: str
    description: Optional[str] = None
    mv_activity: Optional[str] = None
    requires_mv_approval: bool
    sort_order: int
    is_active: bool


class ModelChangeTypeResponse(ModelChangeTypeBase):
    """Response schema for model change type."""
    change_type_id: int
    category_id: int

    class Config:
        from_attributes = True


class ModelChangeCategoryBase(BaseModel):
    """Base schema for model change category."""
    code: str
    name: str
    sort_order: int


class ModelChangeCategoryResponse(ModelChangeCategoryBase):
    """Response schema for model change category with nested types."""
    category_id: int
    change_types: List[ModelChangeTypeResponse] = []

    class Config:
        from_attributes = True
