"""Tests for Due Date Override API."""
import pytest
from datetime import date, datetime, timedelta
from app.models.due_date_override import ModelDueDateOverride
from app.models.model import Model
from app.models.user import User
from app.models.validation import (
    ValidationRequest, ValidationRequestModelVersion, ValidationPolicy,
    ValidationWorkflowSLA
)
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.core.security import get_password_hash, create_access_token
from app.core.roles import RoleCode
from app.models.role import Role


def get_role_id(db_session, role_code: str) -> int:
    return db_session.query(Role).filter(Role.code == role_code).first().role_id


class TestDueDateOverrideAPI:
    """Tests for the Due Date Override API endpoints."""

    @pytest.fixture
    def risk_tier_taxonomy(self, db_session):
        """Create risk tier taxonomy with policy."""
        taxonomy = Taxonomy(
            name="Model Risk Tier",
            description="Risk tier classifications"
        )
        db_session.add(taxonomy)
        db_session.flush()

        tier1 = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="TIER_1",
            label="Tier 1 (High)",
            sort_order=1
        )
        db_session.add(tier1)
        db_session.flush()

        # Create validation policy for this tier
        policy = ValidationPolicy(
            risk_tier_id=tier1.value_id,
            frequency_months=12,
            grace_period_months=3,
            model_change_lead_time_days=90,
            description="High risk tier policy"
        )
        db_session.add(policy)
        db_session.commit()
        return {"taxonomy": taxonomy, "tier1": tier1, "policy": policy}

    @pytest.fixture
    def validation_status_taxonomy(self, db_session):
        """Create validation request status taxonomy."""
        taxonomy = Taxonomy(
            name="Validation Request Status",
            description="Status values for validation requests"
        )
        db_session.add(taxonomy)
        db_session.flush()

        statuses = [
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="INTAKE",
                label="Intake",
                sort_order=1
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="APPROVED",
                label="Approved",
                sort_order=6
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="CANCELLED",
                label="Cancelled",
                sort_order=8
            ),
        ]
        for s in statuses:
            db_session.add(s)
        db_session.commit()
        return {
            "taxonomy": taxonomy,
            "intake": statuses[0],
            "approved": statuses[1],
            "cancelled": statuses[2]
        }

    @pytest.fixture
    def validation_type_taxonomy(self, db_session):
        """Create validation type taxonomy."""
        taxonomy = Taxonomy(
            name="Validation Type",
            description="Types of validation"
        )
        db_session.add(taxonomy)
        db_session.flush()

        val_type = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="COMPREHENSIVE",
            label="Comprehensive Validation",
            sort_order=1
        )
        db_session.add(val_type)
        db_session.commit()
        return {"taxonomy": taxonomy, "comprehensive": val_type}

    @pytest.fixture
    def test_model(self, db_session, admin_user, usage_frequency, risk_tier_taxonomy):
        """Create a test model with risk tier."""
        model = Model(
            model_name="Test Model for Override",
            owner_id=admin_user.user_id,
            row_approval_status="approved",
            usage_frequency_id=usage_frequency["daily"].value_id,
            risk_tier_id=risk_tier_taxonomy["tier1"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    @pytest.fixture
    def sla_config(self, db_session):
        """Create SLA configuration."""
        sla = ValidationWorkflowSLA()
        db_session.add(sla)
        db_session.commit()
        return sla

    @pytest.fixture
    def validation_request(
        self, db_session, test_model, admin_user,
        validation_status_taxonomy, validation_type_taxonomy, sla_config
    ):
        """Create a validation request for override tests."""
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            submission_due_date=date.today() + timedelta(days=60)
        )
        db_session.add(request)
        db_session.flush()

        # Link model to request
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()
        return request

    # ==================== GET CURRENT OVERRIDE ====================

    def test_get_override_no_active_override(
        self, client, admin_headers, test_model
    ):
        """GET /models/{id}/due-date-override returns no override when none exists."""
        response = client.get(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == test_model.model_id
        assert data["model_name"] == "Test Model for Override"
        assert data["has_active_override"] is False
        assert data["active_override"] is None

    def test_get_override_with_active_override(
        self, client, admin_headers, test_model, admin_user, db_session
    ):
        """GET /models/{id}/due-date-override returns active override details."""
        # Create an override
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="ONE_TIME",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Test override for accelerated review",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        response = client.get(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_active_override"] is True
        assert data["active_override"]["override_type"] == "ONE_TIME"
        assert data["active_override"]["target_scope"] == "NEXT_CYCLE"
        assert data["active_override"]["reason"] == "Test override for accelerated review"

    def test_get_override_requires_auth(self, client, test_model):
        """GET /models/{id}/due-date-override requires authentication."""
        response = client.get(f"/models/{test_model.model_id}/due-date-override")
        # FastAPI returns 403 when no auth provided (depends on auth dependency behavior)
        assert response.status_code in [401, 403]

    # ==================== CREATE OVERRIDE ====================

    def test_create_override_one_time_next_cycle(
        self, client, admin_headers, test_model, validation_request, db_session
    ):
        """POST /models/{id}/due-date-override creates ONE_TIME NEXT_CYCLE override."""
        # Override date must be earlier than submission_due_date (60 days from now)
        override_date = date.today() + timedelta(days=30)

        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "NEXT_CYCLE",
                "override_date": override_date.isoformat(),
                "reason": "Model showing poor performance, expediting review"
            }
        )
        assert response.status_code == 201  # API returns 201 CREATED
        data = response.json()
        assert data["override_type"] == "ONE_TIME"
        assert data["target_scope"] == "NEXT_CYCLE"
        assert data["is_active"] is True

        # Verify in database
        override = db_session.query(ModelDueDateOverride).filter_by(
            model_id=test_model.model_id,
            is_active=True
        ).first()
        assert override is not None
        assert override.override_type == "ONE_TIME"

    def test_create_override_permanent_current_request(
        self, client, admin_headers, test_model, validation_request, db_session
    ):
        """POST /models/{id}/due-date-override creates PERMANENT CURRENT_REQUEST override."""
        override_date = date.today() + timedelta(days=30)

        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "PERMANENT",
                "target_scope": "CURRENT_REQUEST",
                "override_date": override_date.isoformat(),
                "reason": "Establishing accelerated schedule for this model"
            }
        )
        assert response.status_code == 201  # API returns 201 CREATED
        data = response.json()
        assert data["override_type"] == "PERMANENT"
        assert data["target_scope"] == "CURRENT_REQUEST"
        assert data["validation_request_id"] == validation_request.request_id

    def test_create_override_supersedes_existing(
        self, client, admin_headers, test_model, admin_user, validation_request, db_session
    ):
        """Creating new override supersedes existing active override."""
        # Create first override
        first_override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="ONE_TIME",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="First override",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(first_override)
        db_session.commit()
        first_id = first_override.override_id

        # Create second override (earlier date)
        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "PERMANENT",
                "target_scope": "NEXT_CYCLE",
                "override_date": (date.today() + timedelta(days=20)).isoformat(),
                "reason": "Replacing with permanent override"
            }
        )
        assert response.status_code == 201

        # Verify first override is superseded
        db_session.refresh(first_override)
        assert first_override.is_active is False
        assert first_override.cleared_type == "SUPERSEDED"
        assert first_override.superseded_by_override_id is not None

    def test_create_override_rejects_future_date_past_policy(
        self, client, admin_headers, test_model, validation_request
    ):
        """POST rejects override date that is NOT earlier than policy date."""
        # Override date must be earlier than submission_due_date (60 days)
        # Set date to be AFTER the policy date (should fail)
        override_date = date.today() + timedelta(days=90)

        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "NEXT_CYCLE",
                "override_date": override_date.isoformat(),
                "reason": "Trying to extend deadline (should fail)"
            }
        )
        # Should fail because override must be earlier than policy date
        assert response.status_code == 400

    def test_create_override_rejects_past_date(
        self, client, admin_headers, test_model, validation_request
    ):
        """POST rejects override date in the past."""
        past_date = date.today() - timedelta(days=1)

        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "NEXT_CYCLE",
                "override_date": past_date.isoformat(),
                "reason": "Trying to set past date (should fail)"
            }
        )
        assert response.status_code == 400

    def test_create_override_rejects_short_reason(
        self, client, admin_headers, test_model, validation_request
    ):
        """POST rejects reason shorter than 10 characters."""
        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "NEXT_CYCLE",
                "override_date": (date.today() + timedelta(days=30)).isoformat(),
                "reason": "Too short"  # Less than 10 chars
            }
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_create_override_requires_admin(
        self, client, second_user_headers, test_model, validation_request
    ):
        """POST /models/{id}/due-date-override requires admin role."""
        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=second_user_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "NEXT_CYCLE",
                "override_date": (date.today() + timedelta(days=30)).isoformat(),
                "reason": "Regular user trying to create override"
            }
        )
        assert response.status_code == 403

    def test_create_override_current_request_requires_open_validation(
        self, client, admin_headers, test_model
    ):
        """CURRENT_REQUEST scope requires an open validation request."""
        # test_model has no validation request in this test (no fixture)
        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "CURRENT_REQUEST",
                "override_date": (date.today() + timedelta(days=30)).isoformat(),
                "reason": "Trying to target current request when none exists"
            }
        )
        assert response.status_code == 400

    # ==================== CLEAR OVERRIDE ====================

    def test_clear_override_manually(
        self, client, admin_headers, test_model, admin_user, db_session
    ):
        """DELETE /models/{id}/due-date-override clears active override."""
        # Create an override
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="PERMANENT",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Override to be cleared",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        # Use request() method since delete() doesn't support json body in TestClient
        response = client.request(
            "DELETE",
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={"reason": "Reverting to policy-calculated date"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["cleared_type"] == "MANUAL"

        # Verify in database
        db_session.refresh(override)
        assert override.is_active is False
        assert override.cleared_reason == "Reverting to policy-calculated date"

    def test_clear_override_requires_admin(
        self, client, second_user_headers, test_model, admin_user, db_session
    ):
        """DELETE /models/{id}/due-date-override requires admin role."""
        # Create an override
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="ONE_TIME",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Override to test clear permission",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        response = client.request(
            "DELETE",
            f"/models/{test_model.model_id}/due-date-override",
            headers=second_user_headers,
            json={"reason": "Regular user trying to clear"}
        )
        assert response.status_code == 403

    def test_clear_override_no_active_returns_404(
        self, client, admin_headers, test_model
    ):
        """DELETE returns 404 when no active override exists."""
        response = client.request(
            "DELETE",
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={"reason": "Trying to clear non-existent override"}
        )
        assert response.status_code == 404

    # ==================== GET HISTORY ====================

    def test_get_override_history(
        self, client, admin_headers, test_model, admin_user, db_session
    ):
        """GET /models/{id}/due-date-override/history returns all overrides."""
        # Create multiple overrides (one cleared, one active)
        override1 = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="ONE_TIME",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="First override (cleared)",
            created_by_user_id=admin_user.user_id,
            is_active=False,
            cleared_type="MANUAL",
            cleared_reason="Replaced"
        )
        db_session.add(override1)
        db_session.flush()

        override2 = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="PERMANENT",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=25),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Current active override",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override2)
        db_session.commit()

        response = client.get(
            f"/models/{test_model.model_id}/due-date-override/history",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == test_model.model_id
        assert data["active_override"] is not None
        assert data["active_override"]["override_type"] == "PERMANENT"
        # History only includes INACTIVE overrides (the cleared ones)
        assert len(data["override_history"]) == 1
        assert data["override_history"][0]["is_active"] is False

    # ==================== HELPER FUNCTION TESTS ====================

    def test_get_active_override_for_request(
        self, db_session, test_model, admin_user, validation_request
    ):
        """Test get_active_override_for_request helper function."""
        from app.api.due_date_override import get_active_override_for_request

        # No override - should return None
        result = get_active_override_for_request(
            db_session, test_model.model_id, validation_request.request_id
        )
        assert result is None

        # Create override linked to request
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            validation_request_id=validation_request.request_id,
            override_type="ONE_TIME",
            target_scope="CURRENT_REQUEST",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Linked override",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        result = get_active_override_for_request(
            db_session, test_model.model_id, validation_request.request_id
        )
        assert result is not None
        assert result.override_id == override.override_id

    def test_clear_override_function(
        self, db_session, test_model, admin_user
    ):
        """Test clear_override helper function."""
        from app.api.due_date_override import clear_override

        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="ONE_TIME",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Override to clear",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        clear_override(
            db_session, override, "AUTO_VALIDATION_COMPLETE",
            admin_user.user_id, "Validation approved"
        )
        db_session.commit()

        db_session.refresh(override)
        assert override.is_active is False
        assert override.cleared_type == "AUTO_VALIDATION_COMPLETE"
        assert override.cleared_by_user_id == admin_user.user_id


