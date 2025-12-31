"""Taxonomy schemas."""
from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Optional


class TaxonomyValueBase(BaseModel):
    """Base schema for taxonomy value."""
    code: str
    label: str
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True
    min_days: int | None = None
    max_days: int | None = None
    downgrade_notches: int | None = None  # Scorecard penalty for Final Risk Ranking
    requires_irp: bool | None = None  # For MRSA Risk Level: True if IRP coverage required


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
    min_days: int | None = None
    max_days: int | None = None
    downgrade_notches: int | None = None  # Scorecard penalty for Final Risk Ranking
    requires_irp: bool | None = None  # For MRSA Risk Level: True if IRP coverage required


class TaxonomyValueResponse(TaxonomyValueBase):
    """Response schema for taxonomy value."""
    value_id: int
    taxonomy_id: int
    is_system_protected: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class TaxonomyBase(BaseModel):
    """Base schema for taxonomy."""
    name: str
    description: str | None = None
    taxonomy_type: str = "standard"


class TaxonomyCreate(TaxonomyBase):
    """Schema for creating a taxonomy."""
    pass


class TaxonomyUpdate(BaseModel):
    """Schema for updating a taxonomy."""
    name: str | None = None
    description: str | None = None
    taxonomy_type: str | None = None


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
