"""Rule evaluation logic for conditional model use approvals.

This module contains the core business logic for:
1. Evaluating which conditional approval rules apply to a validation request
2. Determining which approver roles are required
3. Generating English-language explanations of why approvals are required
"""
from typing import List, Dict, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.models import (
    ValidationRequest, Model, ConditionalApprovalRule, ApproverRole,
    RuleRequiredApprover, TaxonomyValue, Region, ModelRegion, ValidationApproval
)


def get_required_approver_roles(
    db: Session,
    validation_request: ValidationRequest,
    model: Model
) -> Dict:
    """
    Evaluate conditional approval rules and determine which approver roles are required.

    Business Logic:
    - Fetches all active ConditionalApprovalRules
    - For each rule, checks if model/validation attributes satisfy ALL non-empty dimensions
    - Within each dimension, OR logic applies (any value matches)
    - Empty/null dimension = no constraint (matches ANY)
    - Deduplicates approver roles from all matching rules
    - Checks existing approvals (non-voided) for each required role

    Args:
        db: Database session
        validation_request: The validation request being evaluated
        model: The model being validated

    Returns:
        Dict with:
            - required_roles: List of {role_id, role_name, description, approval_status, approval_id}
            - rules_applied: List of {rule_id, rule_name, explanation}
            - explanation_summary: Overall English explanation
    """
    # Fetch all active rules
    active_rules = db.query(ConditionalApprovalRule).filter(
        ConditionalApprovalRule.is_active == True
    ).all()

    if not active_rules:
        return {
            "required_roles": [],
            "rules_applied": [],
            "explanation_summary": "No conditional approval rules are configured or active."
        }

    # Get model's deployed region IDs
    deployed_region_ids = [mr.region_id for mr in model.model_regions] if model.model_regions else []

    # Evaluate each rule
    matching_rules = []
    required_role_ids = set()

    for rule in active_rules:
        if _rule_matches(rule, validation_request, model, deployed_region_ids):
            matching_rules.append(rule)
            # Collect all approver roles required by this rule
            for assoc in rule.required_approvers:
                required_role_ids.add(assoc.approver_role_id)

    if not required_role_ids:
        return {
            "required_roles": [],
            "rules_applied": [],
            "explanation_summary": "No conditional approval rules apply to this validation request."
        }

    # Fetch approver role details and check for existing approvals
    required_roles = []
    for role_id in required_role_ids:
        approver_role = db.query(ApproverRole).filter(ApproverRole.role_id == role_id).first()
        if not approver_role or not approver_role.is_active:
            continue  # Skip inactive roles

        # Check if approval already exists for this role (and not voided)
        existing_approval = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation_request.request_id,
            ValidationApproval.approver_role_id == role_id,
            ValidationApproval.voided_at.is_(None)  # Not voided
        ).first()

        approval_status = None
        approval_id = None
        if existing_approval:
            approval_status = existing_approval.approval_status
            approval_id = existing_approval.approval_id

        required_roles.append({
            "role_id": approver_role.role_id,
            "role_name": approver_role.role_name,
            "description": approver_role.description,
            "approval_status": approval_status,
            "approval_id": approval_id
        })

    # Generate explanations
    rules_applied = []
    for rule in matching_rules:
        explanation = _generate_rule_explanation(db, rule, validation_request, model, deployed_region_ids)
        rules_applied.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "explanation": explanation
        })

    # Generate overall summary
    role_names = [r["role_name"] for r in required_roles]
    if len(role_names) == 1:
        summary = f"Conditional approval required from: {role_names[0]}"
    elif len(role_names) == 2:
        summary = f"Conditional approvals required from: {role_names[0]} and {role_names[1]}"
    else:
        summary = f"Conditional approvals required from: {', '.join(role_names[:-1])}, and {role_names[-1]}"

    return {
        "required_roles": required_roles,
        "rules_applied": rules_applied,
        "explanation_summary": summary
    }


