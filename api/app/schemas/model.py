"""Model schemas."""
from pydantic import BaseModel, field_validator, field_serializer
from datetime import datetime, date
from typing import Optional, List, Any, TYPE_CHECKING
from app.schemas.user import UserResponse
from app.schemas.vendor import VendorResponse
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.region import Region
from app.schemas.model_submission_comment import ModelSubmissionCommentResponse
from app.schemas.model_type_taxonomy import ModelTypeResponse
from app.schemas.methodology import MethodologyResponse

if TYPE_CHECKING:
    from app.schemas.irp import IRPResponse


class IRPContactUser(BaseModel):
    """Minimal user info for IRP contact user in model responses."""
    user_id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


class IRPSummary(BaseModel):
    """Lightweight IRP info for model responses (avoids circular import)."""
    irp_id: int
    process_name: str
    description: Optional[str] = None
    is_active: bool = True
    contact_user_id: int
    contact_user: Optional[IRPContactUser] = None

    class Config:
        from_attributes = True


class UserWithLOBRollup(BaseModel):
    """User info with LOB rolled up to LOB4 level for display."""
    user_id: int
    email: str
    full_name: str
    role: str
    lob_id: int
    lob_name: Optional[str] = None  # User's actual LOB name
    lob_rollup_name: Optional[str] = None  # LOB name rolled up to LOB4

    class Config:
        from_attributes = True


class ModelRolesWithLOB(BaseModel):
    """Response for model roles with LOB information rolled up to LOB4."""
    owner: UserWithLOBRollup
    shared_owner: Optional[UserWithLOBRollup] = None
    developer: Optional[UserWithLOBRollup] = None
    shared_developer: Optional[UserWithLOBRollup] = None
    monitoring_manager: Optional[UserWithLOBRollup] = None


class ModelBase(BaseModel):
    model_name: str
    description: Optional[str] = None
    development_type: str = "In-House"
    status: str = "In Development"


class ModelCreate(ModelBase):
    owner_id: int
    usage_frequency_id: int  # Required field
    developer_id: Optional[int] = None
    shared_owner_id: Optional[int] = None
    shared_developer_id: Optional[int] = None
    monitoring_manager_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    model_type_id: Optional[int] = None
    methodology_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    status_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    user_ids: Optional[List[int]] = None
    regulatory_category_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    initial_version_number: Optional[str] = None
    initial_implementation_date: Optional[date] = None
    is_model: bool = True  # True for models, False for non-models
    # MRSA (Model Risk-Sensitive Application) fields
    is_mrsa: bool = False  # True for MRSAs requiring IRP oversight
    mrsa_risk_level_id: Optional[int] = None  # MRSA Risk Level taxonomy value
    mrsa_risk_rationale: Optional[str] = None  # Narrative explaining risk classification
    irp_ids: Optional[List[int]] = None  # IRPs covering this MRSA
    # Auto-create validation request fields
    auto_create_validation: bool = False
    validation_request_type_id: Optional[int] = None
    validation_request_priority_id: Optional[int] = None
    validation_request_target_date: Optional[date] = None
    validation_request_trigger_reason: Optional[str] = None

    @field_validator('vendor_id')
    @classmethod
    def validate_vendor_required_for_third_party(cls, v, info):
        if info.data.get('development_type') == 'Third-Party' and v is None:
            raise ValueError('Vendor is required for third-party models')
        return v


class ModelUpdate(BaseModel):
    model_name: Optional[str] = None
    description: Optional[str] = None
    development_type: Optional[str] = None
    owner_id: Optional[int] = None
    developer_id: Optional[int] = None
    shared_owner_id: Optional[int] = None
    shared_developer_id: Optional[int] = None
    monitoring_manager_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    model_type_id: Optional[int] = None
    methodology_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    usage_frequency_id: Optional[int] = None
    status_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    status: Optional[str] = None  # Deprecated, use status_id
    user_ids: Optional[List[int]] = None
    regulatory_category_ids: Optional[List[int]] = None
    is_model: Optional[bool] = None  # True for models, False for non-models
    # MRSA (Model Risk-Sensitive Application) fields
    is_mrsa: Optional[bool] = None  # True for MRSAs requiring IRP oversight
    mrsa_risk_level_id: Optional[int] = None  # MRSA Risk Level taxonomy value
    mrsa_risk_rationale: Optional[str] = None  # Narrative explaining risk classification
    irp_ids: Optional[List[int]] = None  # IRPs covering this MRSA


