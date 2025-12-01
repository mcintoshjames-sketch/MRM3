# Recommendation Timeframe Enforcement Implementation Plan

## Overview

This document describes the implementation of configurable maximum remediation target timelines for recommendations, including:

1. Adding `ENFORCE_TIMEFRAMES` configuration to priority settings (base + regional overrides)
2. Database-driven timeframe configuration (replacing static REC_TIMES.json)
3. Automatic target date calculation based on priority, model risk tier, and usage frequency
4. Enforcement logic with "most restrictive wins" for multi-region scenarios
5. Target date change tracking with required explanations

---

## Development Methodology: Test-Driven Development (TDD)

This implementation follows strict TDD principles:

### Red-Green-Refactor Cycle

1. **RED**: Write a failing test that defines expected behavior
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Clean up code while keeping tests green

### TDD Rules for This Implementation

- No production code without a failing test first
- Each test should fail for the right reason before implementation
- Tests are grouped by feature slice, not by layer
- Integration tests cover API endpoints; unit tests cover business logic
- Frontend tests written before UI components

---

## Current State

### Existing Priority Configuration

**RecommendationPriorityConfig** (base):
- `requires_action_plan: bool` - Whether action plan submission is required
- `requires_final_approval: bool` - Whether Global/Regional approvals needed for closure

**RecommendationPriorityRegionalOverride** (per region):
- Same fields, can override base config per region
- NULL values inherit from base config
- "Most restrictive wins" logic already implemented

### Related Taxonomies

| Taxonomy | Codes | Notes |
|----------|-------|-------|
| Recommendation Priority | HIGH, MEDIUM, LOW, CONSIDERATION | CONSIDERATION has `requires_action_plan=false` |
| Model Risk Tier | TIER_1, TIER_2, TIER_3, TIER_4 | Maps to inherent risk level |
| Model Usage Frequency | DAILY, MONTHLY, QUARTERLY, ANNUALLY | How often model runs |

### Current Timeframe Data (REC_TIMES.json)

```json
{
    "recommendation_timeframes": {
        "high_priority": {
            "high_inherent_risk": { "daily": 0, "monthly": 0, "quarterly": 90, "annually": 90 },
            "medium_inherent_risk": { "daily": 0, "monthly": 90, "quarterly": 90, "annually": 180 },
            "low_inherent_risk": { "daily": 90, "monthly": 90, "quarterly": 180, "annually": 180 }
        },
        "medium_priority": {
            "high_inherent_risk": { "daily": 180, "monthly": 180, "quarterly": 180, "annually": 180 },
            "medium_inherent_risk": { "daily": 180, "monthly": 180, "quarterly": 180, "annually": 365 },
            "low_inherent_risk": { "daily": 180, "monthly": 180, "quarterly": 365, "annually": 365 }
        },
        "low_priority": {
            "high_inherent_risk": { "daily": 365, "monthly": 365, "quarterly": 365, "annually": 365 },
            "medium_inherent_risk": { "daily": 365, "monthly": 365, "quarterly": 365, "annually": 1095 },
            "low_inherent_risk": { "daily": 365, "monthly": 365, "quarterly": 1095, "annually": 1095 }
        }
    }
}
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CONSIDERATION priority | No timeframe enforcement | Already has `requires_action_plan=false`, no remediation tracking |
| Risk tier mapping | Add 4th tier (very_low) | Align with TIER_4 in taxonomy |
| Multi-region enforcement | Most restrictive wins | Consistent with existing override pattern |
| Timeframe storage | Database tables | Admin-editable via UI |
| Creation date reference | Date recommendation created (DRAFT) | Clear starting point |
| Target date updates | Allowed with explanation | Flexibility with audit trail |

---

## TDD Implementation Phases

Each phase follows: **Write Tests → Run (RED) → Implement → Run (GREEN) → Refactor**

---

## Phase 1: Database Schema & Models (TDD)

### 1.1 Write Failing Tests First

**File**: `api/tests/test_recommendation_timeframes.py`

```python
"""
TDD Tests for Recommendation Timeframe Enforcement.

These tests are written BEFORE implementation.
Run order: Write test → See RED → Implement → See GREEN → Refactor
"""
import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.recommendation import (
    RecommendationTimeframeConfig,
    RecommendationPriorityConfig,
    RecommendationPriorityRegionalOverride,
    Recommendation
)


class TestTimeframeConfigModel:
    """Phase 1: Test that the model exists and has correct structure."""

    def test_timeframe_config_model_exists(self, db: Session):
        """RED: Model class should exist."""
        # This will fail until we create the model
        assert RecommendationTimeframeConfig is not None

    def test_timeframe_config_has_required_fields(self, db: Session):
        """RED: Model should have priority_id, risk_tier_id, usage_frequency_id, max_days."""
        config = RecommendationTimeframeConfig(
            priority_id=1,
            risk_tier_id=2,
            usage_frequency_id=3,
            max_days=90
        )
        assert config.priority_id == 1
        assert config.risk_tier_id == 2
        assert config.usage_frequency_id == 3
        assert config.max_days == 90

    def test_timeframe_config_unique_constraint(self, db: Session, seed_taxonomies):
        """RED: Should enforce unique constraint on priority+risk+frequency."""
        priority_id = seed_taxonomies["recommendation_priority"]["HIGH"]
        risk_tier_id = seed_taxonomies["model_risk_tier"]["TIER_1"]
        freq_id = seed_taxonomies["usage_frequency"]["DAILY"]

        config1 = RecommendationTimeframeConfig(
            priority_id=priority_id,
            risk_tier_id=risk_tier_id,
            usage_frequency_id=freq_id,
            max_days=90
        )
        db.add(config1)
        db.commit()

        # Duplicate should fail
        config2 = RecommendationTimeframeConfig(
            priority_id=priority_id,
            risk_tier_id=risk_tier_id,
            usage_frequency_id=freq_id,
            max_days=180
        )
        db.add(config2)
        with pytest.raises(Exception):  # IntegrityError
            db.commit()


class TestPriorityConfigEnforceTimeframes:
    """Phase 1: Test enforce_timeframes field on priority config."""

    def test_priority_config_has_enforce_timeframes_field(self, db: Session):
        """RED: PriorityConfig should have enforce_timeframes boolean field."""
        config = RecommendationPriorityConfig(
            priority_id=1,
            requires_action_plan=True,
            requires_final_approval=True,
            enforce_timeframes=True
        )
        assert config.enforce_timeframes is True

    def test_priority_config_enforce_timeframes_defaults_true(self, db: Session):
        """RED: enforce_timeframes should default to True."""
        config = RecommendationPriorityConfig(
            priority_id=1,
            requires_action_plan=True,
            requires_final_approval=True
        )
        # Default should be True
        assert config.enforce_timeframes is True


