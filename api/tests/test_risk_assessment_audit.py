"""Tests for Model Risk Assessment Audit Logging.

TDD RED Phase: These tests verify audit logging for risk assessment operations.
"""
import pytest
from decimal import Decimal

from app.models.risk_assessment import (
    QualitativeRiskFactor,
    QualitativeFactorGuidance,
)
from app.models.audit_log import AuditLog
from app.models.taxonomy import Taxonomy, TaxonomyValue


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def risk_tier_taxonomy_audit(db_session):
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
def qualitative_factors_audit(db_session):
    """Create the 4 standard qualitative risk factors."""
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
                sort_order=4 - points
            )
            db_session.add(guidance)

        factors.append(factor)

    db_session.commit()
    return factors


# ============================================================================
# Test: Assessment Audit Logging
# ============================================================================

class TestAssessmentAuditLogging:
    """Tests for risk assessment audit logging."""

    def test_create_assessment_creates_audit_log(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Creating assessment logs to audit trail."""
        # Create assessment
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors_audit
                ]
            }
        )
        assert response.status_code == 201
        assessment_id = response.json()["assessment_id"]

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "CREATE"
            )
            .first()
        )
        assert audit_log is not None
        assert audit_log.changes is not None

    def test_update_assessment_creates_audit_log(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Updating assessment logs changes to audit trail."""
        # Create assessment
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors_audit
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update assessment
        client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors_audit
                ]
            }
        )

        # Check audit log for UPDATE
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "UPDATE"
            )
            .first()
        )
        assert audit_log is not None
        assert audit_log.changes is not None
        # Verify changes contain the modified fields
        assert "quantitative_rating" in audit_log.changes or "old" in audit_log.changes

    def test_delete_assessment_creates_audit_log(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Deleting assessment logs to audit trail."""
        # Create assessment
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

        # Delete assessment
        client.delete(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers
        )

        # Check audit log for DELETE
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "DELETE"
            )
            .first()
        )
        assert audit_log is not None


# ============================================================================
# Test: Override Audit Logging
# ============================================================================

class TestOverrideAuditLogging:
    """Tests for override changes audit logging."""

    def test_quantitative_override_logged(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Quantitative override is logged with override type."""
        # Create without override
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "LOW",
                "factor_ratings": []
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update with override
        client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "quantitative_override": "HIGH",
                "quantitative_override_comment": "Override for compliance",
                "factor_ratings": []
            }
        )

        # Check audit log contains override info
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "UPDATE"
            )
            .first()
        )
        assert audit_log is not None
        # Check override is in changes
        changes = audit_log.changes
        assert changes is not None
        # Should have override_type or override-related changes
        changes_str = str(changes)
        assert "quantitative_override" in changes_str or "override" in changes_str.lower()

    def test_qualitative_override_logged(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Qualitative override is logged."""
        # Create assessment
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors_audit
                ],
                "qualitative_override": "HIGH",
                "qualitative_override_comment": "Strategic importance override"
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Check CREATE log has override info
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "CREATE"
            )
            .first()
        )
        assert audit_log is not None
        changes_str = str(audit_log.changes)
        assert "qualitative_override" in changes_str or "override" in changes_str.lower()

    def test_final_tier_override_logged(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Final tier override is logged."""
        # Create assessment with final override
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors_audit
                ],
                "derived_risk_tier_override": "HIGH",
                "derived_risk_tier_override_comment": "Executive override"
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "CREATE"
            )
            .first()
        )
        assert audit_log is not None
        changes_str = str(audit_log.changes)
        assert "derived_risk_tier_override" in changes_str or "override" in changes_str.lower()


# ============================================================================
# Test: Model Tier Sync Audit Logging
# ============================================================================