class ModelResponse(ModelBase):
    model_id: int
    owner_id: int
    usage_frequency_id: int  # Required field
    developer_id: Optional[int] = None
    shared_owner_id: Optional[int] = None
    shared_developer_id: Optional[int] = None
    monitoring_manager_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    model_type_id: Optional[int] = None
    methodology_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    status_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_model: bool = True  # True for models, False for non-models
    is_aiml: Optional[bool] = None  # Computed from methodology category
    # MRSA (Model Risk-Sensitive Application) fields
    is_mrsa: bool = False  # True for MRSAs requiring IRP oversight
    mrsa_risk_level_id: Optional[int] = None
    mrsa_risk_rationale: Optional[str] = None
    # Row approval workflow fields
    row_approval_status: Optional[str] = None
    submitted_by_user_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    # Computed field: Owner's LOB rolled up to LOB4 level
    business_line_name: Optional[str] = None
    # Computed field: Production date of latest ACTIVE version
    model_last_updated: Optional[date] = None

    class Config:
        from_attributes = True


class ModelRegionListItem(BaseModel):
    """Simplified model-region info for list views."""
    region_id: int
    region_code: str
    region_name: str

    class Config:
        from_attributes = True


# Lightweight schemas for list view performance
class LOBListItem(BaseModel):
    """Minimal LOB info for list views."""
    lob_id: int
    name: str

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    """Minimal user info for list views."""
    user_id: int
    full_name: str
    email: str
    lob: Optional[LOBListItem] = None  # Nested for frontend compatibility

    class Config:
        from_attributes = True


class VendorListItem(BaseModel):
    """Minimal vendor info for list views."""
    vendor_id: int
    name: str

    class Config:
        from_attributes = True


class TaxonomyListItem(BaseModel):
    """Minimal taxonomy value for list views."""
    value_id: int
    label: str
    code: Optional[str] = None

    class Config:
        from_attributes = True


class MethodologyListItem(BaseModel):
    """Minimal methodology info for list views."""
    methodology_id: int
    name: str

    class Config:
        from_attributes = True


class ModelTypeListItem(BaseModel):
    """Minimal model type info for list views."""
    type_id: int
    name: str

    class Config:
        from_attributes = True


class IRPContactUserListItem(BaseModel):
    """Minimal user info for IRP contact in list views."""
    user_id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


class IRPListItem(BaseModel):
    """Minimal IRP info for model list views."""
    irp_id: int
    process_name: str
    description: Optional[str] = None
    is_active: bool = True
    contact_user_id: int
    contact_user: Optional[IRPContactUserListItem] = None

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """Lightweight model response for list views - optimized for performance."""
    model_id: int
    model_name: str
    description: Optional[str] = None
    development_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    is_model: bool = True
    is_aiml: Optional[bool] = None
    row_approval_status: Optional[str] = None
    business_line_name: Optional[str] = None
    model_last_updated: Optional[date] = None
    # MRSA fields
    is_mrsa: bool = False
    mrsa_risk_level_id: Optional[int] = None
    mrsa_risk_rationale: Optional[str] = None

    # IDs for filtering
    owner_id: int
    developer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    usage_frequency_id: Optional[int] = None

    # Lightweight nested objects (pre-computed)
    owner: Optional[UserListItem] = None
    developer: Optional[UserListItem] = None
    shared_owner: Optional[UserListItem] = None
    shared_developer: Optional[UserListItem] = None
    monitoring_manager: Optional[UserListItem] = None
    vendor: Optional[VendorListItem] = None
    risk_tier: Optional[TaxonomyListItem] = None
    methodology: Optional[MethodologyListItem] = None
    ownership_type: Optional[TaxonomyListItem] = None
    model_type: Optional[ModelTypeListItem] = None
    wholly_owned_region: Optional[ModelRegionListItem] = None
    mrsa_risk_level: Optional[TaxonomyListItem] = None  # MRSA risk level
    usage_frequency: Optional[TaxonomyListItem] = None

    # Collections (simplified)
    regions: List[ModelRegionListItem] = []
    users: List[UserListItem] = []
    regulatory_categories: List[TaxonomyListItem] = []
    irps: List[IRPListItem] = []  # IRPs covering this MRSA

    # Computed fields (optional, expensive)
    scorecard_outcome: Optional[str] = None
    residual_risk: Optional[str] = None
    approval_status: Optional[str] = None
    approval_status_label: Optional[str] = None

    # Computed revalidation fields (when include_computed_fields=True)
    validation_status: Optional[str] = None  # 'current', 'due_soon', 'overdue'
    next_validation_due_date: Optional[str] = None  # ISO date string
    days_until_validation_due: Optional[int] = None
    last_validation_date: Optional[str] = None  # ISO date string
    days_overdue: Optional[int] = None
    penalty_notches: Optional[int] = None
    adjusted_scorecard_outcome: Optional[str] = None

    class Config:
        from_attributes = True