class TestRegionalOverrideEnforceTimeframes:
    """Phase 1: Test enforce_timeframes field on regional override."""

    def test_regional_override_has_enforce_timeframes_field(self, db: Session):
        """RED: RegionalOverride should have nullable enforce_timeframes field."""
        override = RecommendationPriorityRegionalOverride(
            priority_id=1,
            region_id=1,
            enforce_timeframes=True
        )
        assert override.enforce_timeframes is True

    def test_regional_override_enforce_timeframes_nullable(self, db: Session):
        """RED: enforce_timeframes can be None (inherit from base)."""
        override = RecommendationPriorityRegionalOverride(
            priority_id=1,
            region_id=1,
            enforce_timeframes=None
        )
        assert override.enforce_timeframes is None


class TestRecommendationTargetDateReason:
    """Phase 1: Test target_date_change_reason field on Recommendation."""

    def test_recommendation_has_target_date_change_reason(self, db: Session):
        """RED: Recommendation should have target_date_change_reason text field."""
        # Assuming Recommendation model exists
        rec = Recommendation(
            model_id=1,
            validation_request_id=1,
            title="Test",
            description="Test",
            priority_id=1,
            status_id=1,
            target_date_change_reason="Changed due to resource constraints"
        )
        assert rec.target_date_change_reason == "Changed due to resource constraints"
```

### 1.2 Implementation: Database Migration

**File**: `api/alembic/versions/xxx_add_timeframe_enforcement.py`

```python
"""Add timeframe enforcement support.

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Create timeframe configs table
    op.create_table(
        'recommendation_timeframe_configs',
        sa.Column('config_id', sa.Integer(), primary_key=True),
        sa.Column('priority_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=False),
        sa.Column('risk_tier_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=False),
        sa.Column('usage_frequency_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=False),
        sa.Column('max_days', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('priority_id', 'risk_tier_id', 'usage_frequency_id', name='uq_timeframe_config')
    )

    # 2. Add enforce_timeframes to priority config
    op.add_column(
        'recommendation_priority_configs',
        sa.Column('enforce_timeframes', sa.Boolean(), nullable=False, server_default='true')
    )

    # 3. Add enforce_timeframes to regional override
    op.add_column(
        'recommendation_priority_regional_overrides',
        sa.Column('enforce_timeframes', sa.Boolean(), nullable=True)
    )

    # 4. Add target_date_change_reason to recommendations
    op.add_column(
        'recommendations',
        sa.Column('target_date_change_reason', sa.Text(), nullable=True)
    )

def downgrade():
    op.drop_column('recommendations', 'target_date_change_reason')
    op.drop_column('recommendation_priority_regional_overrides', 'enforce_timeframes')
    op.drop_column('recommendation_priority_configs', 'enforce_timeframes')
    op.drop_table('recommendation_timeframe_configs')
```

### 1.3 Implementation: SQLAlchemy Models

Update `api/app/models/recommendation.py` with new model and fields.

### 1.4 Run Tests → GREEN

```bash
cd api && python -m pytest tests/test_recommendation_timeframes.py -v
```

---

## Phase 2: Business Logic - Max Days Lookup (TDD)

### 2.1 Write Failing Tests First

```python
class TestGetMaxDaysForRecommendation:
    """Phase 2: Test max days lookup function."""

    def test_get_max_days_returns_correct_value(self, db: Session, seed_timeframe_configs):
        """RED: Should return configured max_days for priority/risk/frequency combo."""
        from app.api.recommendations import get_max_days_for_recommendation

        # HIGH priority + TIER_1 + DAILY = 0 days (from REC_TIMES)
        max_days = get_max_days_for_recommendation(
            db,
            priority_id=seed_timeframe_configs["HIGH"],
            risk_tier_id=seed_timeframe_configs["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["DAILY"]
        )
        assert max_days == 0

    def test_get_max_days_medium_priority_tier2_monthly(self, db: Session, seed_timeframe_configs):
        """RED: MEDIUM priority + TIER_2 + MONTHLY = 180 days."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db,
            priority_id=seed_timeframe_configs["MEDIUM"],
            risk_tier_id=seed_timeframe_configs["TIER_2"],
            usage_frequency_id=seed_timeframe_configs["MONTHLY"]
        )
        assert max_days == 180

    def test_get_max_days_low_priority_tier4_annually(self, db: Session, seed_timeframe_configs):
        """RED: LOW priority + TIER_4 + ANNUALLY = 1095 days."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db,
            priority_id=seed_timeframe_configs["LOW"],
            risk_tier_id=seed_timeframe_configs["TIER_4"],
            usage_frequency_id=seed_timeframe_configs["ANNUALLY"]
        )
        assert max_days == 1095

    def test_get_max_days_returns_none_if_not_configured(self, db: Session):
        """RED: Should return None if no config exists for combination."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db,
            priority_id=99999,  # Non-existent
            risk_tier_id=99999,
            usage_frequency_id=99999
        )
        assert max_days is None
```

### 2.2 Implementation: get_max_days_for_recommendation()

```python
def get_max_days_for_recommendation(
    db: Session,
    priority_id: int,
    risk_tier_id: int,
    usage_frequency_id: int
) -> Optional[int]:
    """
    Look up the maximum days allowed for a priority/risk/frequency combination.
    Returns None if no configuration found.
    """
    config = db.query(RecommendationTimeframeConfig).filter(
        RecommendationTimeframeConfig.priority_id == priority_id,
        RecommendationTimeframeConfig.risk_tier_id == risk_tier_id,
        RecommendationTimeframeConfig.usage_frequency_id == usage_frequency_id
    ).first()

    return config.max_days if config else None
