"""API endpoints for conditional approval rules management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.core.rule_evaluation import generate_rule_translation_preview
from app.models import (
    User, ConditionalApprovalRule, ApproverRole, RuleRequiredApprover,
    TaxonomyValue, Region
)
from app.schemas.conditional_approval import (
    ConditionalApprovalRuleCreate,
    ConditionalApprovalRuleUpdate,
    ConditionalApprovalRuleResponse,
    ConditionalApprovalRuleListResponse,
    RuleTranslationPreviewRequest,
    RuleTranslationPreviewResponse,
    ApproverRoleResponse
)

router = APIRouter(prefix="/additional-approval-rules", tags=["Additional Approval Rules"])


def _build_rule_translation(db: Session, rule: ConditionalApprovalRule) -> str:
    """Generate English translation for a rule."""
    return generate_rule_translation_preview(
        db=db,
        validation_type_ids=rule.get_validation_type_ids() or None,
        risk_tier_ids=rule.get_risk_tier_ids() or None,
        governance_region_ids=rule.get_governance_region_ids() or None,
        deployed_region_ids=rule.get_deployed_region_ids() or None,
        approver_role_ids=[assoc.approver_role_id for assoc in rule.required_approvers]
    )


def _build_conditions_summary(db: Session, rule: ConditionalApprovalRule) -> str:
    """Build a concise conditions summary for list view."""
    parts = []

    validation_type_ids = rule.get_validation_type_ids()
    if validation_type_ids:
        type_names = [v.label for v in db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id.in_(validation_type_ids)
        ).all()]
        parts.append(f"Validation Type: {', '.join(type_names)}")

    risk_tier_ids = rule.get_risk_tier_ids()
    if risk_tier_ids:
        tier_names = [v.label for v in db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id.in_(risk_tier_ids)
        ).all()]
        parts.append(f"Risk Tier: {', '.join(tier_names)}")

    governance_region_ids = rule.get_governance_region_ids()
    if governance_region_ids:
        region_names = [r.name for r in db.query(Region).filter(
            Region.region_id.in_(governance_region_ids)
        ).all()]
        parts.append(f"Governance: {', '.join(region_names)}")

    deployed_region_ids = rule.get_deployed_region_ids()
    if deployed_region_ids:
        region_names = [r.name for r in db.query(Region).filter(
            Region.region_id.in_(deployed_region_ids)
        ).all()]
        parts.append(f"Deployed: {', '.join(region_names)}")

    if not parts:
        return "No specific conditions (applies to all validations)"

    return "; ".join(parts)


@router.get("/", response_model=List[ConditionalApprovalRuleListResponse])
def list_conditional_approval_rules(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all conditional approval rules.

    Query Parameters:
    - is_active: Filter by active status (optional)

    Returns list with conditions summary and required approver names.
    """
    query = db.query(ConditionalApprovalRule)

    if is_active is not None:
        query = query.filter(ConditionalApprovalRule.is_active == is_active)

    rules = query.order_by(ConditionalApprovalRule.rule_name).all()

    result = []
    for rule in rules:
        conditions_summary = _build_conditions_summary(db, rule)

        # Get required approver role names
        approver_names = [
            assoc.approver_role.role_name
            for assoc in rule.required_approvers
            if assoc.approver_role.is_active
        ]
        required_approver_names = ", ".join(approver_names) if approver_names else "None"

        result.append(ConditionalApprovalRuleListResponse(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            description=rule.description,
            is_active=rule.is_active,
            conditions_summary=conditions_summary,
            required_approver_names=required_approver_names,
            created_at=rule.created_at
        ))

    return result


