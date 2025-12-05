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
    pass


class ModelBase(BaseModel):
    model_name: str
    description: Optional[str] = None
    development_type: str = "In-House"
    status: str = "In Development"


class ModelCreate(ModelBase):
    owner_id: int
    usage_frequency_id: int  # Required field
    developer_id: Optional[int] = None
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


class ModelResponse(ModelBase):
    model_id: int
    owner_id: int
    usage_frequency_id: int  # Required field
    developer_id: Optional[int] = None
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
    # Row approval workflow fields
    row_approval_status: Optional[str] = None
    submitted_by_user_id: Optional[int] = None
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelRegionListItem(BaseModel):
    """Simplified model-region info for list views."""
    region_id: int
    region_code: str
    region_name: str

    class Config:
        from_attributes = True


class ModelDetailResponse(ModelResponse):
    """Model response with nested user and vendor details."""
    owner: UserResponse
    usage_frequency: TaxonomyValueResponse  # Required field
    developer: Optional[UserResponse] = None
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
    # Row approval workflow fields
    row_approval_status: Optional[str] = None
    submitted_by_user_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    # Relationships
    owner: UserResponse
    usage_frequency: TaxonomyValueResponse  # Required field
    developer: Optional[UserResponse] = None
    submitted_by_user: Optional[UserResponse] = None
    vendor: Optional[VendorResponse] = None
    risk_tier: Optional[TaxonomyValueResponse] = None
    validation_type: Optional[TaxonomyValueResponse] = None
    model_type: Optional[ModelTypeResponse] = None
    methodology: Optional[MethodologyResponse] = None
    ownership_type: Optional[TaxonomyValueResponse] = None
    status_value: Optional[TaxonomyValueResponse] = None
    wholly_owned_region: Optional[Any] = None
    users: List[UserResponse] = []
    regulatory_categories: List[TaxonomyValueResponse] = []
    regions: List[ModelRegionListItem] = []
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