```

### 2.3 Run Tests → GREEN

---

## Phase 3: Business Logic - Enforcement Check (TDD)

### 3.1 Write Failing Tests First

```python
class TestCheckEnforceTimeframes:
    """Phase 3: Test enforcement determination with regional overrides."""

    def test_enforce_from_base_config_when_no_regions(
        self, db: Session, seed_priority_configs
    ):
        """RED: Use base config when model has no regional deployments."""
        from app.api.recommendations import check_enforce_timeframes

        # HIGH priority has enforce_timeframes=True in base config
        enforce, region = check_enforce_timeframes(
            db,
            priority_id=seed_priority_configs["HIGH"],
            model_id=1  # Model with no regions
        )
        assert enforce is True
        assert region is None

    def test_enforce_from_base_config_when_no_overrides(
        self, db: Session, seed_priority_configs, model_with_regions
    ):
        """RED: Use base config when no regional overrides exist."""
        from app.api.recommendations import check_enforce_timeframes

        enforce, region = check_enforce_timeframes(
            db,
            priority_id=seed_priority_configs["HIGH"],
            model_id=model_with_regions.model_id
        )
        assert enforce is True
        assert region is None

    def test_regional_override_true_enforces(
        self, db: Session, seed_priority_configs, model_with_regions,
        regional_override_enforce_true
    ):
        """RED: Regional override with enforce_timeframes=True should enforce."""
        from app.api.recommendations import check_enforce_timeframes

        enforce, region = check_enforce_timeframes(
            db,
            priority_id=seed_priority_configs["LOW"],  # Base might be False
            model_id=model_with_regions.model_id
        )
        assert enforce is True
        assert region is not None  # Should name the enforcing region

    def test_regional_override_false_disables(
        self, db: Session, seed_priority_configs, model_with_single_region,
        regional_override_enforce_false
    ):
        """RED: All overrides False should disable enforcement."""
        from app.api.recommendations import check_enforce_timeframes

        enforce, region = check_enforce_timeframes(
            db,
            priority_id=seed_priority_configs["HIGH"],  # Base is True
            model_id=model_with_single_region.model_id
        )
        assert enforce is False
        assert region is None

    def test_most_restrictive_wins_multi_region(
        self, db: Session, seed_priority_configs, model_with_multiple_regions,
        mixed_regional_overrides  # One True, one False
    ):
        """RED: If ANY region enforces, enforcement applies (most restrictive)."""
        from app.api.recommendations import check_enforce_timeframes

        enforce, region = check_enforce_timeframes(
            db,
            priority_id=seed_priority_configs["LOW"],
            model_id=model_with_multiple_regions.model_id
        )
        assert enforce is True
        assert region is not None  # Names the enforcing region

    def test_null_override_inherits_base(
        self, db: Session, seed_priority_configs, model_with_regions,
        regional_override_null
    ):
        """RED: NULL override inherits from base config."""
        from app.api.recommendations import check_enforce_timeframes

        enforce, region = check_enforce_timeframes(
            db,
            priority_id=seed_priority_configs["HIGH"],  # Base is True
            model_id=model_with_regions.model_id
        )
        assert enforce is True  # Inherited from base
```

### 3.2 Implementation: check_enforce_timeframes()

```python
def check_enforce_timeframes(
    db: Session, priority_id: int, model_id: int
) -> tuple[bool, Optional[str]]:
    """
    Check if timeframe enforcement applies for a recommendation.

    Returns:
        (enforce: bool, enforced_by_region: Optional[str])

    Resolution logic (most restrictive wins):
    1. Get base config for priority
    2. Get model's deployed regions
    3. Check regional overrides - if ANY override says True, enforce
    4. If all overrides explicitly say False, don't enforce
    5. Fall back to base config
    """
    # Get base config
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == priority_id
    ).first()

    base_enforces = config.enforce_timeframes if config else True

    # Get model's deployed region IDs
    model_region_ids = db.query(ModelRegion.region_id).filter(
        ModelRegion.model_id == model_id
    ).all()
    region_ids = [r[0] for r in model_region_ids]

    if not region_ids:
        return (base_enforces, None)

    # Get regional overrides
    overrides = db.query(RecommendationPriorityRegionalOverride).options(
        joinedload(RecommendationPriorityRegionalOverride.region)
    ).filter(
        RecommendationPriorityRegionalOverride.priority_id == priority_id,
        RecommendationPriorityRegionalOverride.region_id.in_(region_ids)
    ).all()

    if not overrides:
        return (base_enforces, None)

    # Most restrictive wins - if ANY override says True, enforce
    for override in overrides:
        if override.enforce_timeframes is True:
            return (True, override.region.name)

    # Check if all overrides explicitly say False
    explicit_false_count = sum(1 for o in overrides if o.enforce_timeframes is False)
    if explicit_false_count == len(overrides):
        return (False, None)

    # Some NULL, none True - use base
    return (base_enforces, None)
