"""Model Due Date Override schemas."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime, date
from typing import Optional, Literal
from app.schemas.user import UserResponse


class DueDateOverrideCreate(BaseModel):
    """Schema for creating a due date override."""
    override_type: Literal["ONE_TIME", "PERMANENT"] = Field(
        ..., description="ONE_TIME auto-clears after validation, PERMANENT persists and rolls forward"
    )
    target_scope: Literal["CURRENT_REQUEST", "NEXT_CYCLE"] = Field(
        ..., description="CURRENT_REQUEST affects active validation, NEXT_CYCLE affects future"
    )
    override_date: date = Field(
        ..., description="New due date (must be earlier than calculated and in the future)"
    )
    reason: str = Field(
        ..., min_length=10, description="Justification for override (min 10 characters)"
    )

    @field_validator('reason')
    @classmethod
    def validate_reason_length(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("Reason must be at least 10 characters")
        return v.strip()


class DueDateOverrideClear(BaseModel):
    """Schema for clearing/canceling an override."""
    reason: str = Field(
        ..., min_length=10, description="Reason for clearing the override"
    )

    @field_validator('reason')
    @classmethod
    def validate_reason_length(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("Reason must be at least 10 characters")
        return v.strip()


class DueDateOverrideResponse(BaseModel):
    """Response schema for a single override."""
    override_id: int
    model_id: int
    validation_request_id: Optional[int] = None
    override_type: str
    target_scope: str
    override_date: date
    original_calculated_date: date
    reason: str
    created_by_user_id: int
    created_by_user: UserResponse
    created_at: datetime
    is_active: bool
    cleared_at: Optional[datetime] = None
    cleared_by_user_id: Optional[int] = None
    cleared_by_user: Optional[UserResponse] = None
    cleared_reason: Optional[str] = None
    cleared_type: Optional[str] = None
    superseded_by_override_id: Optional[int] = None
    rolled_from_override_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class CurrentDueDateOverrideResponse(BaseModel):
    """Response schema for current override status."""
    model_id: int
    model_name: str
    has_active_override: bool
    active_override: Optional[DueDateOverrideResponse] = None

    # Calculated dates for reference
    policy_calculated_date: Optional[date] = None
    effective_due_date: Optional[date] = None  # min(override, calculated) - enforces earlier-only

    # Validation request context (if applicable)
    current_validation_request_id: Optional[int] = None
    current_validation_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class DueDateOverrideHistoryResponse(BaseModel):
    """Response schema for override history."""
    model_id: int
    model_name: str
    active_override: Optional[DueDateOverrideResponse] = None
    override_history: list[DueDateOverrideResponse] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
