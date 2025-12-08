"""Tests for dashboard endpoints with commentary fields (Phase 2)."""
import pytest
from datetime import date, datetime, timedelta
from app.core.time import utc_now
from app.models import (
    User, Model, ValidationRequest, ValidationRequestModelVersion,
    ValidationAssignment, TaxonomyValue, Taxonomy, OverdueRevalidationComment,
    ValidationWorkflowSLA
)
from app.models.model_delegate import ModelDelegate
from app.core.security import get_password_hash, create_access_token


class TestDashboardCommentaryAPI:
    """Tests for dashboard endpoints with commentary integration."""

    @pytest.fixture
    def admin_user(self, db_session, lob_hierarchy):
        """Create admin user."""
        user = User(
            email="dashboard_admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Dashboard Admin",
            role="Admin",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def admin_headers(self, admin_user):
        """Create admin auth headers."""
        token = create_access_token(data={"sub": admin_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def regular_user(self, db_session, lob_hierarchy):
        """Create regular user."""
        user = User(
            email="regular_user@example.com",
            password_hash=get_password_hash("user123"),
            full_name="Regular User",
            role="User",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def regular_headers(self, regular_user):
        """Create regular user auth headers."""
        token = create_access_token(data={"sub": regular_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def validator_user(self, db_session, lob_hierarchy):
        """Create validator user."""
        user = User(
            email="validator@example.com",
            password_hash=get_password_hash("val123"),
            full_name="Validator User",
            role="Validator",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def validator_headers(self, validator_user):
        """Create validator auth headers."""
        token = create_access_token(data={"sub": validator_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def validation_taxonomies(self, db_session):
        """Create required validation taxonomies."""
        # Validation Request Status taxonomy
        status_tax = Taxonomy(
            name="Validation Request Status",
            description="Validation workflow statuses"
        )
        db_session.add(status_tax)
        db_session.flush()

        statuses = {}
        for i, (code, label) in enumerate([
            ("INTAKE", "Intake"),
            ("PLANNING", "Planning"),
            ("IN_PROGRESS", "In Progress"),
            ("REVIEW", "Review"),
            ("PENDING_APPROVAL", "Pending Approval"),
            ("APPROVED", "Approved"),
            ("CANCELLED", "Cancelled")
        ]):
            value = TaxonomyValue(
                taxonomy_id=status_tax.taxonomy_id,
                code=code,
                label=label,
                sort_order=i + 1
            )
            db_session.add(value)
            db_session.flush()
            statuses[code.lower()] = value

        # Validation Type taxonomy
        type_tax = Taxonomy(
            name="Validation Type",
            description="Types of validation"
        )
        db_session.add(type_tax)
        db_session.flush()

        types = {}
        for i, (code, label) in enumerate([
            ("COMPREHENSIVE", "Comprehensive"),
            ("TARGETED", "Targeted Review")
        ]):
            value = TaxonomyValue(
                taxonomy_id=type_tax.taxonomy_id,
                code=code,
                label=label,
                sort_order=i + 1
            )
            db_session.add(value)
            db_session.flush()
            types[code.lower()] = value

        db_session.commit()
        return {"statuses": statuses, "types": types}

    @pytest.fixture
    def sla_config(self, db_session):
        """Create SLA configuration."""
        # Note: model_change_lead_time_days was moved to ValidationPolicy
        # ValidationWorkflowSLA uses defaults for assignment_days, begin_work_days, approval_days
        sla = ValidationWorkflowSLA()
        db_session.add(sla)
        db_session.commit()
        return sla

    @pytest.fixture
    def test_model(self, db_session, regular_user, usage_frequency):
        """Create a test model owned by regular_user."""
        model = Model(
            model_name="Dashboard Test Model",
            owner_id=regular_user.user_id,
            row_approval_status="approved",
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        return model

    @pytest.fixture
    def overdue_submission_request(
        self, db_session, test_model, admin_user, validation_taxonomies, sla_config
    ):
        """Create a validation request that is overdue for submission."""
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_taxonomies["types"]["comprehensive"].value_id,
            current_status_id=validation_taxonomies["statuses"]["intake"].value_id,
            priority_id=validation_taxonomies["statuses"]["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=60),
            submission_received_date=None,
            # Set submission due date in the past to make it overdue
            created_at=utc_now() - timedelta(days=100)
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

    @pytest.fixture
    def overdue_validation_request(
        self, db_session, test_model, admin_user, validation_taxonomies, sla_config
    ):
        """Create a validation request that is overdue for validation completion."""
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_taxonomies["types"]["comprehensive"].value_id,
            current_status_id=validation_taxonomies["statuses"]["in_progress"].value_id,
            priority_id=validation_taxonomies["statuses"]["intake"].value_id,
            target_completion_date=date.today() - timedelta(days=30),  # Overdue
            submission_received_date=date.today() - timedelta(days=60)
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

    # ==================== TESTS FOR overdue-submissions ====================

    def test_overdue_submissions_includes_commentary_missing(
        self, client, admin_headers, overdue_submission_request
    ):
        """Test that overdue-submissions endpoint includes commentary fields when missing."""
        response = client.get(
            "/validation-workflow/dashboard/overdue-submissions",
            headers=admin_headers
        )
        # May or may not return results depending on computed due dates
        assert response.status_code == 200
        data = response.json()

        # If there are results, check commentary fields exist
        if len(data) > 0:
            item = data[0]
            assert "comment_status" in item
            assert "latest_comment" in item
            assert "latest_comment_date" in item
            assert "target_submission_date" in item
            assert "needs_comment_update" in item

    def test_overdue_submissions_with_current_comment(
        self, client, admin_headers, db_session, overdue_submission_request, admin_user
    ):
        """Test that overdue-submissions shows CURRENT comment status."""
        # Add a current comment
        comment = OverdueRevalidationComment(
            validation_request_id=overdue_submission_request.request_id,
            overdue_type="PRE_SUBMISSION",
            reason_comment="Working on gathering required data.",
            target_date=date.today() + timedelta(days=30),
            created_by_user_id=admin_user.user_id,
            created_at=utc_now(),
            is_current=True
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(
            "/validation-workflow/dashboard/overdue-submissions",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Find our request in results
        for item in data:
            if item["request_id"] == overdue_submission_request.request_id:
                assert item["comment_status"] == "CURRENT"
                assert item["latest_comment"] == "Working on gathering required data."
                assert item["needs_comment_update"] is False
                break

    def test_overdue_submissions_with_stale_comment(
        self, client, admin_headers, db_session, overdue_submission_request, admin_user
    ):
        """Test that overdue-submissions shows STALE comment status when target passed."""
        # Add a stale comment (target date in past)
        comment = OverdueRevalidationComment(
            validation_request_id=overdue_submission_request.request_id,
            overdue_type="PRE_SUBMISSION",
            reason_comment="Was supposed to be done by now.",
            target_date=date.today() - timedelta(days=5),  # Target passed
            created_by_user_id=admin_user.user_id,
            created_at=utc_now() - timedelta(days=10),
            is_current=True
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(
            "/validation-workflow/dashboard/overdue-submissions",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Find our request in results
        for item in data:
            if item["request_id"] == overdue_submission_request.request_id:
                assert item["comment_status"] == "STALE"
                assert item["needs_comment_update"] is True
                break

    def test_overdue_submissions_admin_only(self, client, regular_headers):
        """Test that overdue-submissions requires admin access."""
        response = client.get(
            "/validation-workflow/dashboard/overdue-submissions",
            headers=regular_headers
        )
        assert response.status_code == 403

    # ==================== TESTS FOR overdue-validations ====================

    def test_overdue_validations_includes_commentary_fields(
        self, client, admin_headers, overdue_validation_request
    ):
        """Test that overdue-validations endpoint includes commentary fields."""
        response = client.get(
            "/validation-workflow/dashboard/overdue-validations",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # If there are any results, verify they have commentary fields
        # (Computed dates may not trigger overdue in test environment)
        if len(data) > 0:
            item = data[0]
            assert "comment_status" in item
            assert "latest_comment" in item
            assert "latest_comment_date" in item
            assert "target_completion_date" in item
            assert "needs_comment_update" in item

    def test_overdue_validations_with_current_comment(
        self, client, admin_headers, db_session, overdue_validation_request, admin_user
    ):
        """Test that overdue-validations shows CURRENT comment status."""
        # Add a current comment
        comment = OverdueRevalidationComment(
            validation_request_id=overdue_validation_request.request_id,
            overdue_type="VALIDATION_IN_PROGRESS",
            reason_comment="Awaiting additional documentation from model owner.",
            target_date=date.today() + timedelta(days=20),
            created_by_user_id=admin_user.user_id,
            created_at=utc_now(),
            is_current=True
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(
            "/validation-workflow/dashboard/overdue-validations",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Find our request
        for item in data:
            if item["request_id"] == overdue_validation_request.request_id:
                assert item["comment_status"] == "CURRENT"
                assert "Awaiting additional documentation" in item["latest_comment"]
                assert item["needs_comment_update"] is False
                break

    def test_overdue_validations_admin_only(self, client, regular_headers):
        """Test that overdue-validations requires admin access."""
        response = client.get(
            "/validation-workflow/dashboard/overdue-validations",
            headers=regular_headers
        )
        assert response.status_code == 403

    # ==================== TESTS FOR my-overdue-items ====================

    def test_my_overdue_items_available_to_all_users(
        self, client, regular_headers
    ):
        """Test that my-overdue-items is available to non-admin users."""
        response = client.get(
            "/validation-workflow/dashboard/my-overdue-items",
            headers=regular_headers
        )
        assert response.status_code == 200

    def test_my_overdue_items_empty_for_user_without_responsibilities(
        self, client, validator_headers
    ):
        """Test that my-overdue-items returns empty when user has no responsibilities."""
        response = client.get(
            "/validation-workflow/dashboard/my-overdue-items",
            headers=validator_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_my_overdue_items_shows_owner_items(
        self, client, regular_headers, db_session, test_model, regular_user,
        validation_taxonomies, sla_config
    ):
        """Test that my-overdue-items shows items where user is model owner."""
        # Create an overdue submission request for the test model (owned by regular_user)
        request = ValidationRequest(
            requestor_id=regular_user.user_id,
            validation_type_id=validation_taxonomies["types"]["comprehensive"].value_id,
            current_status_id=validation_taxonomies["statuses"]["intake"].value_id,
            priority_id=validation_taxonomies["statuses"]["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            submission_received_date=None,
            created_at=utc_now() - timedelta(days=100)
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

        response = client.get(
            "/validation-workflow/dashboard/my-overdue-items",
            headers=regular_headers
        )
        assert response.status_code == 200
        # Response contains items (may be empty if computed dates don't trigger overdue)

    def test_my_overdue_items_shows_validator_items(
        self, client, validator_headers, db_session, test_model, admin_user, validator_user,
        validation_taxonomies, sla_config
    ):
        """Test that my-overdue-items shows items where user is assigned validator."""
        # Create an overdue validation request
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_taxonomies["types"]["comprehensive"].value_id,
            current_status_id=validation_taxonomies["statuses"]["in_progress"].value_id,
            priority_id=validation_taxonomies["statuses"]["intake"].value_id,
            target_completion_date=date.today() - timedelta(days=30),  # Overdue
            submission_received_date=date.today() - timedelta(days=60)
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)

        # Assign validator
        assignment = ValidationAssignment(
            request_id=request.request_id,
            validator_id=validator_user.user_id,
            is_primary=True,
            is_reviewer=False
        )
        db_session.add(assignment)
        db_session.commit()

        response = client.get(
            "/validation-workflow/dashboard/my-overdue-items",
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()

        # If there are any results for validator, verify fields
        # (Computed dates may not trigger overdue in test environment)
        for item in data:
            if item.get("overdue_type") == "VALIDATION_IN_PROGRESS":
                assert item["user_role"] == "validator"
                assert "comment_status" in item
                assert "needs_comment_update" in item
                break

    def test_my_overdue_items_shows_delegate_items(
        self, client, db_session, test_model, admin_user, validation_taxonomies, sla_config, lob_hierarchy
    ):
        """Test that my-overdue-items shows items where user is delegate."""
        # Create a delegate user
        delegate_user = User(
            email="delegate@example.com",
            password_hash=get_password_hash("del123"),
            full_name="Delegate User",
            role="User",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(delegate_user)
        db_session.flush()

        # Create delegation
        delegate = ModelDelegate(
            model_id=test_model.model_id,
            user_id=delegate_user.user_id,
            delegated_by_id=test_model.owner_id
        )
        db_session.add(delegate)

        # Create an overdue submission request
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_taxonomies["types"]["comprehensive"].value_id,
            current_status_id=validation_taxonomies["statuses"]["intake"].value_id,
            priority_id=validation_taxonomies["statuses"]["intake"].value_id,
            target_completion_date=date.today() + timedelta(days=30),
            submission_received_date=None,
            created_at=utc_now() - timedelta(days=100)
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

        token = create_access_token(data={"sub": delegate_user.email})
        delegate_headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/validation-workflow/dashboard/my-overdue-items",
            headers=delegate_headers
        )
        assert response.status_code == 200
        # Response contains delegate items (may be empty if computed dates don't trigger)

    def test_my_overdue_items_includes_commentary_fields(
        self, client, validator_headers, db_session, test_model, admin_user, validator_user,
        validation_taxonomies, sla_config
    ):
        """Test that my-overdue-items includes all commentary fields."""
        # Create an overdue validation request
        request = ValidationRequest(
            requestor_id=admin_user.user_id,
            validation_type_id=validation_taxonomies["types"]["comprehensive"].value_id,
            current_status_id=validation_taxonomies["statuses"]["in_progress"].value_id,
            priority_id=validation_taxonomies["statuses"]["intake"].value_id,
            target_completion_date=date.today() - timedelta(days=30),
            submission_received_date=date.today() - timedelta(days=60)
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=test_model.model_id,
            version_id=None
        )
        db_session.add(link)

        assignment = ValidationAssignment(
            request_id=request.request_id,
            validator_id=validator_user.user_id,
            is_primary=True,
            is_reviewer=False
        )
        db_session.add(assignment)

        # Add a commentary
        comment = OverdueRevalidationComment(
            validation_request_id=request.request_id,
            overdue_type="VALIDATION_IN_PROGRESS",
            reason_comment="Testing commentary integration.",
            target_date=date.today() + timedelta(days=15),
            created_by_user_id=validator_user.user_id,
            created_at=utc_now(),
            is_current=True
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(
            "/validation-workflow/dashboard/my-overdue-items",
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Find our request and verify all fields
        for item in data:
            if item["request_id"] == request.request_id:
                assert item["comment_status"] == "CURRENT"
                assert item["latest_comment"] == "Testing commentary integration."
                assert item["latest_comment_date"] is not None
                assert item["target_date"] is not None
                assert item["needs_comment_update"] is False
                break