def _rule_matches(
    rule: ConditionalApprovalRule,
    validation_request: ValidationRequest,
    model: Model,
    deployed_region_ids: List[int]
) -> bool:
    """
    Check if a rule's conditions match the validation/model attributes.

    Logic: ALL non-empty dimensions must match (AND across dimensions).
    Within each dimension, OR logic (any value satisfies).
    Empty dimension = no constraint.
    """
    # Check validation type
    validation_type_ids = rule.get_validation_type_ids()
    if validation_type_ids:  # Non-empty = constraint exists
        if validation_request.validation_type_id not in validation_type_ids:
            return False  # Validation type doesn't match

    # Check risk tier
    risk_tier_ids = rule.get_risk_tier_ids()
    if risk_tier_ids:
        if not model.risk_tier_id or model.risk_tier_id not in risk_tier_ids:
            return False  # Risk tier doesn't match

    # Check governance region (wholly_owned_region_id)
    governance_region_ids = rule.get_governance_region_ids()
    if governance_region_ids:
        if not model.wholly_owned_region_id or model.wholly_owned_region_id not in governance_region_ids:
            return False  # Governance region doesn't match

    # Check deployed regions (ANY overlap = match)
    deployed_region_rule_ids = rule.get_deployed_region_ids()
    if deployed_region_rule_ids:
        if not deployed_region_ids:
            return False  # No deployed regions, but rule requires them
        if not any(dep_id in deployed_region_rule_ids for dep_id in deployed_region_ids):
            return False  # No overlap between model's deployed regions and rule's regions

    # All dimensions matched (or were empty)
    return True


def _generate_rule_explanation(
    db: Session,
    rule: ConditionalApprovalRule,
    validation_request: ValidationRequest,
    model: Model,
    deployed_region_ids: List[int]
) -> str:
    """
    Generate English-language explanation of why a rule applies.

    Example output:
    "US Model Risk Management Committee approval required because:
    - Validation type is Initial Validation
    - Model inherent risk tier is High (Tier 1)
    - Model governance region is US wholly-owned"
    """
    # Get approver role names for this rule
    role_names = [assoc.approver_role.role_name for assoc in rule.required_approvers if assoc.approver_role.is_active]
    if not role_names:
        return f"Rule '{rule.rule_name}' applies (no active approver roles configured)"

    if len(role_names) == 1:
        header = f"{role_names[0]} approval required because:"
    else:
        header = f"Approvals from {', '.join(role_names[:-1])} and {role_names[-1]} required because:"

    reasons = []

    # Explain validation type match
    validation_type_ids = rule.get_validation_type_ids()
    if validation_type_ids:
        type_names = _get_taxonomy_names(db, validation_type_ids)
        if len(type_names) == 1:
            reasons.append(f"- Validation type is {type_names[0]}")
        else:
            reasons.append(f"- Validation type is one of: {', '.join(type_names)}")

    # Explain risk tier match
    risk_tier_ids = rule.get_risk_tier_ids()
    if risk_tier_ids:
        tier_names = _get_taxonomy_names(db, risk_tier_ids)
        if len(tier_names) == 1:
            reasons.append(f"- Model inherent risk tier is {tier_names[0]}")
        else:
            reasons.append(f"- Model inherent risk tier is one of: {', '.join(tier_names)}")

    # Explain governance region match
    governance_region_ids = rule.get_governance_region_ids()
    if governance_region_ids:
        region_names = _get_region_names(db, governance_region_ids)
        if len(region_names) == 1:
            reasons.append(f"- Model governance region is {region_names[0]}")
        else:
            reasons.append(f"- Model governance region is one of: {', '.join(region_names)}")

    # Explain deployed regions match
    deployed_region_rule_ids = rule.get_deployed_region_ids()
    if deployed_region_rule_ids:
        region_names = _get_region_names(db, deployed_region_rule_ids)
        if len(region_names) == 1:
            reasons.append(f"- Model is deployed to {region_names[0]}")
        else:
            reasons.append(f"- Model is deployed to one or more of: {', '.join(region_names)}")

    if not reasons:
        reasons.append("- Rule has no specific conditions (applies to all validations)")

    return header + "\n" + "\n".join(reasons)


