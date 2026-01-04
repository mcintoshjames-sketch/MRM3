"""Pydantic schemas for Model Exceptions API."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums / Choices
# =============================================================================

EXCEPTION_TYPES = [
    "UNMITIGATED_PERFORMANCE",
    "OUTSIDE_INTENDED_PURPOSE",
    "USE_PRIOR_TO_VALIDATION",
]

EXCEPTION_STATUSES = [
    "OPEN",
    "ACKNOWLEDGED",
    "CLOSED",
]


# =============================================================================
# Nested Response Schemas (for related entities)
# =============================================================================

class UserBrief(BaseModel):
    """Brief user info for embedding in exception responses."""
    user_id: int
    email: str
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelBrief(BaseModel):
    """Brief model info for embedding in exception responses."""
    model_id: int
    model_name: str
    model_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TaxonomyValueBrief(BaseModel):
    """Brief taxonomy value info."""
    value_id: int
    code: str
    label: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# =============================================================================
# Status History
# =============================================================================

class ModelExceptionStatusHistoryResponse(BaseModel):
    """Response schema for exception status history."""
    history_id: int
    exception_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by_id: Optional[int] = None
    changed_by: Optional[UserBrief] = None
    changed_at: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# =============================================================================
# Exception Response Schemas
# =============================================================================

class ModelExceptionListResponse(BaseModel):
    """Response schema for exception list view (minimal details)."""
    exception_id: int
    exception_code: str
    model_id: int
    model: ModelBrief
    exception_type: str
    status: str
    description: str
    detected_at: datetime
    auto_closed: bool
    acknowledged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelExceptionDetailResponse(BaseModel):
    """Response schema for exception detail view (full details)."""
    exception_id: int
    exception_code: str
    model_id: int
    model: ModelBrief
    exception_type: str
    status: str
    description: str
    detected_at: datetime
    auto_closed: bool

    # Source entity IDs (only one will be populated)
    monitoring_result_id: Optional[int] = None
    attestation_response_id: Optional[int] = None
    deployment_task_id: Optional[int] = None

    # Acknowledgment
    acknowledged_by_id: Optional[int] = None
    acknowledged_by: Optional[UserBrief] = None
    acknowledged_at: Optional[datetime] = None
    acknowledgment_notes: Optional[str] = None

    # Closure
    closed_at: Optional[datetime] = None
    closed_by_id: Optional[int] = None
    closed_by: Optional[UserBrief] = None
    closure_narrative: Optional[str] = None
    closure_reason_id: Optional[int] = None
    closure_reason: Optional[TaxonomyValueBrief] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Status history
    status_history: List[ModelExceptionStatusHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# =============================================================================
# Request Schemas
# =============================================================================

class AcknowledgeExceptionRequest(BaseModel):
    """Request schema for acknowledging an exception."""
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional acknowledgment notes"
    )


class CloseExceptionRequest(BaseModel):
    """Request schema for manually closing an exception."""
    closure_narrative: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Required narrative explaining closure (min 10 chars)"
    )
    closure_reason_id: int = Field(
        ...,
        description="FK to taxonomy_values for closure reason"
    )


class CreateExceptionRequest(BaseModel):
    """Request schema for manually creating an exception (Admin only)."""
    model_id: int = Field(
        ...,
        description="Model ID to create exception for"
    )
    exception_type: str = Field(
        ...,
        description="Type: UNMITIGATED_PERFORMANCE, OUTSIDE_INTENDED_PURPOSE, or USE_PRIOR_TO_VALIDATION"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Description of the exception (min 10 chars)"
    )
    acknowledgment_notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional notes (if creating in ACKNOWLEDGED status)"
    )
    initial_status: str = Field(
        default="OPEN",
        description="Initial status: OPEN or ACKNOWLEDGED"
    )


    model_config = ConfigDict(protected_namespaces=())
# =============================================================================
# Detection Request/Response Schemas
# =============================================================================

class DetectionResponse(BaseModel):
    """Response schema for exception detection endpoints."""
    type1_count: int = Field(..., description="Number of Type 1 (Unmitigated Performance) exceptions created")
    type2_count: int = Field(..., description="Number of Type 2 (Outside Intended Purpose) exceptions created")
    type3_count: int = Field(..., description="Number of Type 3 (Use Prior to Validation) exceptions created")
    total_created: int = Field(..., description="Total number of new exceptions created")
    exceptions: List[ModelExceptionListResponse] = Field(
        default_factory=list,
        description="List of newly created exceptions"
    )


# =============================================================================
# Paginated List Response
# =============================================================================

class PaginatedExceptionResponse(BaseModel):
    """Paginated response for exception list."""
    items: List[ModelExceptionListResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Summary / Stats Schemas
# =============================================================================

class ExceptionSummary(BaseModel):
    """Summary statistics for exceptions."""
    total_open: int
    total_acknowledged: int
    total_closed: int
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count by exception type"
    )
