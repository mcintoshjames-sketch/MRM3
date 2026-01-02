"""Model-Application relationship schemas."""
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Literal
from app.schemas.map_application import MapApplicationListResponse
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.user import UserResponse


class ModelApplicationCreate(BaseModel):
    """Schema for creating a model-application relationship."""
    application_id: int
    relationship_type_id: int
    relationship_direction: Literal["UPSTREAM", "DOWNSTREAM"]
    description: Optional[str] = None
    effective_date: Optional[date] = None


class ModelApplicationUpdate(BaseModel):
    """Schema for updating a model-application relationship."""
    relationship_type_id: Optional[int] = None
    relationship_direction: Optional[Literal["UPSTREAM", "DOWNSTREAM"]] = None
    description: Optional[str] = None
    end_date: Optional[date] = None


class ModelApplicationResponse(BaseModel):
    """Response schema for model-application relationship."""
    model_id: int
    application_id: int
    application: MapApplicationListResponse
    relationship_type: TaxonomyValueResponse
    relationship_direction: Optional[Literal["UPSTREAM", "DOWNSTREAM", "UNKNOWN"]] = None
    description: Optional[str] = None
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    created_by_user: Optional[UserResponse] = None
    updated_at: datetime

    class Config:
        from_attributes = True
