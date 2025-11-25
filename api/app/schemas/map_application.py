"""MAP Application schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MapApplicationBase(BaseModel):
    """Base schema for MAP application."""
    application_code: str
    application_name: str
    description: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    department: Optional[str] = None
    technology_stack: Optional[str] = None
    criticality_tier: Optional[str] = None
    status: str = "Active"
    external_url: Optional[str] = None


class MapApplicationResponse(MapApplicationBase):
    """Response schema for MAP application."""
    application_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MapApplicationListResponse(BaseModel):
    """Simplified response for MAP application lists."""
    application_id: int
    application_code: str
    application_name: str
    owner_name: Optional[str] = None
    department: Optional[str] = None
    criticality_tier: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
