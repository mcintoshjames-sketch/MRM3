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
    enforce_validation_plan: bool = Field(
        default=False,
        description="Whether validations in this region must include a validation plan"
    )


class RegionCreate(RegionBase):
    """Schema for creating a region."""
    pass


class RegionUpdate(BaseModel):
    """Schema for updating a region."""
    code: str | None = Field(None, max_length=10)
    name: str | None = Field(None, max_length=100)
    requires_regional_approval: bool | None = Field(None)
    enforce_validation_plan: bool | None = Field(None)


class Region(RegionBase):
    """Region response schema."""
    region_id: int
    created_at: datetime

    class Config:
        from_attributes = True
