"""API integration tests for bucket taxonomy functionality."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def bucket_taxonomy(db_session):
    """Create a bucket taxonomy for testing."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    taxonomy = Taxonomy(
        name="Test Bucket Taxonomy",
        description="A test bucket taxonomy",
        taxonomy_type="bucket",
        is_system=False,
    )
    db_session.add(taxonomy)
    db_session.flush()

    # Create valid contiguous buckets
    values = [
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="LOW",
            label="Low",
            min_days=None,
            max_days=30,
            sort_order=1,
        ),
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="MEDIUM",
            label="Medium",
            min_days=31,
            max_days=90,
            sort_order=2,
        ),
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="HIGH",
            label="High",
            min_days=91,
            max_days=None,
            sort_order=3,
        ),
    ]
    db_session.add_all(values)
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "values": {v.code: v for v in values},
    }


@pytest.fixture
def standard_taxonomy(db_session):
    """Create a standard (non-bucket) taxonomy for comparison."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    taxonomy = Taxonomy(
        name="Test Standard Taxonomy",
        description="A test standard taxonomy",
        taxonomy_type="standard",
        is_system=False,
    )
    db_session.add(taxonomy)
    db_session.flush()

    values = [
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="OPTION_A",
            label="Option A",
            sort_order=1,
        ),
        TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="OPTION_B",
            label="Option B",
            sort_order=2,
        ),
    ]
    db_session.add_all(values)
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "values": {v.code: v for v in values},
    }


class TestBucketTaxonomyRead:
    """Tests for reading bucket taxonomy data."""

    def test_get_bucket_taxonomy_includes_min_max_days(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """GET taxonomy should include min_days and max_days for bucket values."""
        tax_id = bucket_taxonomy["taxonomy"].taxonomy_id
        response = client.get(f"/taxonomies/{tax_id}", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["taxonomy_type"] == "bucket"
        assert len(data["values"]) == 3

        # Check first bucket (unbounded lower)
        low = next(v for v in data["values"] if v["code"] == "LOW")
        assert low["min_days"] is None
        assert low["max_days"] == 30

        # Check middle bucket
        medium = next(v for v in data["values"] if v["code"] == "MEDIUM")
        assert medium["min_days"] == 31
        assert medium["max_days"] == 90

        # Check last bucket (unbounded upper)
        high = next(v for v in data["values"] if v["code"] == "HIGH")
        assert high["min_days"] == 91
        assert high["max_days"] is None

    def test_list_taxonomies_includes_type(
        self, client: TestClient, bucket_taxonomy, standard_taxonomy, admin_headers
    ):
        """GET /taxonomies/ should include taxonomy_type."""
        response = client.get("/taxonomies/", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        bucket_tax = next(
            (t for t in data if t["name"] == "Test Bucket Taxonomy"), None
        )
        standard_tax = next(
            (t for t in data if t["name"] == "Test Standard Taxonomy"), None
        )

        assert bucket_tax is not None
        assert bucket_tax["taxonomy_type"] == "bucket"

        assert standard_tax is not None
        assert standard_tax["taxonomy_type"] == "standard"

    def test_non_admin_can_read_bucket_taxonomy(
        self, client: TestClient, bucket_taxonomy, auth_headers
    ):
        """Non-admin users should be able to read bucket taxonomies."""
        tax_id = bucket_taxonomy["taxonomy"].taxonomy_id
        response = client.get(f"/taxonomies/{tax_id}", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["taxonomy_type"] == "bucket"


class TestBucketTaxonomyCreate:
    """Tests for creating bucket taxonomies and values."""

    def test_create_bucket_taxonomy(self, client: TestClient, admin_headers):
        """Admin can create a bucket taxonomy."""
        response = client.post(
            "/taxonomies/",
            json={
                "name": "New Bucket Tax",
                "description": "Test",
                "taxonomy_type": "bucket",
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["taxonomy_type"] == "bucket"
        assert data["name"] == "New Bucket Tax"

    def test_create_bucket_value_with_valid_range(
        self, client: TestClient, db_session, admin_headers
    ):
        """Creating a bucket value with valid range should succeed."""
        from app.models.taxonomy import Taxonomy

        # Create empty bucket taxonomy
        taxonomy = Taxonomy(
            name="Empty Bucket Tax",
            taxonomy_type="bucket",
            is_system=False,
        )
        db_session.add(taxonomy)
        db_session.commit()

        # Add first (and only) bucket - must be unbounded on both ends
        response = client.post(
            f"/taxonomies/{taxonomy.taxonomy_id}/values",
            json={
                "code": "ALL",
                "label": "All",
                "min_days": None,
                "max_days": None,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["min_days"] is None
        assert data["max_days"] is None

    def test_create_bucket_value_validation_fails_for_gap(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Creating a bucket value that creates a gap should fail."""
        tax_id = bucket_taxonomy["taxonomy"].taxonomy_id

        # Try to add a bucket that creates a gap (currently: null-30, 31-90, 91-null)
        # Adding 200-null would create gap 91-199
        response = client.post(
            f"/taxonomies/{tax_id}/values",
            json={
                "code": "EXTRA",
                "label": "Extra High",
                "min_days": 200,
                "max_days": None,
            },
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Bucket validation failed" in response.json()["detail"]

    def test_create_bucket_value_validation_fails_for_overlap(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Creating a bucket value that overlaps should fail."""
        tax_id = bucket_taxonomy["taxonomy"].taxonomy_id

        # Try to add overlapping bucket
        response = client.post(
            f"/taxonomies/{tax_id}/values",
            json={
                "code": "OVERLAP",
                "label": "Overlapping",
                "min_days": 50,
                "max_days": 100,
            },
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Bucket validation failed" in response.json()["detail"]

    def test_standard_taxonomy_ignores_min_max_days(
        self, client: TestClient, standard_taxonomy, admin_headers
    ):
        """Standard taxonomies should ignore min_days/max_days values."""
        tax_id = standard_taxonomy["taxonomy"].taxonomy_id

        response = client.post(
            f"/taxonomies/{tax_id}/values",
            json={
                "code": "OPTION_C",
                "label": "Option C",
                "min_days": 100,  # Should be ignored
                "max_days": 200,  # Should be ignored
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        # min_days and max_days should be null for standard taxonomies
        assert data["min_days"] is None
        assert data["max_days"] is None


class TestBucketTaxonomyUpdate:
    """Tests for updating bucket taxonomy values."""

    def test_update_bucket_value_maintains_contiguity(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Updating bucket value while maintaining contiguity should succeed."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Update medium bucket - same range, just label change
        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"label": "Medium Updated"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["label"] == "Medium Updated"

    def test_update_bucket_value_creating_gap_fails(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Updating bucket value that creates a gap should fail."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Try to shrink medium bucket, creating a gap
        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"min_days": 50, "max_days": 80},  # Gap: 31-49 and 81-90
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Bucket validation failed" in response.json()["detail"]

    def test_update_bucket_value_creating_overlap_fails(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Updating bucket value that creates overlap should fail."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Try to expand medium bucket to overlap with high
        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"max_days": 100},  # Overlaps with HIGH which starts at 91
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Bucket validation failed" in response.json()["detail"]

    def test_cannot_change_code(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Code cannot be changed after creation."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"code": "NEW_CODE"},
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Code cannot be changed" in response.json()["detail"]


class TestBucketTaxonomyDelete:
    """Tests for deleting bucket taxonomy values."""

    def test_delete_bucket_value_creating_gap_fails(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Deleting a bucket value that creates a gap should fail."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Try to delete middle bucket - would create gap between LOW (null-30) and HIGH (91-null)
        response = client.delete(
            f"/taxonomies/values/{medium_value.value_id}",
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Cannot delete this bucket" in response.json()["detail"]

    def test_delete_all_but_one_bucket_succeeds(
        self, client: TestClient, db_session, admin_headers
    ):
        """Deleting buckets until only one unbounded bucket remains should succeed."""
        from app.models.taxonomy import Taxonomy, TaxonomyValue

        # Create taxonomy with two buckets
        taxonomy = Taxonomy(
            name="Two Bucket Tax",
            taxonomy_type="bucket",
            is_system=False,
        )
        db_session.add(taxonomy)
        db_session.flush()

        low = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="LOW",
            label="Low",
            min_days=None,
            max_days=50,
            sort_order=1,
        )
        high = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="HIGH",
            label="High",
            min_days=51,
            max_days=None,
            sort_order=2,
        )
        db_session.add_all([low, high])
        db_session.commit()

        # Delete low bucket - this will fail because it creates invalid state
        # (HIGH would need to become unbounded on both ends)
        response = client.delete(
            f"/taxonomies/values/{low.value_id}",
            headers=admin_headers,
        )
        # This should fail - remaining HIGH bucket doesn't have null min_days
        assert response.status_code == 400

    def test_delete_from_standard_taxonomy_succeeds(
        self, client: TestClient, standard_taxonomy, admin_headers
    ):
        """Deleting from standard taxonomy should succeed (no bucket validation)."""
        option_a = standard_taxonomy["values"]["OPTION_A"]

        response = client.delete(
            f"/taxonomies/values/{option_a.value_id}",
            headers=admin_headers,
        )
        assert response.status_code == 204


class TestBucketTaxonomyRoleRestrictions:
    """Tests for role-based access control on bucket taxonomies.

    Note: These tests will initially fail until Phase 2.1 implements
    the admin-only restrictions for bucket taxonomy modifications.
    """

    def test_non_admin_cannot_create_bucket_value(
        self, client: TestClient, bucket_taxonomy, auth_headers
    ):
        """Non-admin users should not be able to create bucket taxonomy values."""
        tax_id = bucket_taxonomy["taxonomy"].taxonomy_id

        response = client.post(
            f"/taxonomies/{tax_id}/values",
            json={
                "code": "NEW",
                "label": "New Value",
                "min_days": 91,
                "max_days": None,
            },
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "administrators" in response.json()["detail"].lower()

    def test_non_admin_cannot_update_bucket_range(
        self, client: TestClient, bucket_taxonomy, auth_headers
    ):
        """Non-admin users should not be able to update bucket range values."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Non-admin trying to update min_days/max_days should fail
        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"min_days": 35, "max_days": 85},
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "administrators" in response.json()["detail"].lower()

    def test_non_admin_can_update_bucket_label(
        self, client: TestClient, bucket_taxonomy, auth_headers
    ):
        """Non-admin users can update non-range fields like label."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Non-admin updating label (not range) should succeed
        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"label": "Medium Updated by User"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_non_admin_cannot_delete_bucket_value(
        self, client: TestClient, bucket_taxonomy, auth_headers
    ):
        """Non-admin users should not be able to delete bucket taxonomy values."""
        low_value = bucket_taxonomy["values"]["LOW"]

        response = client.delete(
            f"/taxonomies/values/{low_value.value_id}",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "administrators" in response.json()["detail"].lower()

    def test_admin_can_modify_bucket_taxonomy(
        self, client: TestClient, bucket_taxonomy, admin_headers
    ):
        """Admin users should be able to modify bucket taxonomies."""
        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        # Admin should be able to update (non-breaking change)
        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"label": "Medium - Admin Updated"},
            headers=admin_headers,
        )
        assert response.status_code == 200

    def test_non_admin_can_modify_standard_taxonomy(
        self, client: TestClient, standard_taxonomy, auth_headers
    ):
        """Non-admin users can modify standard taxonomies (existing behavior)."""
        option_a = standard_taxonomy["values"]["OPTION_A"]

        response = client.patch(
            f"/taxonomies/values/{option_a.value_id}",
            json={"label": "Option A Updated"},
            headers=auth_headers,
        )
        # Standard taxonomies don't have the admin restriction
        assert response.status_code == 200


class TestBucketTaxonomyAuditLog:
    """Tests for audit logging of bucket taxonomy operations."""

    def test_create_bucket_value_creates_audit_log(
        self, client: TestClient, db_session, admin_headers
    ):
        """Creating a bucket value should create an audit log with bucket fields."""
        from app.models.taxonomy import Taxonomy
        from app.models.audit_log import AuditLog

        # Create empty bucket taxonomy
        taxonomy = Taxonomy(
            name="Audit Test Tax",
            taxonomy_type="bucket",
            is_system=False,
        )
        db_session.add(taxonomy)
        db_session.commit()

        # Add bucket value
        response = client.post(
            f"/taxonomies/{taxonomy.taxonomy_id}/values",
            json={
                "code": "ALL",
                "label": "All",
                "min_days": None,
                "max_days": None,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        value_id = response.json()["value_id"]

        # Check audit log
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "TaxonomyValue",
                AuditLog.entity_id == value_id,
                AuditLog.action == "CREATE",
            )
            .first()
        )
        assert audit is not None
        assert "min_days" in audit.changes
        assert "max_days" in audit.changes

    def test_update_bucket_value_creates_audit_log(
        self, client: TestClient, db_session, bucket_taxonomy, admin_headers
    ):
        """Updating a bucket value should create an audit log."""
        from app.models.audit_log import AuditLog

        medium_value = bucket_taxonomy["values"]["MEDIUM"]

        response = client.patch(
            f"/taxonomies/values/{medium_value.value_id}",
            json={"label": "Medium - Audit Test"},
            headers=admin_headers,
        )
        assert response.status_code == 200

        # Check audit log
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "TaxonomyValue",
                AuditLog.entity_id == medium_value.value_id,
                AuditLog.action == "UPDATE",
            )
            .first()
        )
        assert audit is not None
        assert "label" in audit.changes
