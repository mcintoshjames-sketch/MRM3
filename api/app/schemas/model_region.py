"""Model-Region schemas."""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ModelRegionBase(BaseModel):
    """Base model-region schema."""
    version_id: Optional[int] = Field(None, description="Regional version (NULL = same as global)")
    notes: Optional[str] = Field(None, description="Regional context notes")


class ModelRegionCreate(ModelRegionBase):
    """Schema for creating a model-region link."""
    model_id: int
    region_id: int
    shared_model_owner_id: Optional[int] = Field(None, description="Regional owner if different from global")


class ModelRegionUpdate(BaseModel):
    """Schema for updating a model-region link."""
    shared_model_owner_id: Optional[int] = None
    version_id: Optional[int] = None
    notes: Optional[str] = None


class ModelRegion(ModelRegionBase):
    """Model-region response schema."""
    id: int
    model_id: int
    region_id: int
    shared_model_owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
