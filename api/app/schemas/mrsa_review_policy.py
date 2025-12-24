"""MRSA Review Policy and Exception schemas."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional
from enum import Enum
from app.schemas.user import UserResponse
from app.schemas.taxonomy import TaxonomyValueResponse


# ============================================================================
# MRSA Review Status Enum
# ============================================================================

class MRSAReviewStatusEnum(str, Enum):
    """Status classification for MRSA review compliance."""
    CURRENT = "CURRENT"  # Next review not yet due
    UPCOMING = "UPCOMING"  # Due within warning window
    OVERDUE = "OVERDUE"  # Past due date
    NO_IRP = "NO_IRP"  # Requires IRP but has no coverage
    NEVER_REVIEWED = "NEVER_REVIEWED"  # No reviews recorded
    NO_REQUIREMENT = "NO_REQUIREMENT"  # No review policy applies


# ============================================================================
# MRSA Review Policy Schemas
# ============================================================================

class MRSAReviewPolicyBase(BaseModel):
    """Base schema for MRSA review policy."""
    mrsa_risk_level_id: int
    frequency_months: int
    initial_review_months: int
    warning_days: int = 30
    is_active: bool = True


class MRSAReviewPolicyCreate(MRSAReviewPolicyBase):
    """Schema for creating an MRSA review policy."""
    pass


class MRSAReviewPolicyUpdate(BaseModel):
    """Schema for updating an MRSA review policy."""
    mrsa_risk_level_id: Optional[int] = None
    frequency_months: Optional[int] = None
    initial_review_months: Optional[int] = None
    warning_days: Optional[int] = None
    is_active: Optional[bool] = None


class MRSAReviewPolicyResponse(MRSAReviewPolicyBase):
    """Response schema for MRSA review policy."""
    policy_id: int
    mrsa_risk_level: Optional[TaxonomyValueResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MRSA Review Exception Schemas
# ============================================================================

class MRSAReviewExceptionCreate(BaseModel):
    """Schema for creating an MRSA review exception."""
    mrsa_id: int
    override_due_date: date
    reason: str


class MRSAReviewExceptionUpdate(BaseModel):
    """Schema for updating an MRSA review exception."""
    override_due_date: Optional[date] = None
    reason: Optional[str] = None
    is_active: Optional[bool] = None


class MRSAReviewExceptionMRSASummary(BaseModel):
    """Lightweight MRSA summary for exception responses."""
    model_id: int
    model_name: str
    mrsa_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class MRSAReviewExceptionResponse(BaseModel):
    """Response schema for MRSA review exception."""
    exception_id: int
    mrsa_id: int
    mrsa: Optional[MRSAReviewExceptionMRSASummary] = None
    override_due_date: date
    reason: str
    approved_by_user_id: int
    approved_by: Optional[UserResponse] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MRSA Review Status Schemas
# ============================================================================

class MRSAReviewStatusOwnerSummary(BaseModel):
    """Lightweight owner summary for review status responses."""
    user_id: int
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class MRSAReviewStatus(BaseModel):
    """Response schema for single MRSA review status."""
    mrsa_id: int
    mrsa_name: str
    risk_level: Optional[str] = None
    last_review_date: Optional[date] = None
    next_due_date: Optional[date] = None
    status: MRSAReviewStatusEnum
    days_until_due: Optional[int] = None
    owner: Optional[MRSAReviewStatusOwnerSummary] = None
    has_exception: bool = False
    exception_due_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class MRSAReviewSummary(BaseModel):
    """Dashboard summary of MRSA review statuses."""
    total_count: int = 0
    current_count: int = 0
    upcoming_count: int = 0
    overdue_count: int = 0
    no_irp_count: int = 0
    never_reviewed_count: int = 0
    no_requirement_count: int = 0

    model_config = ConfigDict(from_attributes=True)