class ModelDetailResponse(ModelResponse):
    """Model response with nested user and vendor details."""
    owner: UserResponse
    usage_frequency: TaxonomyValueResponse  # Required field
    developer: Optional[UserResponse] = None
    shared_owner: Optional[UserResponse] = None
    shared_developer: Optional[UserResponse] = None
    monitoring_manager: Optional[UserResponse] = None
    submitted_by_user: Optional[UserResponse] = None
    vendor: Optional[VendorResponse] = None
    risk_tier: Optional[TaxonomyValueResponse] = None
    validation_type: Optional[TaxonomyValueResponse] = None
    model_type: Optional[ModelTypeResponse] = None
    methodology: Optional[MethodologyResponse] = None
    ownership_type: Optional[TaxonomyValueResponse] = None
    status_value: Optional[TaxonomyValueResponse] = None
    wholly_owned_region: Optional[Region] = None
    users: List[UserResponse] = []
    regulatory_categories: List[TaxonomyValueResponse] = []
    regions: List[ModelRegionListItem] = []
    submission_comments: List[ModelSubmissionCommentResponse] = []
    # MRSA nested relationships
    mrsa_risk_level: Optional[TaxonomyValueResponse] = None  # MRSA risk classification
    irps: List[IRPSummary] = []  # IRPs covering this MRSA
    # Computed validation fields (populated from final_risk_ranking computation)
    scorecard_outcome: Optional[str] = None
    residual_risk: Optional[str] = None
    # Computed approval status fields (populated from model_approval_status computation)
    approval_status: Optional[str] = None  # NEVER_VALIDATED, APPROVED, INTERIM_APPROVED, VALIDATION_IN_PROGRESS, EXPIRED
    approval_status_label: Optional[str] = None  # Human-readable label
    # Computed exception count for UI badge
    open_exception_count: int = 0

    class Config:
        from_attributes = True


class ValidationGroupingSuggestion(BaseModel):
    """Suggested models based on previous validation groupings."""
    suggested_model_ids: List[int]
    suggested_models: List[ModelDetailResponse]
    last_validation_request_id: Optional[int] = None
    last_grouped_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelCreateWarning(BaseModel):
    """Warning message for model creation."""
    type: str
    message: str


class ModelCreateResponse(BaseModel):
    """Response for model creation with optional warnings."""
    model_id: int
    model_name: str
    description: Optional[str] = None
    development_type: str
    status: str
    owner_id: int
    usage_frequency_id: int  # Required field
    developer_id: Optional[int] = None
    shared_owner_id: Optional[int] = None
    shared_developer_id: Optional[int] = None
    monitoring_manager_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    model_type_id: Optional[int] = None
    methodology_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    status_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_model: bool = True  # True for models, False for non-models
    is_aiml: Optional[bool] = None  # Computed from methodology category
    # MRSA (Model Risk-Sensitive Application) fields
    is_mrsa: bool = False  # True for MRSAs requiring IRP oversight
    mrsa_risk_level_id: Optional[int] = None
    mrsa_risk_rationale: Optional[str] = None
    # Row approval workflow fields
    row_approval_status: Optional[str] = None
    submitted_by_user_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    # Computed field: Owner's LOB rolled up to LOB4 level
    business_line_name: Optional[str] = None
    # Relationships
    owner: UserResponse
    usage_frequency: TaxonomyValueResponse  # Required field
    developer: Optional[UserResponse] = None
    shared_owner: Optional[UserResponse] = None
    shared_developer: Optional[UserResponse] = None
    monitoring_manager: Optional[UserResponse] = None
    submitted_by_user: Optional[UserResponse] = None
    vendor: Optional[VendorResponse] = None
    risk_tier: Optional[TaxonomyValueResponse] = None
    validation_type: Optional[TaxonomyValueResponse] = None
    model_type: Optional[ModelTypeResponse] = None
    methodology: Optional[MethodologyResponse] = None
    ownership_type: Optional[TaxonomyValueResponse] = None
    status_value: Optional[TaxonomyValueResponse] = None
    wholly_owned_region: Optional[Region] = None
    mrsa_risk_level: Optional[TaxonomyValueResponse] = None  # MRSA risk classification
    users: List[UserResponse] = []
    regulatory_categories: List[TaxonomyValueResponse] = []
    regions: List[ModelRegionListItem] = []
    irps: List[IRPSummary] = []  # IRPs covering this MRSA
    warnings: Optional[List[ModelCreateWarning]] = None

    class Config:
        from_attributes = True