class TestDueDateOverrideIntegration:
    """Integration tests for due date override with validation workflow."""

    @pytest.fixture
    def risk_tier_taxonomy(self, db_session):
        """Create risk tier taxonomy with policy."""
        taxonomy = Taxonomy(
            name="Model Risk Tier",
            description="Risk tier classifications"
        )
        db_session.add(taxonomy)
        db_session.flush()

        tier1 = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="TIER_1",
            label="Tier 1 (High)",
            sort_order=1
        )
        db_session.add(tier1)
        db_session.flush()

        policy = ValidationPolicy(
            risk_tier_id=tier1.value_id,
            frequency_months=12,
            grace_period_months=3,
            model_change_lead_time_days=90,
            description="High risk tier policy"
        )
        db_session.add(policy)
        db_session.commit()
        return {"taxonomy": taxonomy, "tier1": tier1, "policy": policy}

    @pytest.fixture
    def test_model(self, db_session, admin_user, usage_frequency, risk_tier_taxonomy):
        """Create a test model with risk tier."""
        model = Model(
            model_name="Integration Test Model",
            owner_id=admin_user.user_id,
            row_approval_status="approved",
            usage_frequency_id=usage_frequency["daily"].value_id,
            risk_tier_id=risk_tier_taxonomy["tier1"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    def test_get_submission_due_date_returns_override_when_earlier(
        self, db_session, test_model, admin_user, validation_status_taxonomy,
        validation_type_taxonomy, sla_config
    ):
        """
        INTEGRATION TEST: Verify ValidationRequest.get_submission_due_date()
        actually returns the override date when it's earlier than policy date.

        This tests the real min(policy, override) logic in the system.
        """
        # Create a validation request with a policy date of 60 days out
        policy_date = date.today() + timedelta(days=60)
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            submission_due_date=policy_date  # Store the policy date
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        # Before override: should return policy date
        db_session.refresh(request)
        initial_due_date = request.get_submission_due_date()
        assert initial_due_date == policy_date

        # Create an override with earlier date (30 days)
        override_date = date.today() + timedelta(days=30)
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="ONE_TIME",
            target_scope="CURRENT_REQUEST",
            validation_request_id=request.request_id,
            override_date=override_date,
            original_calculated_date=policy_date,
            reason="Accelerating due to model performance concerns",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        # After override: should return override date (the earlier one)
        db_session.refresh(request)
        effective_due_date = request.get_submission_due_date()

        # CRITICAL ASSERTION: The system must return the override date
        assert effective_due_date is not None
        assert effective_due_date == override_date
        assert effective_due_date < policy_date

    def test_get_submission_due_date_returns_policy_when_earlier(
        self, db_session, test_model, admin_user, validation_status_taxonomy,
        validation_type_taxonomy, sla_config, risk_tier_taxonomy
    ):
        """
        INTEGRATION TEST: Verify that if policy date becomes earlier than
        override date (e.g., risk tier change), the system returns policy date.

        This tests the "earlier-only" enforcement when circumstances change.
        """
        # Create a second risk tier with more frequent validation (6 months instead of 12)
        tier2 = TaxonomyValue(
            taxonomy_id=risk_tier_taxonomy["taxonomy"].taxonomy_id,
            code="TIER_2_HIGH",
            label="Tier 2 - High Priority",
            sort_order=2
        )
        db_session.add(tier2)
        db_session.flush()

        # Create a more aggressive policy for tier2
        policy2 = ValidationPolicy(
            risk_tier_id=tier2.value_id,
            frequency_months=6,  # More frequent than tier1's 12 months
            grace_period_months=2,
            model_change_lead_time_days=60,
            description="High priority tier policy"
        )
        db_session.add(policy2)
        db_session.commit()

        # Create validation request with original policy date
        original_policy_date = date.today() + timedelta(days=60)
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            submission_due_date=original_policy_date
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        # Create override with date of 45 days out
        override_date = date.today() + timedelta(days=45)
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            override_type="PERMANENT",
            target_scope="CURRENT_REQUEST",
            validation_request_id=request.request_id,
            override_date=override_date,
            original_calculated_date=original_policy_date,
            reason="Establishing accelerated schedule",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        # Verify override is being used (45 < 60)
        db_session.refresh(request)
        assert request.get_submission_due_date() == override_date

        # Simulate policy date becoming earlier by updating the stored date
        # (In real scenario, this would happen via risk tier change)
        new_policy_date = date.today() + timedelta(days=30)  # Earlier than override!
        request.submission_due_date = new_policy_date
        db_session.commit()
        db_session.refresh(request)

        # CRITICAL: System must return policy date since it's now earlier
        effective_date = request.get_submission_due_date()
        assert effective_date is not None
        assert effective_date == new_policy_date
        assert effective_date < override_date

    def test_only_one_active_override_per_model(
        self, client, admin_headers, db_session, test_model, admin_user,
        validation_status_taxonomy, validation_type_taxonomy, sla_config
    ):
        """Test that only one active override can exist per model."""
        # First create a validation request so we can create overrides via API
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            submission_due_date=date.today() + timedelta(days=60)
        )
        db_session.add(request)
        db_session.flush()
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        # Create first override via API
        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "ONE_TIME",
                "target_scope": "NEXT_CYCLE",
                "override_date": (date.today() + timedelta(days=30)).isoformat(),
                "reason": "First override created via API"
            }
        )
        assert response.status_code == 201

        # Create second override via API (should supersede first)
        response = client.post(
            f"/models/{test_model.model_id}/due-date-override",
            headers=admin_headers,
            json={
                "override_type": "PERMANENT",
                "target_scope": "NEXT_CYCLE",
                "override_date": (date.today() + timedelta(days=25)).isoformat(),
                "reason": "Second override supersedes first"
            }
        )
        assert response.status_code == 201

        # Verify only one active
        active_count = db_session.query(ModelDueDateOverride).filter_by(
            model_id=test_model.model_id,
            is_active=True
        ).count()
        assert active_count == 1

        # Verify there are 2 total (one superseded, one active)
        total_count = db_session.query(ModelDueDateOverride).filter_by(
            model_id=test_model.model_id
        ).count()
        assert total_count == 2

    @pytest.fixture
    def validation_status_taxonomy(self, db_session):
        """Create validation request status taxonomy."""
        taxonomy = Taxonomy(
            name="Validation Request Status",
            description="Status values for validation requests"
        )
        db_session.add(taxonomy)
        db_session.flush()

        statuses = [
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="INTAKE",
                label="Intake",
                sort_order=1
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="APPROVED",
                label="Approved",
                sort_order=6
            ),
        ]
        for s in statuses:
            db_session.add(s)
        db_session.commit()
        return {
            "taxonomy": taxonomy,
            "intake": statuses[0],
            "approved": statuses[1]
        }

    @pytest.fixture
    def validation_type_taxonomy(self, db_session):
        """Create validation type taxonomy."""
        taxonomy = Taxonomy(
            name="Validation Type",
            description="Types of validation"
        )
        db_session.add(taxonomy)
        db_session.flush()

        val_type = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="COMPREHENSIVE",
            label="Comprehensive Validation",
            sort_order=1
        )
        db_session.add(val_type)
        db_session.commit()
        return {"taxonomy": taxonomy, "comprehensive": val_type}

    @pytest.fixture
    def sla_config(self, db_session):
        """Create SLA configuration."""
        sla = ValidationWorkflowSLA()
        db_session.add(sla)
        db_session.commit()
        return sla


