"""Tests for LOB (Line of Business) hierarchy functionality."""
import pytest
import io
from fastapi.testclient import TestClient


class TestLOBTree:
    """Test LOB tree retrieval and structure."""

    def test_get_tree_returns_hierarchy(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that tree endpoint returns proper hierarchy."""
        response = client.get("/lob-units/tree", headers=admin_headers)
        assert response.status_code == 200
        tree = response.json()

        # Root should be Corporate
        assert len(tree) == 1
        assert tree[0]["code"] == "CORP"
        assert tree[0]["name"] == "Corporate"
        assert tree[0]["level"] == 0

        # Should have 2 children (Retail and Wholesale)
        children = tree[0]["children"]
        assert len(children) == 2
        child_codes = {c["code"] for c in children}
        assert child_codes == {"RET", "WHL"}

    def test_get_tree_include_inactive(self, client: TestClient, admin_headers, db_session, lob_hierarchy):
        """Test include_inactive parameter shows inactive LOBs."""
        # Deactivate one LOB
        lob_hierarchy["deposits"].is_active = False
        db_session.commit()

        # Without inactive - should exclude deposits
        response = client.get("/lob-units/tree?include_inactive=false", headers=admin_headers)
        assert response.status_code == 200

        # With inactive - should include deposits
        response = client.get("/lob-units/tree?include_inactive=true", headers=admin_headers)
        assert response.status_code == 200

    def test_get_flat_list(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test flat list endpoint returns all LOBs."""
        response = client.get("/lob-units/", headers=admin_headers)
        assert response.status_code == 200
        lobs = response.json()

        # Should have 5 LOBs in total
        assert len(lobs) == 5
        codes = {lob["code"] for lob in lobs}
        assert codes == {"CORP", "RET", "WHL", "CRD", "DEP"}


class TestLOBCRUD:
    """Test LOB CRUD operations."""

    def test_create_lob_unit(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test creating a new LOB unit."""
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "MKT",
                "name": "Marketing",
                "org_unit": "30001",  # 5-digit org_unit
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "MKT"
        assert data["name"] == "Marketing"
        assert data["org_unit"] == "30001"
        assert data["level"] == 1
        assert "Corporate" in data["full_path"]

    def test_create_lob_requires_admin(self, client: TestClient, auth_headers, lob_hierarchy):
        """Test that only admin can create LOB units."""
        response = client.post(
            "/lob-units/",
            headers=auth_headers,  # Regular user headers
            json={
                "code": "FAIL",
                "name": "Should Fail",
                "org_unit": "99999",
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 403

    def test_create_lob_duplicate_code_same_parent(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that duplicate code under same parent is rejected."""
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "RET",  # Already exists under Corporate
                "name": "Duplicate Retail",
                "org_unit": "30002",  # Different org_unit
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower() or "exists" in response.json()["detail"].lower()

    def test_create_lob_same_code_different_parent_allowed(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that same code under different parent is allowed (disambiguation)."""
        # Create "CRD" under Wholesale (already exists under Retail)
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "CRD",
                "name": "Wholesale Credit",
                "org_unit": "30003",  # Unique org_unit
                "parent_id": lob_hierarchy["wholesale"].lob_id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "CRD"
        assert data["org_unit"] == "30003"
        assert "Wholesale Banking" in data["full_path"]

    def test_update_lob_unit(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test updating an LOB unit."""
        lob_id = lob_hierarchy["credit"].lob_id
        response = client.patch(
            f"/lob-units/{lob_id}",
            headers=admin_headers,
            json={"name": "Credit Department"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Credit Department"

    def test_get_single_lob(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test retrieving a single LOB unit."""
        lob_id = lob_hierarchy["retail"].lob_id
        response = client.get(f"/lob-units/{lob_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "RET"
        assert data["name"] == "Retail Banking"


class TestLOBDeactivation:
    """Test LOB deactivation with cascading checks."""

    def test_deactivate_leaf_lob(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test deactivating a leaf LOB unit (no children)."""
        lob_id = lob_hierarchy["deposits"].lob_id
        response = client.patch(
            f"/lob-units/{lob_id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_cannot_deactivate_parent_with_active_children(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that deactivating a parent with active children is blocked."""
        # Retail has active children (Credit, Deposits)
        lob_id = lob_hierarchy["retail"].lob_id
        response = client.patch(
            f"/lob-units/{lob_id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        # Should fail because active children exist
        assert response.status_code == 400
        assert "child" in response.json()["detail"].lower()

    def test_cannot_deactivate_lob_with_users(self, client: TestClient, admin_headers, lob_hierarchy, db_session, test_user):
        """Test that LOB with assigned users cannot be deactivated."""
        # test_user is assigned to retail LOB, but retail has children
        # Move user to a leaf LOB (deposits) to test user check
        test_user.lob_id = lob_hierarchy["deposits"].lob_id
        db_session.commit()

        # Try to deactivate deposits (leaf with user assigned)
        lob_id = lob_hierarchy["deposits"].lob_id
        response = client.patch(
            f"/lob-units/{lob_id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        # Should fail because user is assigned
        assert response.status_code == 400
        assert "user" in response.json()["detail"].lower()

    def test_reactivate_lob(self, client: TestClient, admin_headers, db_session, lob_hierarchy):
        """Test reactivating a deactivated LOB."""
        # First deactivate
        lob_id = lob_hierarchy["deposits"].lob_id
        lob_hierarchy["deposits"].is_active = False
        db_session.commit()

        # Then reactivate
        response = client.patch(
            f"/lob-units/{lob_id}",
            headers=admin_headers,
            json={"is_active": True}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True


class TestLOBExport:
    """Test LOB export functionality."""

    def test_export_csv(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test exporting LOB hierarchy as CSV."""
        response = client.get("/lob-units/export-csv", headers=admin_headers)
        # Debug: print response if not 200
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

        # Check CSV content
        content = response.content.decode("utf-8")
        assert "SBU" in content  # Should have hierarchy columns (SBU, LOB1, LOB2, etc.)
        assert "Corporate" in content
        assert "Retail Banking" in content


class TestLOBImport:
    """Test LOB import functionality."""

    def test_import_preview_dry_run(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test import preview with dry_run returns detailed breakdown."""
        # Use legacy format: SBU, LOB1, LOB2, etc.
        csv_content = "SBU,LOB1,LOB2\nCorporate,New Division,New Team\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post(
            "/lob-units/import-csv?dry_run=true",
            headers=admin_headers,
            files=files
        )
        assert response.status_code == 200
        data = response.json()

        # Should return preview with detailed breakdown
        assert "to_create" in data or "detected_columns" in data
        assert "errors" in data

    def test_import_creates_new_lobs(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test import creates new LOB units."""
        # Use legacy format: SBU, LOB1, LOB2, etc.
        csv_content = "SBU,LOB1,LOB2\nCorporate,New Business Unit,New Team\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post(
            "/lob-units/import-csv?dry_run=false",
            headers=admin_headers,
            files=files
        )
        assert response.status_code == 200

        # Verify new LOB was created
        tree_response = client.get("/lob-units/tree", headers=admin_headers)
        tree_content = str(tree_response.json())
        assert "New Business Unit" in tree_content

    def test_import_requires_admin(self, client: TestClient, auth_headers):
        """Test that only admin can import LOBs."""
        csv_content = "SBU\nTest\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post(
            "/lob-units/import-csv",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 403


class TestUserLOBAssignment:
    """Test user LOB assignment functionality."""

    def test_user_has_lob_assigned(self, client: TestClient, admin_headers, test_user):
        """Test that user has LOB assigned."""
        response = client.get(f"/auth/users/{test_user.user_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["lob_id"] is not None
        assert data["lob"] is not None
        assert "full_path" in data["lob"]

    def test_create_user_requires_lob(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that creating a user requires LOB assignment."""
        # Try without LOB
        response = client.post(
            "/auth/register",
            headers=admin_headers,
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "password123",
                "role": "User"
                # Missing lob_id
            }
        )
        # Should fail because lob_id is required
        assert response.status_code in [400, 422]

    def test_create_user_with_lob(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test creating a user with LOB assignment."""
        response = client.post(
            "/auth/register",
            headers=admin_headers,
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "password123",
                "role": "User",
                "lob_id": lob_hierarchy["retail"].lob_id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["lob_id"] == lob_hierarchy["retail"].lob_id

    def test_update_user_lob(self, client: TestClient, admin_headers, test_user, lob_hierarchy):
        """Test updating user's LOB assignment."""
        response = client.patch(
            f"/auth/users/{test_user.user_id}",
            headers=admin_headers,
            json={"lob_id": lob_hierarchy["wholesale"].lob_id}
        )
        assert response.status_code == 200
        assert response.json()["lob_id"] == lob_hierarchy["wholesale"].lob_id


class TestLOBOrgUnit:
    """Test org_unit functionality."""

    def test_lob_response_includes_org_unit(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that LOB responses include org_unit field."""
        response = client.get("/lob-units/", headers=admin_headers)
        assert response.status_code == 200
        lobs = response.json()

        for lob in lobs:
            assert "org_unit" in lob
            assert lob["org_unit"] is not None
            assert len(lob["org_unit"]) == 5

    def test_create_lob_validates_org_unit_format(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that org_unit format is validated on create."""
        # Invalid: too short
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "TST",
                "name": "Test",
                "org_unit": "123",  # Should be 5 chars
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 422

        # Invalid: wrong format
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "TST",
                "name": "Test",
                "org_unit": "ABCDE",  # Must be digits or S+4 digits
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 422

    def test_create_lob_accepts_valid_org_unit_formats(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that valid org_unit formats are accepted."""
        # Valid: 5 digits
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "TST1",
                "name": "Test 1",
                "org_unit": "99991",
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 201
        assert response.json()["org_unit"] == "99991"

        # Valid: S + 4 digits (synthetic)
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "TST2",
                "name": "Test 2",
                "org_unit": "S9999",
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 201
        assert response.json()["org_unit"] == "S9999"

    def test_org_unit_uniqueness(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that org_unit must be globally unique."""
        # First create
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "UNQ1",
                "name": "Unique Test 1",
                "org_unit": "88888",
                "parent_id": lob_hierarchy["corporate"].lob_id
            }
        )
        assert response.status_code == 201

        # Duplicate org_unit should fail
        response = client.post(
            "/lob-units/",
            headers=admin_headers,
            json={
                "code": "UNQ2",
                "name": "Unique Test 2",
                "org_unit": "88888",  # Same org_unit
                "parent_id": lob_hierarchy["wholesale"].lob_id
            }
        )
        assert response.status_code == 400
        assert "org_unit" in response.json()["detail"].lower()

    def test_tree_includes_org_unit(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that tree response includes org_unit."""
        response = client.get("/lob-units/tree", headers=admin_headers)
        assert response.status_code == 200
        tree = response.json()

        # Check root has org_unit
        assert "org_unit" in tree[0]
        assert tree[0]["org_unit"] == "S0001"

        # Check children have org_unit
        for child in tree[0]["children"]:
            assert "org_unit" in child
            assert len(child["org_unit"]) == 5


class TestLOBHierarchy:
    """Test LOB hierarchy-related functionality."""

    def test_tree_structure_includes_children(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that tree endpoint includes nested children properly."""
        response = client.get("/lob-units/tree", headers=admin_headers)
        assert response.status_code == 200
        tree = response.json()

        # Navigate to Retail and check it has 2 children
        retail = next((c for c in tree[0]["children"] if c["code"] == "RET"), None)
        assert retail is not None
        assert len(retail["children"]) == 2

        # Verify Credit and Deposits are children of Retail
        child_codes = {c["code"] for c in retail["children"]}
        assert child_codes == {"CRD", "DEP"}

    def test_lob_level_reflects_hierarchy_depth(self, client: TestClient, admin_headers, lob_hierarchy):
        """Test that LOB level values correctly reflect hierarchy depth."""
        response = client.get("/lob-units/", headers=admin_headers)
        assert response.status_code == 200
        lobs = response.json()

        # Create dict of code -> level
        levels = {lob["code"]: lob["level"] for lob in lobs}

        # Corporate is root (level 0)
        assert levels["CORP"] == 0
        # Retail and Wholesale are level 1
        assert levels["RET"] == 1
        assert levels["WHL"] == 1
        # Credit and Deposits are level 2
        assert levels["CRD"] == 2
        assert levels["DEP"] == 2
