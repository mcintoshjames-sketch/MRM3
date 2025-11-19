"""Region schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class RegionBase(BaseModel):
    """Base region schema."""
    code: str = Field(..., max_length=10, description="Region code (e.g., US, UK, EU, APAC)")
    name: str = Field(..., max_length=100, description="Region name")
    requires_regional_approval: bool = Field(
        default=False,
        description="Whether this region requires regional approver sign-off for validations"
    )


class RegionCreate(RegionBase):
    """Schema for creating a region."""
    pass


class RegionUpdate(BaseModel):
    """Schema for updating a region."""
    code: str | None = Field(None, max_length=10)
    name: str | None = Field(None, max_length=100)
    requires_regional_approval: bool | None = Field(None)


class Region(RegionBase):
    """Region response schema."""
    region_id: int
    created_at: datetime

    class Config:
        from_attributes = True