class TestOverrideLifecycle:
    """
    Integration tests for override lifecycle management.

    Tests the workflow integration functions:
    - handle_override_on_approval (ONE_TIME clears, PERMANENT rolls forward)
    - void_override_on_cancellation
    - promote_next_cycle_override
    """

    @pytest.fixture
    def risk_tier_taxonomy(self, db_session):
        """Create risk tier taxonomy with policy."""
        taxonomy = Taxonomy(
            name="Model Risk Tier",
            description="Risk tier classifications"
        )
        db_session.add(taxonomy)
        db_session.flush()

        tier1 = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="TIER_1",
            label="Tier 1 (High)",
            sort_order=1
        )
        db_session.add(tier1)
        db_session.flush()

        policy = ValidationPolicy(
            risk_tier_id=tier1.value_id,
            frequency_months=12,
            grace_period_months=3,
            model_change_lead_time_days=90,
            description="High risk tier policy"
        )
        db_session.add(policy)
        db_session.commit()
        return {"taxonomy": taxonomy, "tier1": tier1, "policy": policy}

    @pytest.fixture
    def validation_status_taxonomy(self, db_session):
        """Create validation request status taxonomy."""
        taxonomy = Taxonomy(
            name="Validation Request Status",
            description="Status values for validation requests"
        )
        db_session.add(taxonomy)
        db_session.flush()

        statuses = [
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="INTAKE",
                label="Intake",
                sort_order=1
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="APPROVED",
                label="Approved",
                sort_order=6
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="CANCELLED",
                label="Cancelled",
                sort_order=8
            ),
        ]
        for s in statuses:
            db_session.add(s)
        db_session.commit()
        return {
            "taxonomy": taxonomy,
            "intake": statuses[0],
            "approved": statuses[1],
            "cancelled": statuses[2]
        }

    @pytest.fixture
    def validation_type_taxonomy(self, db_session):
        """Create validation type taxonomy."""
        taxonomy = Taxonomy(
            name="Validation Type",
            description="Types of validation"
        )
        db_session.add(taxonomy)
        db_session.flush()

        val_type = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="COMPREHENSIVE",
            label="Comprehensive Validation",
            sort_order=1
        )
        db_session.add(val_type)
        db_session.commit()
        return {"taxonomy": taxonomy, "comprehensive": val_type}

    @pytest.fixture
    def sla_config_lifecycle(self, db_session):
        """Create SLA configuration for lifecycle tests."""
        sla = ValidationWorkflowSLA()
        db_session.add(sla)
        db_session.commit()
        return sla

    @pytest.fixture
    def test_model(self, db_session, admin_user, usage_frequency, risk_tier_taxonomy):
        """Create a test model with risk tier."""
        model = Model(
            model_name="Lifecycle Test Model",
            owner_id=admin_user.user_id,
            row_approval_status="approved",
            usage_frequency_id=usage_frequency["daily"].value_id,
            risk_tier_id=risk_tier_taxonomy["tier1"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    @pytest.fixture
    def validation_request_with_override(
        self, db_session, test_model, admin_user,
        validation_status_taxonomy, validation_type_taxonomy, sla_config_lifecycle
    ):
        """Create a validation request with a linked CURRENT_REQUEST override."""
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            submission_due_date=date.today() + timedelta(days=60)
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()
        return request

    def test_handle_override_on_approval_one_time_clears(
        self, db_session, test_model, admin_user, validation_request_with_override
    ):
        """
        LIFECYCLE TEST: ONE_TIME override is cleared (AUTO_VALIDATION_COMPLETE)
        when its linked validation request is approved.
        """
        from app.api.due_date_override import handle_override_on_approval

        request = validation_request_with_override

        # Create a ONE_TIME override linked to this request
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            validation_request_id=request.request_id,
            override_type="ONE_TIME",
            target_scope="CURRENT_REQUEST",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="One-time acceleration for this validation cycle",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        # Verify override is active
        assert override.is_active is True

        # Simulate validation approval by calling the handler
        handle_override_on_approval(db_session, request, admin_user.user_id)
        db_session.commit()

        # CRITICAL: Override must be cleared
        db_session.refresh(override)
        assert override.is_active is False
        assert override.cleared_type == "AUTO_VALIDATION_COMPLETE"
        assert override.cleared_reason is not None
        assert "approved" in override.cleared_reason.lower()

    def test_handle_override_on_approval_permanent_rolls_forward(
        self, db_session, test_model, admin_user, validation_request_with_override,
        risk_tier_taxonomy
    ):
        """
        LIFECYCLE TEST: PERMANENT override creates a new rolled-forward record
        when its linked validation request is approved.

        Verifies:
        - Original override is cleared with AUTO_ROLL_FORWARD
        - New override is created for next cycle
        - New override date = old date + frequency_months
        - Audit trail links (rolled_from_override_id, superseded_by_override_id)
        """
        from app.api.due_date_override import handle_override_on_approval

        request = validation_request_with_override
        original_override_date = date.today() + timedelta(days=30)
        original_policy_date = date.today() + timedelta(days=60)

        # Create a PERMANENT override linked to this request
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            validation_request_id=request.request_id,
            override_type="PERMANENT",
            target_scope="CURRENT_REQUEST",
            override_date=original_override_date,
            original_calculated_date=original_policy_date,
            reason="Permanent accelerated schedule",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()
        original_override_id = override.override_id

        # Simulate validation approval
        handle_override_on_approval(db_session, request, admin_user.user_id)
        db_session.commit()

        # Original override must be cleared with AUTO_ROLL_FORWARD
        db_session.refresh(override)
        assert override.is_active is False
        assert override.cleared_type == "AUTO_ROLL_FORWARD"

        # A new override must be created
        new_override = db_session.query(ModelDueDateOverride).filter(
            ModelDueDateOverride.model_id == test_model.model_id,
            ModelDueDateOverride.is_active == True
        ).first()

        assert new_override is not None
        assert new_override.override_id != original_override_id
        assert new_override.override_type == "PERMANENT"
        assert new_override.target_scope == "NEXT_CYCLE"

        # New override date should be original + frequency_months (12 months)
        from dateutil.relativedelta import relativedelta
        expected_new_date = original_override_date + relativedelta(months=12)
        assert new_override.override_date == expected_new_date

        # Audit trail links must be preserved
        assert new_override.rolled_from_override_id == original_override_id
        assert override.superseded_by_override_id == new_override.override_id

    def test_void_override_on_cancellation(
        self, db_session, test_model, admin_user, validation_request_with_override
    ):
        """
        LIFECYCLE TEST: Override is voided (AUTO_REQUEST_CANCELLED) when
        its linked validation request is cancelled.
        """
        from app.api.due_date_override import void_override_on_cancellation

        request = validation_request_with_override

        # Create an override linked to this request
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            validation_request_id=request.request_id,
            override_type="ONE_TIME",
            target_scope="CURRENT_REQUEST",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Override that will be voided",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        # Verify override is active
        assert override.is_active is True

        # Simulate validation cancellation
        void_override_on_cancellation(db_session, request, admin_user.user_id)
        db_session.commit()

        # CRITICAL: Override must be voided
        db_session.refresh(override)
        assert override.is_active is False
        assert override.cleared_type == "AUTO_REQUEST_CANCELLED"
        assert override.cleared_reason is not None
        assert "cancelled" in override.cleared_reason.lower()

    def test_promote_next_cycle_override(
        self, db_session, test_model, admin_user, validation_status_taxonomy,
        validation_type_taxonomy, sla_config_lifecycle
    ):
        """
        LIFECYCLE TEST: NEXT_CYCLE override is promoted to CURRENT_REQUEST
        when a new validation request is created for the model.
        """
        from app.api.due_date_override import promote_next_cycle_override

        # Create a NEXT_CYCLE override (no validation request yet)
        override = ModelDueDateOverride(
            model_id=test_model.model_id,
            validation_request_id=None,  # Not linked to any request
            override_type="PERMANENT",
            target_scope="NEXT_CYCLE",
            override_date=date.today() + timedelta(days=30),
            original_calculated_date=date.today() + timedelta(days=60),
            reason="Waiting for next validation cycle",
            created_by_user_id=admin_user.user_id,
            is_active=True
        )
        db_session.add(override)
        db_session.commit()

        # Verify initial state
        assert override.target_scope == "NEXT_CYCLE"
        assert override.validation_request_id is None

        # Create a new validation request
        new_request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=90),
            submission_due_date=date.today() + timedelta(days=60)
        )
        db_session.add(new_request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=new_request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()

        # Simulate the promotion that would happen when a new request is created
        promote_next_cycle_override(
            db_session, test_model.model_id, new_request.request_id, admin_user.user_id
        )
        db_session.commit()

        # CRITICAL: Override must be promoted
        db_session.refresh(override)
        assert override.target_scope == "CURRENT_REQUEST"
        assert override.validation_request_id == new_request.request_id
        assert override.is_active is True  # Still active, just promoted
