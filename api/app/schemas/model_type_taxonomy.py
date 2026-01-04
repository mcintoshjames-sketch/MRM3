"""Model type taxonomy schemas."""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ModelTypeBase(BaseModel):
    """Base schema for model type."""
    name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool


class ModelTypeUpdate(BaseModel):
    """Update schema for model type (all fields optional)."""
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ModelTypeResponse(ModelTypeBase):
    """Response schema for model type."""
    type_id: int
    category_id: int

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelTypeCategoryBase(BaseModel):
    """Base schema for model type category."""
    name: str
    description: Optional[str] = None
    sort_order: int


class ModelTypeCategoryResponse(ModelTypeCategoryBase):
    """Response schema for model type category with nested types."""
    category_id: int
    model_types: List[ModelTypeResponse] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
