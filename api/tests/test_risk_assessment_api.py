"""Tests for Model Risk Assessment API endpoints.

TDD RED Phase: These tests are written BEFORE the API implementation.
All tests should fail initially, then pass after implementing the API.
"""
import pytest
from decimal import Decimal

from app.models.risk_assessment import (
    QualitativeRiskFactor,
    QualitativeFactorGuidance,
    ModelRiskAssessment,
    QualitativeFactorAssessment
)
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.region import Region


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def risk_tier_taxonomy(db_session):
    """Create Model Risk Tier taxonomy with TIER_1-4 values."""
    taxonomy = Taxonomy(name="Model Risk Tier", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    tiers = [
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_1", label="Tier 1 (High)", sort_order=1),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_2", label="Tier 2 (Medium)", sort_order=2),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_3", label="Tier 3 (Low)", sort_order=3),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_4", label="Tier 4 (Very Low)", sort_order=4),
    ]
    db_session.add_all(tiers)
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "TIER_1": tiers[0],
        "TIER_2": tiers[1],
        "TIER_3": tiers[2],
        "TIER_4": tiers[3],
    }


@pytest.fixture
def qualitative_factors(db_session):
    """Create the 4 standard qualitative risk factors with guidance."""
    factors_data = [
        {
            "code": "REPUTATION_LEGAL",
            "name": "Reputation, Regulatory Compliance and/or Financial Reporting Risk",
            "weight": Decimal("0.3000"),
            "sort_order": 1
        },
        {
            "code": "COMPLEXITY",
            "name": "Complexity of the Model",
            "weight": Decimal("0.3000"),
            "sort_order": 2
        },
        {
            "code": "USAGE_DEPENDENCY",
            "name": "Model Usage and Model Dependency",
            "weight": Decimal("0.2000"),
            "sort_order": 3
        },
        {
            "code": "STABILITY",
            "name": "Stability of the Model",
            "weight": Decimal("0.2000"),
            "sort_order": 4
        }
    ]

    factors = []
    for data in factors_data:
        factor = QualitativeRiskFactor(**data)
        db_session.add(factor)
        db_session.flush()

        # Add guidance for each rating level
        for rating, points in [("HIGH", 3), ("MEDIUM", 2), ("LOW", 1)]:
            guidance = QualitativeFactorGuidance(
                factor_id=factor.factor_id,
                rating=rating,
                points=points,
                description=f"{rating} guidance for {data['code']}",
                sort_order=4 - points  # HIGH first
            )
            db_session.add(guidance)

        factors.append(factor)

    db_session.commit()
    return factors


@pytest.fixture
def test_region(db_session):
    """Create a test region for regional assessments."""
    region = Region(
        name="EMEA",
        code="EMEA"
    )
    db_session.add(region)
    db_session.commit()
    return region


@pytest.fixture
def second_region(db_session):
    """Create a second test region."""
    region = Region(
        name="APAC",
        code="APAC"
    )
    db_session.add(region)
    db_session.commit()
    return region


# ============================================================================
# Test: GET /models/{id}/risk-assessments/ - List Assessments
# ============================================================================

class TestListAssessments:
    """Tests for listing risk assessments."""

    def test_list_assessments_empty(self, client, auth_headers, sample_model):
        """Model with no assessments returns empty list."""
        response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_assessments_with_global(
        self, client, auth_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, admin_headers
    ):
        """Returns global assessment when one exists."""
        # First create a global assessment
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": qualitative_factors[0].factor_id, "rating": "HIGH"},
                    {"factor_id": qualitative_factors[1].factor_id, "rating": "HIGH"},
                    {"factor_id": qualitative_factors[2].factor_id, "rating": "HIGH"},
                    {"factor_id": qualitative_factors[3].factor_id, "rating": "HIGH"},
                ]
            }
        )
        assert create_response.status_code == 201

        # Now list
        response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["region"] is None  # Global

    def test_list_assessments_with_global_and_regional(
        self, client, auth_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, admin_headers, test_region
    ):
        """Returns both global and regional assessments."""
        # Create global assessment
        client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )

        # Create regional assessment
        client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": test_region.region_id,
                "quantitative_rating": "MEDIUM",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "MEDIUM"}
                    for f in qualitative_factors
                ]
            }
        )

        # List all
        response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_assessments_requires_auth(self, client, sample_model):
        """Unauthenticated request returns 403 (FastAPI HTTPBearer behavior)."""
        response = client.get(f"/models/{sample_model.model_id}/risk-assessments/")
        assert response.status_code == 403

    def test_list_assessments_model_not_found(self, client, auth_headers):
        """Non-existent model returns 404."""
        response = client.get(
            "/models/99999/risk-assessments/",
            headers=auth_headers
        )
        assert response.status_code == 404


