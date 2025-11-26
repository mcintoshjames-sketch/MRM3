"""Pydantic schemas for decommissioning workflow."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, field_validator

from app.schemas.user import UserResponse
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.region import Region


# --- Helper Schemas ---

class RegionBasic(BaseModel):
    """Minimal region info for decommissioning display (without created_at)."""
    region_id: int
    code: str
    name: str

    class Config:
        from_attributes = True


# --- Request/Input Schemas ---

class DecommissioningRequestCreate(BaseModel):
    """Schema for creating a new decommissioning request."""
    model_id: int
    reason_id: int
    replacement_model_id: Optional[int] = None
    replacement_implementation_date: Optional[date] = None  # For creating version if needed
    last_production_date: date
    gap_justification: Optional[str] = None
    archive_location: str
    downstream_impact_verified: bool = False

    @field_validator('archive_location')
    @classmethod
    def validate_archive_location(cls, v):
        if not v or not v.strip():
            raise ValueError('Archive location is required')
        return v.strip()


class ValidatorReviewRequest(BaseModel):
    """Schema for validator review (Stage 1)."""
    approved: bool
    comment: str

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        if not v or not v.strip():
            raise ValueError('Comment is required for validator review')
        return v.strip()


class OwnerReviewRequest(BaseModel):
    """Schema for owner review (Stage 1 - parallel with validator if owner != requestor)."""
    approved: bool
    comment: str

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        if not v or not v.strip():
            raise ValueError('Comment is required for owner review')
        return v.strip()


class ApprovalSubmitRequest(BaseModel):
    """Schema for Global/Regional approval submission (Stage 2)."""
    is_approved: bool
    comment: Optional[str] = None


class WithdrawRequest(BaseModel):
    """Schema for withdrawing a decommissioning request."""
    reason: Optional[str] = None


class DecommissioningRequestUpdate(BaseModel):
    """
    Schema for updating a decommissioning request.

    Restrictions:
    - Only allowed while status is PENDING (before any approvals)
    - Only request creator or Admin can update
    """
    reason_id: Optional[int] = None
    replacement_model_id: Optional[int] = None
    replacement_implementation_date: Optional[date] = None
    last_production_date: Optional[date] = None
    gap_justification: Optional[str] = None
    archive_location: Optional[str] = None

    @field_validator('archive_location')
    @classmethod
    def validate_archive_location(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Archive location cannot be empty')
        return v.strip() if v else v


# --- Response Schemas ---

class DecommissioningApprovalResponse(BaseModel):
    """Response schema for decommissioning approval record."""
    approval_id: int
    request_id: int
    approver_type: str  # GLOBAL, REGIONAL
    region_id: Optional[int] = None
    region: Optional[Region] = None
    approved_by_id: Optional[int] = None
    approved_by: Optional[UserResponse] = None
    approved_at: Optional[datetime] = None
    is_approved: Optional[bool] = None  # NULL=pending
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class DecommissioningStatusHistoryResponse(BaseModel):
    """Response schema for status history entry."""
    history_id: int
    request_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by_id: int
    changed_by: Optional[UserResponse] = None
    changed_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ReplacementModelInfo(BaseModel):
    """Minimal model info for replacement model display."""
    model_id: int
    model_name: str
    implementation_date: Optional[date] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class DecommissioningModelInfo(BaseModel):
    """Model info for decommissioning display."""
    model_id: int
    model_name: str
    owner_id: int
    owner_name: Optional[str] = None
    risk_tier: Optional[str] = None
    status: Optional[str] = None
    regions: List[RegionBasic] = []

    class Config:
        from_attributes = True


class DecommissioningRequestResponse(BaseModel):
    """Response schema for decommissioning request."""
    request_id: int
    model_id: int
    model: Optional[DecommissioningModelInfo] = None
    status: str
    reason_id: int
    reason: Optional[TaxonomyValueResponse] = None
    replacement_model_id: Optional[int] = None
    replacement_model: Optional[ReplacementModelInfo] = None
    last_production_date: date
    gap_justification: Optional[str] = None
    gap_days: Optional[int] = None  # Computed: replacement implementation - last production
    archive_location: str
    downstream_impact_verified: bool

    # Creation info
    created_at: datetime
    created_by_id: int
    created_by: Optional[UserResponse] = None

    # Validator review
    validator_reviewed_by_id: Optional[int] = None
    validator_reviewed_by: Optional[UserResponse] = None
    validator_reviewed_at: Optional[datetime] = None
    validator_comment: Optional[str] = None

    # Owner review (required if owner != requestor)
    owner_approval_required: bool = False
    owner_reviewed_by_id: Optional[int] = None
    owner_reviewed_by: Optional[UserResponse] = None
    owner_reviewed_at: Optional[datetime] = None
    owner_comment: Optional[str] = None

    # Final status
    final_reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Related data
    status_history: List[DecommissioningStatusHistoryResponse] = []
    approvals: List[DecommissioningApprovalResponse] = []

    class Config:
        from_attributes = True


class DecommissioningRequestListItem(BaseModel):
    """Simplified response for list views."""
    request_id: int
    model_id: int
    model_name: str
    status: str
    reason: Optional[str] = None
    replacement_model_id: Optional[int] = None
    replacement_model_name: Optional[str] = None
    last_production_date: date
    created_at: datetime
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class ModelImplementationDateResponse(BaseModel):
    """Response for checking a model's implementation date."""
    model_id: int
    model_name: str
    has_implementation_date: bool
    implementation_date: Optional[date] = None
    latest_version_id: Optional[int] = None
    latest_version_status: Optional[str] = None

    class Config:
        from_attributes = True


# --- Constants for reason codes that require replacement ---

REASONS_REQUIRING_REPLACEMENT = ['REPLACEMENT', 'CONSOLIDATION']
