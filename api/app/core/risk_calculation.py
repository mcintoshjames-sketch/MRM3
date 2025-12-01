"""Risk calculation logic for Model Risk Assessment.

Implements:
- Weighted qualitative score calculation
- Inherent risk matrix lookup
- Tier code mapping
- Effective values calculation with overrides
"""
from decimal import Decimal
from typing import List, Tuple, Optional, Any


# Rating scores are fixed (High=3, Medium=2, Low=1)
RATING_SCORES = {
    'HIGH': 3,
    'MEDIUM': 2,
    'LOW': 1
}

# Inherent risk matrix: (Quantitative, Qualitative) -> Result
# Based on INHERENT_MATRIX.png
INHERENT_RISK_MATRIX = {
    ('HIGH', 'HIGH'): 'HIGH',
    ('HIGH', 'MEDIUM'): 'MEDIUM',
    ('HIGH', 'LOW'): 'LOW',
    ('MEDIUM', 'HIGH'): 'MEDIUM',
    ('MEDIUM', 'MEDIUM'): 'MEDIUM',
    ('MEDIUM', 'LOW'): 'LOW',
    ('LOW', 'HIGH'): 'LOW',
    ('LOW', 'MEDIUM'): 'LOW',
    ('LOW', 'LOW'): 'VERY_LOW',
}

# Tier mapping: Risk level -> Model Risk Tier code
TIER_MAPPING = {
    'HIGH': 'TIER_1',
    'MEDIUM': 'TIER_2',
    'LOW': 'TIER_3',
    'VERY_LOW': 'TIER_4'
}

# Level thresholds for qualitative score
LEVEL_THRESHOLDS = {
    'HIGH': Decimal('2.1'),     # Score >= 2.1 is HIGH
    'MEDIUM': Decimal('1.6'),   # Score >= 1.6 is MEDIUM
}


def calculate_qualitative_score(factor_assessments: List[Any]) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Calculate weighted qualitative score from factor assessments.

    Uses weight_at_assessment (snapshot) for existing assessments,
    which ensures historical accuracy when factor weights change.

    Args:
        factor_assessments: List of factor assessments with rating and weight_at_assessment

    Returns:
        Tuple of (score, level) where:
        - score: Weighted sum of (rating_points * weight) rounded to 2 decimal places
        - level: 'HIGH' if score >= 2.1, 'MEDIUM' if score >= 1.6, 'LOW' otherwise
        Returns (None, None) if no factors are rated.
    """
    # Filter to only rated factors
    rated_factors = [fa for fa in factor_assessments if fa.rating is not None]

    if not rated_factors:
        return None, None

    # Calculate weighted sum
    total = Decimal('0')
    for fa in rated_factors:
        points = RATING_SCORES.get(fa.rating, 0)
        weight = fa.weight_at_assessment if isinstance(fa.weight_at_assessment, Decimal) else Decimal(str(fa.weight_at_assessment))
        total += weight * points

    # Round to 2 decimal places
    score = total.quantize(Decimal('0.01'))

    # Determine level based on thresholds
    if score >= LEVEL_THRESHOLDS['HIGH']:
        level = 'HIGH'
    elif score >= LEVEL_THRESHOLDS['MEDIUM']:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return score, level


def lookup_inherent_risk(quantitative: Optional[str], qualitative: Optional[str]) -> Optional[str]:
    """
    Matrix lookup for derived inherent risk tier.

    Args:
        quantitative: Effective quantitative rating ('HIGH', 'MEDIUM', 'LOW')
        qualitative: Effective qualitative level ('HIGH', 'MEDIUM', 'LOW')

    Returns:
        Derived risk tier ('HIGH', 'MEDIUM', 'LOW', 'VERY_LOW') or None if inputs invalid
    """
    if quantitative is None or qualitative is None:
        return None

    return INHERENT_RISK_MATRIX.get((quantitative, qualitative))


def map_to_tier_code(risk_level: Optional[str]) -> Optional[str]:
    """
    Map risk level to taxonomy tier code.

    Args:
        risk_level: 'HIGH', 'MEDIUM', 'LOW', or 'VERY_LOW'

    Returns:
        Tier code ('TIER_1', 'TIER_2', 'TIER_3', 'TIER_4') or None if invalid
    """
    if risk_level is None:
        return None

    return TIER_MAPPING.get(risk_level)


def get_effective_values(assessment: Any) -> dict:
    """
    Calculate all effective values after applying overrides.

    Override priority:
    1. Quantitative: override replaces rating
    2. Qualitative: override replaces calculated level
    3. Final: override replaces derived tier

    Args:
        assessment: ModelRiskAssessment object with rating/override fields

    Returns:
        dict with:
        - effective_quantitative: After applying quantitative override
        - effective_qualitative: After applying qualitative override
        - derived_risk_tier: From matrix lookup (before final override)
        - effective_risk_tier: After applying final override
        - tier_code: TIER_1/2/3/4 code for taxonomy lookup
    """
    # Apply overrides
    eff_quantitative = assessment.quantitative_override or assessment.quantitative_rating
    eff_qualitative = assessment.qualitative_override or assessment.qualitative_calculated_level

    # Matrix lookup
    derived = None
    if eff_quantitative and eff_qualitative:
        derived = lookup_inherent_risk(eff_quantitative, eff_qualitative)

    # Apply final override
    eff_final = assessment.derived_risk_tier_override or derived

    # Map to tier code
    tier_code = map_to_tier_code(eff_final)

    return {
        'effective_quantitative': eff_quantitative,
        'effective_qualitative': eff_qualitative,
        'derived_risk_tier': derived,
        'effective_risk_tier': eff_final,
        'tier_code': tier_code
    }


def validate_factor_weights(factors: List[Any]) -> bool:
    """
    Validate that active factor weights sum to 1.0 (100%).

    Args:
        factors: List of QualitativeRiskFactor objects

    Returns:
        True if weights sum to 1.0 (within tolerance), False otherwise
    """
    total = sum(
        f.weight if isinstance(f.weight, Decimal) else Decimal(str(f.weight))
        for f in factors
        if getattr(f, 'is_active', True)
    )
    return abs(total - Decimal('1.0')) < Decimal('0.0001')


def create_audit_log_changes(
    old_values: dict,
    new_values: dict,
    override_type: Optional[str] = None,
    model_tier_change: Optional[dict] = None
) -> dict:
    """
    Create audit log changes dict for risk assessment updates.

    Args:
        old_values: Previous assessment values
        new_values: New assessment values
        override_type: Type of override applied ('quantitative', 'qualitative', 'final')
        model_tier_change: Dict with 'from' and 'to' tier codes if model tier changed

    Returns:
        Changes dict suitable for AuditLog.changes field
    """
    changes = {}

    # Compute field differences
    for key in set(old_values.keys()) | set(new_values.keys()):
        old_val = old_values.get(key)
        new_val = new_values.get(key)
        if old_val != new_val:
            changes[key] = {'old': old_val, 'new': new_val}

    # Add override metadata if applicable
    if override_type:
        changes['_override_type'] = override_type

    # Add model tier change metadata if applicable
    if model_tier_change:
        changes['_model_tier_changed_from'] = model_tier_change.get('from')
        changes['_model_tier_changed_to'] = model_tier_change.get('to')

    return changes