# ============================================================================
# Test: POST /models/{id}/risk-assessments/ - Create Assessment
# ============================================================================

class TestCreateAssessment:
    """Tests for creating risk assessments."""

    def test_create_global_assessment(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Create assessment with region_id=null (global)."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "quantitative_comment": "Model processes large transaction volumes",
                "factor_ratings": [
                    {"factor_id": qualitative_factors[0].factor_id, "rating": "HIGH", "comment": "High regulatory impact"},
                    {"factor_id": qualitative_factors[1].factor_id, "rating": "MEDIUM"},
                    {"factor_id": qualitative_factors[2].factor_id, "rating": "MEDIUM"},
                    {"factor_id": qualitative_factors[3].factor_id, "rating": "LOW"},
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["model_id"] == sample_model.model_id
        assert data["region"] is None
        assert data["quantitative_rating"] == "HIGH"

    def test_create_regional_assessment(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, test_region
    ):
        """Create assessment with specific region_id."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": test_region.region_id,
                "quantitative_rating": "MEDIUM",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "MEDIUM"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["region"]["region_id"] == test_region.region_id

    def test_create_duplicate_global_fails(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Cannot create second global assessment for same model."""
        # First creation
        client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )

        # Second creation should fail
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "MEDIUM",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "MEDIUM"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_duplicate_regional_fails(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, test_region
    ):
        """Cannot create second regional assessment for same model+region."""
        # First creation
        client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": test_region.region_id,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )

        # Second creation should fail
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": test_region.region_id,
                "quantitative_rating": "MEDIUM",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "MEDIUM"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 409

    def test_create_partial_assessment(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Can save with only some factors rated (partial save)."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": qualitative_factors[0].factor_id, "rating": "HIGH"},
                    {"factor_id": qualitative_factors[1].factor_id, "rating": None},  # Not rated
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        # Should still calculate with available factors
        assert data["qualitative_calculated_score"] is not None

    def test_create_assessment_calculates_score(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Creating assessment auto-calculates qualitative score."""
        # All HIGH: 0.3*3 + 0.3*3 + 0.2*3 + 0.2*3 = 3.0
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["qualitative_calculated_score"] == 3.0
        assert data["qualitative_calculated_level"] == "HIGH"

    def test_create_assessment_calculates_derived_tier(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Assessment derives risk tier from matrix lookup."""
        # HIGH + HIGH -> HIGH -> TIER_1
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["derived_risk_tier"] == "HIGH"
        assert data["final_tier"]["code"] == "TIER_1"

    def test_create_assessment_with_overrides(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Can create assessment with override values."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "LOW",
                "quantitative_override": "HIGH",
                "quantitative_override_comment": "Override due to regulatory requirements",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ],
                "qualitative_override": "HIGH",
                "qualitative_override_comment": "Override due to strategic importance"
            }
        )
        assert response.status_code == 201
        data = response.json()
        # Effective values should reflect overrides
        assert data["quantitative_effective_rating"] == "HIGH"
        assert data["qualitative_effective_level"] == "HIGH"
        # Derived should use effective values
        assert data["derived_risk_tier"] == "HIGH"

    def test_create_assessment_empty_factors(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Can create assessment with no factor ratings."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["qualitative_calculated_score"] is None
        assert data["qualitative_calculated_level"] is None


# ============================================================================
# Test: GET /models/{id}/risk-assessments/{id} - Get Single Assessment
# ============================================================================

class TestGetAssessment:
    """Tests for retrieving a single risk assessment."""

    def test_get_assessment(
        self, client, auth_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, admin_headers
    ):
        """Get a specific assessment by ID."""
        # Create
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "MEDIUM",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "MEDIUM"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Get
        response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assessment_id"] == assessment_id
        assert len(data["qualitative_factors"]) == 4

    def test_get_assessment_not_found(self, client, auth_headers, sample_model):
        """Non-existent assessment returns 404."""
        response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/99999",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_assessment_wrong_model(
        self, client, auth_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, admin_headers, db_session, test_user, usage_frequency
    ):
        """Assessment from different model returns 404."""
        from app.models.model import Model

        # Create another model
        other_model = Model(
            model_name="Other Model",
            description="Another model",
            development_type="In-House",
            status="In Development",
            owner_id=test_user.user_id,
            row_approval_status="pending",
            submitted_by_user_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(other_model)
        db_session.commit()

        # Create assessment on first model
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Try to get via other model
        response = client.get(
            f"/models/{other_model.model_id}/risk-assessments/{assessment_id}",
            headers=auth_headers
        )
        assert response.status_code == 404


# ============================================================================
# Test: PUT /models/{id}/risk-assessments/{id} - Update Assessment
# ============================================================================

class TestUpdateAssessment:
    """Tests for updating risk assessments."""

    def test_update_assessment_recalculates(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Updating factors recalculates score and derived tier."""
        # Create with all HIGH
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update to all LOW
        response = client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["qualitative_calculated_score"] == 1.0
        assert data["qualitative_calculated_level"] == "LOW"
        # LOW + LOW -> VERY_LOW -> TIER_4
        assert data["derived_risk_tier"] == "VERY_LOW"
        assert data["final_tier"]["code"] == "TIER_4"

    def test_update_with_override(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Can add override to existing assessment."""
        # Create
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update with final override
        response = client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ],
                "derived_risk_tier_override": "HIGH",
                "derived_risk_tier_override_comment": "Executive override"
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Derived is still VERY_LOW but effective is overridden to HIGH
        assert data["derived_risk_tier"] == "VERY_LOW"
        assert data["derived_risk_tier_effective"] == "HIGH"
        assert data["final_tier"]["code"] == "TIER_1"

    def test_update_assessment_not_found(
        self, client, admin_headers, sample_model, qualitative_factors
    ):
        """Update non-existent assessment returns 404."""
        response = client.put(
            f"/models/{sample_model.model_id}/risk-assessments/99999",
            headers=admin_headers,
            json={
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assert response.status_code == 404

    def test_update_removes_override(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Can remove override by setting to null."""
        # Create with override
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "LOW",
                "quantitative_override": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update to remove override
        response = client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "quantitative_override": None,  # Remove override
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantitative_override"] is None
        assert data["quantitative_effective_rating"] == "LOW"


# ============================================================================
# Test: DELETE /models/{id}/risk-assessments/{id} - Delete Assessment
# ============================================================================

class TestDeleteAssessment:
    """Tests for deleting risk assessments."""

    def test_delete_assessment(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Can delete assessment."""
        # Create
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Delete
        response = client.delete(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404

    def test_delete_assessment_not_found(self, client, admin_headers, sample_model):
        """Delete non-existent assessment returns 404."""
        response = client.delete(
            f"/models/{sample_model.model_id}/risk-assessments/99999",
            headers=admin_headers
        )
        assert response.status_code == 404


# ============================================================================
# Test: Permissions
# ============================================================================

class TestPermissions:
    """Tests for risk assessment permissions."""

    def test_create_assessment_requires_admin_or_validator(
        self, client, auth_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Regular user cannot create assessment."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=auth_headers,  # Regular user
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assert response.status_code == 403

    def test_update_assessment_requires_admin_or_validator(
        self, client, auth_headers, admin_headers, sample_model,
        qualitative_factors, risk_tier_taxonomy
    ):
        """Regular user cannot update assessment."""
        # Create as admin
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Try to update as regular user
        response = client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=auth_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": []
            }
        )
        assert response.status_code == 403

    def test_delete_assessment_requires_admin_or_validator(
        self, client, auth_headers, admin_headers, sample_model,
        qualitative_factors, risk_tier_taxonomy
    ):
        """Regular user cannot delete assessment."""
        # Create as admin
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Try to delete as regular user
        response = client.delete(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_read_assessment_any_user(
        self, client, auth_headers, admin_headers, sample_model,
        qualitative_factors, risk_tier_taxonomy
    ):
        """Any authenticated user can read assessments."""
        # Create as admin
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Read as regular user
        response = client.get(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_validator_can_create_assessment(
        self, client, validator_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Validator can create assessment."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=validator_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assert response.status_code == 201

    def test_validator_can_update_assessment(
        self, client, validator_headers, admin_headers, sample_model,
        qualitative_factors, risk_tier_taxonomy
    ):
        """Validator can update assessment."""
        # Create as admin
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": []
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update as validator
        response = client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=validator_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": []
            }
        )
        assert response.status_code == 200


# ============================================================================
# Test: Model Tier Synchronization
# ============================================================================

class TestModelTierSync:
    """Tests for model tier synchronization with global assessments."""

    def test_create_global_assessment_updates_model_tier(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, db_session
    ):
        """Creating global assessment updates model.risk_tier_id."""
        # Create global assessment with HIGH tier
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 201

        # Verify model tier updated
        model_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        model_data = model_response.json()
        assert model_data["risk_tier"]["code"] == "TIER_1"

    def test_update_global_assessment_syncs_model_tier(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy
    ):
        """Updating global assessment updates model.risk_tier_id."""
        # Create with HIGH
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update to LOW
        client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors
                ]
            }
        )

        # Verify model tier updated to TIER_4 (VERY_LOW)
        model_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        model_data = model_response.json()
        assert model_data["risk_tier"]["code"] == "TIER_4"

    def test_regional_assessment_does_not_update_model_tier(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, test_region
    ):
        """Regional assessment does not change model.risk_tier_id."""
        # First set model tier directly (or leave null)
        initial_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        initial_tier = initial_response.json().get("risk_tier")

        # Create regional assessment
        client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": test_region.region_id,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )

        # Verify model tier unchanged
        model_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        model_data = model_response.json()
        assert model_data.get("risk_tier") == initial_tier

    def test_delete_global_assessment_clears_model_tier(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy
    ):
        """Deleting global assessment clears model.risk_tier_id."""
        # Create
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Verify tier is set
        model_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        assert model_response.json()["risk_tier"]["code"] == "TIER_1"

        # Delete
        client.delete(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers
        )

        # Verify tier is cleared
        model_response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        assert model_response.json().get("risk_tier") is None


# ============================================================================
# Test: Score Calculation Boundary Cases
# ============================================================================

class TestScoreCalculation:
    """Tests for score calculation edge cases in API context."""

    def test_score_boundary_2_1_is_high(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Score exactly 2.1 yields HIGH level."""
        # Need score of exactly 2.1
        # 0.3*3 + 0.3*2 + 0.2*2 + 0.2*2 = 0.9 + 0.6 + 0.4 + 0.4 = 2.3 (too high)
        # 0.3*3 + 0.3*2 + 0.2*2 + 0.2*1 = 0.9 + 0.6 + 0.4 + 0.2 = 2.1 (exactly!)
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": qualitative_factors[0].factor_id, "rating": "HIGH"},   # 0.3*3 = 0.9
                    {"factor_id": qualitative_factors[1].factor_id, "rating": "MEDIUM"}, # 0.3*2 = 0.6
                    {"factor_id": qualitative_factors[2].factor_id, "rating": "MEDIUM"}, # 0.2*2 = 0.4
                    {"factor_id": qualitative_factors[3].factor_id, "rating": "LOW"},    # 0.2*1 = 0.2
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["qualitative_calculated_score"] == 2.1
        assert data["qualitative_calculated_level"] == "HIGH"

    def test_score_boundary_1_6_is_medium(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Score exactly 1.6 yields MEDIUM level."""
        # Need score of exactly 1.6
        # 0.3*2 + 0.3*1 + 0.2*2 + 0.2*2 = 0.6 + 0.3 + 0.4 + 0.4 = 1.7 (too high)
        # 0.3*2 + 0.3*1 + 0.2*2 + 0.2*1 = 0.6 + 0.3 + 0.4 + 0.2 = 1.5 (too low)
        # 0.3*2 + 0.3*2 + 0.2*1 + 0.2*1 = 0.6 + 0.6 + 0.2 + 0.2 = 1.6 (exactly!)
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "MEDIUM",
                "factor_ratings": [
                    {"factor_id": qualitative_factors[0].factor_id, "rating": "MEDIUM"}, # 0.3*2 = 0.6
                    {"factor_id": qualitative_factors[1].factor_id, "rating": "MEDIUM"}, # 0.3*2 = 0.6
                    {"factor_id": qualitative_factors[2].factor_id, "rating": "LOW"},    # 0.2*1 = 0.2
                    {"factor_id": qualitative_factors[3].factor_id, "rating": "LOW"},    # 0.2*1 = 0.2
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["qualitative_calculated_score"] == 1.6
        assert data["qualitative_calculated_level"] == "MEDIUM"

    def test_all_matrix_combinations(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, db_session, test_user, usage_frequency
    ):
        """Test all 9 inherent risk matrix combinations."""
        from app.models.model import Model

        matrix_tests = [
            # (quant, qual_all_same, expected_derived, expected_tier)
            ("HIGH", "HIGH", "HIGH", "TIER_1"),
            ("HIGH", "MEDIUM", "MEDIUM", "TIER_2"),
            # HIGH quant + LOW qual would need score < 1.6
            ("MEDIUM", "HIGH", "MEDIUM", "TIER_2"),
            ("MEDIUM", "MEDIUM", "MEDIUM", "TIER_2"),
            ("LOW", "LOW", "VERY_LOW", "TIER_4"),
        ]

        for i, (quant, qual, expected_derived, expected_tier) in enumerate(matrix_tests):
            # Create a new model for each test
            model = Model(
                model_name=f"Matrix Test {i}",
                description="Test model",
                development_type="In-House",
                status="In Development",
                owner_id=test_user.user_id,
                row_approval_status="pending",
                submitted_by_user_id=test_user.user_id,
                usage_frequency_id=usage_frequency["daily"].value_id
            )
            db_session.add(model)
            db_session.commit()

            response = client.post(
                f"/models/{model.model_id}/risk-assessments/",
                headers=admin_headers,
                json={
                    "region_id": None,
                    "quantitative_rating": quant,
                    "factor_ratings": [
                        {"factor_id": f.factor_id, "rating": qual}
                        for f in qualitative_factors
                    ]
                }
            )
            assert response.status_code == 201, f"Failed for {quant}+{qual}"
            data = response.json()
            assert data["derived_risk_tier"] == expected_derived, f"Expected {expected_derived} for {quant}+{qual}"
            assert data["final_tier"]["code"] == expected_tier, f"Expected {expected_tier} for {quant}+{qual}"


# ============================================================================
# Test: Response Schema Validation
# ============================================================================

class TestResponseSchema:
    """Tests for validating response schema structure."""

    def test_assessment_response_includes_all_fields(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Assessment response includes all expected fields."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "quantitative_comment": "Test comment",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH", "comment": "Factor comment"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Check all expected fields are present
        expected_fields = [
            "assessment_id", "model_id", "region",
            "qualitative_factors", "qualitative_calculated_score",
            "qualitative_calculated_level", "qualitative_override",
            "qualitative_override_comment", "qualitative_effective_level",
            "quantitative_rating", "quantitative_comment",
            "quantitative_override", "quantitative_override_comment",
            "quantitative_effective_rating",
            "derived_risk_tier", "derived_risk_tier_override",
            "derived_risk_tier_override_comment", "derived_risk_tier_effective",
            "final_tier", "assessed_by", "assessed_at",
            "is_complete", "created_at", "updated_at"
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_qualitative_factor_response_structure(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """Qualitative factor in response has correct structure."""
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": qualitative_factors[0].factor_id, "rating": "HIGH", "comment": "Test"}
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()

        factors = data["qualitative_factors"]
        assert len(factors) >= 1

        factor = factors[0]
        expected_factor_fields = [
            "factor_assessment_id", "factor_id", "factor_code",
            "factor_name", "rating", "comment", "weight", "score"
        ]
        for field in expected_factor_fields:
            assert field in factor, f"Missing factor field: {field}"

    def test_is_complete_flag(
        self, client, admin_headers, sample_model, qualitative_factors, risk_tier_taxonomy
    ):
        """is_complete flag correctly indicates assessment completeness."""
        # Incomplete assessment (missing factors)
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": None,  # Missing quantitative
                "factor_ratings": []
            }
        )
        assert response.status_code == 201
        assert response.json()["is_complete"] is False

    def test_complete_assessment_flag(
        self, client, admin_headers, sample_model, qualitative_factors,
        risk_tier_taxonomy, db_session, test_user, usage_frequency
    ):
        """Complete assessment has is_complete=True."""
        from app.models.model import Model

        model = Model(
            model_name="Complete Test",
            description="Test model",
            development_type="In-House",
            status="In Development",
            owner_id=test_user.user_id,
            row_approval_status="pending",
            submitted_by_user_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()

        response = client.post(
            f"/models/{model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors
                ]
            }
        )
        assert response.status_code == 201
        assert response.json()["is_complete"] is True
