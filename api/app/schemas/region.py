"""Region schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class RegionBase(BaseModel):
    """Base region schema."""
    code: str = Field(..., max_length=10, description="Region code (e.g., US, UK, EU, APAC)")
    name: str = Field(..., max_length=100, description="Region name")


class RegionCreate(RegionBase):
    """Schema for creating a region."""
    pass


class RegionUpdate(BaseModel):
    """Schema for updating a region."""
    code: str | None = Field(None, max_length=10)
    name: str | None = Field(None, max_length=100)


class Region(RegionBase):
    """Region response schema."""
    region_id: int
    created_at: datetime

    class Config:
        from_attributes = True
