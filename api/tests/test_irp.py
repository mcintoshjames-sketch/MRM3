"""Tests for IRP (Independent Review Process) endpoints."""
import pytest


class TestIRPList:
    """Tests for listing IRPs."""

    def test_list_irps_empty(self, client, admin_headers):
        """Test listing IRPs when none exist."""
        response = client.get("/irps/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_irps_with_data(self, client, admin_headers, sample_irp):
        """Test listing IRPs with existing data."""
        response = client.get("/irps/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["irp_id"] == sample_irp.irp_id
        assert data[0]["process_name"] == "Test IRP"
        assert data[0]["is_active"] == True
        assert data[0]["covered_mrsa_count"] == 1

    def test_list_irps_filter_active(self, client, admin_headers, sample_irp, db_session):
        """Test filtering IRPs by active status."""
        # Create an inactive IRP
        from app.models.irp import IRP
        inactive_irp = IRP(
            process_name="Inactive IRP",
            contact_user_id=sample_irp.contact_user_id,
            is_active=False
        )
        db_session.add(inactive_irp)
        db_session.commit()

        # Filter for active only
        response = client.get("/irps/?is_active=true", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["process_name"] == "Test IRP"

        # Filter for inactive only
        response = client.get("/irps/?is_active=false", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["process_name"] == "Inactive IRP"

    def test_list_irps_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/irps/")
        assert response.status_code == 403


class TestIRPCreate:
    """Tests for creating IRPs."""

    def test_create_irp_admin(self, client, admin_headers, admin_user):
        """Test creating an IRP as admin."""
        response = client.post(
            "/irps/",
            json={
                "process_name": "New IRP",
                "description": "A new IRP for testing",
                "contact_user_id": admin_user.user_id,
                "is_active": True
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["process_name"] == "New IRP"
        assert data["description"] == "A new IRP for testing"
        assert data["contact_user_id"] == admin_user.user_id
        assert data["is_active"] == True
        assert "irp_id" in data

    def test_create_irp_with_mrsas(
        self, client, admin_headers, admin_user, sample_mrsa
    ):
        """Test creating an IRP with linked MRSAs."""
        response = client.post(
            "/irps/",
            json={
                "process_name": "IRP with MRSAs",
                "contact_user_id": admin_user.user_id,
                "mrsa_ids": [sample_mrsa.model_id]
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["covered_mrsa_count"] == 1
        assert len(data["covered_mrsas"]) == 1
        assert data["covered_mrsas"][0]["model_id"] == sample_mrsa.model_id

    def test_create_irp_non_admin_forbidden(self, client, auth_headers, test_user):
        """Test that non-admins cannot create IRPs."""
        response = client.post(
            "/irps/",
            json={
                "process_name": "Unauthorized IRP",
                "contact_user_id": test_user.user_id
            },
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_create_irp_duplicate_name(self, client, admin_headers, admin_user, sample_irp):
        """Test that duplicate IRP names are rejected."""
        response = client.post(
            "/irps/",
            json={
                "process_name": sample_irp.process_name,
                "contact_user_id": admin_user.user_id
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_irp_invalid_contact_user(self, client, admin_headers):
        """Test creating IRP with non-existent contact user."""
        response = client.post(
            "/irps/",
            json={
                "process_name": "Invalid Contact IRP",
                "contact_user_id": 99999
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "Contact user not found" in response.json()["detail"]

    def test_create_irp_invalid_mrsa(self, client, admin_headers, admin_user):
        """Test creating IRP with non-existent MRSA."""
        response = client.post(
            "/irps/",
            json={
                "process_name": "Invalid MRSA IRP",
                "contact_user_id": admin_user.user_id,
                "mrsa_ids": [99999]
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "not found or not MRSAs" in response.json()["detail"]


class TestIRPDetail:
    """Tests for getting IRP details."""

    def test_get_irp_detail(self, client, admin_headers, sample_irp):
        """Test getting IRP detail with relationships."""
        response = client.get(f"/irps/{sample_irp.irp_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["irp_id"] == sample_irp.irp_id
        assert data["process_name"] == "Test IRP"
        assert "covered_mrsas" in data
        assert "reviews" in data
        assert "certifications" in data

    def test_get_irp_not_found(self, client, admin_headers):
        """Test getting non-existent IRP."""
        response = client.get("/irps/99999", headers=admin_headers)
        assert response.status_code == 404


class TestIRPUpdate:
    """Tests for updating IRPs."""

    def test_update_irp_admin(self, client, admin_headers, sample_irp):
        """Test updating an IRP as admin."""
        response = client.patch(
            f"/irps/{sample_irp.irp_id}",
            json={"description": "Updated description"},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_irp_non_admin_forbidden(self, client, auth_headers, sample_irp):
        """Test that non-admins cannot update IRPs."""
        response = client.patch(
            f"/irps/{sample_irp.irp_id}",
            json={"description": "Unauthorized update"},
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_update_irp_not_found(self, client, admin_headers):
        """Test updating non-existent IRP."""
        response = client.patch(
            "/irps/99999",
            json={"description": "Update non-existent"},
            headers=admin_headers
        )
        assert response.status_code == 404


class TestIRPDelete:
    """Tests for deleting IRPs."""

    def test_delete_irp_admin(self, client, admin_headers, sample_irp, db_session):
        """Test deleting an IRP as admin."""
        irp_id = sample_irp.irp_id
        response = client.delete(f"/irps/{irp_id}", headers=admin_headers)
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/irps/{irp_id}", headers=admin_headers)
        assert response.status_code == 404

    def test_delete_irp_non_admin_forbidden(self, client, auth_headers, sample_irp):
        """Test that non-admins cannot delete IRPs."""
        response = client.delete(f"/irps/{sample_irp.irp_id}", headers=auth_headers)
        assert response.status_code == 403

    def test_delete_irp_not_found(self, client, admin_headers):
        """Test deleting non-existent IRP."""
        response = client.delete("/irps/99999", headers=admin_headers)
        assert response.status_code == 404


class TestIRPReviews:
    """Tests for IRP review endpoints."""

    def test_list_reviews_empty(self, client, admin_headers, sample_irp):
        """Test listing reviews when none exist."""
        response = client.get(f"/irps/{sample_irp.irp_id}/reviews", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_review(
        self, client, admin_headers, sample_irp, irp_outcome_taxonomy
    ):
        """Test creating a review for an IRP."""
        response = client.post(
            f"/irps/{sample_irp.irp_id}/reviews",
            json={
                "review_date": "2025-12-11",
                "outcome_id": irp_outcome_taxonomy["satisfactory"].value_id,
                "notes": "All MRSAs adequately governed"
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["irp_id"] == sample_irp.irp_id
        assert data["outcome"]["code"] == "SATISFACTORY"
        assert data["notes"] == "All MRSAs adequately governed"

    def test_list_reviews_with_data(
        self, client, admin_headers, sample_irp, irp_outcome_taxonomy, db_session
    ):
        """Test listing reviews with existing data."""
        from app.models.irp import IRPReview
        from datetime import date

        review = IRPReview(
            irp_id=sample_irp.irp_id,
            review_date=date(2025, 12, 11),
            outcome_id=irp_outcome_taxonomy["satisfactory"].value_id,
            reviewed_by_user_id=sample_irp.contact_user_id
        )
        db_session.add(review)
        db_session.commit()

        response = client.get(f"/irps/{sample_irp.irp_id}/reviews", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["outcome"]["code"] == "SATISFACTORY"


class TestIRPCertifications:
    """Tests for IRP certification endpoints."""

    def test_list_certifications_empty(self, client, admin_headers, sample_irp):
        """Test listing certifications when none exist."""
        response = client.get(
            f"/irps/{sample_irp.irp_id}/certifications",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_create_certification_admin(self, client, admin_headers, sample_irp):
        """Test creating a certification as admin."""
        response = client.post(
            f"/irps/{sample_irp.irp_id}/certifications",
            json={
                "certification_date": "2025-12-11",
                "conclusion_summary": "IRP adequately addresses MRSA risks"
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["irp_id"] == sample_irp.irp_id
        assert data["conclusion_summary"] == "IRP adequately addresses MRSA risks"

    def test_create_certification_non_admin_forbidden(
        self, client, auth_headers, sample_irp
    ):
        """Test that non-admins cannot create certifications."""
        response = client.post(
            f"/irps/{sample_irp.irp_id}/certifications",
            json={
                "certification_date": "2025-12-11",
                "conclusion_summary": "Unauthorized certification"
            },
            headers=auth_headers
        )
        assert response.status_code == 403


class TestIRPCoverageCheck:
    """Tests for IRP coverage check endpoint."""

    def test_coverage_check_with_coverage(
        self, client, admin_headers, sample_irp, sample_mrsa
    ):
        """Test coverage check for MRSA with IRP coverage."""
        response = client.get("/irps/coverage/check", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == sample_mrsa.model_id
        assert data[0]["requires_irp"] == True
        assert data[0]["has_irp_coverage"] == True
        assert data[0]["is_compliant"] == True
        assert sample_irp.irp_id in data[0]["irp_ids"]

    def test_coverage_check_without_coverage(
        self, client, admin_headers, sample_mrsa, db_session
    ):
        """Test coverage check for MRSA without IRP coverage."""
        # Remove IRP from MRSA
        sample_mrsa.irps = []
        db_session.commit()

        response = client.get("/irps/coverage/check", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["requires_irp"] == True
        assert data[0]["has_irp_coverage"] == False
        assert data[0]["is_compliant"] == False

    def test_coverage_check_low_risk_compliant(
        self, client, admin_headers, admin_user, usage_frequency, mrsa_risk_level_taxonomy, db_session
    ):
        """Test that low-risk MRSAs are compliant without IRP."""
        from app.models.model import Model

        low_risk_mrsa = Model(
            model_name="Low Risk MRSA",
            development_type="In-House",
            owner_id=admin_user.user_id,
            is_model=False,
            is_mrsa=True,
            mrsa_risk_level_id=mrsa_risk_level_taxonomy["low_risk"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(low_risk_mrsa)
        db_session.commit()

        response = client.get(
            f"/irps/coverage/check?mrsa_ids={low_risk_mrsa.model_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["requires_irp"] == False
        assert data[0]["is_compliant"] == True  # Compliant because doesn't require IRP

    def test_coverage_check_filter_require_irp(
        self, client, admin_headers, sample_mrsa
    ):
        """Test filtering coverage check for only IRPs that require coverage."""
        response = client.get(
            "/irps/coverage/check?require_irp_only=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should only return high-risk MRSAs
        for item in data:
            assert item["requires_irp"] == True


class TestModelsIsMarFilter:
    """Tests for is_mrsa filter on models endpoint."""

    def test_filter_mrsas_only(
        self, client, admin_headers, sample_mrsa, sample_model
    ):
        """Test filtering to show only MRSAs."""
        response = client.get("/models/?is_mrsa=true", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only contain the MRSA
        model_ids = [m["model_id"] for m in data]
        assert sample_mrsa.model_id in model_ids
        assert sample_model.model_id not in model_ids

    def test_filter_models_only(
        self, client, admin_headers, sample_mrsa, sample_model
    ):
        """Test filtering to show only models (not MRSAs)."""
        response = client.get("/models/?is_mrsa=false", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only contain the regular model
        model_ids = [m["model_id"] for m in data]
        assert sample_model.model_id in model_ids
        assert sample_mrsa.model_id not in model_ids
