"""Tests for Overdue Revalidation Commentary API."""
import pytest
from datetime import date, datetime, timedelta
from app.models.overdue_comment import OverdueRevalidationComment
from app.models.model import Model
from app.models.user import User
from app.models.validation import (
    ValidationRequest, ValidationRequestModelVersion, ValidationAssignment,
    ValidationWorkflowSLA
)
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model_delegate import ModelDelegate
from app.core.security import get_password_hash, create_access_token


class TestOverdueCommentaryAPI:
    """Tests for the Overdue Commentary API endpoints."""

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
                code="IN_PROGRESS",
                label="In Progress",
                sort_order=2
            ),
        ]
        for s in statuses:
            db_session.add(s)
        db_session.commit()
        return {"taxonomy": taxonomy, "intake": statuses[0], "in_progress": statuses[1]}

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
    def test_model_for_commentary(self, db_session, admin_user):
        """Create a test model for commentary tests."""
        model = Model(
            model_name="Test Model for Commentary",
            owner_id=admin_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.commit()
        return model

    @pytest.fixture
    def sla_config(self, db_session):
        """Create SLA configuration."""
        sla = ValidationWorkflowSLA(
            model_change_lead_time_days=90
        )
        db_session.add(sla)
        db_session.commit()
        return sla

    @pytest.fixture
    def validation_request_pre_submission(
        self, db_session, test_model_for_commentary, admin_user,
        validation_status_taxonomy, validation_type_taxonomy, sla_config
    ):
        """Create a validation request in pre-submission state (no submission_received_date)."""
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["intake"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,  # Using intake as priority placeholder
            target_completion_date=date.today() + timedelta(days=90),
            submission_received_date=None  # Pre-submission
        )
        db_session.add(request)
        db_session.flush()

        # Link model to request
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model_for_commentary.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()
        return request

    @pytest.fixture
    def validation_request_in_progress(
        self, db_session, test_model_for_commentary, admin_user,
        validation_status_taxonomy, validation_type_taxonomy, sla_config
    ):
        """Create a validation request in progress (has submission_received_date)."""
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_type_taxonomy["comprehensive"].value_id,
            current_status_id=validation_status_taxonomy["in_progress"].value_id,
            priority_id=validation_status_taxonomy["intake"].value_id,  # Using intake as priority placeholder
            target_completion_date=date.today() + timedelta(days=60),
            submission_received_date=date.today() - timedelta(days=10)  # Already submitted
        )
        db_session.add(request)
        db_session.flush()

        # Link model to request
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model_for_commentary.model_id,
            version_id=None
        )
        db_session.add(link)
        db_session.commit()
        return request

    def test_get_overdue_commentary_empty(
        self, client, admin_headers, validation_request_pre_submission
    ):
        """Test getting commentary when none exists."""
        response = client.get(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_current_comment"] is False
        assert data["current_comment"] is None
        assert data["overdue_type"] == "PRE_SUBMISSION"
        assert data["is_stale"] is False

    def test_get_overdue_commentary_in_progress(
        self, client, admin_headers, validation_request_in_progress
    ):
        """Test getting commentary for in-progress validation."""
        response = client.get(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overdue_type"] == "VALIDATION_IN_PROGRESS"

    def test_create_pre_submission_commentary(
        self, client, admin_headers, validation_request_pre_submission
    ):
        """Test creating pre-submission commentary."""
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Waiting for additional data from business unit before submission.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason_comment"] == payload["reason_comment"]
        assert data["overdue_type"] == "PRE_SUBMISSION"
        assert data["is_current"] is True

    def test_create_in_progress_commentary(
        self, client, admin_headers, validation_request_in_progress
    ):
        """Test creating in-progress commentary."""
        payload = {
            "overdue_type": "VALIDATION_IN_PROGRESS",
            "reason_comment": "Extended testing required due to model complexity.",
            "target_date": (date.today() + timedelta(days=45)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason_comment"] == payload["reason_comment"]
        assert data["overdue_type"] == "VALIDATION_IN_PROGRESS"

    def test_create_commentary_wrong_type_pre_submission(
        self, client, admin_headers, validation_request_pre_submission
    ):
        """Test that VALIDATION_IN_PROGRESS cannot be used before submission."""
        payload = {
            "overdue_type": "VALIDATION_IN_PROGRESS",
            "reason_comment": "This should fail - validation not in progress yet.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "before submission" in response.json()["detail"].lower()

    def test_create_commentary_wrong_type_in_progress(
        self, client, admin_headers, validation_request_in_progress
    ):
        """Test that PRE_SUBMISSION cannot be used after submission."""
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "This should fail - already submitted.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "after submission" in response.json()["detail"].lower()

    def test_create_commentary_past_target_date(
        self, client, admin_headers, validation_request_pre_submission
    ):
        """Test that target date must be in the future."""
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "This should fail - past target date.",
            "target_date": (date.today() - timedelta(days=1)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "future" in response.json()["detail"].lower()

    def test_create_commentary_short_reason(
        self, client, admin_headers, validation_request_pre_submission
    ):
        """Test that reason comment must be at least 10 characters."""
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Too short",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 422  # Validation error

    def test_commentary_supersedes_previous(
        self, client, admin_headers, validation_request_pre_submission, db_session
    ):
        """Test that new commentary supersedes previous."""
        # Create first comment
        payload1 = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "First explanation for the delay in submission.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response1 = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload1,
            headers=admin_headers
        )
        assert response1.status_code == 201
        first_comment_id = response1.json()["comment_id"]

        # Create second comment
        payload2 = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Updated explanation - additional delays encountered.",
            "target_date": (date.today() + timedelta(days=45)).isoformat()
        }
        response2 = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload2,
            headers=admin_headers
        )
        assert response2.status_code == 201
        second_comment_id = response2.json()["comment_id"]

        # Verify first comment is superseded
        first_comment = db_session.query(OverdueRevalidationComment).filter(
            OverdueRevalidationComment.comment_id == first_comment_id
        ).first()
        assert first_comment.is_current is False
        assert first_comment.superseded_by_comment_id == second_comment_id

        # Verify second comment is current
        second_comment = db_session.query(OverdueRevalidationComment).filter(
            OverdueRevalidationComment.comment_id == second_comment_id
        ).first()
        assert second_comment.is_current is True

    def test_get_commentary_history(
        self, client, admin_headers, validation_request_pre_submission
    ):
        """Test getting commentary history."""
        # Create multiple comments
        for i in range(3):
            payload = {
                "overdue_type": "PRE_SUBMISSION",
                "reason_comment": f"Commentary update number {i+1} explaining delays.",
                "target_date": (date.today() + timedelta(days=30 + i*10)).isoformat()
            }
            client.post(
                f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
                json=payload,
                headers=admin_headers
            )

        # Get history
        response = client.get(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary/history",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_comment"] is not None
        assert len(data["comment_history"]) == 2  # 2 superseded comments

    def test_get_model_overdue_commentary(
        self, client, admin_headers, validation_request_pre_submission, test_model_for_commentary
    ):
        """Test getting overdue commentary via model convenience endpoint."""
        # Create a comment first
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Commentary for model convenience endpoint test.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )

        # Get via model endpoint
        response = client.get(
            f"/models/{test_model_for_commentary.model_id}/overdue-commentary",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == test_model_for_commentary.model_id
        assert data["has_current_comment"] is True
        assert data["current_comment"]["reason_comment"] == payload["reason_comment"]

    def test_get_model_overdue_commentary_no_request(
        self, client, admin_headers, db_session, admin_user
    ):
        """Test model convenience endpoint when no validation request exists."""
        # Create model without validation request
        model = Model(
            model_name="Model Without Validation",
            owner_id=admin_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.commit()

        response = client.get(
            f"/models/{model.model_id}/overdue-commentary",
            headers=admin_headers
        )
        assert response.status_code == 404
        assert "no validation request" in response.json()["detail"].lower()

    def test_non_admin_owner_can_create_pre_submission(
        self, client, db_session, validation_request_pre_submission, test_model_for_commentary
    ):
        """Test that model owner can create PRE_SUBMISSION commentary."""
        # Create a regular user who owns the model
        owner = User(
            email="owner_commentary@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Model Owner",
            role="User"
        )
        db_session.add(owner)
        db_session.flush()

        # Update model ownership
        test_model_for_commentary.owner_id = owner.user_id
        db_session.commit()

        token = create_access_token(data={"sub": owner.email})
        owner_headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Owner submitting pre-submission commentary.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=owner_headers
        )
        assert response.status_code == 201

    def test_non_owner_cannot_create_pre_submission(
        self, client, db_session, validation_request_pre_submission
    ):
        """Test that non-owner cannot create PRE_SUBMISSION commentary."""
        other_user = User(
            email="other_commentary@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Other User",
            role="User"
        )
        db_session.add(other_user)
        db_session.commit()

        token = create_access_token(data={"sub": other_user.email})
        other_headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "This should fail - not owner or developer.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=other_headers
        )
        assert response.status_code == 403

    def test_delegate_can_create_pre_submission(
        self, client, db_session, validation_request_pre_submission, test_model_for_commentary
    ):
        """Test that model delegate can create PRE_SUBMISSION commentary."""
        delegate_user = User(
            email="delegate_commentary@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Delegate User",
            role="User"
        )
        db_session.add(delegate_user)
        db_session.flush()

        # Add as delegate
        delegate = ModelDelegate(
            model_id=test_model_for_commentary.model_id,
            user_id=delegate_user.user_id,
            delegated_by_id=test_model_for_commentary.owner_id
        )
        db_session.add(delegate)
        db_session.commit()

        token = create_access_token(data={"sub": delegate_user.email})
        delegate_headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Delegate submitting pre-submission commentary.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=delegate_headers
        )
        assert response.status_code == 201

    def test_assigned_validator_can_create_in_progress(
        self, client, db_session, validation_request_in_progress
    ):
        """Test that assigned validator can create VALIDATION_IN_PROGRESS commentary."""
        validator = User(
            email="validator_commentary@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Validator User",
            role="Validator"
        )
        db_session.add(validator)
        db_session.flush()

        # Assign validator
        assignment = ValidationAssignment(
            request_id=validation_request_in_progress.request_id,
            validator_id=validator.user_id,
            is_primary=True,
            is_reviewer=False
        )
        db_session.add(assignment)
        db_session.commit()

        token = create_access_token(data={"sub": validator.email})
        validator_headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "overdue_type": "VALIDATION_IN_PROGRESS",
            "reason_comment": "Validator needs more time for comprehensive review.",
            "target_date": (date.today() + timedelta(days=45)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 201

    def test_unassigned_validator_cannot_create_in_progress(
        self, client, db_session, validation_request_in_progress
    ):
        """Test that unassigned validator cannot create VALIDATION_IN_PROGRESS commentary."""
        validator = User(
            email="unassigned_validator@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Unassigned Validator",
            role="Validator"
        )
        db_session.add(validator)
        db_session.commit()

        # NOT assigning this validator to the request

        token = create_access_token(data={"sub": validator.email})
        validator_headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "overdue_type": "VALIDATION_IN_PROGRESS",
            "reason_comment": "This should fail - not assigned to this validation.",
            "target_date": (date.today() + timedelta(days=45)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 403

    def test_validation_request_not_found(self, client, admin_headers):
        """Test 404 for non-existent validation request."""
        response = client.get(
            "/validation-workflow/requests/99999/overdue-commentary",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_unauthenticated_access_denied(self, client, validation_request_pre_submission):
        """Test that unauthenticated requests are denied."""
        response = client.get(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary"
        )
        assert response.status_code in (401, 403)

    def test_computed_completion_date_pre_submission(
        self, client, admin_headers, validation_request_pre_submission, sla_config
    ):
        """Test computed completion date for pre-submission (target + lead time)."""
        target_date = date.today() + timedelta(days=30)
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Testing computed completion date calculation.",
            "target_date": target_date.isoformat()
        }
        client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )

        response = client.get(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            headers=admin_headers
        )
        data = response.json()

        # Computed completion = target_date + lead_time (90 days from sla_config)
        expected_completion = target_date + timedelta(days=90)
        assert data["computed_completion_date"] == expected_completion.isoformat()

    def test_computed_completion_date_in_progress(
        self, client, admin_headers, validation_request_in_progress
    ):
        """Test computed completion date for in-progress (use request's target)."""
        response = client.get(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            headers=admin_headers
        )
        data = response.json()

        # Computed completion should be the validation request's target_completion_date
        expected = validation_request_in_progress.target_completion_date.isoformat()
        assert data["computed_completion_date"] == expected

    def test_admin_can_create_pre_submission_for_non_owned_model(
        self, client, admin_headers, db_session, validation_request_pre_submission, test_model_for_commentary
    ):
        """Test that Admin can create PRE_SUBMISSION commentary even for models they don't own."""
        # Create a different user to be the model owner
        other_owner = User(
            email="other_owner_admin_test@example.com",
            password_hash=get_password_hash("testpass"),
            full_name="Other Owner",
            role="User"
        )
        db_session.add(other_owner)
        db_session.flush()

        # Change model ownership to someone else (admin is NOT the owner)
        test_model_for_commentary.owner_id = other_owner.user_id
        db_session.commit()

        # Admin should still be able to create commentary on behalf of the owner
        payload = {
            "overdue_type": "PRE_SUBMISSION",
            "reason_comment": "Admin providing update on behalf of model owner.",
            "target_date": (date.today() + timedelta(days=30)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_pre_submission.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason_comment"] == payload["reason_comment"]

    def test_admin_can_create_in_progress_without_assignment(
        self, client, admin_headers, validation_request_in_progress
    ):
        """Test that Admin can create VALIDATION_IN_PROGRESS commentary even without being assigned."""
        # Admin is NOT assigned to this validation, but should still be able to submit
        payload = {
            "overdue_type": "VALIDATION_IN_PROGRESS",
            "reason_comment": "Admin providing update on behalf of validation team.",
            "target_date": (date.today() + timedelta(days=45)).isoformat()
        }
        response = client.post(
            f"/validation-workflow/requests/{validation_request_in_progress.request_id}/overdue-commentary",
            json=payload,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reason_comment"] == payload["reason_comment"]
        assert data["overdue_type"] == "VALIDATION_IN_PROGRESS"
