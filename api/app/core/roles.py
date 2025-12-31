"""Role normalization helpers and canonical mappings."""
from __future__ import annotations

import enum
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class RoleCode(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    VALIDATOR = "VALIDATOR"
    GLOBAL_APPROVER = "GLOBAL_APPROVER"
    REGIONAL_APPROVER = "REGIONAL_APPROVER"


ROLE_CODE_TO_DISPLAY: Dict[str, str] = {
    RoleCode.ADMIN.value: "Admin",
    RoleCode.USER.value: "User",
    RoleCode.VALIDATOR.value: "Validator",
    RoleCode.GLOBAL_APPROVER.value: "Global Approver",
    RoleCode.REGIONAL_APPROVER.value: "Regional Approver"
}

ROLE_DISPLAY_TO_CODE: Dict[str, str] = {
    "admin": RoleCode.ADMIN.value,
    "administrator": RoleCode.ADMIN.value,
    "user": RoleCode.USER.value,
    "validator": RoleCode.VALIDATOR.value,
    "global approver": RoleCode.GLOBAL_APPROVER.value,
    "global_approver": RoleCode.GLOBAL_APPROVER.value,
    "regional approver": RoleCode.REGIONAL_APPROVER.value,
    "regional_approver": RoleCode.REGIONAL_APPROVER.value
}


def normalize_role_code(value: str | None) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    upper = normalized.upper().replace(" ", "_")
    if upper in RoleCode.__members__:
        return RoleCode[upper].value
    return ROLE_DISPLAY_TO_CODE.get(normalized.strip().lower())


def resolve_role_code(role_code: str | None, role_display: str | None) -> Optional[str]:
    resolved = normalize_role_code(role_code)
    if resolved:
        return resolved
    return normalize_role_code(role_display)


def get_role_display(role_code: str | None, fallback: str | None = None) -> Optional[str]:
    if not role_code:
        return fallback
    return ROLE_CODE_TO_DISPLAY.get(role_code, fallback)


def get_user_role_code(user: "User") -> Optional[str]:
    if user.role_ref:
        return user.role_ref.code
    return None


def is_admin(user: "User") -> bool:
    return get_user_role_code(user) == RoleCode.ADMIN.value


def is_validator(user: "User") -> bool:
    return get_user_role_code(user) == RoleCode.VALIDATOR.value


def is_global_approver(user: "User") -> bool:
    return get_user_role_code(user) == RoleCode.GLOBAL_APPROVER.value


def is_regional_approver(user: "User") -> bool:
    return get_user_role_code(user) == RoleCode.REGIONAL_APPROVER.value


def is_approver(user: "User") -> bool:
    return get_user_role_code(user) in {
        RoleCode.GLOBAL_APPROVER.value,
        RoleCode.REGIONAL_APPROVER.value
    }


def is_privileged(user: "User") -> bool:
    return get_user_role_code(user) in {
        RoleCode.ADMIN.value,
        RoleCode.VALIDATOR.value,
        RoleCode.GLOBAL_APPROVER.value,
        RoleCode.REGIONAL_APPROVER.value
    }


def build_capabilities(role_code: str | None) -> dict:
    is_admin = role_code == RoleCode.ADMIN.value
    is_validator = role_code == RoleCode.VALIDATOR.value
    is_global_approver = role_code == RoleCode.GLOBAL_APPROVER.value
    is_regional_approver = role_code == RoleCode.REGIONAL_APPROVER.value
    is_approver = is_global_approver or is_regional_approver
    is_admin_or_validator = is_admin or is_validator

    return {
        "is_admin": is_admin,
        "is_validator": is_validator,
        "is_global_approver": is_global_approver,
        "is_regional_approver": is_regional_approver,
        "can_manage_users": is_admin,
        "can_manage_taxonomy": is_admin_or_validator,
        "can_manage_regions": is_admin,
        "can_view_admin_dashboard": is_admin,
        "can_view_validator_dashboard": is_validator,
        "can_view_approver_dashboard": is_admin or is_approver,
        "can_proxy_approve": is_admin,
        "can_void_approvals": is_admin,
        "can_view_audit_logs": is_admin_or_validator,
        "can_view_validation_alerts": is_admin,
        "can_manage_workflow_config": is_admin,
        "can_manage_delegates": is_admin,
        "can_manage_validation_policies": is_admin,
        "can_manage_mrsa_review_policies": is_admin,
        "can_manage_approver_roles": is_admin,
        "can_manage_conditional_approvals": is_admin,
        "can_manage_monitoring_plans": is_admin,
        "can_edit_monitoring_plan": is_admin,
        "can_manage_attestations": is_admin,
        "can_manage_irps": is_admin,
        "can_manage_models": is_admin,
        "can_manage_model_relationships": is_admin,
        "can_manage_lob": is_admin,
        "can_manage_validations": is_admin_or_validator,
        "can_manage_recommendations": is_admin_or_validator,
        "can_manage_decommissioning": is_admin_or_validator,
        "can_approve_model": is_admin
    }
