"""
TDD Tests for Recommendation Timeframe Enforcement.

Phase 1: Database Schema & Models

These tests are written BEFORE implementation.
Run order: Write test -> See RED -> Implement -> See GREEN -> Refactor
"""
import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.user import User
from app.models.model import Model
from app.models.region import Region
from app.core.security import get_password_hash


# ============================================================================
# Test Fixtures for Phase 1
# ============================================================================

@pytest.fixture
def timeframe_taxonomies(db_session):
    """Create required taxonomies for timeframe testing."""
    # Recommendation Priority taxonomy
    rec_priority_tax = Taxonomy(name="Recommendation Priority", is_system=True)
    db_session.add(rec_priority_tax)
    db_session.flush()

    high = TaxonomyValue(
        taxonomy_id=rec_priority_tax.taxonomy_id,
        code="HIGH", label="High", sort_order=1
    )
    medium = TaxonomyValue(
        taxonomy_id=rec_priority_tax.taxonomy_id,
        code="MEDIUM", label="Medium", sort_order=2
    )
    low = TaxonomyValue(
        taxonomy_id=rec_priority_tax.taxonomy_id,
        code="LOW", label="Low", sort_order=3
    )
    consideration = TaxonomyValue(
        taxonomy_id=rec_priority_tax.taxonomy_id,
        code="CONSIDERATION", label="Consideration", sort_order=4
    )

    # Model Risk Tier taxonomy
    risk_tier_tax = Taxonomy(name="Model Risk Tier", is_system=True)
    db_session.add(risk_tier_tax)
    db_session.flush()

    tier1 = TaxonomyValue(
        taxonomy_id=risk_tier_tax.taxonomy_id,
        code="TIER_1", label="Tier 1 - High Risk", sort_order=1
    )
    tier2 = TaxonomyValue(
        taxonomy_id=risk_tier_tax.taxonomy_id,
        code="TIER_2", label="Tier 2 - Medium Risk", sort_order=2
    )
    tier3 = TaxonomyValue(
        taxonomy_id=risk_tier_tax.taxonomy_id,
        code="TIER_3", label="Tier 3 - Low Risk", sort_order=3
    )
    tier4 = TaxonomyValue(
        taxonomy_id=risk_tier_tax.taxonomy_id,
        code="TIER_4", label="Tier 4 - Very Low Risk", sort_order=4
    )

    # Model Usage Frequency taxonomy
    freq_tax = Taxonomy(name="Model Usage Frequency", is_system=True)
    db_session.add(freq_tax)
    db_session.flush()

    daily = TaxonomyValue(
        taxonomy_id=freq_tax.taxonomy_id,
        code="DAILY", label="Daily", sort_order=1
    )
    monthly = TaxonomyValue(
        taxonomy_id=freq_tax.taxonomy_id,
        code="MONTHLY", label="Monthly", sort_order=2
    )
    quarterly = TaxonomyValue(
        taxonomy_id=freq_tax.taxonomy_id,
        code="QUARTERLY", label="Quarterly", sort_order=3
    )
    annually = TaxonomyValue(
        taxonomy_id=freq_tax.taxonomy_id,
        code="ANNUALLY", label="Annually", sort_order=4
    )

    # Recommendation Status taxonomy (needed for Recommendation model)
    rec_status_tax = Taxonomy(name="Recommendation Status", is_system=True)
    db_session.add(rec_status_tax)
    db_session.flush()

    draft_status = TaxonomyValue(
        taxonomy_id=rec_status_tax.taxonomy_id,
        code="REC_DRAFT", label="Draft", sort_order=1
    )

    db_session.add_all([
        high, medium, low, consideration,
        tier1, tier2, tier3, tier4,
        daily, monthly, quarterly, annually,
        draft_status
    ])
    db_session.commit()

    return {
        "recommendation_priority": {
            "HIGH": high.value_id,
            "MEDIUM": medium.value_id,
            "LOW": low.value_id,
            "CONSIDERATION": consideration.value_id
        },
        "model_risk_tier": {
            "TIER_1": tier1.value_id,
            "TIER_2": tier2.value_id,
            "TIER_3": tier3.value_id,
            "TIER_4": tier4.value_id
        },
        "usage_frequency": {
            "DAILY": daily.value_id,
            "MONTHLY": monthly.value_id,
            "QUARTERLY": quarterly.value_id,
            "ANNUALLY": annually.value_id
        },
        "recommendation_status": {
            "REC_DRAFT": draft_status.value_id
        }
    }


@pytest.fixture
def test_region(db_session):
    """Create a test region."""
    region = Region(code="US", name="United States")
    db_session.add(region)
    db_session.commit()
    return region


# ============================================================================
# Phase 1: Test RecommendationTimeframeConfig Model
# ============================================================================

