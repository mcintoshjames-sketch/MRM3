"""Tests for Qualitative Risk Factor Configuration API endpoints.

TDD RED Phase: These tests are written BEFORE the API implementation.
Admin-only endpoints for managing qualitative risk factors.
"""
import pytest
from decimal import Decimal

from app.models.risk_assessment import QualitativeRiskFactor, QualitativeFactorGuidance


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def seeded_factors(db_session):
    """Create the 4 standard qualitative risk factors with guidance."""
    factors_data = [
        {
            "code": "REPUTATION_LEGAL",
            "name": "Reputation, Regulatory Compliance and/or Financial Reporting Risk",
            "description": "Reputation Risk is defined as the risk of negative publicity...",
            "weight": Decimal("0.3000"),
            "sort_order": 1
        },
        {
            "code": "COMPLEXITY",
            "name": "Complexity of the Model",
            "description": "The complexity of the model refers to the mathematical sophistication...",
            "weight": Decimal("0.3000"),
            "sort_order": 2
        },
        {
            "code": "USAGE_DEPENDENCY",
            "name": "Model Usage and Model Dependency",
            "description": "The model usage and model dependency assesses...",
            "weight": Decimal("0.2000"),
            "sort_order": 3
        },
        {
            "code": "STABILITY",
            "name": "Stability of the Model",
            "description": "The stability of the model refers to the likelihood of model error...",
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
        for rating, points, desc in [
            ("HIGH", 3, f"High guidance for {data['code']}"),
            ("MEDIUM", 2, f"Medium guidance for {data['code']}"),
            ("LOW", 1, f"Low guidance for {data['code']}")
        ]:
            guidance = QualitativeFactorGuidance(
                factor_id=factor.factor_id,
                rating=rating,
                points=points,
                description=desc,
                sort_order=4 - points
            )
            db_session.add(guidance)

        factors.append(factor)

    db_session.commit()
    return factors


# ============================================================================
# Test: GET /risk-assessment/factors/ - List All Factors
# ============================================================================

class TestListFactors:
    """Tests for listing qualitative risk factors."""

    def test_list_factors_returns_all(self, client, admin_headers, seeded_factors):
        """Returns all active factors."""
        response = client.get(
            "/risk-assessment/factors/",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_list_factors_includes_guidance(self, client, admin_headers, seeded_factors):
        """Each factor includes its guidance entries."""
        response = client.get(
            "/risk-assessment/factors/",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Each factor should have 3 guidance entries (HIGH, MEDIUM, LOW)
        for factor in data:
            assert "guidance" in factor
            assert len(factor["guidance"]) == 3

    def test_list_factors_ordered_by_sort_order(self, client, admin_headers, seeded_factors):
        """Factors are returned in sort_order."""
        response = client.get(
            "/risk-assessment/factors/",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify order matches sort_order
        codes_in_order = [f["code"] for f in data]
        assert codes_in_order == ["REPUTATION_LEGAL", "COMPLEXITY", "USAGE_DEPENDENCY", "STABILITY"]

    def test_list_factors_excludes_inactive(self, client, admin_headers, seeded_factors, db_session):
        """Inactive factors are excluded by default."""
        # Deactivate one factor
        factor = seeded_factors[0]
        factor.is_active = False
        db_session.commit()

        response = client.get(
            "/risk-assessment/factors/",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # One factor excluded

    def test_list_factors_include_inactive_param(self, client, admin_headers, seeded_factors, db_session):
        """Can include inactive factors with query param."""
        # Deactivate one factor
        factor = seeded_factors[0]
        factor.is_active = False
        db_session.commit()

        response = client.get(
            "/risk-assessment/factors/?include_inactive=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4  # All factors included

    def test_list_factors_requires_auth(self, client, seeded_factors):
        """Unauthenticated request returns 403."""
        response = client.get("/risk-assessment/factors/")
        assert response.status_code == 403


# ============================================================================
# Test: GET /risk-assessment/factors/{id} - Get Single Factor
# ============================================================================

class TestGetFactor:
    """Tests for retrieving a single factor."""

    def test_get_factor_with_guidance(self, client, admin_headers, seeded_factors):
        """Returns factor with all guidance entries."""
        factor = seeded_factors[0]
        response = client.get(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["factor_id"] == factor.factor_id
        assert data["code"] == "REPUTATION_LEGAL"
        assert len(data["guidance"]) == 3

    def test_get_factor_not_found(self, client, admin_headers):
        """Non-existent factor returns 404."""
        response = client.get(
            "/risk-assessment/factors/99999",
            headers=admin_headers
        )
        assert response.status_code == 404


# ============================================================================
# Test: POST /risk-assessment/factors/ - Create Factor
# ============================================================================

class TestCreateFactor:
    """Tests for creating qualitative risk factors."""

    def test_create_factor_admin_only(self, client, auth_headers, seeded_factors):
        """Only admin can create factors (not regular user)."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=auth_headers,  # Regular user
            json={
                "code": "NEW_FACTOR",
                "name": "New Factor",
                "weight": 0.1,
                "sort_order": 5
            }
        )
        assert response.status_code == 403

    def test_create_factor_validator_forbidden(self, client, validator_headers, seeded_factors):
        """Validator cannot create factors (Admin only)."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=validator_headers,
            json={
                "code": "NEW_FACTOR",
                "name": "New Factor",
                "weight": 0.1,
                "sort_order": 5
            }
        )
        assert response.status_code == 403

    def test_create_factor_success(self, client, admin_headers, seeded_factors):
        """Admin can create new factor."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "DATA_QUALITY",
                "name": "Data Quality",
                "description": "Assessment of input data quality",
                "weight": 0.0,  # Initially 0, will adjust weights later
                "sort_order": 5
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "DATA_QUALITY"
        assert data["is_active"] is True

    def test_create_factor_with_guidance(self, client, admin_headers, seeded_factors):
        """Can create factor with initial guidance."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "DATA_QUALITY",
                "name": "Data Quality",
                "weight": 0.0,
                "sort_order": 5,
                "guidance": [
                    {"rating": "HIGH", "points": 3, "description": "High data quality risk"},
                    {"rating": "MEDIUM", "points": 2, "description": "Medium data quality risk"},
                    {"rating": "LOW", "points": 1, "description": "Low data quality risk"}
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data.get("guidance", [])) == 3

    def test_create_factor_duplicate_code_fails(self, client, admin_headers, seeded_factors):
        """Cannot create factor with existing code."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "REPUTATION_LEGAL",  # Already exists
                "name": "Duplicate Factor",
                "weight": 0.1,
                "sort_order": 5
            }
        )
        assert response.status_code == 409

    def test_create_factor_validates_weight_range(self, client, admin_headers, seeded_factors):
        """Weight must be between 0 and 1."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "INVALID_WEIGHT",
                "name": "Invalid Weight Factor",
                "weight": 1.5,  # Invalid: > 1
                "sort_order": 5
            }
        )
        assert response.status_code == 422


# ============================================================================
# Test: PUT /risk-assessment/factors/{id} - Update Factor
# ============================================================================

class TestUpdateFactor:
    """Tests for updating factors."""

    def test_update_factor_name(self, client, admin_headers, seeded_factors):
        """Can update factor name and description."""
        factor = seeded_factors[0]
        response = client.put(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=admin_headers,
            json={
                "name": "Updated Factor Name",
                "description": "Updated description"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Factor Name"
        assert data["description"] == "Updated description"

    def test_update_factor_weight(self, client, admin_headers, seeded_factors):
        """Can update factor weight."""
        factor = seeded_factors[0]
        response = client.put(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=admin_headers,
            json={
                "weight": 0.25
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["weight"] == 0.25

    def test_update_factor_admin_only(self, client, validator_headers, seeded_factors):
        """Only admin can update factors."""
        factor = seeded_factors[0]
        response = client.put(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=validator_headers,
            json={
                "name": "Updated Name"
            }
        )
        assert response.status_code == 403

    def test_update_factor_not_found(self, client, admin_headers):
        """Update non-existent factor returns 404."""
        response = client.put(
            "/risk-assessment/factors/99999",
            headers=admin_headers,
            json={"name": "New Name"}
        )
        assert response.status_code == 404

    def test_update_code_duplicate_fails(self, client, admin_headers, seeded_factors):
        """Cannot update code to existing value."""
        factor = seeded_factors[0]
        response = client.put(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=admin_headers,
            json={
                "code": "COMPLEXITY"  # Already exists on another factor
            }
        )
        assert response.status_code == 409


# ============================================================================
# Test: PATCH /risk-assessment/factors/{id}/weight - Update Weight Only
# ============================================================================

class TestPatchFactorWeight:
    """Tests for updating factor weight only."""

    def test_patch_weight_success(self, client, admin_headers, seeded_factors):
        """Can patch weight directly."""
        factor = seeded_factors[0]
        response = client.patch(
            f"/risk-assessment/factors/{factor.factor_id}/weight",
            headers=admin_headers,
            json={"weight": 0.35}
        )
        assert response.status_code == 200
        assert response.json()["weight"] == 0.35

    def test_patch_weight_validates_range(self, client, admin_headers, seeded_factors):
        """Weight must be valid."""
        factor = seeded_factors[0]
        response = client.patch(
            f"/risk-assessment/factors/{factor.factor_id}/weight",
            headers=admin_headers,
            json={"weight": -0.1}  # Invalid
        )
        assert response.status_code == 422


# ============================================================================
# Test: DELETE /risk-assessment/factors/{id} - Soft Delete Factor
# ============================================================================

class TestDeleteFactor:
    """Tests for deleting (deactivating) factors."""

    def test_delete_factor_soft_deletes(self, client, admin_headers, seeded_factors, db_session):
        """Delete sets is_active=false, not hard delete."""
        factor = seeded_factors[0]
        response = client.delete(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # Verify soft deleted
        db_session.refresh(factor)
        assert factor.is_active is False

    def test_delete_factor_admin_only(self, client, validator_headers, seeded_factors):
        """Only admin can delete factors."""
        factor = seeded_factors[0]
        response = client.delete(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=validator_headers
        )
        assert response.status_code == 403

    def test_delete_factor_in_use_fails(
        self, client, admin_headers, seeded_factors, db_session,
        sample_model, risk_tier_taxonomy
    ):
        """Cannot delete factor used in existing assessments."""
        from app.models.risk_assessment import ModelRiskAssessment, QualitativeFactorAssessment

        # Create an assessment using the factor
        assessment = ModelRiskAssessment(
            model_id=sample_model.model_id,
            region_id=None
        )
        db_session.add(assessment)
        db_session.flush()

        factor = seeded_factors[0]
        factor_assessment = QualitativeFactorAssessment(
            assessment_id=assessment.assessment_id,
            factor_id=factor.factor_id,
            rating="HIGH",
            weight_at_assessment=Decimal("0.30"),
            score=Decimal("0.90")
        )
        db_session.add(factor_assessment)
        db_session.commit()

        # Try to delete factor
        response = client.delete(
            f"/risk-assessment/factors/{factor.factor_id}",
            headers=admin_headers
        )
        assert response.status_code == 409
        assert "in use" in response.json()["detail"].lower()

    def test_delete_factor_not_found(self, client, admin_headers):
        """Delete non-existent factor returns 404."""
        response = client.delete(
            "/risk-assessment/factors/99999",
            headers=admin_headers
        )
        assert response.status_code == 404


# ============================================================================
# Test: POST /risk-assessment/factors/validate-weights - Validate Weights
# ============================================================================

class TestValidateWeights:
    """Tests for weight validation endpoint."""

    def test_validate_weights_pass(self, client, admin_headers, seeded_factors):
        """Weights summing to 1.0 passes validation."""
        response = client.post(
            "/risk-assessment/factors/validate-weights",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["total"] == 1.0

    def test_validate_weights_fail(self, client, admin_headers, seeded_factors, db_session):
        """Weights not summing to 1.0 fails validation."""
        # Change one weight
        factor = seeded_factors[0]
        factor.weight = Decimal("0.50")
        db_session.commit()

        response = client.post(
            "/risk-assessment/factors/validate-weights",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["total"] == 1.2  # 0.5 + 0.3 + 0.2 + 0.2

    def test_validate_weights_excludes_inactive(self, client, admin_headers, seeded_factors, db_session):
        """Only active factors counted in validation."""
        # Deactivate one factor
        factor = seeded_factors[0]
        factor.is_active = False
        db_session.commit()

        response = client.post(
            "/risk-assessment/factors/validate-weights",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Now only 0.3 + 0.2 + 0.2 = 0.7
        assert data["valid"] is False
        assert data["total"] == 0.7


# ============================================================================
# Test: POST /risk-assessment/factors/reorder - Reorder Factors
# ============================================================================

class TestReorderFactors:
    """Tests for reordering factors."""

    def test_reorder_factors_success(self, client, admin_headers, seeded_factors):
        """Can reorder factors by providing new order."""
        new_order = [
            seeded_factors[3].factor_id,  # STABILITY first
            seeded_factors[2].factor_id,  # USAGE_DEPENDENCY
            seeded_factors[1].factor_id,  # COMPLEXITY
            seeded_factors[0].factor_id,  # REPUTATION_LEGAL last
        ]
        response = client.post(
            "/risk-assessment/factors/reorder",
            headers=admin_headers,
            json={"factor_ids": new_order}
        )
        assert response.status_code == 200

        # Verify new order
        list_response = client.get(
            "/risk-assessment/factors/",
            headers=admin_headers
        )
        data = list_response.json()
        result_ids = [f["factor_id"] for f in data]
        assert result_ids == new_order

    def test_reorder_factors_admin_only(self, client, validator_headers, seeded_factors):
        """Only admin can reorder factors."""
        response = client.post(
            "/risk-assessment/factors/reorder",
            headers=validator_headers,
            json={"factor_ids": [1, 2, 3, 4]}
        )
        assert response.status_code == 403

    def test_reorder_factors_invalid_ids(self, client, admin_headers, seeded_factors):
        """Returns error for invalid factor IDs."""
        response = client.post(
            "/risk-assessment/factors/reorder",
            headers=admin_headers,
            json={"factor_ids": [99999, 99998]}
        )
        assert response.status_code == 400


# ============================================================================
# Test: POST /risk-assessment/factors/{id}/guidance - Add Guidance
# ============================================================================

class TestAddGuidance:
    """Tests for adding guidance to factors."""

    def test_add_guidance_success(self, client, admin_headers, db_session):
        """Can add guidance entry to a factor."""
        # Create a factor without guidance
        factor = QualitativeRiskFactor(
            code="NEW_FACTOR",
            name="New Factor",
            weight=Decimal("0.0"),
            sort_order=5
        )
        db_session.add(factor)
        db_session.commit()

        response = client.post(
            f"/risk-assessment/factors/{factor.factor_id}/guidance",
            headers=admin_headers,
            json={
                "rating": "HIGH",
                "points": 3,
                "description": "High risk guidance text"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == "HIGH"
        assert data["points"] == 3

    def test_add_guidance_duplicate_rating_fails(self, client, admin_headers, seeded_factors):
        """Cannot add duplicate rating for same factor."""
        factor = seeded_factors[0]
        response = client.post(
            f"/risk-assessment/factors/{factor.factor_id}/guidance",
            headers=admin_headers,
            json={
                "rating": "HIGH",  # Already exists
                "points": 3,
                "description": "Duplicate guidance"
            }
        )
        assert response.status_code == 409

    def test_add_guidance_admin_only(self, client, validator_headers, seeded_factors):
        """Only admin can add guidance."""
        factor = seeded_factors[0]
        response = client.post(
            f"/risk-assessment/factors/{factor.factor_id}/guidance",
            headers=validator_headers,
            json={
                "rating": "VERY_HIGH",
                "points": 4,
                "description": "New guidance"
            }
        )
        assert response.status_code == 403

    def test_add_guidance_factor_not_found(self, client, admin_headers):
        """Add guidance to non-existent factor returns 404."""
        response = client.post(
            "/risk-assessment/factors/99999/guidance",
            headers=admin_headers,
            json={
                "rating": "HIGH",
                "points": 3,
                "description": "Guidance"
            }
        )
        assert response.status_code == 404


# ============================================================================
# Test: PUT /risk-assessment/factors/guidance/{id} - Update Guidance
# ============================================================================

class TestUpdateGuidance:
    """Tests for updating guidance entries."""

    def test_update_guidance_text(self, client, admin_headers, seeded_factors, db_session):
        """Can update guidance description."""
        # Get a guidance entry
        guidance = db_session.query(QualitativeFactorGuidance).filter(
            QualitativeFactorGuidance.factor_id == seeded_factors[0].factor_id,
            QualitativeFactorGuidance.rating == "HIGH"
        ).first()

        response = client.put(
            f"/risk-assessment/factors/guidance/{guidance.guidance_id}",
            headers=admin_headers,
            json={
                "description": "Updated guidance description"
            }
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated guidance description"

    def test_update_guidance_points(self, client, admin_headers, seeded_factors, db_session):
        """Can update guidance points."""
        guidance = db_session.query(QualitativeFactorGuidance).filter(
            QualitativeFactorGuidance.factor_id == seeded_factors[0].factor_id,
            QualitativeFactorGuidance.rating == "HIGH"
        ).first()

        response = client.put(
            f"/risk-assessment/factors/guidance/{guidance.guidance_id}",
            headers=admin_headers,
            json={
                "points": 5
            }
        )
        assert response.status_code == 200
        assert response.json()["points"] == 5

    def test_update_guidance_admin_only(self, client, validator_headers, seeded_factors, db_session):
        """Only admin can update guidance."""
        guidance = db_session.query(QualitativeFactorGuidance).filter(
            QualitativeFactorGuidance.factor_id == seeded_factors[0].factor_id
        ).first()

        response = client.put(
            f"/risk-assessment/factors/guidance/{guidance.guidance_id}",
            headers=validator_headers,
            json={"description": "Updated"}
        )
        assert response.status_code == 403

    def test_update_guidance_not_found(self, client, admin_headers):
        """Update non-existent guidance returns 404."""
        response = client.put(
            "/risk-assessment/factors/guidance/99999",
            headers=admin_headers,
            json={"description": "Updated"}
        )
        assert response.status_code == 404


# ============================================================================
# Test: DELETE /risk-assessment/factors/guidance/{id} - Delete Guidance
# ============================================================================

class TestDeleteGuidance:
    """Tests for deleting guidance entries."""

    def test_delete_guidance_success(self, client, admin_headers, seeded_factors, db_session):
        """Can delete guidance entry."""
        guidance = db_session.query(QualitativeFactorGuidance).filter(
            QualitativeFactorGuidance.factor_id == seeded_factors[0].factor_id,
            QualitativeFactorGuidance.rating == "HIGH"
        ).first()

        response = client.delete(
            f"/risk-assessment/factors/guidance/{guidance.guidance_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

    def test_delete_guidance_admin_only(self, client, validator_headers, seeded_factors, db_session):
        """Only admin can delete guidance."""
        guidance = db_session.query(QualitativeFactorGuidance).filter(
            QualitativeFactorGuidance.factor_id == seeded_factors[0].factor_id
        ).first()

        response = client.delete(
            f"/risk-assessment/factors/guidance/{guidance.guidance_id}",
            headers=validator_headers
        )
        assert response.status_code == 403

    def test_delete_guidance_not_found(self, client, admin_headers):
        """Delete non-existent guidance returns 404."""
        response = client.delete(
            "/risk-assessment/factors/guidance/99999",
            headers=admin_headers
        )
        assert response.status_code == 404


# ============================================================================
# Test: Response Schema Structure
# ============================================================================

class TestResponseSchema:
    """Tests for validating response structure."""

    def test_factor_response_structure(self, client, admin_headers, seeded_factors):
        """Factor response includes all expected fields."""
        response = client.get(
            f"/risk-assessment/factors/{seeded_factors[0].factor_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        expected_fields = [
            "factor_id", "code", "name", "description",
            "weight", "sort_order", "is_active",
            "guidance", "created_at", "updated_at"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_guidance_response_structure(self, client, admin_headers, seeded_factors, db_session):
        """Guidance response includes all expected fields."""
        guidance = db_session.query(QualitativeFactorGuidance).filter(
            QualitativeFactorGuidance.factor_id == seeded_factors[0].factor_id
        ).first()

        response = client.put(
            f"/risk-assessment/factors/guidance/{guidance.guidance_id}",
            headers=admin_headers,
            json={"description": "Test update"}
        )
        assert response.status_code == 200
        data = response.json()

        expected_fields = [
            "guidance_id", "factor_id", "rating",
            "points", "description", "sort_order"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