@router.get("/{rule_id}", response_model=ConditionalApprovalRuleResponse)
def get_conditional_approval_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get conditional approval rule details by ID.

    Includes English-language translation of the rule.
    """
    rule = db.query(ConditionalApprovalRule).filter(
        ConditionalApprovalRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conditional approval rule with ID {rule_id} not found"
        )

    # Build response with translation
    required_approver_roles = [
        ApproverRoleResponse(
            role_id=assoc.approver_role.role_id,
            role_name=assoc.approver_role.role_name,
            description=assoc.approver_role.description,
            is_active=assoc.approver_role.is_active,
            created_at=assoc.approver_role.created_at,
            updated_at=assoc.approver_role.updated_at
        )
        for assoc in rule.required_approvers
    ]

    rule_translation = _build_rule_translation(db, rule)

    return ConditionalApprovalRuleResponse(
        rule_id=rule.rule_id,
        rule_name=rule.rule_name,
        description=rule.description,
        is_active=rule.is_active,
        validation_type_ids=rule.get_validation_type_ids(),
        risk_tier_ids=rule.get_risk_tier_ids(),
        governance_region_ids=rule.get_governance_region_ids(),
        deployed_region_ids=rule.get_deployed_region_ids(),
        required_approver_roles=required_approver_roles,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        rule_translation=rule_translation
    )


@router.post("/", response_model=ConditionalApprovalRuleResponse, status_code=status.HTTP_201_CREATED)
def create_conditional_approval_rule(
    rule_data: ConditionalApprovalRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new conditional approval rule (Admin only).

    Required fields:
    - rule_name: Name for the rule
    - required_approver_role_ids: At least one approver role

    Optional condition fields (empty = ANY):
    - validation_type_ids
    - risk_tier_ids
    - governance_region_ids
    - deployed_region_ids
    """
    # Check Admin permission
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can create conditional approval rules"
        )

    # Validate that approver roles exist and are active
    approver_roles = db.query(ApproverRole).filter(
        ApproverRole.role_id.in_(rule_data.required_approver_role_ids)
    ).all()

    if len(approver_roles) != len(rule_data.required_approver_role_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more approver role IDs not found"
        )

    inactive_roles = [r.role_name for r in approver_roles if not r.is_active]
    if inactive_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot use inactive approver roles: {', '.join(inactive_roles)}"
        )

    # Convert lists to comma-separated strings
    validation_type_ids_str = ",".join(map(str, rule_data.validation_type_ids)) if rule_data.validation_type_ids else None
    risk_tier_ids_str = ",".join(map(str, rule_data.risk_tier_ids)) if rule_data.risk_tier_ids else None
    governance_region_ids_str = ",".join(map(str, rule_data.governance_region_ids)) if rule_data.governance_region_ids else None
    deployed_region_ids_str = ",".join(map(str, rule_data.deployed_region_ids)) if rule_data.deployed_region_ids else None

    # Create new rule
    new_rule = ConditionalApprovalRule(
        rule_name=rule_data.rule_name,
        description=rule_data.description,
        is_active=rule_data.is_active,
        validation_type_ids=validation_type_ids_str,
        risk_tier_ids=risk_tier_ids_str,
        governance_region_ids=governance_region_ids_str,
        deployed_region_ids=deployed_region_ids_str
    )

    db.add(new_rule)
    db.flush()  # Get rule_id before adding associations

    # Create required approver associations
    for role_id in rule_data.required_approver_role_ids:
        assoc = RuleRequiredApprover(
            rule_id=new_rule.rule_id,
            approver_role_id=role_id
        )
        db.add(assoc)

    db.commit()
    db.refresh(new_rule)

    # Return rule details with translation
    return get_conditional_approval_rule(new_rule.rule_id, db, current_user)