class TestTimeframeConfigModel:
    """Phase 1: Test that the RecommendationTimeframeConfig model exists and has correct structure."""

    def test_timeframe_config_model_exists(self, db_session):
        """RED: Model class should exist and be importable."""
        from app.models.recommendation import RecommendationTimeframeConfig
        assert RecommendationTimeframeConfig is not None

    def test_timeframe_config_has_required_fields(self, db_session, timeframe_taxonomies):
        """RED: Model should have priority_id, risk_tier_id, usage_frequency_id, max_days."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = RecommendationTimeframeConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"],
            max_days=90
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        assert config.config_id is not None
        assert config.priority_id == timeframe_taxonomies["recommendation_priority"]["HIGH"]
        assert config.risk_tier_id == timeframe_taxonomies["model_risk_tier"]["TIER_1"]
        assert config.usage_frequency_id == timeframe_taxonomies["usage_frequency"]["DAILY"]
        assert config.max_days == 90

    def test_timeframe_config_accepts_zero_max_days(self, db_session, timeframe_taxonomies):
        """RED: max_days=0 should be valid (immediate resolution required)."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = RecommendationTimeframeConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"],
            max_days=0
        )
        db_session.add(config)
        db_session.commit()

        assert config.max_days == 0

    def test_timeframe_config_has_description_field(self, db_session, timeframe_taxonomies):
        """RED: Model should have optional description field."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = RecommendationTimeframeConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"],
            max_days=90,
            description="High priority, Tier 1 risk, Daily frequency"
        )
        db_session.add(config)
        db_session.commit()

        assert config.description == "High priority, Tier 1 risk, Daily frequency"

    def test_timeframe_config_has_timestamps(self, db_session, timeframe_taxonomies):
        """RED: Model should have created_at and updated_at timestamps."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = RecommendationTimeframeConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"],
            max_days=90
        )
        db_session.add(config)
        db_session.commit()

        assert config.created_at is not None
        assert config.updated_at is not None

    def test_timeframe_config_unique_constraint(self, db_session, timeframe_taxonomies):
        """RED: Should enforce unique constraint on priority+risk+frequency."""
        from app.models.recommendation import RecommendationTimeframeConfig

        priority_id = timeframe_taxonomies["recommendation_priority"]["HIGH"]
        risk_tier_id = timeframe_taxonomies["model_risk_tier"]["TIER_1"]
        freq_id = timeframe_taxonomies["usage_frequency"]["DAILY"]

        config1 = RecommendationTimeframeConfig(
            priority_id=priority_id,
            risk_tier_id=risk_tier_id,
            usage_frequency_id=freq_id,
            max_days=90
        )
        db_session.add(config1)
        db_session.commit()

        # Duplicate should fail
        config2 = RecommendationTimeframeConfig(
            priority_id=priority_id,
            risk_tier_id=risk_tier_id,
            usage_frequency_id=freq_id,
            max_days=180
        )
        db_session.add(config2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_timeframe_config_has_relationships(self, db_session, timeframe_taxonomies):
        """RED: Model should have relationships to TaxonomyValue."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = RecommendationTimeframeConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"],
            max_days=90
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        # Should have relationship properties
        assert config.priority is not None
        assert config.priority.code == "HIGH"
        assert config.risk_tier is not None
        assert config.risk_tier.code == "TIER_1"
        assert config.usage_frequency is not None
        assert config.usage_frequency.code == "DAILY"


# ============================================================================
# Phase 1: Test enforce_timeframes on RecommendationPriorityConfig
# ============================================================================

class TestPriorityConfigEnforceTimeframes:
    """Phase 1: Test enforce_timeframes field on RecommendationPriorityConfig."""

    def test_priority_config_has_enforce_timeframes_field(self, db_session, timeframe_taxonomies):
        """RED: RecommendationPriorityConfig should have enforce_timeframes boolean field."""
        from app.models.recommendation import RecommendationPriorityConfig

        config = RecommendationPriorityConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            requires_action_plan=True,
            requires_final_approval=True,
            enforce_timeframes=True
        )
        db_session.add(config)
        db_session.commit()

        assert config.enforce_timeframes is True

    def test_priority_config_enforce_timeframes_can_be_false(self, db_session, timeframe_taxonomies):
        """RED: enforce_timeframes can be explicitly set to False."""
        from app.models.recommendation import RecommendationPriorityConfig

        config = RecommendationPriorityConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["CONSIDERATION"],
            requires_action_plan=False,
            requires_final_approval=False,
            enforce_timeframes=False
        )
        db_session.add(config)
        db_session.commit()

        assert config.enforce_timeframes is False

    def test_priority_config_enforce_timeframes_defaults_true(self, db_session, timeframe_taxonomies):
        """RED: enforce_timeframes should default to True when not specified."""
        from app.models.recommendation import RecommendationPriorityConfig

        config = RecommendationPriorityConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"]["MEDIUM"],
            requires_action_plan=True,
            requires_final_approval=True
            # enforce_timeframes not specified - should default to True
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        assert config.enforce_timeframes is True


# ============================================================================
# Phase 1: Test enforce_timeframes on RecommendationPriorityRegionalOverride
# ============================================================================

class TestRegionalOverrideEnforceTimeframes:
    """Phase 1: Test enforce_timeframes field on RecommendationPriorityRegionalOverride."""

    def test_regional_override_has_enforce_timeframes_field(
        self, db_session, timeframe_taxonomies, test_region
    ):
        """RED: RecommendationPriorityRegionalOverride should have nullable enforce_timeframes field."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            region_id=test_region.region_id,
            enforce_timeframes=True
        )
        db_session.add(override)
        db_session.commit()

        assert override.enforce_timeframes is True

    def test_regional_override_enforce_timeframes_can_be_false(
        self, db_session, timeframe_taxonomies, test_region
    ):
        """RED: enforce_timeframes can be explicitly set to False."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            region_id=test_region.region_id,
            enforce_timeframes=False
        )
        db_session.add(override)
        db_session.commit()

        assert override.enforce_timeframes is False

    def test_regional_override_enforce_timeframes_nullable(
        self, db_session, timeframe_taxonomies, test_region
    ):
        """RED: enforce_timeframes can be None (inherit from base config)."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            region_id=test_region.region_id,
            enforce_timeframes=None  # Explicitly NULL
        )
        db_session.add(override)
        db_session.commit()

        assert override.enforce_timeframes is None

    def test_regional_override_enforce_timeframes_defaults_null(
        self, db_session, timeframe_taxonomies, test_region
    ):
        """RED: enforce_timeframes should default to None when not specified."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=timeframe_taxonomies["recommendation_priority"]["LOW"],
            region_id=test_region.region_id
            # enforce_timeframes not specified - should be None
        )
        db_session.add(override)
        db_session.commit()

        assert override.enforce_timeframes is None


# ============================================================================
# Phase 1: Test target_date_change_reason on Recommendation
# ============================================================================

class TestRecommendationTargetDateReason:
    """Phase 1: Test target_date_change_reason field on Recommendation model."""

    def test_recommendation_has_target_date_change_reason_field(
        self, db_session, timeframe_taxonomies, lob_hierarchy
    ):
        """RED: Recommendation should have target_date_change_reason text field."""
        from app.models.recommendation import Recommendation

        # Create required user
        user = User(
            email="validator@test.com",
            full_name="Validator",
            password_hash=get_password_hash("test123"),
            role="Validator",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.flush()

        # Create required model (with usage_frequency_id)
        model = Model(
            model_name="Test Model",
            description="Test",
            development_type="In-House",
            owner_id=user.user_id,
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation with target_date_change_reason
        rec = Recommendation(
            recommendation_code="REC-2025-00001",
            model_id=model.model_id,
            title="Test Recommendation",
            description="Test description",
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            current_status_id=timeframe_taxonomies["recommendation_status"]["REC_DRAFT"],
            created_by_id=user.user_id,
            assigned_to_id=user.user_id,
            original_target_date=date(2025, 6, 30),
            current_target_date=date(2025, 5, 15),
            target_date_change_reason="Accelerated timeline per management request"
        )
        db_session.add(rec)
        db_session.commit()

        assert rec.target_date_change_reason == "Accelerated timeline per management request"

    def test_recommendation_target_date_change_reason_nullable(
        self, db_session, timeframe_taxonomies, lob_hierarchy
    ):
        """RED: target_date_change_reason should be nullable."""
        from app.models.recommendation import Recommendation

        # Create required user
        user = User(
            email="validator2@test.com",
            full_name="Validator 2",
            password_hash=get_password_hash("test123"),
            role="Validator",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.flush()

        # Create required model (with usage_frequency_id)
        model = Model(
            model_name="Test Model 2",
            description="Test",
            development_type="In-House",
            owner_id=user.user_id,
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["MONTHLY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation without target_date_change_reason
        rec = Recommendation(
            recommendation_code="REC-2025-00002",
            model_id=model.model_id,
            title="Test Recommendation",
            description="Test description",
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            current_status_id=timeframe_taxonomies["recommendation_status"]["REC_DRAFT"],
            created_by_id=user.user_id,
            assigned_to_id=user.user_id,
            original_target_date=date(2025, 6, 30),
            current_target_date=date(2025, 6, 30)
            # target_date_change_reason not specified - should be None
        )
        db_session.add(rec)
        db_session.commit()

        assert rec.target_date_change_reason is None

    def test_recommendation_target_date_change_reason_can_be_updated(
        self, db_session, timeframe_taxonomies, lob_hierarchy
    ):
        """RED: target_date_change_reason should be updatable."""
        from app.models.recommendation import Recommendation

        # Create required user
        user = User(
            email="validator3@test.com",
            full_name="Validator 3",
            password_hash=get_password_hash("test123"),
            role="Validator",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.flush()

        # Create required model (with usage_frequency_id)
        model = Model(
            model_name="Test Model 3",
            description="Test",
            development_type="In-House",
            owner_id=user.user_id,
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["QUARTERLY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation
        rec = Recommendation(
            recommendation_code="REC-2025-00003",
            model_id=model.model_id,
            title="Test Recommendation",
            description="Test description",
            priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
            current_status_id=timeframe_taxonomies["recommendation_status"]["REC_DRAFT"],
            created_by_id=user.user_id,
            assigned_to_id=user.user_id,
            original_target_date=date(2025, 6, 30),
            current_target_date=date(2025, 6, 30)
        )
        db_session.add(rec)
        db_session.commit()

        # Update the reason
        rec.current_target_date = date(2025, 8, 15)
        rec.target_date_change_reason = "Extended due to resource constraints"
        db_session.commit()
        db_session.refresh(rec)

        assert rec.target_date_change_reason == "Extended due to resource constraints"
        assert rec.current_target_date == date(2025, 8, 15)


# ============================================================================
# Phase 2: Test get_max_days_for_recommendation Function
# ============================================================================

@pytest.fixture
def seed_timeframe_configs(db_session, timeframe_taxonomies):
    """Seed timeframe configurations based on REC_TIMES.json data."""
    from app.models.recommendation import RecommendationTimeframeConfig

    # Mapping from REC_TIMES.json structure:
    # high_priority -> HIGH, medium_priority -> MEDIUM, low_priority -> LOW
    # high_inherent_risk -> TIER_1, medium_inherent_risk -> TIER_2,
    # low_inherent_risk -> TIER_3, very_low_inherent_risk -> TIER_4

    timeframe_data = {
        # HIGH priority
        ("HIGH", "TIER_1", "DAILY"): 0,
        ("HIGH", "TIER_1", "MONTHLY"): 0,
        ("HIGH", "TIER_1", "QUARTERLY"): 90,
        ("HIGH", "TIER_1", "ANNUALLY"): 90,
        ("HIGH", "TIER_2", "DAILY"): 0,
        ("HIGH", "TIER_2", "MONTHLY"): 90,
        ("HIGH", "TIER_2", "QUARTERLY"): 90,
        ("HIGH", "TIER_2", "ANNUALLY"): 180,
        ("HIGH", "TIER_3", "DAILY"): 90,
        ("HIGH", "TIER_3", "MONTHLY"): 90,
        ("HIGH", "TIER_3", "QUARTERLY"): 180,
        ("HIGH", "TIER_3", "ANNUALLY"): 180,
        ("HIGH", "TIER_4", "DAILY"): 90,
        ("HIGH", "TIER_4", "MONTHLY"): 90,
        ("HIGH", "TIER_4", "QUARTERLY"): 180,
        ("HIGH", "TIER_4", "ANNUALLY"): 180,

        # MEDIUM priority
        ("MEDIUM", "TIER_1", "DAILY"): 180,
        ("MEDIUM", "TIER_1", "MONTHLY"): 180,
        ("MEDIUM", "TIER_1", "QUARTERLY"): 180,
        ("MEDIUM", "TIER_1", "ANNUALLY"): 180,
        ("MEDIUM", "TIER_2", "DAILY"): 180,
        ("MEDIUM", "TIER_2", "MONTHLY"): 180,
        ("MEDIUM", "TIER_2", "QUARTERLY"): 180,
        ("MEDIUM", "TIER_2", "ANNUALLY"): 365,
        ("MEDIUM", "TIER_3", "DAILY"): 180,
        ("MEDIUM", "TIER_3", "MONTHLY"): 180,
        ("MEDIUM", "TIER_3", "QUARTERLY"): 365,
        ("MEDIUM", "TIER_3", "ANNUALLY"): 365,
        ("MEDIUM", "TIER_4", "DAILY"): 180,
        ("MEDIUM", "TIER_4", "MONTHLY"): 180,
        ("MEDIUM", "TIER_4", "QUARTERLY"): 365,
        ("MEDIUM", "TIER_4", "ANNUALLY"): 365,

        # LOW priority
        ("LOW", "TIER_1", "DAILY"): 365,
        ("LOW", "TIER_1", "MONTHLY"): 365,
        ("LOW", "TIER_1", "QUARTERLY"): 365,
        ("LOW", "TIER_1", "ANNUALLY"): 365,
        ("LOW", "TIER_2", "DAILY"): 365,
        ("LOW", "TIER_2", "MONTHLY"): 365,
        ("LOW", "TIER_2", "QUARTERLY"): 365,
        ("LOW", "TIER_2", "ANNUALLY"): 1095,
        ("LOW", "TIER_3", "DAILY"): 365,
        ("LOW", "TIER_3", "MONTHLY"): 365,
        ("LOW", "TIER_3", "QUARTERLY"): 1095,
        ("LOW", "TIER_3", "ANNUALLY"): 1095,
        ("LOW", "TIER_4", "DAILY"): 365,
        ("LOW", "TIER_4", "MONTHLY"): 365,
        ("LOW", "TIER_4", "QUARTERLY"): 1095,
        ("LOW", "TIER_4", "ANNUALLY"): 1095,
    }

    configs = []
    for (priority, risk, freq), max_days in timeframe_data.items():
        config = RecommendationTimeframeConfig(
            priority_id=timeframe_taxonomies["recommendation_priority"][priority],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"][risk],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"][freq],
            max_days=max_days
        )
        configs.append(config)

    db_session.add_all(configs)
    db_session.commit()

    return timeframe_taxonomies


class TestGetMaxDaysForRecommendation:
    """Phase 2: Test max days lookup function."""

    def test_get_max_days_returns_correct_value_high_tier1_daily(
        self, db_session, seed_timeframe_configs
    ):
        """RED: HIGH priority + TIER_1 + DAILY = 0 days (immediate resolution)."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["HIGH"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["DAILY"]
        )
        assert max_days == 0

    def test_get_max_days_medium_priority_tier2_monthly(
        self, db_session, seed_timeframe_configs
    ):
        """RED: MEDIUM priority + TIER_2 + MONTHLY = 180 days."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["MEDIUM"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_2"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["MONTHLY"]
        )
        assert max_days == 180

    def test_get_max_days_low_priority_tier4_annually(
        self, db_session, seed_timeframe_configs
    ):
        """RED: LOW priority + TIER_4 + ANNUALLY = 1095 days (3 years)."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["LOW"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_4"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["ANNUALLY"]
        )
        assert max_days == 1095

    def test_get_max_days_high_priority_tier3_quarterly(
        self, db_session, seed_timeframe_configs
    ):
        """RED: HIGH priority + TIER_3 + QUARTERLY = 180 days."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["HIGH"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_3"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["QUARTERLY"]
        )
        assert max_days == 180

    def test_get_max_days_returns_none_if_not_configured(
        self, db_session, timeframe_taxonomies
    ):
        """RED: Should return None if no config exists for combination."""
        from app.api.recommendations import get_max_days_for_recommendation

        # CONSIDERATION priority has no timeframe configs
        max_days = get_max_days_for_recommendation(
            db_session,
            priority_id=timeframe_taxonomies["recommendation_priority"]["CONSIDERATION"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"]
        )
        assert max_days is None

    def test_get_max_days_returns_none_for_nonexistent_ids(
        self, db_session, seed_timeframe_configs
    ):
        """RED: Should return None for non-existent taxonomy IDs."""
        from app.api.recommendations import get_max_days_for_recommendation

        max_days = get_max_days_for_recommendation(
            db_session,
            priority_id=99999,
            risk_tier_id=99999,
            usage_frequency_id=99999
        )
        assert max_days is None


# ============================================================================
# Phase 3: Test is_timeframe_enforced Function
# ============================================================================

@pytest.fixture
def enforcement_setup(db_session, timeframe_taxonomies, lob_hierarchy):
    """Set up data for testing is_timeframe_enforced function."""
    from app.models.recommendation import (
        Recommendation, RecommendationPriorityConfig, RecommendationPriorityRegionalOverride
    )
    from app.models.region import Region
    from app.models.model_region import ModelRegion

    # Get status ID for DRAFT
    status_taxonomy = db_session.query(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()
    draft_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == status_taxonomy.taxonomy_id,
        TaxonomyValue.code == "REC_DRAFT"
    ).first()

    # Create user
    user = User(
        email="enforce_test@test.com",
        full_name="Enforce Tester",
        password_hash=get_password_hash("test123"),
        role="Validator",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(user)
    db_session.flush()

    # Create regions
    region_us = Region(
        code="US",
        name="United States",
        requires_regional_approval=True
    )
    region_eu = Region(
        code="EU",
        name="European Union",
        requires_regional_approval=True
    )
    region_apac = Region(
        code="APAC",
        name="Asia Pacific",
        requires_regional_approval=False
    )
    db_session.add_all([region_us, region_eu, region_apac])
    db_session.flush()

    # Create priority configs with different enforce_timeframes settings
    # HIGH priority: enforce_timeframes = True (default)
    high_config = RecommendationPriorityConfig(
        priority_id=timeframe_taxonomies["recommendation_priority"]["HIGH"],
        requires_action_plan=True,
        requires_final_approval=True,
        enforce_timeframes=True
    )
    # MEDIUM priority: enforce_timeframes = True
    medium_config = RecommendationPriorityConfig(
        priority_id=timeframe_taxonomies["recommendation_priority"]["MEDIUM"],
        requires_action_plan=True,
        requires_final_approval=True,
        enforce_timeframes=True
    )
    # LOW priority: enforce_timeframes = False (advisory only)
    low_config = RecommendationPriorityConfig(
        priority_id=timeframe_taxonomies["recommendation_priority"]["LOW"],
        requires_action_plan=True,
        requires_final_approval=False,
        enforce_timeframes=False
    )
    # CONSIDERATION: enforce_timeframes = False
    consideration_config = RecommendationPriorityConfig(
        priority_id=timeframe_taxonomies["recommendation_priority"]["CONSIDERATION"],
        requires_action_plan=False,
        requires_final_approval=False,
        enforce_timeframes=False
    )
    db_session.add_all([high_config, medium_config, low_config, consideration_config])
    db_session.flush()

    return {
        "taxonomies": timeframe_taxonomies,
        "user": user,
        "regions": {
            "US": region_us,
            "EU": region_eu,
            "APAC": region_apac
        },
        "priority_configs": {
            "HIGH": high_config,
            "MEDIUM": medium_config,
            "LOW": low_config,
            "CONSIDERATION": consideration_config
        },
        "draft_status_id": draft_status.value_id
    }


class TestIsTimeframeEnforced:
    """Phase 3: Test enforcement check function."""

    def test_is_timeframe_enforced_returns_true_for_enforced_priority(
        self, db_session, enforcement_setup
    ):
        """RED: HIGH priority with enforce_timeframes=True should return True."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation

        # Create model (no regions)
        model = Model(
            model_name="Test Model Enforced",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation with HIGH priority
        rec = Recommendation(
            recommendation_code="REC-2025-ENF01",
            model_id=model.model_id,
            title="Test Enforced Rec",
            description="Test",
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30)
        )
        db_session.add(rec)
        db_session.flush()

        result = is_timeframe_enforced(db_session, rec)
        assert result is True

    def test_is_timeframe_enforced_returns_false_for_advisory_priority(
        self, db_session, enforcement_setup
    ):
        """RED: LOW priority with enforce_timeframes=False should return False."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation

        # Create model (no regions)
        model = Model(
            model_name="Test Model Advisory",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation with LOW priority
        rec = Recommendation(
            recommendation_code="REC-2025-ADV01",
            model_id=model.model_id,
            title="Test Advisory Rec",
            description="Test",
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["LOW"],
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=365),
            current_target_date=date.today() + timedelta(days=365)
        )
        db_session.add(rec)
        db_session.flush()

        result = is_timeframe_enforced(db_session, rec)
        assert result is False

    def test_is_timeframe_enforced_regional_override_true_wins(
        self, db_session, enforcement_setup
    ):
        """RED: If ANY regional override says True, enforcement applies (most restrictive wins)."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.models.model_region import ModelRegion

        # Create model
        model = Model(
            model_name="Test Model Regional Override True",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Deploy model to US and EU regions
        mr_us = ModelRegion(
            model_id=model.model_id,
            region_id=enforcement_setup["regions"]["US"].region_id
        )
        mr_eu = ModelRegion(
            model_id=model.model_id,
            region_id=enforcement_setup["regions"]["EU"].region_id
        )
        db_session.add_all([mr_us, mr_eu])
        db_session.flush()

        # Create regional overrides:
        # US: enforce_timeframes = False
        # EU: enforce_timeframes = True (should win - most restrictive)
        override_us = RecommendationPriorityRegionalOverride(
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["LOW"],
            region_id=enforcement_setup["regions"]["US"].region_id,
            enforce_timeframes=False
        )
        override_eu = RecommendationPriorityRegionalOverride(
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["LOW"],
            region_id=enforcement_setup["regions"]["EU"].region_id,
            enforce_timeframes=True  # This should make it enforced
        )
        db_session.add_all([override_us, override_eu])
        db_session.flush()

        # Create recommendation with LOW priority (base config = False)
        rec = Recommendation(
            recommendation_code="REC-2025-REG01",
            model_id=model.model_id,
            title="Test Regional Override True",
            description="Test",
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["LOW"],
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=365),
            current_target_date=date.today() + timedelta(days=365)
        )
        db_session.add(rec)
        db_session.flush()

        # Even though base config is False and US override is False,
        # EU override is True - most restrictive wins
        result = is_timeframe_enforced(db_session, rec)
        assert result is True

    def test_is_timeframe_enforced_all_overrides_false_wins(
        self, db_session, enforcement_setup
    ):
        """RED: If ALL regional overrides explicitly say False, enforcement is off."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.models.model_region import ModelRegion

        # Create model
        model = Model(
            model_name="Test Model All Overrides False",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Deploy model to US and EU regions
        mr_us = ModelRegion(
            model_id=model.model_id,
            region_id=enforcement_setup["regions"]["US"].region_id
        )
        mr_eu = ModelRegion(
            model_id=model.model_id,
            region_id=enforcement_setup["regions"]["EU"].region_id
        )
        db_session.add_all([mr_us, mr_eu])
        db_session.flush()

        # Create regional overrides - both explicitly False
        override_us = RecommendationPriorityRegionalOverride(
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            region_id=enforcement_setup["regions"]["US"].region_id,
            enforce_timeframes=False
        )
        override_eu = RecommendationPriorityRegionalOverride(
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            region_id=enforcement_setup["regions"]["EU"].region_id,
            enforce_timeframes=False
        )
        db_session.add_all([override_us, override_eu])
        db_session.flush()

        # Create recommendation with HIGH priority (base config = True)
        rec = Recommendation(
            recommendation_code="REC-2025-REG02",
            model_id=model.model_id,
            title="Test All Overrides False",
            description="Test",
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30)
        )
        db_session.add(rec)
        db_session.flush()

        # Both regions explicitly say False, so enforcement is off
        result = is_timeframe_enforced(db_session, rec)
        assert result is False

    def test_is_timeframe_enforced_null_override_inherits_from_base(
        self, db_session, enforcement_setup
    ):
        """RED: NULL regional override should inherit from base config."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.models.model_region import ModelRegion

        # Create model
        model = Model(
            model_name="Test Model Null Override",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Deploy model to US region
        mr_us = ModelRegion(
            model_id=model.model_id,
            region_id=enforcement_setup["regions"]["US"].region_id
        )
        db_session.add(mr_us)
        db_session.flush()

        # Create regional override with NULL enforce_timeframes (inherit from base)
        override_us = RecommendationPriorityRegionalOverride(
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            region_id=enforcement_setup["regions"]["US"].region_id,
            enforce_timeframes=None  # NULL = inherit from base
        )
        db_session.add(override_us)
        db_session.flush()

        # Create recommendation with HIGH priority (base config = True)
        rec = Recommendation(
            recommendation_code="REC-2025-REG03",
            model_id=model.model_id,
            title="Test Null Override",
            description="Test",
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30)
        )
        db_session.add(rec)
        db_session.flush()

        # NULL override inherits from base config (True)
        result = is_timeframe_enforced(db_session, rec)
        assert result is True

    def test_is_timeframe_enforced_no_regions_uses_base_config(
        self, db_session, enforcement_setup
    ):
        """RED: Model with no regions should use base config only."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation

        # Create model with no region deployments
        model = Model(
            model_name="Test Model No Regions",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation with MEDIUM priority (base config = True)
        rec = Recommendation(
            recommendation_code="REC-2025-NOREG01",
            model_id=model.model_id,
            title="Test No Regions",
            description="Test",
            priority_id=enforcement_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=180),
            current_target_date=date.today() + timedelta(days=180)
        )
        db_session.add(rec)
        db_session.flush()

        # No regions, so uses base config (True)
        result = is_timeframe_enforced(db_session, rec)
        assert result is True

    def test_is_timeframe_enforced_defaults_true_when_no_config(
        self, db_session, enforcement_setup
    ):
        """RED: Should default to True if no priority config exists (fail safe)."""
        from app.api.recommendations import is_timeframe_enforced
        from app.models.recommendation import Recommendation
        from app.models.taxonomy import Taxonomy, TaxonomyValue

        # Create a new priority that has no config
        priority_taxonomy = db_session.query(Taxonomy).filter(
            Taxonomy.name == "Recommendation Priority"
        ).first()
        new_priority = TaxonomyValue(
            taxonomy_id=priority_taxonomy.taxonomy_id,
            code="CRITICAL",
            label="Critical",
            sort_order=0
        )
        db_session.add(new_priority)
        db_session.flush()

        # Create model
        model = Model(
            model_name="Test Model No Config",
            description="Test",
            development_type="In-House",
            owner_id=enforcement_setup["user"].user_id,
            usage_frequency_id=enforcement_setup["taxonomies"]["usage_frequency"]["DAILY"]
        )
        db_session.add(model)
        db_session.flush()

        # Create recommendation with new priority (no config exists)
        rec = Recommendation(
            recommendation_code="REC-2025-NOCFG01",
            model_id=model.model_id,
            title="Test No Config",
            description="Test",
            priority_id=new_priority.value_id,
            current_status_id=enforcement_setup["draft_status_id"],
            created_by_id=enforcement_setup["user"].user_id,
            assigned_to_id=enforcement_setup["user"].user_id,
            original_target_date=date.today() + timedelta(days=30),
            current_target_date=date.today() + timedelta(days=30)
        )
        db_session.add(rec)
        db_session.flush()

        # No config = default to True (fail safe - enforce by default)
        result = is_timeframe_enforced(db_session, rec)
        assert result is True


# ============================================================================
# Phase 4: Test calculate_max_target_date Function
# ============================================================================

class TestCalculateMaxTargetDate:
    """Phase 4: Test max target date calculation function."""

    def test_calculate_max_target_date_immediate_resolution(
        self, db_session, seed_timeframe_configs
    ):
        """RED: HIGH/TIER_1/DAILY = 0 days means target_date = creation_date."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 6, 15)
        max_target = calculate_max_target_date(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["HIGH"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["DAILY"],
            creation_date=creation_date
        )
        # max_days = 0 means immediate resolution
        assert max_target == date(2025, 6, 15)

    def test_calculate_max_target_date_90_days(
        self, db_session, seed_timeframe_configs
    ):
        """RED: HIGH/TIER_1/QUARTERLY = 90 days from creation date."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        max_target = calculate_max_target_date(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["HIGH"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["QUARTERLY"],
            creation_date=creation_date
        )
        # 90 days from Jan 1, 2025 = April 1, 2025
        assert max_target == date(2025, 4, 1)

    def test_calculate_max_target_date_180_days(
        self, db_session, seed_timeframe_configs
    ):
        """RED: MEDIUM/TIER_1/DAILY = 180 days from creation date."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        max_target = calculate_max_target_date(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["MEDIUM"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["DAILY"],
            creation_date=creation_date
        )
        # 180 days from Jan 1, 2025 = June 30, 2025
        assert max_target == date(2025, 6, 30)

    def test_calculate_max_target_date_365_days(
        self, db_session, seed_timeframe_configs
    ):
        """RED: LOW/TIER_1/DAILY = 365 days from creation date."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        max_target = calculate_max_target_date(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["LOW"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["DAILY"],
            creation_date=creation_date
        )
        # 365 days from Jan 1, 2025 = Jan 1, 2026
        assert max_target == date(2026, 1, 1)

    def test_calculate_max_target_date_1095_days(
        self, db_session, seed_timeframe_configs
    ):
        """RED: LOW/TIER_4/ANNUALLY = 1095 days (3 years) from creation date."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        max_target = calculate_max_target_date(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["LOW"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_4"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["ANNUALLY"],
            creation_date=creation_date
        )
        # 1095 days from Jan 1, 2025 = Jan 1, 2028
        # 2025: 365 days (not leap), 2026: 365 days, 2027: 365 days = 1095 days
        assert max_target == date(2028, 1, 1)

    def test_calculate_max_target_date_returns_none_if_no_config(
        self, db_session, timeframe_taxonomies
    ):
        """RED: Should return None if no config exists for the combination."""
        from app.api.recommendations import calculate_max_target_date

        creation_date = date(2025, 1, 1)
        # CONSIDERATION priority has no timeframe configs
        max_target = calculate_max_target_date(
            db_session,
            priority_id=timeframe_taxonomies["recommendation_priority"]["CONSIDERATION"],
            risk_tier_id=timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            usage_frequency_id=timeframe_taxonomies["usage_frequency"]["DAILY"],
            creation_date=creation_date
        )
        assert max_target is None

    def test_calculate_max_target_date_handles_leap_year(
        self, db_session, seed_timeframe_configs
    ):
        """RED: Correctly handles leap year when calculating target date."""
        from app.api.recommendations import calculate_max_target_date

        # 2024 is a leap year
        creation_date = date(2024, 1, 1)
        max_target = calculate_max_target_date(
            db_session,
            priority_id=seed_timeframe_configs["recommendation_priority"]["LOW"],
            risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
            usage_frequency_id=seed_timeframe_configs["usage_frequency"]["DAILY"],
            creation_date=creation_date
        )
        # 365 days from Jan 1, 2024 (leap year) = Dec 31, 2024
        assert max_target == date(2024, 12, 31)


