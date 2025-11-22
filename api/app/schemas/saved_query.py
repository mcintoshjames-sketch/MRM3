"""Saved Query schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class SavedQueryCreate(BaseModel):
    """Schema for creating a saved query."""
    query_name: str = Field(..., min_length=1, max_length=255)
    query_text: str = Field(..., min_length=1)
    description: str | None = None
    is_public: bool = False


class SavedQueryUpdate(BaseModel):
    """Schema for updating a saved query."""
    query_name: str | None = Field(None, min_length=1, max_length=255)
    query_text: str | None = Field(None, min_length=1)
    description: str | None = None
    is_public: bool | None = None


class SavedQueryResponse(BaseModel):
    """Schema for saved query response."""
    query_id: int
    user_id: int
    query_name: str
    query_text: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
