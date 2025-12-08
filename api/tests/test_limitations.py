"""Tests for Model Limitations API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ModelLimitation, Taxonomy, TaxonomyValue, Region, ModelRegion


# ==================== FIXTURES ====================

@pytest.fixture
def validator_user(db_session, lob_hierarchy):
    """Create a validator user."""
    from app.models.user import User
    from app.core.security import get_password_hash

    user = User(
        email="validator@example.com",
        full_name="Validator User",
        password_hash=get_password_hash("validator123"),
        role="Validator",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def validator_headers(validator_user):
    """Get authorization headers for validator user."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": validator_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def limitation_category_taxonomy(db_session):
    """Create Limitation Category taxonomy with values."""
    taxonomy = Taxonomy(name="Limitation Category", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    values = [
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="DATA", label="Data", sort_order=1),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="IMPLEMENTATION", label="Implementation", sort_order=2),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="METHODOLOGY", label="Methodology", sort_order=3),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="MODEL_OUTPUT", label="Model Output", sort_order=4),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="OTHER", label="Other", sort_order=5),
    ]
    db_session.add_all(values)
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "data": values[0],
        "implementation": values[1],
        "methodology": values[2],
        "model_output": values[3],
        "other": values[4],
    }


@pytest.fixture
def test_region(db_session):
    """Create a test region."""
    region = Region(code="NA", name="North America")
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


@pytest.fixture
def sample_limitation(db_session, sample_model, validator_user, limitation_category_taxonomy):
    """Create a sample limitation."""
    limitation = ModelLimitation(
        model_id=sample_model.model_id,
        significance="Non-Critical",
        category_id=limitation_category_taxonomy["data"].value_id,
        description="Test limitation description",
        impact_assessment="Test impact assessment",
        conclusion="Accept",
        conclusion_rationale="Test rationale for accepting",
        is_retired=False,
        created_by_id=validator_user.user_id,
    )
    db_session.add(limitation)
    db_session.commit()
    db_session.refresh(limitation)
    return limitation


# ==================== TESTS: LIST LIMITATIONS ====================