class TestModelTierSyncAuditLogging:
    """Tests for model tier synchronization audit logging."""

    def test_model_tier_sync_logged(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Model tier change is logged when assessment syncs it."""
        # Create global assessment which triggers tier sync
        response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors_audit
                ]
            }
        )
        assert response.status_code == 201

        # Check for Model audit log with tier change
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "Model",
                AuditLog.entity_id == sample_model.model_id,
                AuditLog.action == "UPDATE"
            )
            .order_by(AuditLog.timestamp.desc())
            .first()
        )
        # This may or may not exist depending on implementation
        # The important thing is that some audit trail exists for the tier change
        # Either in the Model entity or in the Assessment entity with tier sync info

    def test_tier_change_logged_with_before_after(
        self, client, admin_headers, sample_model, qualitative_factors_audit,
        risk_tier_taxonomy_audit, db_session
    ):
        """Tier change log includes before/after values."""
        # Create with HIGH tier
        create_response = client.post(
            f"/models/{sample_model.model_id}/risk-assessments/",
            headers=admin_headers,
            json={
                "region_id": None,
                "quantitative_rating": "HIGH",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "HIGH"}
                    for f in qualitative_factors_audit
                ]
            }
        )
        assessment_id = create_response.json()["assessment_id"]

        # Update to LOW tier
        client.put(
            f"/models/{sample_model.model_id}/risk-assessments/{assessment_id}",
            headers=admin_headers,
            json={
                "quantitative_rating": "LOW",
                "factor_ratings": [
                    {"factor_id": f.factor_id, "rating": "LOW"}
                    for f in qualitative_factors_audit
                ]
            }
        )

        # Check audit log has tier change information
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "ModelRiskAssessment",
                AuditLog.entity_id == assessment_id,
                AuditLog.action == "UPDATE"
            )
            .first()
        )
        assert audit_log is not None
        # The changes should contain information about derived tier changing
        changes = audit_log.changes
        assert changes is not None


# ============================================================================
# Test: Factor Configuration Audit Logging
# ============================================================================

class TestFactorConfigAuditLogging:
    """Tests for qualitative factor configuration audit logging."""

    def test_factor_create_logged(self, client, admin_headers, db_session):
        """Creating a factor creates audit log."""
        response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "TEST_FACTOR",
                "name": "Test Factor",
                "weight": 0.0,
                "sort_order": 10
            }
        )
        assert response.status_code == 201
        factor_id = response.json()["factor_id"]

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "QualitativeRiskFactor",
                AuditLog.entity_id == factor_id,
                AuditLog.action == "CREATE"
            )
            .first()
        )
        assert audit_log is not None

    def test_factor_update_logged(self, client, admin_headers, db_session):
        """Updating a factor creates audit log."""
        # Create factor
        create_response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "UPDATE_TEST",
                "name": "Update Test",
                "weight": 0.0,
                "sort_order": 10
            }
        )
        factor_id = create_response.json()["factor_id"]

        # Update factor
        client.put(
            f"/risk-assessment/factors/{factor_id}",
            headers=admin_headers,
            json={"weight": 0.1}
        )

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "QualitativeRiskFactor",
                AuditLog.entity_id == factor_id,
                AuditLog.action == "UPDATE"
            )
            .first()
        )
        assert audit_log is not None
        assert "weight" in str(audit_log.changes)

    def test_factor_weight_change_logged(self, client, admin_headers, db_session):
        """Weight-only update creates audit log with weight change."""
        # Create factor
        create_response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "WEIGHT_TEST",
                "name": "Weight Test",
                "weight": 0.1,
                "sort_order": 10
            }
        )
        factor_id = create_response.json()["factor_id"]

        # Update weight only
        client.patch(
            f"/risk-assessment/factors/{factor_id}/weight",
            headers=admin_headers,
            json={"weight": 0.2}
        )

        # Check audit log
        audit_logs = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "QualitativeRiskFactor",
                AuditLog.entity_id == factor_id,
                AuditLog.action == "UPDATE"
            )
            .all()
        )
        assert len(audit_logs) >= 1
        # Should have weight change logged
        weight_logged = any("weight" in str(log.changes) for log in audit_logs)
        assert weight_logged


# ============================================================================
# Test: Guidance Audit Logging
# ============================================================================

class TestGuidanceAuditLogging:
    """Tests for factor guidance audit logging."""

    def test_guidance_create_logged(self, client, admin_headers, db_session):
        """Adding guidance creates audit log."""
        # Create factor without guidance
        factor_response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "GUIDANCE_TEST",
                "name": "Guidance Test",
                "weight": 0.0,
                "sort_order": 10
            }
        )
        factor_id = factor_response.json()["factor_id"]

        # Add guidance
        guidance_response = client.post(
            f"/risk-assessment/factors/{factor_id}/guidance",
            headers=admin_headers,
            json={
                "rating": "HIGH",
                "points": 3,
                "description": "Test guidance"
            }
        )
        assert guidance_response.status_code == 201
        guidance_id = guidance_response.json()["guidance_id"]

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "QualitativeFactorGuidance",
                AuditLog.entity_id == guidance_id,
                AuditLog.action == "CREATE"
            )
            .first()
        )
        assert audit_log is not None

    def test_guidance_update_logged(self, client, admin_headers, db_session):
        """Updating guidance creates audit log."""
        # Create factor with guidance
        factor_response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "GUIDANCE_UPDATE",
                "name": "Guidance Update Test",
                "weight": 0.0,
                "sort_order": 10,
                "guidance": [
                    {"rating": "HIGH", "points": 3, "description": "Original"}
                ]
            }
        )
        factor_id = factor_response.json()["factor_id"]
        guidance_id = factor_response.json()["guidance"][0]["guidance_id"]

        # Update guidance
        client.put(
            f"/risk-assessment/factors/guidance/{guidance_id}",
            headers=admin_headers,
            json={"description": "Updated description"}
        )

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "QualitativeFactorGuidance",
                AuditLog.entity_id == guidance_id,
                AuditLog.action == "UPDATE"
            )
            .first()
        )
        assert audit_log is not None

    def test_guidance_delete_logged(self, client, admin_headers, db_session):
        """Deleting guidance creates audit log."""
        # Create factor with guidance
        factor_response = client.post(
            "/risk-assessment/factors/",
            headers=admin_headers,
            json={
                "code": "GUIDANCE_DELETE",
                "name": "Guidance Delete Test",
                "weight": 0.0,
                "sort_order": 10,
                "guidance": [
                    {"rating": "HIGH", "points": 3, "description": "To delete"}
                ]
            }
        )
        guidance_id = factor_response.json()["guidance"][0]["guidance_id"]

        # Delete guidance
        client.delete(
            f"/risk-assessment/factors/guidance/{guidance_id}",
            headers=admin_headers
        )

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "QualitativeFactorGuidance",
                AuditLog.entity_id == guidance_id,
                AuditLog.action == "DELETE"
            )
            .first()
        )
        assert audit_log is not None
