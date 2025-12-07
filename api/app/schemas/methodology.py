"""Methodology library schemas."""
from typing import Optional, List
from pydantic import BaseModel


class MethodologyBase(BaseModel):
    """Base schema for methodology."""
    name: str
    description: Optional[str] = None
    variants: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class MethodologyCreate(MethodologyBase):
    """Schema for creating a methodology."""
    category_id: int


class MethodologyUpdate(BaseModel):
    """Update schema for methodology (all fields optional)."""
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MethodologyResponse(MethodologyBase):
    """Response schema for methodology."""
    methodology_id: int
    category_id: int

    class Config:
        from_attributes = True


class MethodologyCategoryBase(BaseModel):
    """Base schema for methodology category."""
    code: str
    name: str
    sort_order: int = 0
    is_aiml: bool = False


class MethodologyCategoryCreate(MethodologyCategoryBase):
    """Schema for creating a methodology category."""
    pass


class MethodologyCategoryUpdate(BaseModel):
    """Update schema for methodology category (all fields optional)."""
    code: Optional[str] = None
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_aiml: Optional[bool] = None


class MethodologyCategoryResponse(MethodologyCategoryBase):
    """Response schema for methodology category with nested methodologies."""
    category_id: int
    methodologies: List[MethodologyResponse] = []

    class Config:
        from_attributes = True


class MethodologyCategoryListResponse(MethodologyCategoryBase):
    """Response schema for methodology category list (without methodologies)."""
    category_id: int

    class Config:
        from_attributes = True