# ============================================================================
# Phase 5: Test validate_target_date Function
# ============================================================================

@pytest.fixture
def validation_setup(db_session, seed_timeframe_configs, enforcement_setup):
    """Set up data for testing validate_target_date function."""
    from app.models.recommendation import Recommendation
    from app.models.model_region import ModelRegion

    # Create models with different risk tiers and usage frequencies

    # Model 1: Tier 1, Daily - strictest enforcement (HIGH priority = 0 days)
    model_strict = Model(
        model_name="Test Model Strict",
        description="Strict timeframe model",
        development_type="In-House",
        owner_id=enforcement_setup["user"].user_id,
        risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_1"],
        usage_frequency_id=seed_timeframe_configs["usage_frequency"]["DAILY"]
    )
    db_session.add(model_strict)
    db_session.flush()

    # Model 2: Tier 4, Annually - longest timeframe (LOW priority = 1095 days)
    model_lenient = Model(
        model_name="Test Model Lenient",
        description="Lenient timeframe model",
        development_type="In-House",
        owner_id=enforcement_setup["user"].user_id,
        risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_4"],
        usage_frequency_id=seed_timeframe_configs["usage_frequency"]["ANNUALLY"]
    )
    db_session.add(model_lenient)
    db_session.flush()

    # Model 3: For advisory (non-enforced) priority
    model_advisory = Model(
        model_name="Test Model Advisory",
        description="Advisory timeframe model",
        development_type="In-House",
        owner_id=enforcement_setup["user"].user_id,
        risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_2"],
        usage_frequency_id=seed_timeframe_configs["usage_frequency"]["MONTHLY"]
    )
    db_session.add(model_advisory)
    db_session.flush()

    return {
        "taxonomies": seed_timeframe_configs,
        "enforcement": enforcement_setup,
        "models": {
            "strict": model_strict,
            "lenient": model_lenient,
            "advisory": model_advisory
        }
    }


