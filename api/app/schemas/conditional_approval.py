"""Pydantic schemas for conditional model use approvals."""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ApproverRole schemas
class ApproverRoleBase(BaseModel):
    role_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: bool = True


class ApproverRoleCreate(ApproverRoleBase):
    pass


class ApproverRoleUpdate(BaseModel):
    role_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ApproverRoleResponse(ApproverRoleBase):
    role_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApproverRoleListResponse(BaseModel):
    role_id: int
    role_name: str
    description: Optional[str]
    is_active: bool
    rules_count: int = 0  # Number of rules using this role

    class Config:
        from_attributes = True


# ConditionalApprovalRule schemas
class ConditionalApprovalRuleBase(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: bool = True
    validation_type_ids: Optional[List[int]] = Field(default=None, description="Empty/null = ANY")
    risk_tier_ids: Optional[List[int]] = Field(default=None, description="Empty/null = ANY")
    governance_region_ids: Optional[List[int]] = Field(default=None, description="Empty/null = ANY")
    deployed_region_ids: Optional[List[int]] = Field(default=None, description="Empty/null = ANY")
    required_approver_role_ids: List[int] = Field(..., min_items=1)


class ConditionalApprovalRuleCreate(ConditionalApprovalRuleBase):
    pass


class ConditionalApprovalRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    validation_type_ids: Optional[List[int]] = None
    risk_tier_ids: Optional[List[int]] = None
    governance_region_ids: Optional[List[int]] = None
    deployed_region_ids: Optional[List[int]] = None
    required_approver_role_ids: Optional[List[int]] = Field(None, min_items=1)


class ConditionalApprovalRuleResponse(BaseModel):
    rule_id: int
    rule_name: str
    description: Optional[str]
    is_active: bool
    validation_type_ids: List[int]
    risk_tier_ids: List[int]
    governance_region_ids: List[int]
    deployed_region_ids: List[int]
    required_approver_roles: List[ApproverRoleResponse]
    created_at: datetime
    updated_at: datetime
    # English translation of the rule
    rule_translation: str

    class Config:
        from_attributes = True


class ConditionalApprovalRuleListResponse(BaseModel):
    rule_id: int
    rule_name: str
    description: Optional[str]
    is_active: bool
    conditions_summary: str  # e.g., "Validation Type: Initial; Risk Tier: High; Governance: US"
    required_approver_names: str  # Comma-separated role names
    created_at: datetime

    class Config:
        from_attributes = True


# Rule translation preview
class RuleTranslationPreviewRequest(BaseModel):
    validation_type_ids: Optional[List[int]] = None
    risk_tier_ids: Optional[List[int]] = None
    governance_region_ids: Optional[List[int]] = None
    deployed_region_ids: Optional[List[int]] = None
    required_approver_role_ids: List[int] = Field(..., min_items=1)


class RuleTranslationPreviewResponse(BaseModel):
    translation: str


# Conditional approval evaluation result
class RequiredApproverRole(BaseModel):
    role_id: int
    role_name: str
    description: Optional[str]
    approval_status: Optional[str] = Field(None, description="Pending, Approved, Rejected, or None if not yet created")
    approval_id: Optional[int] = None


class AppliedRuleInfo(BaseModel):
    rule_id: int
    rule_name: str
    explanation: str


class ConditionalApprovalsEvaluationResponse(BaseModel):
    required_roles: List[RequiredApproverRole]
    rules_applied: List[AppliedRuleInfo]
    explanation_summary: str


# Submit conditional approval
class SubmitConditionalApprovalRequest(BaseModel):
    approver_role_id: int
    approval_status: str = Field(..., pattern="^(Approved|Rejected)$")
    approval_evidence: str = Field(..., min_length=1, description="Description of approval evidence (meeting minutes, email, etc.)")
    comments: Optional[str] = None


class SubmitConditionalApprovalResponse(BaseModel):
    approval_id: int
    message: str


# Void approval requirement
class VoidApprovalRequirementRequest(BaseModel):
    void_reason: str = Field(..., min_length=1)


class VoidApprovalRequirementResponse(BaseModel):
    approval_id: int
    message: str
