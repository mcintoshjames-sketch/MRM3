"""Vendor API tests."""
import pytest


class TestListVendors:
    """Test listing vendors."""

    def test_list_vendors_empty(self, client, auth_headers):
        response = client.get("/vendors/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_vendors_with_data(self, client, auth_headers, sample_vendor):
        response = client.get("/vendors/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Vendor"
        assert data[0]["contact_info"] == "contact@testvendor.com"

    def test_list_vendors_unauthenticated(self, client):
        response = client.get("/vendors/")
        assert response.status_code == 403


class TestCreateVendor:
    """Test creating vendors."""

    def test_create_vendor_success(self, client, auth_headers):
        response = client.post(
            "/vendors/",
            headers=auth_headers,
            json={
                "name": "Bloomberg",
                "contact_info": "support@bloomberg.com"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bloomberg"
        assert data["contact_info"] == "support@bloomberg.com"
        assert "vendor_id" in data
        assert "created_at" in data

    def test_create_vendor_minimal(self, client, auth_headers):
        response = client.post(
            "/vendors/",
            headers=auth_headers,
            json={"name": "MSCI"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "MSCI"
        assert data["contact_info"] is None

    def test_create_vendor_duplicate_name(self, client, auth_headers, sample_vendor):
        response = client.post(
            "/vendors/",
            headers=auth_headers,
            json={"name": "Test Vendor"}
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_vendor_unauthenticated(self, client):
        response = client.post("/vendors/", json={"name": "Vendor"})
        assert response.status_code == 403

    def test_create_vendor_missing_name(self, client, auth_headers):
        response = client.post(
            "/vendors/",
            headers=auth_headers,
            json={"contact_info": "test@test.com"}
        )
        assert response.status_code == 422


class TestGetVendor:
    """Test getting a single vendor."""

    def test_get_vendor_success(self, client, auth_headers, sample_vendor):
        response = client.get(
            f"/vendors/{sample_vendor.vendor_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vendor_id"] == sample_vendor.vendor_id
        assert data["name"] == "Test Vendor"

    def test_get_vendor_not_found(self, client, auth_headers):
        response = client.get("/vendors/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_vendor_unauthenticated(self, client, sample_vendor):
        response = client.get(f"/vendors/{sample_vendor.vendor_id}")
        assert response.status_code == 403


class TestUpdateVendor:
    """Test updating vendors."""

    def test_update_vendor_single_field(self, client, auth_headers, sample_vendor):
        response = client.patch(
            f"/vendors/{sample_vendor.vendor_id}",
            headers=auth_headers,
            json={"name": "Updated Vendor"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Vendor"

    def test_update_vendor_multiple_fields(self, client, auth_headers, sample_vendor):
        response = client.patch(
            f"/vendors/{sample_vendor.vendor_id}",
            headers=auth_headers,
            json={
                "name": "New Name",
                "contact_info": "new@contact.com"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["contact_info"] == "new@contact.com"

    def test_update_vendor_not_found(self, client, auth_headers):
        response = client.patch(
            "/vendors/9999",
            headers=auth_headers,
            json={"name": "Test"}
        )
        assert response.status_code == 404

    def test_update_vendor_duplicate_name(self, client, auth_headers, sample_vendor, db_session):
        # Create another vendor
        from app.models.vendor import Vendor
        vendor2 = Vendor(name="Another Vendor")
        db_session.add(vendor2)
        db_session.commit()

        # Try to update to existing name
        response = client.patch(
            f"/vendors/{vendor2.vendor_id}",
            headers=auth_headers,
            json={"name": "Test Vendor"}
        )
        assert response.status_code == 400

    def test_update_vendor_unauthenticated(self, client, sample_vendor):
        response = client.patch(
            f"/vendors/{sample_vendor.vendor_id}",
            json={"name": "Test"}
        )
        assert response.status_code == 403


class TestDeleteVendor:
    """Test deleting vendors."""

    def test_delete_vendor_success(self, client, auth_headers, sample_vendor):
        response = client.delete(
            f"/vendors/{sample_vendor.vendor_id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_delete_vendor_not_found(self, client, auth_headers):
        response = client.delete("/vendors/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_vendor_unauthenticated(self, client, sample_vendor):
        response = client.delete(f"/vendors/{sample_vendor.vendor_id}")
        assert response.status_code == 403

    def test_deleted_vendor_is_gone(self, client, auth_headers, sample_vendor):
        vendor_id = sample_vendor.vendor_id
        client.delete(f"/vendors/{vendor_id}", headers=auth_headers)
        response = client.get(f"/vendors/{vendor_id}", headers=auth_headers)
        assert response.status_code == 404
