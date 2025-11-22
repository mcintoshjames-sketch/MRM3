"""Models package."""
from app.models.user import User, UserRole, user_regions
from app.models.model import Model, ModelStatus, DevelopmentType, model_users, model_regulatory_categories
from app.models.vendor import Vendor
from app.models.entra_user import EntraUser
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.audit_log import AuditLog
from app.models.region import Region
from app.models.model_region import ModelRegion
from app.models.model_version import ModelVersion
from app.models.model_version_region import ModelVersionRegion
from app.models.model_delegate import ModelDelegate
from app.models.model_submission_comment import ModelSubmissionComment
from app.models.model_change_taxonomy import ModelChangeCategory, ModelChangeType
from app.models.validation import (
    Validation,
    ValidationPolicy,
    ValidationWorkflowSLA,
    ValidationRequest,
    ValidationRequestModelVersion,
    validation_request_models,
    ValidationStatusHistory,
    ValidationAssignment,
    ValidationWorkComponent,
    ValidationOutcome,
    ValidationReviewOutcome,
    ValidationApproval
)
from app.models.validation_grouping import ValidationGroupingMemory
from app.models.export_view import ExportView

__all__ = [
    "User", "UserRole", "user_regions",
    "Model", "ModelStatus", "DevelopmentType", "model_users", "model_regulatory_categories",
    "Vendor",
    "EntraUser",
    "Taxonomy", "TaxonomyValue",
    "AuditLog",
    "Region",
    "ModelRegion",
    "ModelVersion",
    "ModelVersionRegion",
    "ModelDelegate",
    "ModelSubmissionComment",
    "ModelChangeCategory",
    "ModelChangeType",
    # Legacy validation
    "Validation",
    # Validation policy
    "ValidationPolicy",
    "ValidationWorkflowSLA",
    # New workflow-based validation models
    "ValidationRequest",
    "ValidationRequestModelVersion",
    "validation_request_models",
    "ValidationStatusHistory",
    "ValidationAssignment",
    "ValidationWorkComponent",
    "ValidationOutcome",
    "ValidationReviewOutcome",
    "ValidationApproval",
    "ValidationGroupingMemory",
    "ExportView"
]