# Model Name History Schemas
class ModelNameHistoryItem(BaseModel):
    """Response schema for a single name change record."""
    history_id: int
    model_id: int
    old_name: str
    new_name: str
    changed_by_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    changed_at: datetime
    change_reason: Optional[str] = None

    class Config:
        from_attributes = True


class ModelNameHistoryResponse(BaseModel):
    """Response schema for name history of a model."""
    model_id: int
    current_name: str
    history: List[ModelNameHistoryItem]
    total_changes: int


class NameChangeStatistics(BaseModel):
    """Response schema for name change statistics."""
    total_models_with_changes: int
    models_changed_last_90_days: int
    models_changed_last_30_days: int
    total_name_changes: int
    recent_changes: List[ModelNameHistoryItem]


# Pending Edit Schemas for Model Edit Approval Workflow
class ModelPendingEditResponse(BaseModel):
    """Response schema for a pending model edit."""
    pending_edit_id: int
    model_id: int
    requested_by: UserResponse
    requested_at: datetime
    proposed_changes: dict
    original_values: dict
    status: str
    reviewed_by: Optional[UserResponse] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None

    class Config:
        from_attributes = True


class ModelPendingEditWithModel(ModelPendingEditResponse):
    """Pending edit with model details for admin dashboard."""
    model_name: str
    model_owner: UserResponse

    class Config:
        from_attributes = True


class PendingEditReviewRequest(BaseModel):
    """Request schema for reviewing (approving/rejecting) a pending edit."""
    comment: Optional[str] = None


class ModelUpdateWithPendingResponse(BaseModel):
    """Response when a non-admin edit is held for approval."""
    message: str
    pending_edit_id: int
    status: str
    proposed_changes: dict
    model_id: int


# Model Approval Status Schemas
class ModelApprovalStatusResponse(BaseModel):
    """Response schema for a model's current approval status."""
    model_id: int
    model_name: str
    is_model: bool = True

    # Current status
    approval_status: Optional[str] = None  # NULL for non-models
    approval_status_label: Optional[str] = None
    status_determined_at: datetime

    # Validation context
    latest_approved_validation_id: Optional[int] = None
    latest_approved_validation_date: Optional[datetime] = None
    latest_approved_validation_type: Optional[str] = None  # INITIAL, COMPREHENSIVE, INTERIM, etc.

    active_validation_id: Optional[int] = None
    active_validation_status: Optional[str] = None

    # Approval details
    all_approvals_complete: bool = True
    pending_approval_count: int = 0

    # Expiration context
    next_validation_due_date: Optional[date] = None
    days_until_due: Optional[int] = None  # Negative if overdue
    is_overdue: bool = False


class ModelApprovalStatusHistoryItem(BaseModel):
    """Response schema for a single approval status change record."""
    history_id: int
    old_status: Optional[str] = None
    old_status_label: Optional[str] = None
    new_status: str
    new_status_label: str
    changed_at: datetime
    trigger_type: str
    trigger_entity_type: Optional[str] = None
    trigger_entity_id: Optional[int] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ModelApprovalStatusHistoryResponse(BaseModel):
    """Response schema for approval status history of a model."""
    model_id: int
    model_name: str
    total_count: int
    history: List[ModelApprovalStatusHistoryItem]


class BulkApprovalStatusRequest(BaseModel):
    """Request schema for bulk approval status computation."""
    model_ids: List[int]


class BulkApprovalStatusItem(BaseModel):
    """Response schema for a single model in bulk approval status computation."""
    model_id: int
    model_name: Optional[str] = None
    approval_status: Optional[str] = None
    approval_status_label: Optional[str] = None
    is_overdue: bool = False
    next_validation_due: Optional[date] = None
    days_until_due: Optional[int] = None
    error: Optional[str] = None  # Set if model not found or error occurred


class BulkApprovalStatusResponse(BaseModel):
    """Response schema for bulk approval status computation."""
    total_requested: int
    total_found: int
    results: List[BulkApprovalStatusItem]