```

### 3.3 Run Tests → GREEN

---

## Phase 4: Business Logic - Calculate Max Target Date (TDD)

### 4.1 Write Failing Tests First

```python
class TestCalculateMaxTargetDate:
    """Phase 4: Test max target date calculation."""

    def test_calculate_max_date_basic(
        self, db: Session, model_with_tier1_daily, seed_all
    ):
        """RED: Should calculate correct max date from creation + max_days."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 15)
        # HIGH priority + TIER_1 + DAILY = 0 days
        max_date, max_days, enforce, region = calculate_max_target_date(
            db,
            model_id=model_with_tier1_daily.model_id,
            priority_id=seed_all["HIGH"],
            creation_date=creation_date
        )
        assert max_days == 0
        assert max_date == date(2025, 1, 15)  # Same day
        assert enforce is True

    def test_calculate_max_date_90_days(
        self, db: Session, model_with_tier3_quarterly, seed_all
    ):
        """RED: HIGH + TIER_3 + QUARTERLY = 180 days."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        max_date, max_days, enforce, region = calculate_max_target_date(
            db,
            model_id=model_with_tier3_quarterly.model_id,
            priority_id=seed_all["HIGH"],
            creation_date=creation_date
        )
        assert max_days == 180
        assert max_date == date(2025, 6, 30)  # 180 days later

    def test_calculate_max_date_model_missing_risk_tier(
        self, db: Session, model_without_risk_tier, seed_all
    ):
        """RED: Should raise error if model has no risk_tier_id."""
        from app.api.recommendations import calculate_max_target_date

        with pytest.raises(ValueError, match="risk_tier"):
            calculate_max_target_date(
                db,
                model_id=model_without_risk_tier.model_id,
                priority_id=seed_all["HIGH"],
                creation_date=date(2025, 1, 1)
            )

    def test_calculate_max_date_model_missing_usage_frequency(
        self, db: Session, model_without_usage_frequency, seed_all
    ):
        """RED: Should raise error if model has no usage_frequency_id."""
        from app.api.recommendations import calculate_max_target_date

        with pytest.raises(ValueError, match="usage_frequency"):
            calculate_max_target_date(
                db,
                model_id=model_without_usage_frequency.model_id,
                priority_id=seed_all["HIGH"],
                creation_date=date(2025, 1, 1)
            )

    def test_calculate_max_date_defaults_to_365_if_no_config(
        self, db: Session, model_with_unconfigured_combo, seed_all
    ):
        """RED: Should default to 365 days if no config found."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        max_date, max_days, enforce, region = calculate_max_target_date(
            db,
            model_id=model_with_unconfigured_combo.model_id,
            priority_id=seed_all["HIGH"],  # Using unconfigured priority
            creation_date=creation_date
        )
        assert max_days == 365
        assert max_date == date(2026, 1, 1)
```

### 4.2 Implementation: calculate_max_target_date()

```python
def calculate_max_target_date(
    db: Session,
    model_id: int,
    priority_id: int,
    creation_date: date
) -> tuple[date, int, bool, Optional[str]]:
    """
    Calculate the maximum allowed target date for a recommendation.

    Returns:
        (max_date: date, max_days: int, enforce: bool, enforced_by_region: Optional[str])
    """
    # Get model's risk tier and usage frequency
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise ValueError("Model not found")

    if not model.risk_tier_id:
        raise ValueError("Model must have risk_tier set to create recommendations")

    if not model.usage_frequency_id:
        raise ValueError("Model must have usage_frequency set to create recommendations")

    # Look up max days
    max_days = get_max_days_for_recommendation(
        db, priority_id, model.risk_tier_id, model.usage_frequency_id
    )

    if max_days is None:
        # No config found - default to 365 days
        max_days = 365

    # Calculate max date
    max_date = creation_date + timedelta(days=max_days)

    # Check enforcement
    enforce, enforced_by = check_enforce_timeframes(db, priority_id, model_id)

    return (max_date, max_days, enforce, enforced_by)
```

### 4.3 Run Tests → GREEN

---

## Phase 5: Business Logic - Validate Target Date (TDD)

### 5.1 Write Failing Tests First

```python
class TestValidateTargetDate:
    """Phase 5: Test target date validation logic."""

    def test_validate_accepts_date_within_max(
        self, db: Session, model_with_tier2_monthly, seed_all
    ):
        """RED: Should accept date within allowed range."""
        from app.api.recommendations import validate_target_date

        creation_date = date(2025, 1, 1)
        # MEDIUM + TIER_2 + MONTHLY = 180 days, max = 2025-06-30

        # This should NOT raise
        validate_target_date(
            db,
            model_id=model_with_tier2_monthly.model_id,
            priority_id=seed_all["MEDIUM"],
            creation_date=creation_date,
            proposed_target_date=date(2025, 5, 1),  # Within range
            target_date_change_reason=None
        )

    def test_validate_rejects_date_exceeds_max_when_enforced(
        self, db: Session, model_with_tier2_monthly, seed_all
    ):
        """RED: Should reject date exceeding max when enforcement applies."""
        from app.api.recommendations import validate_target_date
        from fastapi import HTTPException

        creation_date = date(2025, 1, 1)
        # MEDIUM + TIER_2 + MONTHLY = 180 days, max = 2025-06-30

        with pytest.raises(HTTPException) as exc_info:
            validate_target_date(
                db,
                model_id=model_with_tier2_monthly.model_id,
                priority_id=seed_all["MEDIUM"],
                creation_date=creation_date,
                proposed_target_date=date(2025, 12, 31),  # Exceeds max
                target_date_change_reason=None
            )
        assert exc_info.value.status_code == 400
        assert "cannot exceed" in exc_info.value.detail.lower()

    def test_validate_allows_date_exceeds_max_when_not_enforced(
        self, db: Session, model_with_enforcement_disabled, seed_all
    ):
        """RED: Should allow any date when enforcement disabled."""
        from app.api.recommendations import validate_target_date

        creation_date = date(2025, 1, 1)

        # This should NOT raise even though date exceeds calculated max
        validate_target_date(
            db,
            model_id=model_with_enforcement_disabled.model_id,
            priority_id=seed_all["CONSIDERATION"],  # No enforcement
            creation_date=creation_date,
            proposed_target_date=date(2030, 12, 31),  # Way in future
            target_date_change_reason="Testing without enforcement"
        )

    def test_validate_requires_reason_when_date_differs_from_max(
        self, db: Session, model_with_tier2_monthly, seed_all
    ):
        """RED: Should require explanation when date differs from calculated max."""
        from app.api.recommendations import validate_target_date
        from fastapi import HTTPException

        creation_date = date(2025, 1, 1)
        # Max = 2025-06-30

        with pytest.raises(HTTPException) as exc_info:
            validate_target_date(
                db,
                model_id=model_with_tier2_monthly.model_id,
                priority_id=seed_all["MEDIUM"],
                creation_date=creation_date,
                proposed_target_date=date(2025, 3, 15),  # Earlier than max
                target_date_change_reason=None  # No reason provided!
            )
        assert exc_info.value.status_code == 400
        assert "explanation required" in exc_info.value.detail.lower()

    def test_validate_accepts_different_date_with_reason(
        self, db: Session, model_with_tier2_monthly, seed_all
    ):
        """RED: Should accept different date when reason provided."""
        from app.api.recommendations import validate_target_date

        creation_date = date(2025, 1, 1)

        # This should NOT raise
        validate_target_date(
            db,
            model_id=model_with_tier2_monthly.model_id,
            priority_id=seed_all["MEDIUM"],
            creation_date=creation_date,
            proposed_target_date=date(2025, 3, 15),  # Earlier than max
            target_date_change_reason="Accelerated timeline per management request"
        )

    def test_validate_accepts_exact_max_date_without_reason(
        self, db: Session, model_with_tier2_monthly, seed_all
    ):
        """RED: Should accept exact max date without requiring reason."""
        from app.api.recommendations import validate_target_date

        creation_date = date(2025, 1, 1)
        # Max = 2025-06-30

        # This should NOT raise
        validate_target_date(
            db,
            model_id=model_with_tier2_monthly.model_id,
            priority_id=seed_all["MEDIUM"],
            creation_date=creation_date,
            proposed_target_date=date(2025, 6, 30),  # Exact max
            target_date_change_reason=None
        )


class TestConsiderationPriorityNoEnforcement:
    """Phase 5: Test that CONSIDERATION priority bypasses enforcement."""

    def test_consideration_priority_no_action_plan_no_date_required(
        self, db: Session, model_with_tier1_daily, seed_all
    ):
        """RED: CONSIDERATION should allow no target date when action plan not required."""
        from app.api.recommendations import validate_target_date

        # CONSIDERATION has requires_action_plan=False
        # Should accept None target date
        validate_target_date(
            db,
            model_id=model_with_tier1_daily.model_id,
            priority_id=seed_all["CONSIDERATION"],
            creation_date=date(2025, 1, 1),
            proposed_target_date=None,  # No date!
            target_date_change_reason=None
        )
```

### 5.2 Implementation: validate_target_date()

```python
def validate_target_date(
    db: Session,
    model_id: int,
    priority_id: int,
    creation_date: date,
    proposed_target_date: Optional[date],
    target_date_change_reason: Optional[str]
) -> None:
    """
    Validate that proposed target date is acceptable.

    Raises HTTPException if:
    - Enforcement applies and proposed date exceeds max
    - Date differs from max but no reason provided
    """
    # Check if action plan is required for this priority
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == priority_id
    ).first()

    if config and not config.requires_action_plan:
        # No action plan required - any date (or no date) is fine
        return

    if proposed_target_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target date is required for this priority level"
        )

    max_date, max_days, enforce, enforced_by = calculate_max_target_date(
        db, model_id, priority_id, creation_date
    )

    if enforce:
        if proposed_target_date > max_date:
            region_msg = f" (enforced by {enforced_by})" if enforced_by else ""
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target date cannot exceed {max_date.isoformat()}{region_msg}. "
                       f"Maximum {max_days} days from creation for this priority/risk/frequency combination."
            )

    # If date differs from calculated max, require explanation
    if proposed_target_date != max_date and not target_date_change_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Explanation required when target date differs from calculated maximum "
                   f"({max_date.isoformat()})"
        )
```

### 5.3 Run Tests → GREEN

---

## Phase 6: API Endpoints - Timeframe Config CRUD (TDD)

### 6.1 Write Failing Tests First

```python
class TestTimeframeConfigEndpoints:
    """Phase 6: Test timeframe config API endpoints."""

    def test_list_timeframe_configs(
        self, client, admin_token, seed_timeframe_configs
    ):
        """RED: GET /recommendations/timeframe-config/ should list all configs."""
        response = client.get(
            "/recommendations/timeframe-config/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 48  # 3 priorities × 4 tiers × 4 frequencies

    def test_get_single_timeframe_config(
        self, client, admin_token, seed_timeframe_configs
    ):
        """RED: GET /recommendations/timeframe-config/{id} should return single config."""
        response = client.get(
            "/recommendations/timeframe-config/1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "config_id" in data
        assert "priority" in data
        assert "risk_tier" in data
        assert "usage_frequency" in data
        assert "max_days" in data

    def test_update_timeframe_config_admin_only(
        self, client, admin_token, user_token, seed_timeframe_configs
    ):
        """RED: PATCH should only be allowed for admins."""
        # Non-admin should fail
        response = client.patch(
            "/recommendations/timeframe-config/1",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"max_days": 999}
        )
        assert response.status_code == 403

        # Admin should succeed
        response = client.patch(
            "/recommendations/timeframe-config/1",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"max_days": 999}
        )
        assert response.status_code == 200
        assert response.json()["max_days"] == 999

    def test_update_timeframe_config_validates_max_days(
        self, client, admin_token, seed_timeframe_configs
    ):
        """RED: PATCH should reject negative max_days."""
        response = client.patch(
            "/recommendations/timeframe-config/1",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"max_days": -5}
        )
        assert response.status_code == 422  # Validation error


class TestCalculateTimeframeEndpoint:
    """Phase 6: Test calculate timeframe endpoint."""

    def test_calculate_timeframe_returns_correct_data(
        self, client, admin_token, model_with_tier2_monthly, seed_all
    ):
        """RED: POST /recommendations/timeframe-config/calculate should return timeframe info."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "priority_id": seed_all["MEDIUM"],
                "model_id": model_with_tier2_monthly.model_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority_code"] == "MEDIUM"
        assert data["risk_tier_code"] == "TIER_2"
        assert data["usage_frequency_code"] == "MONTHLY"
        assert data["max_days"] == 180
        assert "calculated_max_date" in data
        assert "enforce_timeframes" in data

    def test_calculate_timeframe_model_not_found(
        self, client, admin_token, seed_all
    ):
        """RED: Should return 404 for non-existent model."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "priority_id": seed_all["MEDIUM"],
                "model_id": 99999
            }
        )
        assert response.status_code == 404
```

### 6.2 Implementation: API Endpoints

Add to `api/app/api/recommendations.py`:

```python
@router.get("/timeframe-config/", response_model=List[TimeframeConfigResponse])
def list_timeframe_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all timeframe configurations."""
    configs = db.query(RecommendationTimeframeConfig).options(
        joinedload(RecommendationTimeframeConfig.priority),
        joinedload(RecommendationTimeframeConfig.risk_tier),
        joinedload(RecommendationTimeframeConfig.usage_frequency)
    ).all()
    return configs