@router.patch("/{rule_id}", response_model=ConditionalApprovalRuleResponse)
def update_conditional_approval_rule(
    rule_id: int,
    rule_data: ConditionalApprovalRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update conditional approval rule (Admin only).

    Allows updating:
    - rule_name
    - description
    - is_active
    - All condition fields
    - required_approver_role_ids (replaces existing associations)
    """
    # Check Admin permission
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can update conditional approval rules"
        )

    # Find rule
    rule = db.query(ConditionalApprovalRule).filter(
        ConditionalApprovalRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conditional approval rule with ID {rule_id} not found"
        )

    # Update fields
    if rule_data.rule_name is not None:
        rule.rule_name = rule_data.rule_name

    if rule_data.description is not None:
        rule.description = rule_data.description

    if rule_data.is_active is not None:
        rule.is_active = rule_data.is_active

    if rule_data.validation_type_ids is not None:
        rule.validation_type_ids = ",".join(map(str, rule_data.validation_type_ids)) if rule_data.validation_type_ids else None

    if rule_data.risk_tier_ids is not None:
        rule.risk_tier_ids = ",".join(map(str, rule_data.risk_tier_ids)) if rule_data.risk_tier_ids else None

    if rule_data.governance_region_ids is not None:
        rule.governance_region_ids = ",".join(map(str, rule_data.governance_region_ids)) if rule_data.governance_region_ids else None

    if rule_data.deployed_region_ids is not None:
        rule.deployed_region_ids = ",".join(map(str, rule_data.deployed_region_ids)) if rule_data.deployed_region_ids else None

    # Update required approver roles if provided
    if rule_data.required_approver_role_ids is not None:
        # Validate approver roles exist and are active
        approver_roles = db.query(ApproverRole).filter(
            ApproverRole.role_id.in_(rule_data.required_approver_role_ids)
        ).all()

        if len(approver_roles) != len(rule_data.required_approver_role_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more approver role IDs not found"
            )

        inactive_roles = [r.role_name for r in approver_roles if not r.is_active]
        if inactive_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot use inactive approver roles: {', '.join(inactive_roles)}"
            )

        # Delete existing associations
        db.query(RuleRequiredApprover).filter(
            RuleRequiredApprover.rule_id == rule_id
        ).delete()

        # Create new associations
        for role_id in rule_data.required_approver_role_ids:
            assoc = RuleRequiredApprover(
                rule_id=rule.rule_id,
                approver_role_id=role_id
            )
            db.add(assoc)

    db.commit()
    db.refresh(rule)

    # Return updated rule details with translation
    return get_conditional_approval_rule(rule.rule_id, db, current_user)


@router.delete("/{rule_id}", status_code=status.HTTP_200_OK)
def delete_conditional_approval_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete conditional approval rule by setting is_active=false (Admin only).

    This prevents the rule from being evaluated for new validations.
    """
    # Check Admin permission
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can delete conditional approval rules"
        )

    # Find rule
    rule = db.query(ConditionalApprovalRule).filter(
        ConditionalApprovalRule.rule_id == rule_id
    ).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conditional approval rule with ID {rule_id} not found"
        )

    # Soft delete (set is_active=false)
    rule.is_active = False
    db.commit()

    return {"message": f"Conditional approval rule '{rule.rule_name}' deactivated successfully"}


@router.post("/preview", response_model=RuleTranslationPreviewResponse)
def preview_rule_translation(
    preview_data: RuleTranslationPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Preview English translation of a rule being configured (Admin only).

    This endpoint is used by the Admin UI to show "what this rule means"
    before the user saves it.
    """
    # Check Admin permission
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can preview rule translations"
        )

    # Validate that approver roles exist
    if preview_data.required_approver_role_ids:
        approver_roles = db.query(ApproverRole).filter(
            ApproverRole.role_id.in_(preview_data.required_approver_role_ids)
        ).all()

        if len(approver_roles) != len(preview_data.required_approver_role_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more approver role IDs not found"
            )

    # Generate translation
    translation = generate_rule_translation_preview(
        db=db,
        validation_type_ids=preview_data.validation_type_ids,
        risk_tier_ids=preview_data.risk_tier_ids,
        governance_region_ids=preview_data.governance_region_ids,
        deployed_region_ids=preview_data.deployed_region_ids,
        approver_role_ids=preview_data.required_approver_role_ids
    )

    return RuleTranslationPreviewResponse(translation=translation)
