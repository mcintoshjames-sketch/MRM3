"""Overdue Revalidation Commentary schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional, Literal
from app.schemas.user import UserResponse


class OverdueCommentaryBase(BaseModel):
    """Base schema for overdue commentary."""
    reason_comment: str = Field(..., min_length=10, description="Explanation for the overdue status")
    target_date: date = Field(..., description="Target Submission Date (PRE_SUBMISSION) or Target Completion Date (VALIDATION_IN_PROGRESS)")


class OverdueCommentaryCreate(OverdueCommentaryBase):
    """Schema for creating overdue commentary."""
    overdue_type: Literal["PRE_SUBMISSION", "VALIDATION_IN_PROGRESS"] = Field(
        ..., description="Type of overdue: PRE_SUBMISSION or VALIDATION_IN_PROGRESS"
    )


class OverdueCommentaryResponse(OverdueCommentaryBase):
    """Response schema for a single overdue comment."""
    comment_id: int
    validation_request_id: int
    overdue_type: str
    created_by_user_id: int
    created_by_user: UserResponse
    created_at: datetime
    is_current: bool
    superseded_at: Optional[datetime] = None
    superseded_by_comment_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class CurrentOverdueCommentaryResponse(BaseModel):
    """Response schema for current overdue commentary status."""
    validation_request_id: int
    model_id: int
    model_name: str
    overdue_type: Optional[str] = None
    has_current_comment: bool
    current_comment: Optional[OverdueCommentaryResponse] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    computed_completion_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class OverdueCommentaryHistoryResponse(BaseModel):
    """Response schema for overdue commentary history."""
    validation_request_id: int
    model_id: int
    model_name: str
    current_comment: Optional[OverdueCommentaryResponse] = None
    comment_history: list[OverdueCommentaryResponse] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
