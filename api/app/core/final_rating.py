"""
Final Model Risk Ranking computation module.

Computes the final risk ranking by:
1. Getting the model's most recent validation scorecard outcome
2. Applying past-due downgrade notches based on model's overdue status
3. Using adjusted scorecard + inherent risk tier in the Residual Risk Map
"""

from datetime import date
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.taxonomy import Taxonomy, TaxonomyValue


# Scorecard outcomes ordered from best (0) to worst (5)
SCORECARD_ORDER = ["Green", "Green-", "Yellow+", "Yellow", "Yellow-", "Red"]

# Mapping from risk tier taxonomy labels to residual risk map keys
RISK_TIER_MAPPING = {
    "High Inherent Risk": "High",
    "Medium Inherent Risk": "Medium",
    "Low Inherent Risk": "Low",
    "Very Low Inherent Risk": "Very Low",
    # Also support direct labels
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
    "Very Low": "Very Low",
    # Support Tier labels
    "Tier 1 (High Risk)": "High",
    "Tier 2 (Medium Risk)": "Medium",
    "Tier 3 (Low Risk)": "Low",
    "Tier 4 (Very Low Risk)": "Very Low",
}


def downgrade_scorecard(original_outcome: str, notches: int) -> str:
    """
    Downgrade a scorecard outcome by N notches, capped at Red.

    Args:
        original_outcome: Original scorecard outcome (e.g., "Green", "Yellow+")
        notches: Number of notches to downgrade (0 = no change)

    Returns:
        Adjusted scorecard outcome, capped at "Red"
    """
    if notches <= 0:
        return original_outcome

    try:
        current_position = SCORECARD_ORDER.index(original_outcome)
    except ValueError:
        # Unknown outcome, return as-is
        return original_outcome

    new_position = min(current_position + notches, len(SCORECARD_ORDER) - 1)
    return SCORECARD_ORDER[new_position]


def get_past_due_level_with_notches(
    db: Session,
    days_overdue: int
) -> Optional[Dict[str, Any]]:
    """
    Get the Past Due Level bucket info including downgrade_notches.

    Args:
        db: Database session
        days_overdue: Number of days the model is overdue (negative = not overdue)

    Returns:
        Dictionary with bucket details including downgrade_notches,
        or None if no matching bucket found.
    """
    # Find the "Past Due Level" taxonomy
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Past Due Level",
        Taxonomy.taxonomy_type == "bucket"
    ).first()

    if not taxonomy:
        return None

    # Get all bucket values ordered by sort_order
    values = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.is_active == True
    ).order_by(TaxonomyValue.sort_order).all()

    # Find the matching bucket
    for value in values:
        min_days = value.min_days
        max_days = value.max_days

        # Check if days_overdue falls within this bucket
        if min_days is None and max_days is None:
            # Single unbounded bucket - matches everything
            return {
                "value_id": value.value_id,
                "code": value.code,
                "label": value.label,
                "description": value.description,
                "downgrade_notches": value.downgrade_notches or 0,
            }
        elif min_days is None:
            # Lower unbounded: matches if days_overdue <= max_days
            if days_overdue <= max_days:
                return {
                    "value_id": value.value_id,
                    "code": value.code,
                    "label": value.label,
                    "description": value.description,
                    "downgrade_notches": value.downgrade_notches or 0,
                }
        elif max_days is None:
            # Upper unbounded: matches if days_overdue >= min_days
            if days_overdue >= min_days:
                return {
                    "value_id": value.value_id,
                    "code": value.code,
                    "label": value.label,
                    "description": value.description,
                    "downgrade_notches": value.downgrade_notches or 0,
                }
        else:
            # Bounded: matches if min_days <= days_overdue <= max_days
            if min_days <= days_overdue <= max_days:
                return {
                    "value_id": value.value_id,
                    "code": value.code,
                    "label": value.label,
                    "description": value.description,
                    "downgrade_notches": value.downgrade_notches or 0,
                }

    return None


def lookup_residual_risk(
    db: Session,
    inherent_risk_tier: str,
    scorecard_outcome: str
) -> Optional[str]:
    """
    Look up residual risk from the active configuration matrix.

    Args:
        db: Database session
        inherent_risk_tier: Normalized tier (e.g., "High", "Medium", "Low")
        scorecard_outcome: Scorecard rating (e.g., "Green", "Yellow", "Red")

    Returns:
        Residual risk rating ("High", "Medium", "Low") or None if not found
    """
    from app.models.residual_risk_map import ResidualRiskMapConfig

    config = db.query(ResidualRiskMapConfig).filter(
        ResidualRiskMapConfig.is_active == True
    ).first()

    if not config or not config.matrix_config:
        return None

    matrix = config.matrix_config.get("matrix", {})

    # Look up: matrix[risk_tier][scorecard_outcome]
    tier_row = matrix.get(inherent_risk_tier)
    if not tier_row:
        return None

    return tier_row.get(scorecard_outcome)