def _get_taxonomy_names(db: Session, value_ids: List[int]) -> List[str]:
    """Fetch taxonomy value labels by IDs."""
    values = db.query(TaxonomyValue).filter(TaxonomyValue.value_id.in_(value_ids)).all()
    return [v.label for v in values]


def _get_region_names(db: Session, region_ids: List[int]) -> List[str]:
    """Fetch region names by IDs."""
    regions = db.query(Region).filter(Region.region_id.in_(region_ids)).all()
    return [r.name for r in regions]


def generate_rule_translation_preview(
    db: Session,
    validation_type_ids: Optional[List[int]],
    risk_tier_ids: Optional[List[int]],
    governance_region_ids: Optional[List[int]],
    deployed_region_ids: Optional[List[int]],
    approver_role_ids: List[int]
) -> str:
    """
    Generate English translation preview for a rule being configured.

    Used by Admin UI to show what the rule means before saving.

    Args:
        db: Database session
        validation_type_ids: List of validation type IDs (or None/empty for ANY)
        risk_tier_ids: List of risk tier IDs (or None/empty for ANY)
        governance_region_ids: List of governance region IDs (or None/empty for ANY)
        deployed_region_ids: List of deployed region IDs (or None/empty for ANY)
        approver_role_ids: List of approver role IDs required by this rule

    Returns:
        English translation string with explicit AND/OR logic
    """
    # Get approver role names
    roles = db.query(ApproverRole).filter(ApproverRole.role_id.in_(approver_role_ids)).all()
    role_names = [r.role_name for r in roles]

    if not role_names:
        header = "This rule will require approval from (no roles selected)"
    elif len(role_names) == 1:
        header = f"This rule will require approval from: {role_names[0]}"
    else:
        header = f"This rule will require approvals from: {', '.join(role_names[:-1])} and {role_names[-1]}"

    conditions = []
    has_constraints = False

    # Validation type condition
    if validation_type_ids:
        has_constraints = True
        type_names = _get_taxonomy_names(db, validation_type_ids)
        if len(type_names) == 1:
            conditions.append(f"Validation type is {type_names[0]}")
        else:
            conditions.append(f"Validation type is {' OR '.join(type_names)} (any one matches)")
    else:
        conditions.append("Validation type: ANY (no constraint)")

    # Risk tier condition
    if risk_tier_ids:
        has_constraints = True
        tier_names = _get_taxonomy_names(db, risk_tier_ids)
        if len(tier_names) == 1:
            conditions.append(f"Model inherent risk tier is {tier_names[0]}")
        else:
            conditions.append(f"Model inherent risk tier is {' OR '.join(tier_names)} (any one matches)")
    else:
        conditions.append("Model inherent risk tier: ANY (no constraint)")

    # Governance region condition
    if governance_region_ids:
        has_constraints = True
        region_names = _get_region_names(db, governance_region_ids)
        if len(region_names) == 1:
            conditions.append(f"Model governance region is {region_names[0]}")
        else:
            conditions.append(f"Model governance region is {' OR '.join(region_names)} (any one matches)")
    else:
        conditions.append("Model governance region: ANY (no constraint)")

    # Deployed regions condition
    if deployed_region_ids:
        has_constraints = True
        region_names = _get_region_names(db, deployed_region_ids)
        if len(region_names) == 1:
            conditions.append(f"Model is deployed to {region_names[0]}")
        else:
            conditions.append(f"Model is deployed to ANY of: {', '.join(region_names)} (any overlap matches)")
    else:
        conditions.append("Model deployed regions: ANY (no constraint)")

    # Build explanation with explicit AND logic
    if not has_constraints:
        logic_explanation = "\n\nThis rule applies to ALL validation requests (no constraints specified)."
    else:
        logic_explanation = "\n\nThis rule applies when ALL of the following conditions are met (AND logic across dimensions):\n"
        logic_explanation += "\n  AND\n".join([f"  • {cond}" for cond in conditions])
        logic_explanation += "\n\nNote: Within each dimension, OR logic applies (any selected value satisfies that dimension)."

    return header + logic_explanation
