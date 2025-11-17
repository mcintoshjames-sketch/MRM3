"""Taxonomy schemas."""
from pydantic import BaseModel
from datetime import datetime


class TaxonomyValueBase(BaseModel):
    """Base schema for taxonomy value."""
    code: str
    label: str
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True


class TaxonomyValueCreate(TaxonomyValueBase):
    """Schema for creating a taxonomy value."""
    pass


class TaxonomyValueUpdate(BaseModel):
    """Schema for updating a taxonomy value."""
    code: str | None = None
    label: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class TaxonomyValueResponse(TaxonomyValueBase):
    """Response schema for taxonomy value."""
    value_id: int
    taxonomy_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaxonomyBase(BaseModel):
    """Base schema for taxonomy."""
    name: str
    description: str | None = None


class TaxonomyCreate(TaxonomyBase):
    """Schema for creating a taxonomy."""
    pass


class TaxonomyUpdate(BaseModel):
    """Schema for updating a taxonomy."""
    name: str | None = None
    description: str | None = None


class TaxonomyResponse(TaxonomyBase):
    """Response schema for taxonomy."""
    taxonomy_id: int
    is_system: bool
    created_at: datetime
    values: list[TaxonomyValueResponse] = []

    class Config:
        from_attributes = True


class TaxonomyListResponse(TaxonomyBase):
    """Response schema for taxonomy list (without values)."""
    taxonomy_id: int
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True