def calculate_model_days_overdue(db: Session, model_id: int) -> int:
    """
    Calculate how many days overdue a model is for validation.

    Uses the model's current validation status to determine days overdue.
    Considers the most recent validation request's completion date and
    the validation policy frequency.

    Returns:
        Days overdue (positive), 0 if due today, negative if not yet due.
        Returns 0 if unable to determine (e.g., no prior validation).
    """
    from app.models import Model
    from app.models.validation import ValidationRequest, ValidationPolicy, ValidationRequestModelVersion

    today = date.today()

    # Get the model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return 0

    # Find the most recent APPROVED validation for this model
    # that has a completion_date (the date when validation was finished)
    # ValidationRequest uses a many-to-many relationship with models via validation_request_models
    latest_approved = db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id,
        ValidationRequest.current_status.has(code="APPROVED"),
        ValidationRequest.completion_date.isnot(None)
    ).order_by(ValidationRequest.completion_date.desc()).first()

    if not latest_approved or not latest_approved.completion_date:
        # No prior validation - model hasn't been validated yet
        # For new models, we don't penalize until they should have been validated
        return 0

    # Get the validation policy for this model's risk tier
    risk_tier_id = model.risk_tier_id
    if not risk_tier_id:
        return 0

    policy = db.query(ValidationPolicy).filter(
        ValidationPolicy.risk_tier_id == risk_tier_id
    ).first()

    if not policy:
        # No active policy for this tier
        return 0

    # Calculate when the next validation is due
    # Due date = last completion date + frequency_months + grace_period_months
    from dateutil.relativedelta import relativedelta

    frequency_months = policy.frequency_months or 12
    grace_period_months = policy.grace_period_months or 0

    # Next due date is completion_date + frequency_months
    completion_date = latest_approved.completion_date
    if isinstance(completion_date, str):
        completion_date = date.fromisoformat(completion_date)
    elif hasattr(completion_date, 'date'):
        # Handle datetime objects
        completion_date = completion_date.date()

    next_due_date = completion_date + relativedelta(months=frequency_months)

    # Add grace period for the "past due" calculation
    grace_period_end = next_due_date + relativedelta(months=grace_period_months)

    # Calculate days overdue (positive if past grace period end)
    days_overdue = (today - grace_period_end).days

    return days_overdue


def compute_final_model_risk_ranking(
    db: Session,
    model_id: int
) -> Optional[Dict[str, Any]]:
    """
    Compute the Final Model Risk Ranking for a model.

    The Final Risk Ranking reflects both the model's inherent risk characteristics
    AND its validation compliance status (past-due penalty applied).

    Computation flow:
    1. Get original scorecard outcome from most recent validation
    2. Calculate model's days overdue
    3. Get past due level bucket and its downgrade_notches
    4. Downgrade scorecard by N notches (capped at Red)
    5. Look up final residual risk using adjusted scorecard

    Args:
        db: Database session
        model_id: ID of the model

    Returns:
        Dictionary with computation details:
        {
            "original_scorecard": "Green",
            "days_overdue": 400,
            "past_due_level": "Moderate",
            "past_due_level_code": "MODERATE",
            "downgrade_notches": 2,
            "adjusted_scorecard": "Yellow+",
            "inherent_risk_tier": "High",
            "final_rating": "High",
            "residual_risk_without_penalty": "Low"
        }
        Returns None if insufficient data to compute.
    """
    from app.models import Model
    from app.models.validation import ValidationRequest, ValidationRequestModelVersion

    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return None

    # Get inherent risk tier and normalize it
    inherent_risk_tier = None
    inherent_risk_tier_label = None
    if model.risk_tier:
        inherent_risk_tier_label = model.risk_tier.label
        inherent_risk_tier = RISK_TIER_MAPPING.get(inherent_risk_tier_label)

    if not inherent_risk_tier:
        return None

    # Get most recent validation with a scorecard result
    # Order by completion_date to get the most recent completed validation
    # ValidationRequest uses a many-to-many relationship with models
    latest_validation = db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id,
        ValidationRequest.scorecard_result.has()
    ).order_by(ValidationRequest.completion_date.desc().nullslast()).first()

    if not latest_validation or not latest_validation.scorecard_result:
        return None

    original_scorecard = latest_validation.scorecard_result.overall_rating
    if not original_scorecard:
        return None

    # Calculate days overdue for the model
    days_overdue = calculate_model_days_overdue(db, model_id)

    # Get past due level and downgrade notches
    past_due_info = get_past_due_level_with_notches(db, days_overdue)
    downgrade_notches = past_due_info.get("downgrade_notches", 0) if past_due_info else 0
    past_due_level = past_due_info.get("label", "Current") if past_due_info else "Current"
    past_due_level_code = past_due_info.get("code", "CURRENT") if past_due_info else "CURRENT"

    # Apply downgrade to scorecard
    adjusted_scorecard = downgrade_scorecard(original_scorecard, downgrade_notches)

    # Compute final residual risk with adjusted scorecard
    final_rating = lookup_residual_risk(db, inherent_risk_tier, adjusted_scorecard)

    # Also compute what residual risk would be without penalty (for comparison)
    residual_risk_without_penalty = lookup_residual_risk(db, inherent_risk_tier, original_scorecard)

    return {
        "original_scorecard": original_scorecard,
        "days_overdue": days_overdue,
        "past_due_level": past_due_level,
        "past_due_level_code": past_due_level_code,
        "downgrade_notches": downgrade_notches,
        "adjusted_scorecard": adjusted_scorecard,
        "inherent_risk_tier": inherent_risk_tier,
        "inherent_risk_tier_label": inherent_risk_tier_label,
        "final_rating": final_rating,
        "residual_risk_without_penalty": residual_risk_without_penalty,
    }
