"""Schemas for model activity timeline."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ActivityTimelineItem(BaseModel):
    """Single activity in the model timeline."""
    timestamp: datetime
    activity_type: str  # "model_created", "version_created", "validation_status_change", etc.
    title: str  # Short description
    description: Optional[str] = None  # Detailed info
    user_name: Optional[str] = None  # Who performed the action
    user_id: Optional[int] = None
    entity_type: Optional[str] = None  # "ModelVersion", "ValidationRequest", etc.
    entity_id: Optional[int] = None  # Reference to related entity
    icon: str  # Icon identifier for frontend

    class Config:
        from_attributes = True


class ActivityTimelineResponse(BaseModel):
    """Response containing all activities for a model."""
    model_id: int
    model_name: str
    activities: List[ActivityTimelineItem]
    total_count: int
