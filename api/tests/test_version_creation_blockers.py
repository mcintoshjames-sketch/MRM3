"""Tests for version creation blocker API contract.

These tests verify that the 409 response shape matches what the frontend expects.
Critical for frontend SubmitChangeModal.tsx error handling.
"""
import pytest
from datetime import date, timedelta
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.validation import ValidationRequest, ValidationRequestModelVersion
from app.models.taxonomy import Taxonomy, TaxonomyValue


@pytest.fixture
def blocker_test_setup(db_session, test_user, taxonomy_values, usage_frequency):
    """Setup model and taxonomies for blocker testing."""
    # Create model
    model = Model(
        model_name="Blocker Test Model",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        risk_tier_id=taxonomy_values["tier1"].value_id,
        usage_frequency_id=usage_frequency["monthly"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    return {
        "model": model,
        "tier1_id": taxonomy_values["tier1"].value_id,
        "status_intake": taxonomy_values["status_intake"],
        "status_planning": taxonomy_values["status_planning"],
        "status_in_progress": taxonomy_values["status_in_progress"],
        "status_approved": taxonomy_values["status_approved"],
        # Add validation type and priority for ValidationRequest creation
        "validation_type_initial": taxonomy_values["initial"],
        "priority_standard": taxonomy_values["priority_standard"],
    }


class TestVersionCreationBlockerContract:
    """Tests verifying the 409 response contract matches frontend expectations.

    Frontend (SubmitChangeModal.tsx) expects:
    - err.response.data.detail.error === 'version_creation_blocked'
    - err.response.data.detail.blocking_validation_id (NOT blocking_validation_request_id)
    """

    def test_blocker_response_has_detail_wrapper(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Verify 409 response has 'detail' key wrapping the error info.

        Frontend accesses: err.response.data.detail.error
        NOT: err.response.data.error
        """
        model = blocker_test_setup["model"]

        # Create a version in DRAFT status (undeployed) to trigger B1 blocker
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Initial version",
            status="DRAFT",
            created_by_id=model.owner_id
        )
        db_session.add(version)
        db_session.commit()

        # Try to create another version - should be blocked
        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "Second version attempt"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()

        # Critical: Frontend expects data.detail, not data directly
        assert "detail" in data, "Response must have 'detail' key for HTTPException"
        assert isinstance(data["detail"], dict), "'detail' must be a dict containing error info"

    def test_blocker_response_error_field_in_detail(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Verify error field is inside detail, not at top level.

        Frontend checks: err.response.data.detail.error === 'version_creation_blocked'
        """
        model = blocker_test_setup["model"]

        # Create undeployed version to trigger blocker
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Initial version",
            status="DRAFT",
            created_by_id=model.owner_id
        )
        db_session.add(version)
        db_session.commit()

        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "Second version attempt"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()

        # Error field must be inside detail
        assert "error" in data["detail"], "'error' field must be inside 'detail'"
        assert data["detail"]["error"] == "version_creation_blocked"

    def test_blocker_uses_blocking_validation_id_not_request_id(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Verify field name is blocking_validation_id, NOT blocking_validation_request_id.

        Frontend interface expects: blocking_validation_id
        NOT: blocking_validation_request_id (this was the bug)
        """
        model = blocker_test_setup["model"]
        status_in_progress = blocker_test_setup["status_in_progress"]

        # Create version in active validation to trigger B2 blocker
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Initial version",
            status="IN_VALIDATION",
            created_by_id=model.owner_id
        )
        db_session.add(version)
        db_session.flush()

        # Create active validation request for this version
        validation = ValidationRequest(
            requestor_id=model.owner_id,
            validation_type_id=blocker_test_setup["validation_type_initial"].value_id,
            priority_id=blocker_test_setup["priority_standard"].value_id,
            current_status_id=status_in_progress.value_id,
            target_completion_date=date.today() + timedelta(days=30)
        )
        db_session.add(validation)
        db_session.flush()

        # Link model/version to validation via association class
        assoc = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=model.model_id,
            version_id=version.version_id
        )
        db_session.add(assoc)
        db_session.commit()

        # Try to create another version - should be blocked by active validation
        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "Second version attempt"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()

        # Critical: Field name must be blocking_validation_id
        assert "blocking_validation_id" in data["detail"], \
            "Must use 'blocking_validation_id', not 'blocking_validation_request_id'"

        # Verify it's NOT using the wrong field name
        assert "blocking_validation_request_id" not in data["detail"], \
            "Should NOT have 'blocking_validation_request_id' - frontend expects 'blocking_validation_id'"

        # Verify the value is correct
        assert data["detail"]["blocking_validation_id"] == validation.request_id

    def test_b1_blocker_undeployed_version_response_shape(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Test B1 blocker (undeployed version exists) returns correct shape."""
        model = blocker_test_setup["model"]

        # Create version in APPROVED status without actual_production_date (undeployed)
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Approved but not deployed",
            status="APPROVED",
            created_by_id=model.owner_id,
            actual_production_date=None  # Not deployed
        )
        db_session.add(version)
        db_session.commit()

        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "Second version attempt"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()

        # Verify complete response shape for B1 blocker
        detail = data["detail"]
        assert detail["error"] == "version_creation_blocked"
        assert detail["reason"] == "undeployed_version_exists"
        assert "blocking_version_number" in detail
        assert detail["blocking_version_number"] == "1.0"
        assert "message" in detail

    def test_b2_blocker_active_validation_response_shape(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Test B2 blocker (version in active validation) returns correct shape."""
        model = blocker_test_setup["model"]
        status_planning = blocker_test_setup["status_planning"]

        # Create version in active validation
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Version in validation",
            status="IN_VALIDATION",
            created_by_id=model.owner_id
        )
        db_session.add(version)
        db_session.flush()

        validation = ValidationRequest(
            requestor_id=model.owner_id,
            validation_type_id=blocker_test_setup["validation_type_initial"].value_id,
            priority_id=blocker_test_setup["priority_standard"].value_id,
            current_status_id=status_planning.value_id,
            target_completion_date=date.today() + timedelta(days=30)
        )
        db_session.add(validation)
        db_session.flush()

        # Link model/version to validation via association class
        assoc = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=model.model_id,
            version_id=version.version_id
        )
        db_session.add(assoc)
        db_session.commit()

        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "Second version attempt"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 409
        data = response.json()

        # Verify complete response shape for B2 blocker
        detail = data["detail"]
        assert detail["error"] == "version_creation_blocked"
        assert detail["reason"] == "version_in_active_validation"
        assert "blocking_version_number" in detail
        assert "blocking_validation_id" in detail
        assert detail["blocking_validation_id"] == validation.request_id
        assert "message" in detail

    def test_no_blocker_when_version_deployed(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Verify no blocker when previous version is deployed (has actual_production_date)."""
        model = blocker_test_setup["model"]

        # Create deployed version
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Deployed version",
            status="ACTIVE",
            created_by_id=model.owner_id,
            actual_production_date=date.today() - timedelta(days=10)  # Deployed
        )
        db_session.add(version)
        db_session.commit()

        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "New version after deployed one"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        # Should succeed - no blocker
        assert response.status_code == 201

    def test_no_blocker_when_validation_approved(
        self, client, db_session, auth_headers, blocker_test_setup
    ):
        """Verify no blocker when validation is in APPROVED status (completed)."""
        model = blocker_test_setup["model"]
        status_approved = blocker_test_setup["status_approved"]

        # Create version with completed validation
        version = ModelVersion(
            model_id=model.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Version with approved validation",
            status="APPROVED",
            created_by_id=model.owner_id,
            actual_production_date=date.today()  # Deployed
        )
        db_session.add(version)
        db_session.flush()

        validation = ValidationRequest(
            requestor_id=model.owner_id,
            validation_type_id=blocker_test_setup["validation_type_initial"].value_id,
            priority_id=blocker_test_setup["priority_standard"].value_id,
            current_status_id=status_approved.value_id,  # APPROVED = completed
            target_completion_date=date.today()
        )
        db_session.add(validation)
        db_session.flush()

        # Link model/version to validation via association class
        assoc = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=model.model_id,
            version_id=version.version_id
        )
        db_session.add(assoc)
        db_session.commit()

        payload = {
            "version_number": "2.0",
            "change_type": "MAJOR",
            "change_description": "New version after approved validation"
        }
        response = client.post(
            f"/models/{model.model_id}/versions",
            json=payload,
            headers=auth_headers
        )

        # Should succeed - validation is completed
        assert response.status_code == 201
