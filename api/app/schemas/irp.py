"""IRP (Independent Review Process) schemas."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional, List
from app.schemas.user import UserResponse
from app.schemas.taxonomy import TaxonomyValueResponse


# ============================================================================
# MRSA Summary (lightweight model info for IRP views)
# ============================================================================

class MRSASummary(BaseModel):
    """Lightweight MRSA summary for IRP views."""
    model_id: int
    model_name: str
    description: Optional[str] = None
    mrsa_risk_level_id: Optional[int] = None
    mrsa_risk_level_label: Optional[str] = None
    mrsa_risk_rationale: Optional[str] = None
    is_mrsa: bool = True
    owner_id: int
    owner_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# IRP Review Schemas
# ============================================================================

class IRPReviewCreate(BaseModel):
    """Schema for creating an IRP review."""
    review_date: date
    outcome_id: int
    notes: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None  # Defaults to IRP contact if not provided


class IRPReviewResponse(BaseModel):
    """Response schema for IRP review."""
    review_id: int
    irp_id: int
    review_date: date
    outcome_id: int
    outcome: Optional[TaxonomyValueResponse] = None
    notes: Optional[str] = None
    reviewed_by_user_id: int
    reviewed_by: Optional[UserResponse] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# IRP Certification Schemas
# ============================================================================

class IRPCertificationCreate(BaseModel):
    """Schema for creating an IRP certification."""
    certification_date: date
    certified_by_email: str
    conclusion_summary: str


class IRPCertificationResponse(BaseModel):
    """Response schema for IRP certification."""
    certification_id: int
    irp_id: int
    certification_date: date
    certified_by_user_id: int
    certified_by_user: Optional[UserResponse] = None
    certified_by_email: str
    conclusion_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# IRP Schemas
# ============================================================================

class IRPBase(BaseModel):
    """Base schema for IRP."""
    process_name: str
    description: Optional[str] = None
    is_active: bool = True


class IRPCreate(IRPBase):
    """Schema for creating an IRP."""
    contact_user_id: int
    mrsa_ids: Optional[List[int]] = None  # MRSAs to cover


class IRPUpdate(BaseModel):
    """Schema for updating an IRP."""
    process_name: Optional[str] = None
    description: Optional[str] = None
    contact_user_id: Optional[int] = None
    is_active: Optional[bool] = None
    mrsa_ids: Optional[List[int]] = None  # Update covered MRSAs


class IRPResponse(IRPBase):
    """Response schema for IRP (list view)."""
    irp_id: int
    contact_user_id: int
    contact_user: Optional[UserResponse] = None
    created_at: datetime
    updated_at: datetime
    covered_mrsa_count: int = 0
    latest_review_date: Optional[date] = None
    latest_review_outcome: Optional[str] = None
    latest_certification_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class IRPDetailResponse(IRPBase):
    """Detailed response schema for IRP (detail view)."""
    irp_id: int
    contact_user_id: int
    contact_user: Optional[UserResponse] = None
    created_at: datetime
    updated_at: datetime

    # Covered MRSAs
    covered_mrsas: List[MRSASummary] = []
    covered_mrsa_count: int = 0

    # Review history
    reviews: List[IRPReviewResponse] = []
    latest_review: Optional[IRPReviewResponse] = None

    # Certification history
    certifications: List[IRPCertificationResponse] = []
    latest_certification: Optional[IRPCertificationResponse] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# IRP Coverage Check Response
# ============================================================================

class IRPCoverageStatus(BaseModel):
    """Response schema for checking if an MRSA has required IRP coverage."""
    model_id: int
    model_name: str
    is_mrsa: bool
    mrsa_risk_level_id: Optional[int] = None
    mrsa_risk_level_label: Optional[str] = None
    requires_irp: bool = False
    has_irp_coverage: bool = False
    is_compliant: bool = True  # True if doesn't require IRP or has coverage
    irp_ids: List[int] = []
    irp_names: List[str] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
