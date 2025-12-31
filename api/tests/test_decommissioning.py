"""Tests for Model Decommissioning API."""
import pytest
from datetime import date, timedelta
from app.models.model import Model
from app.models.user import User
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model_version import ModelVersion
from app.models.decommissioning import (
    DecommissioningRequest, DecommissioningStatusHistory, DecommissioningApproval
)
from app.core.security import get_password_hash, create_access_token
from app.core.roles import RoleCode
from app.models.role import Role


def get_role_id(db_session, role_code: str) -> int:
    return db_session.query(Role).filter(Role.code == role_code).first().role_id


class TestDecommissioningAPI:
    """Tests for the Decommissioning API endpoints."""

    @pytest.fixture
    def decommission_reason_taxonomy(self, db_session):
        """Create Model Decommission Reason taxonomy."""
        taxonomy = Taxonomy(
            name="Model Decommission Reason",
            description="Reasons for decommissioning a model"
        )
        db_session.add(taxonomy)
        db_session.flush()

        reasons = [
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="REPLACEMENT",
                label="Replaced by New Model",
                sort_order=1
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="CONSOLIDATION",
                label="Consolidated into Another Model",
                sort_order=2
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="OBSOLETE",
                label="Business Process Obsolete",
                sort_order=3
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="REGULATORY",
                label="Regulatory Change",
                sort_order=4
            ),
        ]
        for r in reasons:
            db_session.add(r)
        db_session.commit()
        return {
            "taxonomy": taxonomy,
            "replacement": reasons[0],
            "consolidation": reasons[1],
            "obsolete": reasons[2],
            "regulatory": reasons[3]
        }

    @pytest.fixture
    def model_status_taxonomy(self, db_session):
        """Create Model Status taxonomy."""
        taxonomy = Taxonomy(
            name="Model Status",
            description="Model lifecycle status"
        )
        db_session.add(taxonomy)
        db_session.flush()

        statuses = [
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="ACTIVE",
                label="Active",
                sort_order=1
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="DECOMMISSIONING",
                label="Pending Decommission",
                sort_order=2
            ),
            TaxonomyValue(
                taxonomy_id=taxonomy.taxonomy_id,
                code="RETIRED",
                label="Retired",
                sort_order=3
            ),
        ]
        for s in statuses:
            db_session.add(s)
        db_session.commit()
        return {
            "taxonomy": taxonomy,
            "active": statuses[0],
            "decommissioning": statuses[1],
            "retired": statuses[2]
        }

    @pytest.fixture
    def validator_user(self, db_session, lob_hierarchy):
        """Create a validator user."""
        user = User(
            email="validator@example.com",
            full_name="Validator User",
            password_hash=get_password_hash("validator123"),
            role_id=get_role_id(db_session, RoleCode.VALIDATOR.value),
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def validator_headers(self, validator_user):
        """Get auth headers for validator."""
        token = create_access_token(data={"sub": validator_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_model(self, db_session, admin_user, model_status_taxonomy, usage_frequency):
        """Create a test model for decommissioning."""
        model = Model(
            model_name="Test Model for Decommission",
            owner_id=admin_user.user_id,
            status="Active",
            status_id=model_status_taxonomy["active"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    @pytest.fixture
    def replacement_model(self, db_session, admin_user, model_status_taxonomy, usage_frequency):
        """Create a replacement model."""
        model = Model(
            model_name="Replacement Model",
            owner_id=admin_user.user_id,
            status="Active",
            status_id=model_status_taxonomy["active"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.flush()

        # Add version with implementation date
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="INITIAL",
            change_description="Initial version",
            created_by_id=admin_user.user_id,
            production_date=date.today() + timedelta(days=30),
            status="ACTIVE",
            scope="GLOBAL"
        )
        db_session.add(version)
        db_session.commit()
        return model

    @pytest.fixture
    def test_region(self, db_session):
        """Create a test region."""
        region = Region(
            code="US",
            name="United States",
            requires_regional_approval=True
        )
        db_session.add(region)
        db_session.commit()
        return region

    # --- List/Read Tests ---

    def test_list_decommissioning_requests_empty(
        self, client, admin_headers, decommission_reason_taxonomy
    ):
        """Test listing decommissioning requests when none exist."""
        response = client.get("/decommissioning/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_implementation_date_no_version(
        self, client, admin_headers, test_model
    ):
        """Test getting implementation date for model without version."""
        response = client.get(
            f"/decommissioning/models/{test_model.model_id}/implementation-date",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == test_model.model_id
        assert data["has_implementation_date"] is False
        assert data["implementation_date"] is None

    def test_get_implementation_date_with_version(
        self, client, admin_headers, replacement_model
    ):
        """Test getting implementation date for model with version."""
        response = client.get(
            f"/decommissioning/models/{replacement_model.model_id}/implementation-date",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == replacement_model.model_id
        assert data["has_implementation_date"] is True
        assert data["implementation_date"] is not None

    # --- Create Tests ---

    def test_create_decommissioning_request_obsolete(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test creating decommissioning request with OBSOLETE reason (no replacement needed)."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        response = client.post("/decommissioning/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["model_id"] == test_model.model_id
        assert data["status"] == "PENDING"
        assert data["replacement_model_id"] is None

    def test_create_decommissioning_request_replacement_required(
        self, client, admin_headers, test_model, replacement_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test creating decommissioning request with REPLACEMENT reason (replacement required)."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["replacement"].value_id,
            "replacement_model_id": replacement_model.model_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        response = client.post("/decommissioning/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["replacement_model_id"] == replacement_model.model_id

    def test_create_decommissioning_request_replacement_missing(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test that REPLACEMENT reason fails without replacement model."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["replacement"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        response = client.post("/decommissioning/", json=payload, headers=admin_headers)
        assert response.status_code == 400
        assert "requires a replacement model" in response.json()["detail"]

    def test_create_decommissioning_request_downstream_not_verified(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test that request fails if downstream impact not verified."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": False
        }
        response = client.post("/decommissioning/", json=payload, headers=admin_headers)
        assert response.status_code == 400
        assert "verify downstream impact" in response.json()["detail"]

    def test_create_decommissioning_request_duplicate(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test that duplicate pending requests are rejected."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        # First request succeeds
        response1 = client.post("/decommissioning/", json=payload, headers=admin_headers)
        assert response1.status_code == 201

        # Second request fails
        response2 = client.post("/decommissioning/", json=payload, headers=admin_headers)
        assert response2.status_code == 400
        assert "pending decommissioning request" in response2.json()["detail"]

    # --- Validator Review Tests ---

    def test_validator_review_approve(
        self, client, admin_headers, validator_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy, test_region, db_session
    ):
        """Test validator approving a decommissioning request."""
        # Add region to model
        model_region = ModelRegion(model_id=test_model.model_id, region_id=test_region.region_id)
        db_session.add(model_region)
        db_session.commit()

        # Create request
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Validator approves
        review_resp = client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": True, "comment": "Looks good"},
            headers=validator_headers
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == "VALIDATOR_APPROVED"

        # Verify approval records created
        detail_resp = client.get(f"/decommissioning/{request_id}", headers=admin_headers)
        approvals = detail_resp.json()["approvals"]
        assert len(approvals) >= 1  # At least GLOBAL
        assert any(a["approver_type"] == "GLOBAL" for a in approvals)

    def test_validator_review_reject(
        self, client, admin_headers, validator_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test validator rejecting a decommissioning request."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Validator rejects
        review_resp = client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": False, "comment": "Incomplete documentation"},
            headers=validator_headers
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == "REJECTED"

    def test_validator_review_requires_comment(
        self, client, admin_headers, validator_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test that validator review requires a comment."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Try to approve without comment
        review_resp = client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": True, "comment": ""},
            headers=validator_headers
        )
        assert review_resp.status_code == 422  # Validation error

    # --- Withdraw Tests ---

    def test_withdraw_request(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test withdrawing a decommissioning request."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Withdraw
        withdraw_resp = client.post(
            f"/decommissioning/{request_id}/withdraw",
            json={"reason": "Plans changed"},
            headers=admin_headers
        )
        assert withdraw_resp.status_code == 200
        assert withdraw_resp.json()["status"] == "WITHDRAWN"

    def test_withdraw_only_by_creator_or_admin(
        self, client, admin_headers, auth_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test that only creator or admin can withdraw."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Regular user tries to withdraw
        withdraw_resp = client.post(
            f"/decommissioning/{request_id}/withdraw",
            json={"reason": "I want to withdraw"},
            headers=auth_headers
        )
        assert withdraw_resp.status_code == 403

    # --- Dashboard Tests ---

    def test_pending_validator_review_dashboard(
        self, client, validator_headers, admin_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test getting pending validator review items."""
        # Create a request
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        client.post("/decommissioning/", json=payload, headers=admin_headers)

        # Get pending items
        response = client.get("/decommissioning/pending-validator-review", headers=validator_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_pending_validator_review_not_accessible_by_regular_user(
        self, client, auth_headers
    ):
        """Test that regular users cannot access validator review dashboard."""
        response = client.get("/decommissioning/pending-validator-review", headers=auth_headers)
        assert response.status_code == 403

    # --- Status History Tests ---

    def test_status_history_tracked(
        self, client, admin_headers, validator_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test that status changes are tracked in history."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Verify initial history
        detail_resp = client.get(f"/decommissioning/{request_id}", headers=admin_headers)
        history = detail_resp.json()["status_history"]
        assert len(history) == 1
        assert history[0]["new_status"] == "PENDING"

        # Validator approves
        client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": True, "comment": "Approved"},
            headers=validator_headers
        )

        # Verify history updated
        detail_resp2 = client.get(f"/decommissioning/{request_id}", headers=admin_headers)
        history2 = detail_resp2.json()["status_history"]
        assert len(history2) == 2
        assert history2[-1]["new_status"] == "VALIDATOR_APPROVED"

    # --- Owner Approval Tests (Dual Approval Workflow) ---

    @pytest.fixture
    def non_owner_user(self, db_session, lob_hierarchy):
        """Create a non-owner user who can initiate decommissioning."""
        user = User(
            email="nonowner@example.com",
            full_name="Non Owner User",
            password_hash=get_password_hash("nonowner123"),
            role_id=get_role_id(db_session, RoleCode.USER.value),
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def non_owner_headers(self, non_owner_user):
        """Get auth headers for non-owner user."""
        token = create_access_token(data={"sub": non_owner_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def owner_user(self, db_session, lob_hierarchy):
        """Create a model owner user."""
        user = User(
            email="owner@example.com",
            full_name="Model Owner",
            password_hash=get_password_hash("owner123"),
            role_id=get_role_id(db_session, RoleCode.USER.value),
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def owner_headers(self, owner_user):
        """Get auth headers for model owner."""
        token = create_access_token(data={"sub": owner_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def owner_model(self, db_session, owner_user, model_status_taxonomy, usage_frequency):
        """Create a model owned by owner_user."""
        model = Model(
            model_name="Owner's Model",
            owner_id=owner_user.user_id,
            status="Active",
            status_id=model_status_taxonomy["active"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    def test_owner_approval_required_when_requestor_not_owner(
        self, client, non_owner_headers, admin_headers, owner_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test owner_approval_required is True when requestor != owner."""
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        # Non-owner creates the request
        response = client.post("/decommissioning/", json=payload, headers=admin_headers)
        # Admin is not the owner, so owner_approval_required should be True
        assert response.status_code == 201
        data = response.json()
        assert data["owner_approval_required"] is True

    def test_owner_approval_not_required_when_requestor_is_owner(
        self, client, owner_headers, owner_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test owner_approval_required is False when requestor == owner."""
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        # Owner creates the request
        response = client.post("/decommissioning/", json=payload, headers=owner_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["owner_approval_required"] is False

    def test_owner_review_approve(
        self, client, admin_headers, owner_headers, validator_headers,
        owner_model, decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test model owner can approve their review."""
        # Admin creates request (not owner, so owner approval required)
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]
        assert create_resp.json()["owner_approval_required"] is True

        # Owner approves first
        owner_review_resp = client.post(
            f"/decommissioning/{request_id}/owner-review",
            json={"approved": True, "comment": "I approve this decommissioning"},
            headers=owner_headers
        )
        assert owner_review_resp.status_code == 200
        # Status should still be PENDING (awaiting validator)
        assert owner_review_resp.json()["status"] == "PENDING"

        # Verify owner review recorded
        detail_resp = client.get(f"/decommissioning/{request_id}", headers=admin_headers)
        assert detail_resp.json()["owner_reviewed_at"] is not None
        assert detail_resp.json()["owner_comment"] == "I approve this decommissioning"

    def test_owner_review_reject_terminates_workflow(
        self, client, admin_headers, owner_headers, owner_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test owner rejection terminates the workflow."""
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Owner rejects
        owner_review_resp = client.post(
            f"/decommissioning/{request_id}/owner-review",
            json={"approved": False, "comment": "I do not approve this"},
            headers=owner_headers
        )
        assert owner_review_resp.status_code == 200
        assert owner_review_resp.json()["status"] == "REJECTED"

    def test_dual_approval_owner_first_then_validator(
        self, client, admin_headers, owner_headers, validator_headers,
        owner_model, decommission_reason_taxonomy, model_status_taxonomy, test_region, db_session
    ):
        """Test dual approval flow: owner approves first, then validator."""
        # Add region to model
        model_region = ModelRegion(model_id=owner_model.model_id, region_id=test_region.region_id)
        db_session.add(model_region)
        db_session.commit()

        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Owner approves first - status stays PENDING
        owner_resp = client.post(
            f"/decommissioning/{request_id}/owner-review",
            json={"approved": True, "comment": "Owner approves"},
            headers=owner_headers
        )
        assert owner_resp.json()["status"] == "PENDING"

        # Validator approves - now should move to VALIDATOR_APPROVED
        validator_resp = client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": True, "comment": "Validator approves"},
            headers=validator_headers
        )
        assert validator_resp.json()["status"] == "VALIDATOR_APPROVED"

        # Verify approvals created
        detail_resp = client.get(f"/decommissioning/{request_id}", headers=admin_headers)
        assert len(detail_resp.json()["approvals"]) >= 1

    def test_dual_approval_validator_first_then_owner(
        self, client, admin_headers, owner_headers, validator_headers,
        owner_model, decommission_reason_taxonomy, model_status_taxonomy, test_region, db_session
    ):
        """Test dual approval flow: validator approves first, then owner."""
        # Add region to model
        model_region = ModelRegion(model_id=owner_model.model_id, region_id=test_region.region_id)
        db_session.add(model_region)
        db_session.commit()

        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Validator approves first - status stays PENDING (owner still needed)
        validator_resp = client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": True, "comment": "Validator approves"},
            headers=validator_headers
        )
        assert validator_resp.json()["status"] == "PENDING"

        # Owner approves - now should move to VALIDATOR_APPROVED
        owner_resp = client.post(
            f"/decommissioning/{request_id}/owner-review",
            json={"approved": True, "comment": "Owner approves"},
            headers=owner_headers
        )
        assert owner_resp.json()["status"] == "VALIDATOR_APPROVED"

    def test_owner_review_not_allowed_when_not_required(
        self, client, owner_headers, owner_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test that owner-review fails when owner_approval_required is False."""
        # Owner creates request (owner == requestor, so not required)
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=owner_headers)
        request_id = create_resp.json()["request_id"]
        assert create_resp.json()["owner_approval_required"] is False

        # Try owner review - should fail
        owner_review_resp = client.post(
            f"/decommissioning/{request_id}/owner-review",
            json={"approved": True, "comment": "Trying to review"},
            headers=owner_headers
        )
        assert owner_review_resp.status_code == 400
        assert "not required" in owner_review_resp.json()["detail"]

    def test_owner_review_only_by_owner_or_admin(
        self, client, admin_headers, non_owner_headers, owner_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test that only model owner or admin can submit owner review."""
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Non-owner tries to submit owner review - should fail
        review_resp = client.post(
            f"/decommissioning/{request_id}/owner-review",
            json={"approved": True, "comment": "Trying to review"},
            headers=non_owner_headers
        )
        assert review_resp.status_code == 403
        assert "model owner" in review_resp.json()["detail"]

    # --- Update (PATCH) Tests ---

    def test_update_decommissioning_request_success(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test successfully updating a decommissioning request."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Update archive_location
        update_resp = client.patch(
            f"/decommissioning/{request_id}",
            json={"archive_location": "s3://archive/models/updated-location"},
            headers=admin_headers
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["archive_location"] == "s3://archive/models/updated-location"

    def test_update_decommissioning_request_multiple_fields(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test updating multiple fields at once."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        new_date = date.today() + timedelta(days=90)
        update_resp = client.patch(
            f"/decommissioning/{request_id}",
            json={
                "archive_location": "s3://new/location",
                "last_production_date": str(new_date),
                "gap_justification": "Extended timeline agreed upon"
            },
            headers=admin_headers
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["archive_location"] == "s3://new/location"
        assert data["last_production_date"] == str(new_date)
        assert data["gap_justification"] == "Extended timeline agreed upon"

    def test_update_only_allowed_when_pending(
        self, client, admin_headers, validator_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test that updates are only allowed when status is PENDING."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Validator approves - moves to VALIDATOR_APPROVED
        client.post(
            f"/decommissioning/{request_id}/validator-review",
            json={"approved": True, "comment": "Looks good"},
            headers=validator_headers
        )

        # Try to update - should fail
        update_resp = client.patch(
            f"/decommissioning/{request_id}",
            json={"archive_location": "s3://new/location"},
            headers=admin_headers
        )
        assert update_resp.status_code == 400
        assert "PENDING" in update_resp.json()["detail"]

    def test_update_only_by_creator_or_admin(
        self, client, admin_headers, auth_headers, test_model,
        decommission_reason_taxonomy, model_status_taxonomy
    ):
        """Test that only the creator or Admin can update."""
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        # Admin creates the request
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Regular user tries to update - should fail
        update_resp = client.patch(
            f"/decommissioning/{request_id}",
            json={"archive_location": "s3://new/location"},
            headers=auth_headers
        )
        assert update_resp.status_code == 403
        assert "creator or Admin" in update_resp.json()["detail"]

    def test_update_reason_validates_replacement_requirement(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test that changing to a reason requiring replacement enforces that rule."""
        # Start with OBSOLETE (no replacement needed)
        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Try to change to REPLACEMENT without providing replacement_model_id
        update_resp = client.patch(
            f"/decommissioning/{request_id}",
            json={"reason_id": decommission_reason_taxonomy["replacement"].value_id},
            headers=admin_headers
        )
        assert update_resp.status_code == 400
        assert "requires a replacement model" in update_resp.json()["detail"]

    def test_update_creates_audit_log(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy, db_session
    ):
        """Test that updating a request creates an audit log entry."""
        from app.models import AuditLog

        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Update the request
        client.patch(
            f"/decommissioning/{request_id}",
            json={"archive_location": "s3://new/location"},
            headers=admin_headers
        )

        # Verify audit log was created
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "DecommissioningRequest",
            AuditLog.entity_id == request_id,
            AuditLog.action == "UPDATE"
        ).all()
        assert len(audit_logs) == 1
        assert "fields_changed" in audit_logs[0].changes
        assert "archive_location" in audit_logs[0].changes["fields_changed"]
        assert audit_logs[0].changes["fields_changed"]["archive_location"]["old"] == "s3://archive/models/test"
        assert audit_logs[0].changes["fields_changed"]["archive_location"]["new"] == "s3://new/location"

    def test_update_no_changes_no_audit_log(
        self, client, admin_headers, test_model, decommission_reason_taxonomy,
        model_status_taxonomy, db_session
    ):
        """Test that updating with same values doesn't create audit log."""
        from app.models import AuditLog

        payload = {
            "model_id": test_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        create_resp = client.post("/decommissioning/", json=payload, headers=admin_headers)
        request_id = create_resp.json()["request_id"]

        # Count existing audit logs
        initial_count = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "DecommissioningRequest",
            AuditLog.entity_id == request_id,
            AuditLog.action == "UPDATE"
        ).count()

        # Update with same value
        client.patch(
            f"/decommissioning/{request_id}",
            json={"archive_location": "s3://archive/models/test"},  # Same value
            headers=admin_headers
        )

        # Verify no new audit log was created
        final_count = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "DecommissioningRequest",
            AuditLog.entity_id == request_id,
            AuditLog.action == "UPDATE"
        ).count()
        assert final_count == initial_count

    def test_update_request_not_found(
        self, client, admin_headers, decommission_reason_taxonomy
    ):
        """Test updating a non-existent request returns 404."""
        update_resp = client.patch(
            "/decommissioning/99999",
            json={"archive_location": "s3://new/location"},
            headers=admin_headers
        )
        assert update_resp.status_code == 404

    def test_creator_can_update_own_request(
        self, client, owner_headers, owner_model, decommission_reason_taxonomy,
        model_status_taxonomy
    ):
        """Test that the request creator (non-admin) can update their own request."""
        payload = {
            "model_id": owner_model.model_id,
            "reason_id": decommission_reason_taxonomy["obsolete"].value_id,
            "last_production_date": str(date.today() + timedelta(days=60)),
            "archive_location": "s3://archive/models/test",
            "downstream_impact_verified": True
        }
        # Owner creates the request
        create_resp = client.post("/decommissioning/", json=payload, headers=owner_headers)
        request_id = create_resp.json()["request_id"]

        # Owner updates their own request
        update_resp = client.patch(
            f"/decommissioning/{request_id}",
            json={"archive_location": "s3://updated/by/creator"},
            headers=owner_headers
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["archive_location"] == "s3://updated/by/creator"