class TestListLimitations:
    """Tests for listing limitations."""

    def test_list_limitations_empty(
        self, client, sample_model, auth_headers, limitation_category_taxonomy
    ):
        """Test listing limitations when none exist."""
        response = client.get(
            f"/models/{sample_model.model_id}/limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_limitations_success(
        self, client, sample_model, auth_headers, sample_limitation
    ):
        """Test listing limitations successfully."""
        response = client.get(
            f"/models/{sample_model.model_id}/limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["limitation_id"] == sample_limitation.limitation_id
        assert data[0]["significance"] == "Non-Critical"

    def test_list_limitations_model_not_found(self, client, auth_headers):
        """Test listing limitations for non-existent model."""
        response = client.get("/models/99999/limitations", headers=auth_headers)
        assert response.status_code == 404

    def test_list_limitations_excludes_retired_by_default(
        self, client, db_session, sample_model, auth_headers, sample_limitation
    ):
        """Test that retired limitations are excluded by default."""
        # Retire the limitation
        sample_limitation.is_retired = True
        sample_limitation.retirement_reason = "No longer relevant"
        sample_limitation.retired_by_id = sample_limitation.created_by_id
        from app.core.time import utc_now
        sample_limitation.retirement_date = utc_now()
        db_session.commit()

        response = client.get(
            f"/models/{sample_model.model_id}/limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_limitations_include_retired(
        self, client, db_session, sample_model, auth_headers, sample_limitation
    ):
        """Test that retired limitations can be included."""
        # Retire the limitation
        sample_limitation.is_retired = True
        sample_limitation.retirement_reason = "No longer relevant"
        sample_limitation.retired_by_id = sample_limitation.created_by_id
        from app.core.time import utc_now
        sample_limitation.retirement_date = utc_now()
        db_session.commit()

        response = client.get(
            f"/models/{sample_model.model_id}/limitations?include_retired=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_limitations_filter_by_significance(
        self, client, db_session, sample_model, auth_headers, sample_limitation, limitation_category_taxonomy, validator_user
    ):
        """Test filtering limitations by significance."""
        # Create a critical limitation
        critical_limitation = ModelLimitation(
            model_id=sample_model.model_id,
            significance="Critical",
            category_id=limitation_category_taxonomy["methodology"].value_id,
            description="Critical limitation",
            impact_assessment="High impact",
            conclusion="Mitigate",
            conclusion_rationale="Must be mitigated",
            user_awareness_description="Users are notified via email",
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        db_session.add(critical_limitation)
        db_session.commit()

        response = client.get(
            f"/models/{sample_model.model_id}/limitations?significance=Critical",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["significance"] == "Critical"


# ==================== TESTS: CREATE LIMITATION ====================

class TestCreateLimitation:
    """Tests for creating limitations."""

    def test_create_limitation_success_non_critical(
        self, client, sample_model, validator_headers, limitation_category_taxonomy
    ):
        """Test creating a non-critical limitation."""
        payload = {
            "significance": "Non-Critical",
            "category_id": limitation_category_taxonomy["data"].value_id,
            "description": "Data quality issues in training set",
            "impact_assessment": "May affect model accuracy in edge cases",
            "conclusion": "Accept",
            "conclusion_rationale": "Impact is minimal and monitoring is in place"
        }

        response = client.post(
            f"/models/{sample_model.model_id}/limitations",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["significance"] == "Non-Critical"
        assert data["conclusion"] == "Accept"
        assert data["is_retired"] == False

    def test_create_limitation_success_critical(
        self, client, sample_model, validator_headers, limitation_category_taxonomy
    ):
        """Test creating a critical limitation with user awareness."""
        payload = {
            "significance": "Critical",
            "category_id": limitation_category_taxonomy["methodology"].value_id,
            "description": "Model assumes normal distribution which may not hold",
            "impact_assessment": "Significant underestimation during market stress",
            "conclusion": "Mitigate",
            "conclusion_rationale": "Must implement stress testing overlay",
            "user_awareness_description": "Users are notified via model user guide section 5.2"
        }

        response = client.post(
            f"/models/{sample_model.model_id}/limitations",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["significance"] == "Critical"
        assert data["user_awareness_description"] is not None

    def test_create_limitation_critical_without_awareness_fails(
        self, client, sample_model, validator_headers, limitation_category_taxonomy
    ):
        """Test that critical limitations require user awareness description."""
        payload = {
            "significance": "Critical",
            "category_id": limitation_category_taxonomy["data"].value_id,
            "description": "Critical data issue",
            "impact_assessment": "High impact",
            "conclusion": "Mitigate",
            "conclusion_rationale": "Must be fixed"
            # Missing user_awareness_description
        }

        response = client.post(
            f"/models/{sample_model.model_id}/limitations",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 422  # Validation error

    def test_create_limitation_requires_validator_or_admin(
        self, client, sample_model, auth_headers, limitation_category_taxonomy
    ):
        """Test that regular users cannot create limitations."""
        payload = {
            "significance": "Non-Critical",
            "category_id": limitation_category_taxonomy["data"].value_id,
            "description": "Test",
            "impact_assessment": "Test",
            "conclusion": "Accept",
            "conclusion_rationale": "Test"
        }

        response = client.post(
            f"/models/{sample_model.model_id}/limitations",
            json=payload,
            headers=auth_headers  # Regular user headers
        )
        assert response.status_code == 403

    def test_create_limitation_invalid_category(
        self, client, sample_model, validator_headers
    ):
        """Test creating limitation with invalid category ID."""
        payload = {
            "significance": "Non-Critical",
            "category_id": 99999,  # Invalid ID
            "description": "Test",
            "impact_assessment": "Test",
            "conclusion": "Accept",
            "conclusion_rationale": "Test"
        }

        response = client.post(
            f"/models/{sample_model.model_id}/limitations",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 400

    def test_create_limitation_model_not_found(
        self, client, validator_headers, limitation_category_taxonomy
    ):
        """Test creating limitation for non-existent model."""
        payload = {
            "significance": "Non-Critical",
            "category_id": limitation_category_taxonomy["data"].value_id,
            "description": "Test",
            "impact_assessment": "Test",
            "conclusion": "Accept",
            "conclusion_rationale": "Test"
        }

        response = client.post(
            "/models/99999/limitations",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 404


# ==================== TESTS: GET LIMITATION ====================

class TestGetLimitation:
    """Tests for getting a single limitation."""

    def test_get_limitation_success(
        self, client, sample_limitation, auth_headers
    ):
        """Test getting a limitation by ID."""
        response = client.get(
            f"/limitations/{sample_limitation.limitation_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limitation_id"] == sample_limitation.limitation_id
        assert data["description"] == sample_limitation.description

    def test_get_limitation_not_found(self, client, auth_headers):
        """Test getting non-existent limitation."""
        response = client.get("/limitations/99999", headers=auth_headers)
        assert response.status_code == 404


# ==================== TESTS: UPDATE LIMITATION ====================

class TestUpdateLimitation:
    """Tests for updating limitations."""

    def test_update_limitation_success(
        self, client, sample_limitation, validator_headers
    ):
        """Test updating a limitation."""
        payload = {
            "description": "Updated description",
            "conclusion": "Mitigate"
        }

        response = client.patch(
            f"/limitations/{sample_limitation.limitation_id}",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["conclusion"] == "Mitigate"

    def test_update_limitation_requires_validator_or_admin(
        self, client, sample_limitation, auth_headers
    ):
        """Test that regular users cannot update limitations."""
        payload = {"description": "Updated"}

        response = client.patch(
            f"/limitations/{sample_limitation.limitation_id}",
            json=payload,
            headers=auth_headers  # Regular user
        )
        assert response.status_code == 403

    def test_update_retired_limitation_fails(
        self, client, db_session, sample_limitation, validator_headers
    ):
        """Test that retired limitations cannot be updated."""
        # Retire the limitation
        sample_limitation.is_retired = True
        sample_limitation.retirement_reason = "No longer relevant"
        sample_limitation.retired_by_id = sample_limitation.created_by_id
        from app.core.time import utc_now
        sample_limitation.retirement_date = utc_now()
        db_session.commit()

        payload = {"description": "Updated"}

        response = client.patch(
            f"/limitations/{sample_limitation.limitation_id}",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 400
        assert "retired" in response.json()["detail"].lower()

    def test_update_limitation_to_critical_requires_awareness(
        self, client, sample_limitation, validator_headers
    ):
        """Test that updating to Critical requires user awareness."""
        payload = {
            "significance": "Critical"
            # Missing user_awareness_description
        }

        response = client.patch(
            f"/limitations/{sample_limitation.limitation_id}",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 400


# ==================== TESTS: RETIRE LIMITATION ====================

class TestRetireLimitation:
    """Tests for retiring limitations."""

    def test_retire_limitation_success(
        self, client, sample_limitation, validator_headers
    ):
        """Test retiring a limitation."""
        payload = {"retirement_reason": "Limitation addressed in model version 3.0"}

        response = client.post(
            f"/limitations/{sample_limitation.limitation_id}/retire",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_retired"] == True
        assert data["retirement_reason"] == payload["retirement_reason"]
        assert data["retired_by"] is not None

    def test_retire_limitation_requires_validator_or_admin(
        self, client, sample_limitation, auth_headers
    ):
        """Test that regular users cannot retire limitations."""
        payload = {"retirement_reason": "Test"}

        response = client.post(
            f"/limitations/{sample_limitation.limitation_id}/retire",
            json=payload,
            headers=auth_headers  # Regular user
        )
        assert response.status_code == 403

    def test_retire_already_retired_fails(
        self, client, db_session, sample_limitation, validator_headers
    ):
        """Test that already retired limitations cannot be retired again."""
        # Retire the limitation first
        sample_limitation.is_retired = True
        sample_limitation.retirement_reason = "Original reason"
        sample_limitation.retired_by_id = sample_limitation.created_by_id
        from app.core.time import utc_now
        sample_limitation.retirement_date = utc_now()
        db_session.commit()

        payload = {"retirement_reason": "New reason"}

        response = client.post(
            f"/limitations/{sample_limitation.limitation_id}/retire",
            json=payload,
            headers=validator_headers
        )
        assert response.status_code == 400
        assert "already retired" in response.json()["detail"].lower()


# ==================== TESTS: CRITICAL LIMITATIONS REPORT ====================

class TestCriticalLimitationsReport:
    """Tests for critical limitations report."""

    def test_critical_limitations_report_empty(
        self, client, auth_headers, limitation_category_taxonomy
    ):
        """Test report when no critical limitations exist."""
        response = client.get(
            "/reports/critical-limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["items"] == []

    def test_critical_limitations_report_excludes_non_critical(
        self, client, sample_limitation, auth_headers
    ):
        """Test that report excludes non-critical limitations."""
        response = client.get(
            "/reports/critical-limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0  # sample_limitation is non-critical

    def test_critical_limitations_report_includes_critical(
        self, client, db_session, sample_model, validator_user, limitation_category_taxonomy, auth_headers
    ):
        """Test that report includes critical limitations."""
        # Create a critical limitation
        critical_limitation = ModelLimitation(
            model_id=sample_model.model_id,
            significance="Critical",
            category_id=limitation_category_taxonomy["methodology"].value_id,
            description="Critical methodology issue",
            impact_assessment="High impact on results",
            conclusion="Mitigate",
            conclusion_rationale="Must be addressed",
            user_awareness_description="Users notified via documentation",
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        db_session.add(critical_limitation)
        db_session.commit()

        response = client.get(
            "/reports/critical-limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["significance"] == "Critical" if "significance" in data["items"][0] else True
        assert data["items"][0]["model_name"] == sample_model.model_name

    def test_critical_limitations_report_filter_by_region(
        self, client, db_session, sample_model, validator_user, limitation_category_taxonomy,
        test_region, auth_headers
    ):
        """Test filtering report by region."""
        # Associate model with region
        model_region = ModelRegion(
            model_id=sample_model.model_id,
            region_id=test_region.region_id
        )
        db_session.add(model_region)

        # Create a critical limitation
        critical_limitation = ModelLimitation(
            model_id=sample_model.model_id,
            significance="Critical",
            category_id=limitation_category_taxonomy["data"].value_id,
            description="Critical data issue",
            impact_assessment="High impact",
            conclusion="Accept",
            conclusion_rationale="Accepted with monitoring",
            user_awareness_description="Users notified",
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        db_session.add(critical_limitation)
        db_session.commit()

        # Test with region filter
        response = client.get(
            f"/reports/critical-limitations?region_id={test_region.region_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["filters_applied"]["region_id"] == test_region.region_id

    def test_critical_limitations_report_invalid_region(
        self, client, auth_headers
    ):
        """Test report with invalid region ID."""
        response = client.get(
            "/reports/critical-limitations?region_id=99999",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_critical_limitations_report_excludes_retired(
        self, client, db_session, sample_model, validator_user, limitation_category_taxonomy, auth_headers
    ):
        """Test that report excludes retired limitations."""
        from app.core.time import utc_now

        # Create a retired critical limitation
        critical_limitation = ModelLimitation(
            model_id=sample_model.model_id,
            significance="Critical",
            category_id=limitation_category_taxonomy["methodology"].value_id,
            description="Critical issue",
            impact_assessment="High impact",
            conclusion="Mitigate",
            conclusion_rationale="Must be fixed",
            user_awareness_description="Users notified",
            is_retired=True,
            retirement_date=utc_now(),
            retirement_reason="Fixed in v2",
            retired_by_id=validator_user.user_id,
            created_by_id=validator_user.user_id,
        )
        db_session.add(critical_limitation)
        db_session.commit()

        response = client.get(
            "/reports/critical-limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0


# ==================== TESTS: VALIDATION REQUEST LIMITATIONS ====================

class TestValidationRequestLimitations:
    """Tests for listing limitations by validation request ID."""

    @pytest.fixture
    def validation_taxonomies(self, db_session):
        """Create validation-related taxonomies for tests."""
        from app.models.taxonomy import Taxonomy, TaxonomyValue

        # Create Validation Type taxonomy
        validation_type_tax = Taxonomy(name="Validation Type", is_system=True)
        db_session.add(validation_type_tax)
        db_session.flush()

        validation_type_val = TaxonomyValue(
            taxonomy_id=validation_type_tax.taxonomy_id,
            code="INITIAL",
            label="Initial Validation",
            sort_order=1,
            is_active=True
        )
        db_session.add(validation_type_val)

        # Create Validation Priority taxonomy
        priority_tax = Taxonomy(name="Validation Priority", is_system=True)
        db_session.add(priority_tax)
        db_session.flush()

        priority_val = TaxonomyValue(
            taxonomy_id=priority_tax.taxonomy_id,
            code="STANDARD",
            label="Standard",
            sort_order=1,
            is_active=True
        )
        db_session.add(priority_val)

        # Create Validation Request Status taxonomy
        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        db_session.add(status_tax)
        db_session.flush()

        status_val = TaxonomyValue(
            taxonomy_id=status_tax.taxonomy_id,
            code="INTAKE",
            label="Intake",
            sort_order=1,
            is_active=True
        )
        db_session.add(status_val)

        db_session.commit()

        return {
            "validation_type": validation_type_val,
            "priority": priority_val,
            "status": status_val,
        }

    def test_list_validation_request_limitations_empty(
        self, client, db_session, sample_model, validation_taxonomies, auth_headers
    ):
        """Test listing limitations for a validation request with none linked."""
        from app.models.validation import ValidationRequest
        from datetime import date

        validation_request = ValidationRequest(
            validation_type_id=validation_taxonomies["validation_type"].value_id,
            priority_id=validation_taxonomies["priority"].value_id,
            current_status_id=validation_taxonomies["status"].value_id,
            target_completion_date=date(2025, 12, 31),
            requestor_id=1,
        )
        db_session.add(validation_request)
        db_session.commit()

        response = client.get(
            f"/validation-requests/{validation_request.request_id}/limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_validation_request_limitations_success(
        self, client, db_session, sample_model, validator_user, limitation_category_taxonomy,
        validation_taxonomies, auth_headers
    ):
        """Test listing limitations linked to a validation request."""
        from app.models.validation import ValidationRequest
        from datetime import date

        # Create validation request
        validation_request = ValidationRequest(
            validation_type_id=validation_taxonomies["validation_type"].value_id,
            priority_id=validation_taxonomies["priority"].value_id,
            current_status_id=validation_taxonomies["status"].value_id,
            target_completion_date=date(2025, 12, 31),
            requestor_id=1,
        )
        db_session.add(validation_request)
        db_session.commit()

        # Create a limitation linked to this validation request
        linked_limitation = ModelLimitation(
            model_id=sample_model.model_id,
            validation_request_id=validation_request.request_id,
            significance="Non-Critical",
            category_id=limitation_category_taxonomy["data"].value_id,
            description="Linked limitation",
            impact_assessment="Medium impact",
            conclusion="Accept",
            conclusion_rationale="Accepted",
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        db_session.add(linked_limitation)

        # Create a limitation NOT linked to this validation request
        unlinked_limitation = ModelLimitation(
            model_id=sample_model.model_id,
            validation_request_id=None,
            significance="Non-Critical",
            category_id=limitation_category_taxonomy["data"].value_id,
            description="Unlinked limitation",
            impact_assessment="Low impact",
            conclusion="Accept",
            conclusion_rationale="Accepted",
            is_retired=False,
            created_by_id=validator_user.user_id,
        )
        db_session.add(unlinked_limitation)
        db_session.commit()

        response = client.get(
            f"/validation-requests/{validation_request.request_id}/limitations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["description"] == "Linked limitation"

    def test_list_validation_request_limitations_not_found(
        self, client, auth_headers
    ):
        """Test listing limitations for non-existent validation request."""
        response = client.get(
            "/validation-requests/99999/limitations",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
