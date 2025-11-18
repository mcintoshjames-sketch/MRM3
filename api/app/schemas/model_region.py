"""Model-Region schemas."""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ModelRegionBase(BaseModel):
    """Base model-region schema."""
    regional_risk_level: Optional[str] = Field(None, max_length=20, description="Regional risk level (HIGH, MEDIUM, LOW)")
    notes: Optional[str] = Field(None, description="Regional context notes")


class ModelRegionCreate(ModelRegionBase):
    """Schema for creating a model-region link."""
    model_id: int
    region_id: int
    shared_model_owner_id: Optional[int] = Field(None, description="Regional owner if different from global")


class ModelRegionUpdate(BaseModel):
    """Schema for updating a model-region link."""
    shared_model_owner_id: Optional[int] = None
    regional_risk_level: Optional[str] = Field(None, max_length=20)
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