@router.get("/timeframe-config/{config_id}", response_model=TimeframeConfigResponse)
def get_timeframe_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single timeframe configuration."""
    config = db.query(RecommendationTimeframeConfig).options(
        joinedload(RecommendationTimeframeConfig.priority),
        joinedload(RecommendationTimeframeConfig.risk_tier),
        joinedload(RecommendationTimeframeConfig.usage_frequency)
    ).filter(RecommendationTimeframeConfig.config_id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="Timeframe config not found")
    return config


@router.patch("/timeframe-config/{config_id}", response_model=TimeframeConfigResponse)
def update_timeframe_config(
    config_id: int,
    update_data: TimeframeConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update timeframe configuration (Admin only)."""
    config = db.query(RecommendationTimeframeConfig).filter(
        RecommendationTimeframeConfig.config_id == config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Timeframe config not found")

    if update_data.max_days is not None:
        config.max_days = update_data.max_days
    if update_data.description is not None:
        config.description = update_data.description

    db.commit()
    db.refresh(config)
    return config


@router.post("/timeframe-config/calculate", response_model=TimeframeCalculationResponse)
def calculate_timeframe(
    request: TimeframeCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate maximum target date for a model/priority combination."""
    model = db.query(Model).filter(Model.model_id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    today = date.today()
    max_date, max_days, enforce, enforced_by = calculate_max_target_date(
        db, request.model_id, request.priority_id, today
    )

    # Get codes for response
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request.priority_id
    ).first()
    risk_tier = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == model.risk_tier_id
    ).first()
    usage_freq = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == model.usage_frequency_id
    ).first()

    return TimeframeCalculationResponse(
        priority_code=priority.code if priority else "UNKNOWN",
        risk_tier_code=risk_tier.code if risk_tier else "UNKNOWN",
        usage_frequency_code=usage_freq.code if usage_freq else "UNKNOWN",
        max_days=max_days,
        calculated_max_date=max_date,
        enforce_timeframes=enforce,
        enforced_by_region=enforced_by
    )
```

### 6.3 Run Tests → GREEN

---

## Phase 7: API Endpoints - Create/Update Recommendation (TDD)

### 7.1 Write Failing Tests First

```python
class TestCreateRecommendationWithTimeframe:
    """Phase 7: Test recommendation creation with timeframe validation."""

    def test_create_recommendation_within_max_date(
        self, client, validator_token, model_with_tier2_monthly, validation_request, seed_all
    ):
        """RED: Should allow creating recommendation with date within max."""
        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "model_id": model_with_tier2_monthly.model_id,
                "validation_request_id": validation_request.id,
                "title": "Test Recommendation",
                "description": "Test description",
                "priority_id": seed_all["MEDIUM"],
                "current_target_date": "2025-05-01"  # Within 180 days
            }
        )
        assert response.status_code == 201

    def test_create_recommendation_exceeds_max_date_enforced(
        self, client, validator_token, model_with_tier2_monthly, validation_request, seed_all
    ):
        """RED: Should reject recommendation with date exceeding max when enforced."""
        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "model_id": model_with_tier2_monthly.model_id,
                "validation_request_id": validation_request.id,
                "title": "Test Recommendation",
                "description": "Test description",
                "priority_id": seed_all["MEDIUM"],
                "current_target_date": "2026-12-31"  # Exceeds max
            }
        )
        assert response.status_code == 400
        assert "cannot exceed" in response.json()["detail"].lower()

    def test_create_recommendation_requires_reason_for_early_date(
        self, client, validator_token, model_with_tier2_monthly, validation_request, seed_all
    ):
        """RED: Should require reason when date is earlier than max."""
        # Without reason
        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "model_id": model_with_tier2_monthly.model_id,
                "validation_request_id": validation_request.id,
                "title": "Test Recommendation",
                "description": "Test description",
                "priority_id": seed_all["MEDIUM"],
                "current_target_date": "2025-02-01"  # Earlier than max
                # No target_date_change_reason!
            }
        )
        assert response.status_code == 400
        assert "explanation required" in response.json()["detail"].lower()

        # With reason
        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "model_id": model_with_tier2_monthly.model_id,
                "validation_request_id": validation_request.id,
                "title": "Test Recommendation",
                "description": "Test description",
                "priority_id": seed_all["MEDIUM"],
                "current_target_date": "2025-02-01",
                "target_date_change_reason": "Urgent remediation required"
            }
        )
        assert response.status_code == 201


class TestUpdateRecommendationTargetDate:
    """Phase 7: Test recommendation update with target date validation."""

    def test_update_target_date_requires_reason(
        self, client, validator_token, existing_recommendation
    ):
        """RED: Should require reason when changing target date."""
        response = client.patch(
            f"/recommendations/{existing_recommendation.id}",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "current_target_date": "2025-08-01"
                # No target_date_change_reason!
            }
        )
        assert response.status_code == 400
        assert "explanation required" in response.json()["detail"].lower()

    def test_update_target_date_with_reason_succeeds(
        self, client, validator_token, existing_recommendation
    ):
        """RED: Should allow target date change with reason."""
        response = client.patch(
            f"/recommendations/{existing_recommendation.id}",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "current_target_date": "2025-08-01",
                "target_date_change_reason": "Extended due to dependency on upstream fix"
            }
        )
        assert response.status_code == 200
        assert response.json()["target_date_change_reason"] == "Extended due to dependency on upstream fix"

    def test_update_target_date_cannot_exceed_max_when_enforced(
        self, client, validator_token, existing_recommendation_enforced
    ):
        """RED: Should reject target date exceeding max even on update."""
        response = client.patch(
            f"/recommendations/{existing_recommendation_enforced.id}",
            headers={"Authorization": f"Bearer {validator_token}"},
            json={
                "current_target_date": "2030-12-31",
                "target_date_change_reason": "Trying to extend beyond max"
            }
        )
        assert response.status_code == 400
        assert "cannot exceed" in response.json()["detail"].lower()
```

### 7.2 Implementation: Update Create/Update Endpoints

Modify existing recommendation endpoints to call `validate_target_date()`.

### 7.3 Run Tests → GREEN

---

## Phase 8: Seed Data (TDD)

### 8.1 Write Failing Tests First

```python
class TestTimeframeConfigSeeding:
    """Phase 8: Test that seed data creates all timeframe configs."""

    def test_seed_creates_48_configs(self, db: Session):
        """RED: Should create 3 priorities × 4 tiers × 4 frequencies = 48 configs."""
        from app.seed import seed_timeframe_configs

        seed_timeframe_configs(db)

        count = db.query(RecommendationTimeframeConfig).count()
        assert count == 48

    def test_seed_correct_values_high_tier1_daily(self, db: Session, seed_taxonomies):
        """RED: HIGH + TIER_1 + DAILY should be 0 days."""
        from app.seed import seed_timeframe_configs

        seed_timeframe_configs(db)

        config = db.query(RecommendationTimeframeConfig).filter(
            RecommendationTimeframeConfig.priority_id == seed_taxonomies["HIGH"],
            RecommendationTimeframeConfig.risk_tier_id == seed_taxonomies["TIER_1"],
            RecommendationTimeframeConfig.usage_frequency_id == seed_taxonomies["DAILY"]
        ).first()

        assert config is not None
        assert config.max_days == 0

    def test_seed_correct_values_low_tier4_annually(self, db: Session, seed_taxonomies):
        """RED: LOW + TIER_4 + ANNUALLY should be 1095 days."""
        from app.seed import seed_timeframe_configs

        seed_timeframe_configs(db)

        config = db.query(RecommendationTimeframeConfig).filter(
            RecommendationTimeframeConfig.priority_id == seed_taxonomies["LOW"],
            RecommendationTimeframeConfig.risk_tier_id == seed_taxonomies["TIER_4"],
            RecommendationTimeframeConfig.usage_frequency_id == seed_taxonomies["ANNUALLY"]
        ).first()

        assert config is not None
        assert config.max_days == 1095

    def test_seed_priority_config_has_enforce_timeframes(self, db: Session):
        """RED: Priority configs should have enforce_timeframes set."""
        from app.seed import seed_priority_configs

        seed_priority_configs(db)

        configs = db.query(RecommendationPriorityConfig).all()

        for config in configs:
            priority = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == config.priority_id
            ).first()

            if priority.code == "CONSIDERATION":
                assert config.enforce_timeframes is False
            else:
                assert config.enforce_timeframes is True
```

### 8.2 Implementation: Seed Functions

Add `seed_timeframe_configs()` to `api/app/seed.py`.

### 8.3 Run Tests → GREEN

---

## Phase 9: Pydantic Schemas (TDD)

### 9.1 Write Failing Tests First

```python
class TestTimeframeSchemas:
    """Phase 9: Test Pydantic schema validation."""

    def test_timeframe_config_update_rejects_negative_days(self):
        """RED: TimeframeConfigUpdate should reject negative max_days."""
        from app.schemas.recommendation import TimeframeConfigUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TimeframeConfigUpdate(max_days=-1)

    def test_timeframe_config_update_accepts_zero(self):
        """RED: TimeframeConfigUpdate should accept zero (immediate)."""
        from app.schemas.recommendation import TimeframeConfigUpdate

        update = TimeframeConfigUpdate(max_days=0)
        assert update.max_days == 0

    def test_recommendation_create_includes_reason_field(self):
        """RED: RecommendationCreate should have target_date_change_reason."""
        from app.schemas.recommendation import RecommendationCreate

        rec = RecommendationCreate(
            model_id=1,
            validation_request_id=1,
            title="Test",
            description="Test",
            priority_id=1,
            current_target_date="2025-06-30",
            target_date_change_reason="Earlier deadline requested"
        )
        assert rec.target_date_change_reason == "Earlier deadline requested"
```

### 9.2 Implementation: Update Schemas

Add new schemas to `api/app/schemas/recommendation.py`.

### 9.3 Run Tests → GREEN

---

## Phase 10: Frontend Tests (TDD)

### 10.1 Write Failing Tests First

**File**: `web/src/components/__tests__/TimeframeConfigTable.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TimeframeConfigTable from '../TimeframeConfigTable';
import client from '../../api/client';

vi.mock('../../api/client');

describe('TimeframeConfigTable', () => {
    const mockConfigs = [
        {
            config_id: 1,
            priority: { code: 'HIGH', label: 'High' },
            risk_tier: { code: 'TIER_1', label: 'Tier 1' },
            usage_frequency: { code: 'DAILY', label: 'Daily' },
            max_days: 0
        },
        // ... more mock data
    ];

    beforeEach(() => {
        vi.mocked(client.get).mockResolvedValue({ data: mockConfigs });
    });

    it('renders timeframe configuration matrix', async () => {
        render(<TimeframeConfigTable />);

        await waitFor(() => {
            expect(screen.getByText('HIGH')).toBeInTheDocument();
            expect(screen.getByText('TIER_1')).toBeInTheDocument();
        });
    });

    it('displays correct max_days values', async () => {
        render(<TimeframeConfigTable />);

        await waitFor(() => {
            // HIGH + TIER_1 + DAILY = 0
            expect(screen.getByTestId('config-HIGH-TIER_1-DAILY')).toHaveTextContent('0');
        });
    });

    it('allows admin to edit max_days inline', async () => {
        vi.mocked(client.patch).mockResolvedValue({ data: { ...mockConfigs[0], max_days: 30 } });

        render(<TimeframeConfigTable isAdmin={true} />);

        await waitFor(() => {
            const cell = screen.getByTestId('config-HIGH-TIER_1-DAILY');
            fireEvent.click(cell);
        });

        const input = screen.getByRole('spinbutton');
        fireEvent.change(input, { target: { value: '30' } });
        fireEvent.blur(input);

        await waitFor(() => {
            expect(client.patch).toHaveBeenCalledWith('/recommendations/timeframe-config/1', { max_days: 30 });
        });
    });

    it('applies color coding based on max_days', async () => {
        render(<TimeframeConfigTable />);

        await waitFor(() => {
            const cell = screen.getByTestId('config-HIGH-TIER_1-DAILY');
            expect(cell).toHaveClass('bg-red-100'); // 0 days = red
        });
    });
});
```

**File**: `web/src/components/__tests__/RecommendationForm.test.tsx`

```typescript
describe('RecommendationForm with Timeframe', () => {
    it('calls calculate endpoint when model and priority selected', async () => {
        vi.mocked(client.post).mockResolvedValue({
            data: {
                max_days: 180,
                calculated_max_date: '2025-06-30',
                enforce_timeframes: true
            }
        });

        render(<RecommendationForm modelId={1} />);

        // Select priority
        fireEvent.change(screen.getByLabelText('Priority'), { target: { value: '2' } });

        await waitFor(() => {
            expect(client.post).toHaveBeenCalledWith(
                '/recommendations/timeframe-config/calculate',
                { model_id: 1, priority_id: 2 }
            );
        });
    });

    it('displays calculated max date as default', async () => {
        vi.mocked(client.post).mockResolvedValue({
            data: {
                calculated_max_date: '2025-06-30',
                enforce_timeframes: true
            }
        });

        render(<RecommendationForm modelId={1} />);
        fireEvent.change(screen.getByLabelText('Priority'), { target: { value: '2' } });

        await waitFor(() => {
            const dateInput = screen.getByLabelText('Target Date');
            expect(dateInput).toHaveValue('2025-06-30');
        });
    });

    it('disables dates after max when enforced', async () => {
        vi.mocked(client.post).mockResolvedValue({
            data: {
                calculated_max_date: '2025-06-30',
                enforce_timeframes: true
            }
        });

        render(<RecommendationForm modelId={1} />);
        fireEvent.change(screen.getByLabelText('Priority'), { target: { value: '2' } });

        await waitFor(() => {
            const dateInput = screen.getByLabelText('Target Date');
            expect(dateInput).toHaveAttribute('max', '2025-06-30');
        });
    });

    it('shows enforcement message when applicable', async () => {
        vi.mocked(client.post).mockResolvedValue({
            data: {
                calculated_max_date: '2025-06-30',
                enforce_timeframes: true,
                enforced_by_region: 'EMEA'
            }
        });

        render(<RecommendationForm modelId={1} />);
        fireEvent.change(screen.getByLabelText('Priority'), { target: { value: '2' } });

        await waitFor(() => {
            expect(screen.getByText(/enforced by EMEA/i)).toBeInTheDocument();
        });
    });

    it('shows reason field when date differs from max', async () => {
        vi.mocked(client.post).mockResolvedValue({
            data: {
                calculated_max_date: '2025-06-30',
                enforce_timeframes: false
            }
        });

        render(<RecommendationForm modelId={1} />);
        fireEvent.change(screen.getByLabelText('Priority'), { target: { value: '2' } });

        await waitFor(() => {
            const dateInput = screen.getByLabelText('Target Date');
            fireEvent.change(dateInput, { target: { value: '2025-03-15' } });
        });

        expect(screen.getByLabelText('Reason for Date Change')).toBeInTheDocument();
        expect(screen.getByLabelText('Reason for Date Change')).toBeRequired();
    });
});
```

### 10.2 Implementation: Frontend Components

Build components to make tests pass.

### 10.3 Run Tests → GREEN

---

## Implementation Order (TDD)

| Step | Phase | Activity | Est. Effort |
|------|-------|----------|-------------|
| 1 | 1 | Write model/schema tests (RED) | 30 min |
| 2 | 1 | Create migration + models (GREEN) | 1.5 hours |
| 3 | 2 | Write get_max_days tests (RED) | 20 min |
| 4 | 2 | Implement get_max_days (GREEN) | 30 min |
| 5 | 3 | Write enforce check tests (RED) | 30 min |
| 6 | 3 | Implement enforce check (GREEN) | 45 min |
| 7 | 4 | Write calculate max date tests (RED) | 30 min |
| 8 | 4 | Implement calculate max date (GREEN) | 30 min |
| 9 | 5 | Write validate target date tests (RED) | 45 min |
| 10 | 5 | Implement validate target date (GREEN) | 45 min |
| 11 | 6 | Write API endpoint tests (RED) | 45 min |
| 12 | 6 | Implement API endpoints (GREEN) | 1.5 hours |
| 13 | 7 | Write create/update rec tests (RED) | 30 min |
| 14 | 7 | Update create/update endpoints (GREEN) | 1 hour |
| 15 | 8 | Write seed tests (RED) | 20 min |
| 16 | 8 | Implement seed functions (GREEN) | 45 min |
| 17 | 9 | Write schema tests (RED) | 15 min |
| 18 | 9 | Update schemas (GREEN) | 30 min |
| 19 | 10 | Write frontend tests (RED) | 1 hour |
| 20 | 10 | Implement frontend components (GREEN) | 3 hours |
| 21 | ALL | Refactor pass | 1 hour |

**Total estimated effort**: ~15 hours (same as before, but tests come first)

---

## Progress Tracking (TDD)

| Phase | Task | Test Status | Impl Status | Notes |
|-------|------|-------------|-------------|-------|
| 1.1 | Model tests | [ ] RED → [ ] GREEN | [ ] | |
| 1.2 | Migration | - | [ ] | |
| 1.3 | SQLAlchemy models | - | [ ] | |
| 2.1 | get_max_days tests | [ ] RED → [ ] GREEN | [ ] | |
| 2.2 | get_max_days impl | - | [ ] | |
| 3.1 | enforce check tests | [ ] RED → [ ] GREEN | [ ] | |
| 3.2 | enforce check impl | - | [ ] | |
| 4.1 | calculate max date tests | [ ] RED → [ ] GREEN | [ ] | |
| 4.2 | calculate max date impl | - | [ ] | |
| 5.1 | validate target date tests | [ ] RED → [ ] GREEN | [ ] | |
| 5.2 | validate target date impl | - | [ ] | |
| 6.1 | API endpoint tests | [ ] RED → [ ] GREEN | [ ] | |
| 6.2 | API endpoints impl | - | [ ] | |
| 7.1 | create/update rec tests | [ ] RED → [ ] GREEN | [ ] | |
| 7.2 | create/update rec impl | - | [ ] | |
| 8.1 | seed tests | [ ] RED → [ ] GREEN | [ ] | |
| 8.2 | seed impl | - | [ ] | |
| 9.1 | schema tests | [ ] RED → [ ] GREEN | [ ] | |
| 9.2 | schema impl | - | [ ] | |
| 10.1 | frontend tests | [ ] RED → [ ] GREEN | [ ] | |
| 10.2 | frontend impl | - | [ ] | |

---

## Test Fixtures Required

**File**: `api/tests/conftest.py` additions

```python
@pytest.fixture
def seed_taxonomies(db: Session):
    """Seed required taxonomies and return ID mappings."""
    # Create Recommendation Priority, Model Risk Tier, Usage Frequency taxonomies
    # Return dict mapping codes to value_ids
    pass

@pytest.fixture
def seed_timeframe_configs(db: Session, seed_taxonomies):
    """Seed all 48 timeframe configurations."""
    pass

@pytest.fixture
def seed_priority_configs(db: Session, seed_taxonomies):
    """Seed priority configs with enforce_timeframes."""
    pass

@pytest.fixture
def model_with_tier1_daily(db: Session, seed_taxonomies):
    """Create model with TIER_1 risk and DAILY frequency."""
    pass

@pytest.fixture
def model_with_tier2_monthly(db: Session, seed_taxonomies):
    """Create model with TIER_2 risk and MONTHLY frequency."""
    pass

@pytest.fixture
def model_with_regions(db: Session):
    """Create model deployed to multiple regions."""
    pass

@pytest.fixture
def regional_override_enforce_true(db: Session, seed_taxonomies, model_with_regions):
    """Create regional override with enforce_timeframes=True."""
    pass

@pytest.fixture
def regional_override_enforce_false(db: Session, seed_taxonomies, model_with_single_region):
    """Create regional override with enforce_timeframes=False."""
    pass

@pytest.fixture
def mixed_regional_overrides(db: Session, seed_taxonomies, model_with_multiple_regions):
    """Create multiple regional overrides with mixed enforcement."""
    pass
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior | Test Coverage |
|----------|-------------------|---------------|
| Model missing risk_tier_id | Error: "Model must have risk tier set" | `test_calculate_max_date_model_missing_risk_tier` |
| Model missing usage_frequency_id | Error: "Model must have usage frequency set" | `test_calculate_max_date_model_missing_usage_frequency` |
| No timeframe config for combination | Default to 365 days | `test_calculate_max_date_defaults_to_365_if_no_config` |
| Target date in past | Error: "Target date cannot be in the past" | `test_validate_rejects_past_date` |
| max_days = 0 | Same-day resolution required | `test_calculate_max_date_basic` |
| Regional override NULL | Inherits from base config | `test_null_override_inherits_base` |
| Multiple regions, mixed overrides | Most restrictive wins | `test_most_restrictive_wins_multi_region` |
| CONSIDERATION priority | No enforcement, no date required | `test_consideration_priority_no_action_plan_no_date_required` |

---

## Rollback Plan

If issues arise:

1. **Database**: Run `alembic downgrade -1` to remove new columns/table
2. **API**: New endpoints are additive, can be disabled without breaking existing functionality
3. **Frontend**: Feature can be hidden behind feature flag
4. **Seed data**: Timeframe configs can be deleted without affecting existing recommendations

---

## Future Enhancements

1. **Email notifications** when target date approaching (7 days, 1 day warnings)
2. **Target date extension requests** with approval workflow
3. **Bulk update** of timeframe configs via CSV import
4. **Dashboard widget** showing recommendations by time-to-due
5. **SLA reporting** on target date compliance rates
