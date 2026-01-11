"""Model-Region schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from app.schemas.user_lookup import ModelAssigneeResponse


class ModelRegionBase(BaseModel):
    """Base model-region schema."""
    version_id: Optional[int] = Field(None, description="Regional version (NULL = same as global)")
    regional_risk_level: Optional[str] = Field(None, description="Regional risk level override", max_length=20)
    notes: Optional[str] = Field(None, description="Regional context notes")


class ModelRegionCreate(ModelRegionBase):
    """Schema for creating a model-region link."""
    region_id: int
    shared_model_owner_id: Optional[int] = Field(None, description="Regional owner if different from global")


class ModelRegionUpdate(BaseModel):
    """Schema for updating a model-region link."""
    shared_model_owner_id: Optional[int] = None
    version_id: Optional[int] = None
    regional_risk_level: Optional[str] = None
    notes: Optional[str] = None


class ModelRegion(ModelRegionBase):
    """Model-region response schema."""
    id: int
    model_id: int
    region_id: int
    shared_model_owner_id: Optional[int] = None
    shared_model_owner: Optional[ModelAssigneeResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
