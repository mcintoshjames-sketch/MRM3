"""Export View schemas."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ExportViewBase(BaseModel):
    """Base export view schema."""
    view_name: str
    entity_type: str
    columns: List[str]
    is_public: bool = False
    description: Optional[str] = None


class ExportViewCreate(ExportViewBase):
    """Schema for creating a new export view."""
    pass


class ExportViewUpdate(BaseModel):
    """Schema for updating an export view."""
    view_name: Optional[str] = None
    columns: Optional[List[str]] = None
    is_public: Optional[bool] = None
    description: Optional[str] = None


class ExportViewResponse(ExportViewBase):
    """Schema for export view response."""
    view_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