class TestValidateTargetDate:
    """Phase 5: Test target date validation function."""

    def test_validate_target_date_returns_validation_result_type(
        self, db_session, validation_setup
    ):
        """RED: Function should return a TargetDateValidationResult dataclass/namedtuple."""
        from app.api.recommendations import validate_target_date, TargetDateValidationResult

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            model_id=validation_setup["models"]["strict"].model_id,
            proposed_target_date=date.today(),
            creation_date=date.today()
        )

        # Should be a TargetDateValidationResult
        assert isinstance(result, TargetDateValidationResult)
        # Should have expected fields
        assert hasattr(result, "is_valid")
        assert hasattr(result, "is_enforced")
        assert hasattr(result, "max_target_date")
        assert hasattr(result, "reason_required")
        assert hasattr(result, "message")

    def test_validate_target_date_valid_when_within_max_enforced(
        self, db_session, validation_setup
    ):
        """RED: Target date within max should be valid when enforced."""
        from app.api.recommendations import validate_target_date

        # HIGH priority + TIER_2 + MONTHLY (model_advisory) = 90 days
        creation_date = date(2025, 1, 1)
        proposed_date = date(2025, 3, 1)  # 59 days - within 90 days

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            model_id=validation_setup["models"]["advisory"].model_id,  # TIER_2 + MONTHLY = 90 days for HIGH
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is True
        assert result.is_enforced is True
        assert result.reason_required is False  # No reason needed when within limits

    def test_validate_target_date_invalid_when_exceeds_max_enforced(
        self, db_session, validation_setup
    ):
        """RED: Target date beyond max should be INVALID when enforced."""
        from app.api.recommendations import validate_target_date

        # HIGH priority + TIER_1 + DAILY = 0 days (immediate)
        creation_date = date(2025, 1, 1)
        proposed_date = date(2025, 1, 15)  # 14 days - exceeds 0 days

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            model_id=validation_setup["models"]["strict"].model_id,
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is False
        assert result.is_enforced is True
        assert result.max_target_date == date(2025, 1, 1)  # Same as creation (0 days)
        assert "exceeds" in result.message.lower() or "beyond" in result.message.lower()

    def test_validate_target_date_valid_with_reason_when_exceeds_non_enforced(
        self, db_session, validation_setup
    ):
        """RED: Target date beyond max is VALID when not enforced, but requires reason."""
        from app.api.recommendations import validate_target_date

        # LOW priority has enforce_timeframes=False (advisory)
        # LOW + TIER_2 + MONTHLY = 365 days
        creation_date = date(2025, 1, 1)
        proposed_date = date(2027, 1, 1)  # 730 days - exceeds 365 days

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["LOW"],
            model_id=validation_setup["models"]["advisory"].model_id,
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is True  # Valid because not enforced
        assert result.is_enforced is False
        assert result.reason_required is True  # But reason is required since it exceeds max
        assert "advisory" in result.message.lower() or "recommended" in result.message.lower()

    def test_validate_target_date_no_reason_required_when_within_advisory(
        self, db_session, validation_setup
    ):
        """RED: When advisory and within max, no reason required."""
        from app.api.recommendations import validate_target_date

        # LOW priority has enforce_timeframes=False (advisory)
        creation_date = date(2025, 1, 1)
        proposed_date = date(2025, 6, 1)  # 151 days - within 365 days

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["LOW"],
            model_id=validation_setup["models"]["advisory"].model_id,
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is True
        assert result.is_enforced is False
        assert result.reason_required is False  # Within max, no reason needed

    def test_validate_target_date_exact_max_date_is_valid(
        self, db_session, validation_setup
    ):
        """RED: Target date exactly equal to max should be valid."""
        from app.api.recommendations import validate_target_date

        # HIGH priority + TIER_2 + MONTHLY (model_advisory) = 90 days
        creation_date = date(2025, 1, 1)
        proposed_date = date(2025, 4, 1)  # Exactly 90 days

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            model_id=validation_setup["models"]["advisory"].model_id,  # TIER_2 + MONTHLY = 90 days for HIGH
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is True
        assert result.max_target_date == date(2025, 4, 1)

    def test_validate_target_date_sooner_than_max_is_valid(
        self, db_session, validation_setup
    ):
        """Target date sooner than max is valid (no reason requirement for early dates)."""
        from app.api.recommendations import validate_target_date

        # MEDIUM priority + TIER_4 + ANNUALLY = 365 days
        creation_date = date(2025, 1, 1)
        proposed_date = date(2025, 2, 1)  # Only 31 days - much sooner than 365 days

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
            model_id=validation_setup["models"]["lenient"].model_id,
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is True
        # Early target dates are allowed without explanation
        assert result.reason_required is False

    def test_validate_target_date_no_config_returns_valid_with_warning(
        self, db_session, validation_setup
    ):
        """RED: When no timeframe config exists, should return valid with warning."""
        from app.api.recommendations import validate_target_date

        # CONSIDERATION priority has no timeframe config
        creation_date = date(2025, 1, 1)
        proposed_date = date(2025, 12, 31)

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["CONSIDERATION"],
            model_id=validation_setup["models"]["advisory"].model_id,
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is True
        assert result.max_target_date is None  # No config means no max
        assert "no timeframe" in result.message.lower() or "not configured" in result.message.lower()

    def test_validate_target_date_past_date_is_invalid(
        self, db_session, validation_setup
    ):
        """RED: Target date in the past (before creation) should be invalid."""
        from app.api.recommendations import validate_target_date

        creation_date = date(2025, 6, 15)
        proposed_date = date(2025, 6, 1)  # Before creation date

        result = validate_target_date(
            db_session,
            priority_id=validation_setup["taxonomies"]["recommendation_priority"]["HIGH"],
            model_id=validation_setup["models"]["strict"].model_id,
            proposed_target_date=proposed_date,
            creation_date=creation_date
        )

        assert result.is_valid is False
        assert "before" in result.message.lower() or "past" in result.message.lower()


