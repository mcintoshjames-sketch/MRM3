# Final Model Risk Ranking Implementation Plan

## Overview

The **Final Model Risk Ranking** is a computed risk metric that reflects both a model's inherent risk characteristics AND its validation compliance status. It achieves this by applying a past-due penalty to the scorecard outcome before computing the residual risk.

## Computation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Original Scorecard Outcome                                                 │
│  (from model's most recent validation)                                      │
│  e.g., "Green", "Yellow+", "Yellow-"                                        │
│                                                                             │
│                          ↓                                                  │
│                                                                             │
│  ┌─────────────────────────────────────────┐                                │
│  │  Past-Due Downgrade                     │                                │
│  │  ─────────────────────                  │                                │
│  │  1. Get model's days_overdue            │                                │
│  │  2. Match to Past Due Level bucket      │                                │
│  │  3. Read downgrade_notches from bucket  │                                │
│  │  4. Downgrade scorecard by N notches    │                                │
│  │  5. Cap at "Red" (worst level)          │                                │
│  └─────────────────────────────────────────┘                                │
│                                                                             │
│                          ↓                                                  │
│                                                                             │
│  Adjusted Scorecard Outcome                                                 │
│  e.g., "Green" → "Yellow" (after 2 notch downgrade)                         │
│                                                                             │
│                          ↓                                                  │
│                                                                             │
│  ┌─────────────────────────────────────────┐                                │
│  │  Existing Residual Risk Map             │                                │
│  │  ─────────────────────────              │                                │
│  │  Inherent Risk Tier × Adjusted Scorecard│                                │
│  │  → Final Model Risk Ranking             │                                │
│  └─────────────────────────────────────────┘                                │
│                                                                             │
│                          ↓                                                  │
│                                                                             │
│  Final Model Risk Ranking                                                   │
│  "High", "Medium", or "Low"                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Scorecard Outcome Scale (Best to Worst)

The scorecard outcomes form an ordered scale:

| Position | Outcome | Numeric Value |
|----------|---------|---------------|
| 0 (Best) | Green   | 0             |
| 1        | Green-  | 1             |
| 2        | Yellow+ | 2             |
| 3        | Yellow  | 3             |
| 4        | Yellow- | 4             |
| 5 (Worst)| Red     | 5             |

**Downgrade Logic:**
- 1 notch: Green → Green-, Yellow → Yellow-, etc.
- 2 notches: Green → Yellow+, Yellow+ → Yellow-
- 3 notches: Green → Yellow, Green- → Yellow-, Yellow+ → Red
- Cap at Red (position 5) - cannot go worse

## Leveraging Past Due Level Bucket Taxonomy

### Current Taxonomy Structure

The existing Past Due Level taxonomy (`taxonomy_id` for "Past Due Level") has 6 buckets:

| Code        | Label       | min_days | max_days | Description                  |
|-------------|-------------|----------|----------|------------------------------|
| CURRENT     | Current     | NULL     | 0        | Not past due                 |
| MINIMAL     | Minimal     | 1        | 365      | 1-365 days past due          |
| MODERATE    | Moderate    | 366      | 730      | 1-2 years past due           |
| SIGNIFICANT | Significant | 731      | 1095     | 2-3 years past due           |
| CRITICAL    | Critical    | 1096     | 1825     | 3-5 years past due           |
| OBSOLETE    | Obsolete    | 1826     | NULL     | 5+ years past due            |

### Enhancement: Add `downgrade_notches` Field

Add a new column to `taxonomy_values` table to store the downgrade configuration:

| Code        | downgrade_notches | Effect                                      |
|-------------|-------------------|---------------------------------------------|
| CURRENT     | 0                 | No downgrade (compliant)                    |
| MINIMAL     | 1                 | 1 notch downgrade (< 1 year past due)       |
| MODERATE    | 2                 | 2 notch downgrade (1-2 years past due)      |
| SIGNIFICANT | 3                 | 3 notch downgrade (2-3 years past due)      |
| CRITICAL    | 3                 | 3 notch downgrade (3-5 years past due)      |
| OBSOLETE    | 3                 | 3 notch downgrade (5+ years past due)       |

**Benefits of this approach:**
1. Admin-configurable: Admins can adjust both the day ranges (bucket boundaries) AND the downgrade penalties
2. No separate configuration table needed
3. Consistent with existing taxonomy management UI
4. Self-documenting: Viewing the taxonomy shows both thresholds and penalties

## Implementation Tasks

### Phase 1: Database Schema

#### Task 1.1: Add `downgrade_notches` Column

**File:** `api/alembic/versions/XXXX_add_downgrade_notches_to_taxonomy_values.py`

```python
"""Add downgrade_notches column to taxonomy_values

Revision ID: XXXX
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'taxonomy_values',
        sa.Column('downgrade_notches', sa.Integer(), nullable=True)
    )

def downgrade():
    op.drop_column('taxonomy_values', 'downgrade_notches')
```

#### Task 1.2: Update TaxonomyValue Model

**File:** `api/app/models/taxonomy.py`

Add field to `TaxonomyValue` model:
```python
downgrade_notches: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

#### Task 1.3: Update Seed Data

**File:** `api/app/seed.py`

Update Past Due Level taxonomy seeding to include `downgrade_notches`:
```python
past_due_values = [
    ("CURRENT", "Current", "Model is not past due", None, 0, 0),      # (code, label, desc, min_days, max_days, downgrade_notches)
    ("MINIMAL", "Minimal", "1-365 days past due", 1, 365, 1),
    ("MODERATE", "Moderate", "1-2 years past due", 366, 730, 2),
    ("SIGNIFICANT", "Significant", "2-3 years past due", 731, 1095, 3),
    ("CRITICAL", "Critical", "3-5 years past due", 1096, 1825, 3),
    ("OBSOLETE", "Obsolete", "5+ years past due", 1826, None, 3),
]
```

### Phase 2: Backend API

#### Task 2.1: Update Taxonomy Schemas

**File:** `api/app/schemas/taxonomy.py`

Add `downgrade_notches` to relevant schemas:
```python
class TaxonomyValueRead(TaxonomyValueBase):
    # ... existing fields ...
    downgrade_notches: Optional[int] = None

class TaxonomyValueUpdate(BaseModel):
    # ... existing fields ...
    downgrade_notches: Optional[int] = None
```

#### Task 2.2: Create Final Rating Computation Module

**File:** `api/app/core/final_rating.py` (new file)

```python
"""
Final Model Risk Ranking computation module.

Computes the final risk ranking by:
1. Getting the model's most recent validation scorecard outcome
2. Applying past-due downgrade notches based on model's overdue status
3. Using adjusted scorecard + inherent risk tier in the Residual Risk Map
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session

# Scorecard outcomes ordered from best (0) to worst (5)
SCORECARD_ORDER = ["Green", "Green-", "Yellow+", "Yellow", "Yellow-", "Red"]

def downgrade_scorecard(
    original_outcome: str,
    notches: int
) -> str:
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


def get_downgrade_notches_for_days_overdue(
    db: Session,
    days_overdue: int
) -> int:
    """
    Get the downgrade notches for a given number of days overdue.

    Queries the Past Due Level taxonomy to find matching bucket and returns
    its configured downgrade_notches value.

    Args:
        db: Database session
        days_overdue: Number of days the model is overdue (negative = not overdue)

    Returns:
        Number of notches to downgrade (0 if not overdue or bucket not found)
    """
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    # Find Past Due Level taxonomy
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Past Due Level"
    ).first()

    if not taxonomy:
        return 0

    # Find matching bucket
    buckets = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.is_active == True
    ).all()

    for bucket in buckets:
        min_days = bucket.min_days
        max_days = bucket.max_days

        # Check if days_overdue falls within this bucket
        if min_days is None and max_days is None:
            # Unbounded bucket - matches everything
            return bucket.downgrade_notches or 0
        elif min_days is None:
            # Lower unbounded: matches if days_overdue <= max_days
            if days_overdue <= max_days:
                return bucket.downgrade_notches or 0
        elif max_days is None:
            # Upper unbounded: matches if days_overdue >= min_days
            if days_overdue >= min_days:
                return bucket.downgrade_notches or 0
        else:
            # Bounded: matches if min_days <= days_overdue <= max_days
            if min_days <= days_overdue <= max_days:
                return bucket.downgrade_notches or 0

    return 0


def compute_final_model_risk_ranking(
    db: Session,
    model_id: int
) -> Optional[dict]:
    """
    Compute the Final Model Risk Ranking for a model.

    Args:
        db: Database session
        model_id: ID of the model

    Returns:
        Dictionary with computation details:
        {
            "original_scorecard": "Green",
            "days_overdue": 400,
            "past_due_level": "Moderate",
            "downgrade_notches": 2,
            "adjusted_scorecard": "Yellow+",
            "inherent_risk_tier": "High",
            "final_rating": "High",
            "residual_risk_without_penalty": "Low"  # For comparison
        }
        Returns None if insufficient data to compute.
    """
    from app.models import Model
    from app.models.validation import ValidationRequest
    from app.models.residual_risk_map import get_residual_risk

    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return None

    # Get inherent risk tier
    inherent_risk_tier = None
    if model.risk_tier:
        # Normalize tier label (e.g., "Tier 1 (High Risk)" → "High")
        tier_label = model.risk_tier.label
        if "High" in tier_label:
            inherent_risk_tier = "High"
        elif "Medium" in tier_label:
            inherent_risk_tier = "Medium"
        elif "Low" in tier_label or "Very Low" in tier_label:
            inherent_risk_tier = "Low"
        else:
            inherent_risk_tier = tier_label

    if not inherent_risk_tier:
        return None

    # Get most recent approved validation with scorecard
    latest_validation = db.query(ValidationRequest).filter(
        ValidationRequest.model_id == model_id,
        ValidationRequest.scorecard_result != None
    ).order_by(ValidationRequest.completion_date.desc()).first()

    if not latest_validation or not latest_validation.scorecard_result:
        return None

    original_scorecard = latest_validation.scorecard_result.overall_rating
    if not original_scorecard:
        return None

    # Calculate days overdue for the model
    # Use model's current validation status
    days_overdue = calculate_model_days_overdue(db, model_id)

    # Get past due level and downgrade notches
    past_due_info = get_past_due_level_info(db, days_overdue)
    downgrade_notches = past_due_info.get("downgrade_notches", 0) if past_due_info else 0
    past_due_level = past_due_info.get("label", "Current") if past_due_info else "Current"

    # Apply downgrade
    adjusted_scorecard = downgrade_scorecard(original_scorecard, downgrade_notches)

    # Compute residual risk with adjusted scorecard
    final_rating = get_residual_risk(db, inherent_risk_tier, adjusted_scorecard)

    # Also compute what residual risk would be without penalty (for comparison)
    residual_risk_without_penalty = get_residual_risk(db, inherent_risk_tier, original_scorecard)

    return {
        "original_scorecard": original_scorecard,
        "days_overdue": days_overdue,
        "past_due_level": past_due_level,
        "downgrade_notches": downgrade_notches,
        "adjusted_scorecard": adjusted_scorecard,
        "inherent_risk_tier": inherent_risk_tier,
        "final_rating": final_rating,
        "residual_risk_without_penalty": residual_risk_without_penalty,
    }


def calculate_model_days_overdue(db: Session, model_id: int) -> int:
    """
    Calculate how many days overdue a model is for validation.

    Returns negative number if not yet due, 0 if due today, positive if overdue.
    """
    # Implementation will use existing overdue calculation logic
    # from validation_workflow.py or overdue_revalidation_report.py
    pass  # To be implemented


def get_past_due_level_info(db: Session, days_overdue: int) -> Optional[dict]:
    """
    Get full past due level bucket info for a given days overdue value.

    Returns:
        Dictionary with bucket details including downgrade_notches,
        or None if no matching bucket found.
    """
    # Implementation similar to existing get_past_due_level in overdue_revalidation_report.py
    # but includes downgrade_notches in response
    pass  # To be implemented
```

#### Task 2.3: Add API Endpoint

**File:** `api/app/api/models.py`

Add endpoint to get Final Model Risk Ranking:
```python
@router.get("/{model_id}/final-risk-ranking")
def get_final_risk_ranking(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the Final Model Risk Ranking for a model.

    This rating reflects both the model's inherent risk characteristics
    and its validation compliance status (past-due penalty applied).
    """
    from app.core.final_rating import compute_final_model_risk_ranking

    result = compute_final_model_risk_ranking(db, model_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Unable to compute final risk ranking. Model may be missing validation data."
        )
    return result
```

#### Task 2.4: Update Taxonomy API for Downgrade Notches

**File:** `api/app/api/taxonomies.py`

Ensure PATCH endpoint handles `downgrade_notches` updates:
- Only allow for bucket taxonomy values
- Validate non-negative integer

### Phase 3: Frontend Updates

#### Task 3.1: Update Taxonomy Management UI

**File:** `web/src/pages/TaxonomyPage.tsx`

For bucket taxonomies, add "Downgrade Notches" column and edit capability:
- Display current downgrade_notches value
- Allow admin to edit (input field, 0-5 range)
- Save via existing PATCH endpoint

#### Task 3.2: Update Model Details Page - Risk Summary Section

**File:** `web/src/pages/ModelDetailsPage.tsx`

Enhance Risk Summary section to show:
```
┌─────────────────────────────────────────────────────────────────┐
│ Risk Summary                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Inherent Risk Tier:     [High]                                 │
│                                                                 │
│  Latest Scorecard:       [Green]                                │
│                                                                 │
│  Validation Status:      [Moderate Overdue - 400 days]          │
│  Scorecard Penalty:      [2 notches → Yellow+]                  │
│                                                                 │
│  ─────────────────────────────────────────────────              │
│                                                                 │
│  Residual Risk:          [Low]     (without penalty)            │
│  Final Risk Ranking:     [Medium]  (with overdue penalty)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Task 3.3: Add API Client Function

**File:** `web/src/api/models.ts`

```typescript
export interface FinalRiskRanking {
  original_scorecard: string;
  days_overdue: number;
  past_due_level: string;
  downgrade_notches: number;
  adjusted_scorecard: string;
  inherent_risk_tier: string;
  final_rating: string;
  residual_risk_without_penalty: string;
}

export const getFinalRiskRanking = async (modelId: number): Promise<FinalRiskRanking> => {
  const response = await client.get(`/models/${modelId}/final-risk-ranking`);
  return response.data;
};
```

### Phase 4: Testing

#### Task 4.1: Backend Unit Tests

**File:** `api/tests/test_final_rating.py`

Test cases:
1. `test_downgrade_scorecard_by_one_notch` - Green → Green-
2. `test_downgrade_scorecard_by_three_notches` - Green → Yellow
3. `test_downgrade_caps_at_red` - Yellow- + 3 notches → Red (not beyond)
4. `test_no_downgrade_when_current` - 0 notches leaves scorecard unchanged
5. `test_bucket_matching` - Correct bucket selected for various days_overdue values
6. `test_full_computation_flow` - End-to-end Final Rating computation
7. `test_missing_validation_returns_none` - Graceful handling of missing data

#### Task 4.2: API Integration Tests

**File:** `api/tests/test_final_rating_api.py`

Test cases:
1. `test_get_final_risk_ranking_endpoint` - Returns correct structure
2. `test_final_risk_ranking_model_not_found` - 404 for invalid model
3. `test_final_risk_ranking_no_validation` - 404 when no validation exists

### Phase 5: Documentation

#### Task 5.1: Update ARCHITECTURE.md

Add section describing Final Model Risk Ranking feature.

#### Task 5.2: Update CLAUDE.md

Add Final Rating to feature descriptions.

---

## Example Scenarios

### Scenario 1: Compliant Model
- Original Scorecard: Green
- Days Overdue: -30 (not yet due)
- Past Due Level: Current
- Downgrade Notches: 0
- Adjusted Scorecard: Green
- Inherent Risk: Medium
- **Final Rating: Low** (same as residual risk)

### Scenario 2: Slightly Overdue Model
- Original Scorecard: Green
- Days Overdue: 200
- Past Due Level: Minimal (1-365 days)
- Downgrade Notches: 1
- Adjusted Scorecard: Green-
- Inherent Risk: Medium
- **Final Rating: Low** (minor impact)

### Scenario 3: Significantly Overdue Model
- Original Scorecard: Green
- Days Overdue: 800
- Past Due Level: Significant (731-1095 days)
- Downgrade Notches: 3
- Adjusted Scorecard: Yellow
- Inherent Risk: High
- **Final Rating: High** (elevated from Low due to overdue penalty)

### Scenario 4: Already Poor Scorecard + Overdue
- Original Scorecard: Yellow-
- Days Overdue: 500
- Past Due Level: Moderate (366-730 days)
- Downgrade Notches: 2
- Adjusted Scorecard: Red (capped)
- Inherent Risk: High
- **Final Rating: High** (already at worst)

---

## Configuration Reference

### Default Downgrade Configuration

| Past Due Level | Days Range    | Default Notches | Rationale                           |
|----------------|---------------|-----------------|-------------------------------------|
| Current        | ≤ 0 days      | 0               | Compliant, no penalty               |
| Minimal        | 1-365 days    | 1               | Minor concern, small penalty        |
| Moderate       | 366-730 days  | 2               | Material concern, moderate penalty  |
| Significant    | 731-1095 days | 3               | Serious concern, maximum penalty    |
| Critical       | 1096-1825 days| 3               | Severe concern, maximum penalty     |
| Obsolete       | > 1825 days   | 3               | Critical concern, maximum penalty   |

### Admin Configuration

Admins can adjust:
1. **Bucket boundaries** (min_days, max_days) - via existing Taxonomy management
2. **Downgrade notches per bucket** - via enhanced Taxonomy management

Changes take effect immediately (no version control).

---

## Implementation Order

1. **Phase 1**: Database schema (migration + model update)
2. **Phase 2**: Backend API (computation module + endpoint)
3. **Phase 3**: Frontend (taxonomy UI + model details)
4. **Phase 4**: Testing
5. **Phase 5**: Documentation

Estimated effort: 2-3 days for core implementation + testing.

---

## Future Enhancements

1. **Report Integration**: Add `final_risk_ranking` column to:
   - Overdue Revalidation Report
   - Model List export
   - Dashboard widgets

2. **Alerts**: Trigger notifications when Final Rating changes due to becoming overdue

3. **Historical Tracking**: Optional: snapshot Final Rating at key events for audit trail

4. **Bulk Computation**: API endpoint to get Final Ratings for multiple models efficiently