# ============================================================================
# Phase 6: Test API Endpoints for Timeframe Config CRUD
# ============================================================================

@pytest.fixture
def api_setup(db_session, seed_timeframe_configs, enforcement_setup, lob_hierarchy):
    """Set up data for API endpoint testing."""
    from app.core.security import create_access_token

    # Create admin user and token
    admin_user = User(
        email="admin@example.com",
        full_name="Admin User",
        password_hash=get_password_hash("admin123"),
        role="Admin",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(admin_user)
    db_session.commit()

    admin_token = create_access_token(data={"sub": admin_user.email})

    # Create regular user and token
    regular_user = User(
        email="user@example.com",
        full_name="Regular User",
        password_hash=get_password_hash("test123"),
        role="User",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(regular_user)
    db_session.commit()

    user_token = create_access_token(data={"sub": regular_user.email})

    # Create a model for calculate endpoint tests
    test_model = Model(
        model_name="API Test Model",
        description="Model for API testing",
        development_type="In-House",
        owner_id=enforcement_setup["user"].user_id,
        risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_2"],
        usage_frequency_id=seed_timeframe_configs["usage_frequency"]["MONTHLY"]
    )
    db_session.add(test_model)
    db_session.commit()

    return {
        "admin_token": admin_token,
        "user_token": user_token,
        "taxonomies": seed_timeframe_configs,
        "test_model": test_model
    }


class TestTimeframeConfigAPIEndpoints:
    """Phase 6: Test timeframe config API endpoints."""

    def test_list_timeframe_configs(self, client, api_setup):
        """RED: GET /recommendations/timeframe-config/ should list all configs."""
        response = client.get(
            "/recommendations/timeframe-config/",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should have 48 configs (3 priorities × 4 tiers × 4 frequencies)
        assert len(data) == 48

    def test_get_single_timeframe_config(self, client, api_setup, db_session):
        """RED: GET /recommendations/timeframe-config/{id} should return single config."""
        from app.models.recommendation import RecommendationTimeframeConfig

        # Get an existing config ID
        config = db_session.query(RecommendationTimeframeConfig).first()
        assert config is not None, "Should have at least one config from seed_timeframe_configs"

        response = client.get(
            f"/recommendations/timeframe-config/{config.config_id}",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "config_id" in data
        assert "priority" in data
        assert "risk_tier" in data
        assert "usage_frequency" in data
        assert "max_days" in data

    def test_get_single_timeframe_config_not_found(self, client, api_setup):
        """RED: GET /recommendations/timeframe-config/{id} should return 404 for non-existent config."""
        response = client.get(
            "/recommendations/timeframe-config/99999",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"}
        )
        assert response.status_code == 404

    def test_update_timeframe_config_admin_only(self, client, api_setup, db_session):
        """RED: PATCH should only be allowed for admins."""
        from app.models.recommendation import RecommendationTimeframeConfig

        # Get an existing config ID
        config = db_session.query(RecommendationTimeframeConfig).first()
        assert config is not None

        # Non-admin should fail
        response = client.patch(
            f"/recommendations/timeframe-config/{config.config_id}",
            headers={"Authorization": f"Bearer {api_setup['user_token']}"},
            json={"max_days": 999}
        )
        assert response.status_code == 403

        # Admin should succeed
        response = client.patch(
            f"/recommendations/timeframe-config/{config.config_id}",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={"max_days": 999}
        )
        assert response.status_code == 200
        assert response.json()["max_days"] == 999

    def test_update_timeframe_config_validates_max_days_non_negative(
        self, client, api_setup, db_session
    ):
        """RED: PATCH should reject negative max_days."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = db_session.query(RecommendationTimeframeConfig).first()
        assert config is not None

        response = client.patch(
            f"/recommendations/timeframe-config/{config.config_id}",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={"max_days": -5}
        )
        assert response.status_code == 422  # Validation error

    def test_update_timeframe_config_accepts_zero(self, client, api_setup, db_session):
        """RED: PATCH should accept zero (immediate resolution)."""
        from app.models.recommendation import RecommendationTimeframeConfig

        config = db_session.query(RecommendationTimeframeConfig).first()
        assert config is not None

        response = client.patch(
            f"/recommendations/timeframe-config/{config.config_id}",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={"max_days": 0}
        )
        assert response.status_code == 200
        assert response.json()["max_days"] == 0

    def test_update_timeframe_config_not_found(self, client, api_setup):
        """RED: PATCH should return 404 for non-existent config."""
        response = client.patch(
            "/recommendations/timeframe-config/99999",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={"max_days": 100}
        )
        assert response.status_code == 404


class TestCalculateTimeframeEndpoint:
    """Phase 6: Test calculate timeframe endpoint."""

    def test_calculate_timeframe_returns_correct_data(self, client, api_setup):
        """RED: POST /recommendations/timeframe-config/calculate should return timeframe info."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={
                "priority_id": api_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "model_id": api_setup["test_model"].model_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority_code"] == "MEDIUM"
        assert data["risk_tier_code"] == "TIER_2"
        assert data["usage_frequency_code"] == "MONTHLY"
        assert data["max_days"] == 180  # MEDIUM + TIER_2 + MONTHLY = 180 days
        assert "calculated_max_date" in data
        assert "enforce_timeframes" in data

    def test_calculate_timeframe_high_priority(self, client, api_setup):
        """RED: Calculate timeframe for HIGH priority should return correct max_days."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={
                "priority_id": api_setup["taxonomies"]["recommendation_priority"]["HIGH"],
                "model_id": api_setup["test_model"].model_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        # HIGH + TIER_2 + MONTHLY = 90 days
        assert data["max_days"] == 90
        assert data["enforce_timeframes"] is True

    def test_calculate_timeframe_model_not_found(self, client, api_setup):
        """RED: Should return 404 for non-existent model."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={
                "priority_id": api_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "model_id": 99999
            }
        )
        assert response.status_code == 404

    def test_calculate_timeframe_priority_not_found(self, client, api_setup):
        """RED: Should return 404 or appropriate error for non-existent priority."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            headers={"Authorization": f"Bearer {api_setup['admin_token']}"},
            json={
                "priority_id": 99999,
                "model_id": api_setup["test_model"].model_id
            }
        )
        # Could be 404 or return None/empty data
        assert response.status_code in [404, 200]

    def test_calculate_timeframe_requires_authentication(self, client, api_setup):
        """RED: Calculate endpoint should require authentication."""
        response = client.post(
            "/recommendations/timeframe-config/calculate",
            json={
                "priority_id": api_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "model_id": api_setup["test_model"].model_id
            }
        )
        # Either 401 Unauthorized or 403 Forbidden is acceptable
        assert response.status_code in [401, 403]


# ============================================================================
# Phase 7: Test Recommendation Create/Update with Timeframe Validation
# ============================================================================

@pytest.fixture
def recommendation_setup(db_session, seed_timeframe_configs, enforcement_setup, lob_hierarchy):
    """Set up data for testing recommendation create/update with timeframe validation."""
    from app.core.security import create_access_token

    # Create validator user and token
    validator_user = User(
        email="validator@example.com",
        full_name="Test Validator",
        password_hash=get_password_hash("validator123"),
        role="Validator",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(validator_user)
    db_session.commit()

    validator_token = create_access_token(data={"sub": validator_user.email})

    # Create a developer for assigned_to
    developer_user = User(
        email="developer@example.com",
        full_name="Test Developer",
        password_hash=get_password_hash("developer123"),
        role="User",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(developer_user)
    db_session.commit()

    # Create model with TIER_2 + MONTHLY (180 days for MEDIUM, 90 days for HIGH)
    model_enforced = Model(
        model_name="Enforced Model",
        description="Model with enforced timeframes",
        development_type="In-House",
        owner_id=enforcement_setup["user"].user_id,
        risk_tier_id=seed_timeframe_configs["model_risk_tier"]["TIER_2"],
        usage_frequency_id=seed_timeframe_configs["usage_frequency"]["MONTHLY"]
    )
    db_session.add(model_enforced)
    db_session.commit()

    # Get or create the recommendation status taxonomy
    rec_status_taxonomy = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Recommendation Status"
    ).first()
    if not rec_status_taxonomy:
        rec_status_taxonomy = Taxonomy(
            name="Recommendation Status",
            description="Status values for recommendations",
            is_system=True
        )
        db_session.add(rec_status_taxonomy)
        db_session.flush()

    # Get or create draft status
    draft_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == rec_status_taxonomy.taxonomy_id,
        TaxonomyValue.code == "REC_DRAFT"
    ).first()
    if not draft_status:
        draft_status = TaxonomyValue(
            taxonomy_id=rec_status_taxonomy.taxonomy_id,
            code="REC_DRAFT",
            label="Draft",
            sort_order=1
        )
        db_session.add(draft_status)
        db_session.commit()
    else:
        db_session.commit()

    return {
        "validator_token": validator_token,
        "validator_user": validator_user,
        "developer_user": developer_user,
        "model_enforced": model_enforced,
        "taxonomies": seed_timeframe_configs,
        "draft_status": draft_status
    }


class TestCreateRecommendationWithTimeframe:
    """Phase 7: Test recommendation creation with timeframe validation."""

    def test_create_recommendation_within_max_date(self, client, recommendation_setup):
        """RED: Should allow creating recommendation with date within max."""
        from datetime import date, timedelta

        # MEDIUM priority + TIER_2 + MONTHLY = 180 days max
        target_date = date.today() + timedelta(days=150)  # Within 180 days

        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "model_id": recommendation_setup["model_enforced"].model_id,
                "title": "Test Recommendation Within Max",
                "description": "Test description",
                "priority_id": recommendation_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "assigned_to_id": recommendation_setup["developer_user"].user_id,
                "original_target_date": target_date.isoformat()
            }
        )
        assert response.status_code == 201

    def test_create_recommendation_exceeds_max_date_enforced(self, client, recommendation_setup):
        """RED: Should reject recommendation with date exceeding max when enforced."""
        from datetime import date, timedelta

        # MEDIUM priority + TIER_2 + MONTHLY = 180 days max
        # Set date to 500 days from now - way beyond max
        target_date = date.today() + timedelta(days=500)

        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "model_id": recommendation_setup["model_enforced"].model_id,
                "title": "Test Recommendation Exceeds Max",
                "description": "Test description",
                "priority_id": recommendation_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "assigned_to_id": recommendation_setup["developer_user"].user_id,
                "original_target_date": target_date.isoformat()
            }
        )
        assert response.status_code == 400
        assert "exceed" in response.json()["detail"].lower() or "max" in response.json()["detail"].lower()

    def test_create_recommendation_early_date_succeeds_without_reason(
        self, client, recommendation_setup
    ):
        """Early target dates (within limits) should succeed without requiring a reason."""
        from datetime import date, timedelta

        # MEDIUM priority + TIER_2 + MONTHLY = 180 days max
        # Set date to just 14 days from now - much earlier than 180 max, but still valid
        target_date = date.today() + timedelta(days=14)

        # Early dates within limits should succeed without reason
        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "model_id": recommendation_setup["model_enforced"].model_id,
                "title": "Test Recommendation Early Date",
                "description": "Test description",
                "priority_id": recommendation_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "assigned_to_id": recommendation_setup["developer_user"].user_id,
                "original_target_date": target_date.isoformat()
                # No target_date_change_reason - not required for early dates
            }
        )
        assert response.status_code == 201

    def test_create_recommendation_early_with_optional_reason_succeeds(
        self, client, recommendation_setup
    ):
        """Early date with optional explanation provided should succeed."""
        from datetime import date, timedelta

        # MEDIUM priority + TIER_2 + MONTHLY = 180 days max
        # Set date to just 14 days from now - early but valid
        target_date = date.today() + timedelta(days=14)

        # With optional reason - should succeed
        response = client.post(
            "/recommendations/",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "model_id": recommendation_setup["model_enforced"].model_id,
                "title": "Test Recommendation Early With Reason",
                "description": "Test description",
                "priority_id": recommendation_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
                "assigned_to_id": recommendation_setup["developer_user"].user_id,
                "original_target_date": target_date.isoformat(),
                "target_date_change_reason": "Critical issue requires immediate remediation"
            }
        )
        assert response.status_code == 201


class TestUpdateRecommendationTargetDate:
    """Phase 7: Test recommendation update with target date validation."""

    @pytest.fixture
    def existing_recommendation(self, db_session, recommendation_setup):
        """Create an existing recommendation for update tests."""
        from datetime import date, timedelta
        from app.models.recommendation import Recommendation

        # Create a recommendation with initial target date
        rec = Recommendation(
            recommendation_code="REC-2025-00001",
            model_id=recommendation_setup["model_enforced"].model_id,
            title="Existing Recommendation",
            description="Test recommendation for update tests",
            priority_id=recommendation_setup["taxonomies"]["recommendation_priority"]["MEDIUM"],
            current_status_id=recommendation_setup["draft_status"].value_id,
            created_by_id=recommendation_setup["validator_user"].user_id,
            assigned_to_id=recommendation_setup["developer_user"].user_id,
            original_target_date=date.today() + timedelta(days=90),
            current_target_date=date.today() + timedelta(days=90)
        )
        db_session.add(rec)
        db_session.commit()
        return rec

    def test_update_target_date_requires_reason(
        self, client, recommendation_setup, existing_recommendation
    ):
        """RED: Should require reason when changing target date."""
        from datetime import date, timedelta

        new_target_date = date.today() + timedelta(days=120)

        response = client.patch(
            f"/recommendations/{existing_recommendation.recommendation_id}",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "current_target_date": new_target_date.isoformat()
                # No target_date_change_reason!
            }
        )
        assert response.status_code == 400
        assert "reason" in response.json()["detail"].lower() or "explanation" in response.json()["detail"].lower()

    def test_update_target_date_with_reason_succeeds(
        self, client, recommendation_setup, existing_recommendation
    ):
        """RED: Should allow target date change with reason."""
        from datetime import date, timedelta

        new_target_date = date.today() + timedelta(days=120)

        response = client.patch(
            f"/recommendations/{existing_recommendation.recommendation_id}",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "current_target_date": new_target_date.isoformat(),
                "target_date_change_reason": "Extended due to dependency on upstream fix"
            }
        )
        assert response.status_code == 200
        assert response.json()["target_date_change_reason"] == "Extended due to dependency on upstream fix"

    def test_update_target_date_cannot_exceed_max_when_enforced(
        self, client, recommendation_setup, existing_recommendation
    ):
        """RED: Should reject target date exceeding max even on update."""
        from datetime import date, timedelta

        # Set date way beyond max (MEDIUM + TIER_2 + MONTHLY = 180 days)
        far_future_date = date.today() + timedelta(days=500)

        response = client.patch(
            f"/recommendations/{existing_recommendation.recommendation_id}",
            headers={"Authorization": f"Bearer {recommendation_setup['validator_token']}"},
            json={
                "current_target_date": far_future_date.isoformat(),
                "target_date_change_reason": "Trying to extend beyond max"
            }
        )
        assert response.status_code == 400
        assert "exceed" in response.json()["detail"].lower() or "max" in response.json()["detail"].lower()


# ============================================================================
# Phase 8: Test Seed Data for Timeframe Configs
# ============================================================================

@pytest.fixture
def fresh_db_for_seed_test(db_session):
    """Provide a fresh database session for testing seed functions."""
    from app.models.recommendation import (
        RecommendationTimeframeConfig, RecommendationPriorityConfig
    )

    # Clean up any existing timeframe configs and priority configs
    db_session.query(RecommendationTimeframeConfig).delete()
    db_session.query(RecommendationPriorityConfig).delete()
    db_session.commit()

    return db_session


class TestTimeframeConfigSeeding:
    """Phase 8: Test that seed data creates all timeframe configs."""

    def test_seed_timeframe_configs_creates_48_configs(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: Should create 3 priorities × 4 tiers × 4 frequencies = 48 configs."""
        from app.seed import seed_timeframe_configs
        from app.models.recommendation import RecommendationTimeframeConfig

        # Run the seed function
        seed_timeframe_configs(fresh_db_for_seed_test)

        # Count total configs
        count = fresh_db_for_seed_test.query(RecommendationTimeframeConfig).count()
        assert count == 48

    def test_seed_timeframe_configs_correct_values_high_tier1_daily(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: HIGH + TIER_1 + DAILY should be 0 days (immediate resolution)."""
        from app.seed import seed_timeframe_configs
        from app.models.recommendation import RecommendationTimeframeConfig

        seed_timeframe_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationTimeframeConfig).filter(
            RecommendationTimeframeConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["HIGH"],
            RecommendationTimeframeConfig.risk_tier_id == timeframe_taxonomies["model_risk_tier"]["TIER_1"],
            RecommendationTimeframeConfig.usage_frequency_id == timeframe_taxonomies["usage_frequency"]["DAILY"]
        ).first()

        assert config is not None
        assert config.max_days == 0

    def test_seed_timeframe_configs_correct_values_medium_tier2_monthly(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: MEDIUM + TIER_2 + MONTHLY should be 180 days."""
        from app.seed import seed_timeframe_configs
        from app.models.recommendation import RecommendationTimeframeConfig

        seed_timeframe_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationTimeframeConfig).filter(
            RecommendationTimeframeConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["MEDIUM"],
            RecommendationTimeframeConfig.risk_tier_id == timeframe_taxonomies["model_risk_tier"]["TIER_2"],
            RecommendationTimeframeConfig.usage_frequency_id == timeframe_taxonomies["usage_frequency"]["MONTHLY"]
        ).first()

        assert config is not None
        assert config.max_days == 180

    def test_seed_timeframe_configs_correct_values_low_tier4_annually(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: LOW + TIER_4 + ANNUALLY should be 1095 days (3 years)."""
        from app.seed import seed_timeframe_configs
        from app.models.recommendation import RecommendationTimeframeConfig

        seed_timeframe_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationTimeframeConfig).filter(
            RecommendationTimeframeConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["LOW"],
            RecommendationTimeframeConfig.risk_tier_id == timeframe_taxonomies["model_risk_tier"]["TIER_4"],
            RecommendationTimeframeConfig.usage_frequency_id == timeframe_taxonomies["usage_frequency"]["ANNUALLY"]
        ).first()

        assert config is not None
        assert config.max_days == 1095

    def test_seed_timeframe_configs_idempotent(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: Running seed twice should not create duplicates."""
        from app.seed import seed_timeframe_configs
        from app.models.recommendation import RecommendationTimeframeConfig

        # Run seed twice
        seed_timeframe_configs(fresh_db_for_seed_test)
        seed_timeframe_configs(fresh_db_for_seed_test)

        # Should still be exactly 48
        count = fresh_db_for_seed_test.query(RecommendationTimeframeConfig).count()
        assert count == 48


class TestPriorityConfigEnforceTimeframesSeeding:
    """Phase 8: Test that priority configs have correct enforce_timeframes values."""

    def test_seed_priority_config_high_enforces_timeframes(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: HIGH priority should have enforce_timeframes=True."""
        from app.seed import seed_priority_configs
        from app.models.recommendation import RecommendationPriorityConfig

        seed_priority_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationPriorityConfig).filter(
            RecommendationPriorityConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["HIGH"]
        ).first()

        assert config is not None
        assert config.enforce_timeframes is True

    def test_seed_priority_config_medium_enforces_timeframes(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: MEDIUM priority should have enforce_timeframes=True."""
        from app.seed import seed_priority_configs
        from app.models.recommendation import RecommendationPriorityConfig

        seed_priority_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationPriorityConfig).filter(
            RecommendationPriorityConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["MEDIUM"]
        ).first()

        assert config is not None
        assert config.enforce_timeframes is True

    def test_seed_priority_config_low_enforces_timeframes(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: LOW priority should have enforce_timeframes=True (enforced but longer timeframe)."""
        from app.seed import seed_priority_configs
        from app.models.recommendation import RecommendationPriorityConfig

        seed_priority_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationPriorityConfig).filter(
            RecommendationPriorityConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["LOW"]
        ).first()

        assert config is not None
        assert config.enforce_timeframes is True

    def test_seed_priority_config_consideration_no_enforcement(
        self, fresh_db_for_seed_test, timeframe_taxonomies
    ):
        """RED: CONSIDERATION priority should have enforce_timeframes=False."""
        from app.seed import seed_priority_configs
        from app.models.recommendation import RecommendationPriorityConfig

        seed_priority_configs(fresh_db_for_seed_test)

        config = fresh_db_for_seed_test.query(RecommendationPriorityConfig).filter(
            RecommendationPriorityConfig.priority_id == timeframe_taxonomies["recommendation_priority"]["CONSIDERATION"]
        ).first()

        assert config is not None
        assert config.enforce_timeframes is False
