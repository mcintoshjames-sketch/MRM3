"""Tests for Methodology Library endpoints."""
import pytest


class TestListMethodologyCategories:
    """Tests for GET /methodology-library/categories endpoint."""

    def test_list_categories_success(self, client, auth_headers, methodology_category):
        """Test that authenticated users can list methodology categories."""
        response = client.get("/methodology-library/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Find our test category
        test_cat = next((c for c in data if c["code"] == "TEST_CAT"), None)
        assert test_cat is not None
        assert test_cat["name"] == "Test Category"
        # By default, only active methodologies should be included
        assert len(test_cat["methodologies"]) == 2  # methodology1 and methodology2 (active)

    def test_list_categories_with_inactive(self, client, auth_headers, methodology_category):
        """Test that active_only=false includes inactive methodologies."""
        response = client.get(
            "/methodology-library/categories?active_only=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        test_cat = next((c for c in data if c["code"] == "TEST_CAT"), None)
        assert test_cat is not None
        # Should include all 3 methodologies
        assert len(test_cat["methodologies"]) == 3

    def test_list_categories_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/methodology-library/categories")
        # FastAPI's JWT auth returns 403 Forbidden for missing/invalid tokens
        assert response.status_code in [401, 403]


class TestListMethodologies:
    """Tests for GET /methodology-library/methodologies endpoint."""

    def test_list_methodologies_success(self, client, auth_headers, methodology_category):
        """Test listing methodologies with default active_only=true."""
        response = client.get("/methodology-library/methodologies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only contain active methodologies
        names = [m["name"] for m in data]
        assert "Test Methodology 1" in names
        assert "Test Methodology 2" in names
        assert "Inactive Methodology" not in names

    def test_list_methodologies_include_inactive(self, client, auth_headers, methodology_category):
        """Test listing methodologies with inactive included."""
        response = client.get(
            "/methodology-library/methodologies?active_only=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        names = [m["name"] for m in data]
        assert "Inactive Methodology" in names

    def test_list_methodologies_filter_by_category(self, client, auth_headers, methodology_category):
        """Test filtering methodologies by category_id."""
        category_id = methodology_category["category"].category_id
        response = client.get(
            f"/methodology-library/methodologies?category_id={category_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(m["category_id"] == category_id for m in data)

    def test_search_methodologies_by_name(self, client, auth_headers, methodology_category):
        """Test searching methodologies by name."""
        response = client.get(
            "/methodology-library/methodologies?search=Methodology 1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Methodology 1"

    def test_search_methodologies_by_description(self, client, auth_headers, methodology_category):
        """Test searching methodologies by description."""
        response = client.get(
            "/methodology-library/methodologies?search=First test&active_only=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["description"] == "First test methodology"

    def test_list_methodologies_pagination(self, client, auth_headers, methodology_category):
        """Test pagination of methodologies list."""
        response = client.get(
            "/methodology-library/methodologies?active_only=false&limit=1&offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response2 = client.get(
            "/methodology-library/methodologies?active_only=false&limit=1&offset=1",
            headers=auth_headers
        )
        data2 = response2.json()
        assert len(data2) == 1
        assert data[0]["methodology_id"] != data2[0]["methodology_id"]


class TestGetMethodology:
    """Tests for GET /methodology-library/methodologies/{id} endpoint."""

    def test_get_methodology_success(self, client, auth_headers, methodology_category):
        """Test getting a specific methodology by ID."""
        methodology_id = methodology_category["methodology1"].methodology_id
        response = client.get(
            f"/methodology-library/methodologies/{methodology_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Methodology 1"
        assert data["variants"] == "Variant A, Variant B"

    def test_get_methodology_not_found(self, client, auth_headers):
        """Test getting a non-existent methodology."""
        response = client.get(
            "/methodology-library/methodologies/99999",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestCreateMethodologyCategory:
    """Tests for POST /methodology-library/categories endpoint."""

    def test_create_category_admin_success(self, client, admin_headers):
        """Test that admins can create methodology categories."""
        response = client.post(
            "/methodology-library/categories",
            json={
                "code": "NEW_CAT",
                "name": "New Category",
                "sort_order": 10
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "NEW_CAT"
        assert data["name"] == "New Category"
        assert data["sort_order"] == 10

    def test_create_category_duplicate_code(self, client, admin_headers, methodology_category):
        """Test that duplicate category codes are rejected."""
        response = client.post(
            "/methodology-library/categories",
            json={
                "code": "TEST_CAT",  # Already exists
                "name": "Another Category",
                "sort_order": 5
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_category_non_admin_forbidden(self, client, auth_headers):
        """Test that non-admin users cannot create categories."""
        response = client.post(
            "/methodology-library/categories",
            json={
                "code": "FORBIDDEN_CAT",
                "name": "Should Not Create",
                "sort_order": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 403


class TestUpdateMethodologyCategory:
    """Tests for PATCH /methodology-library/categories/{id} endpoint."""

    def test_update_category_success(self, client, admin_headers, methodology_category):
        """Test that admins can update methodology categories."""
        category_id = methodology_category["category"].category_id
        response = client.patch(
            f"/methodology-library/categories/{category_id}",
            json={
                "name": "Updated Category Name"
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Category Name"
        assert data["code"] == "TEST_CAT"  # Unchanged

    def test_update_category_not_found(self, client, admin_headers):
        """Test updating a non-existent category."""
        response = client.patch(
            "/methodology-library/categories/99999",
            json={"name": "Does Not Exist"},
            headers=admin_headers
        )
        assert response.status_code == 404


class TestDeleteMethodologyCategory:
    """Tests for DELETE /methodology-library/categories/{id} endpoint."""

    def test_delete_category_success(self, client, admin_headers, db_session):
        """Test that admins can delete methodology categories."""
        from app.models.methodology import MethodologyCategory

        # Create a new category to delete
        category = MethodologyCategory(code="DELETE_ME", name="To Delete", sort_order=99)
        db_session.add(category)
        db_session.commit()
        category_id = category.category_id

        response = client.delete(
            f"/methodology-library/categories/{category_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

    def test_delete_category_not_found(self, client, admin_headers):
        """Test deleting a non-existent category."""
        response = client.delete(
            "/methodology-library/categories/99999",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_category_with_model_references_blocked(
        self, client, admin_headers, db_session, methodology_category, test_user, usage_frequency
    ):
        """Test that deletion is blocked when models reference methodologies in the category."""
        from app.models.model import Model

        # Create a model using a methodology from the category
        model = Model(
            model_name="Model With Methodology",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
            methodology_id=methodology_category["methodology1"].methodology_id
        )
        db_session.add(model)
        db_session.commit()

        category_id = methodology_category["category"].category_id
        response = client.delete(
            f"/methodology-library/categories/{category_id}",
            headers=admin_headers
        )
        assert response.status_code == 409
        assert "model(s) reference methodologies" in response.json()["detail"]

    def test_delete_category_force_with_model_references(
        self, client, admin_headers, db_session, methodology_category, test_user, usage_frequency
    ):
        """Test that force=true allows deletion even with model references."""
        from app.models.model import Model

        # Create a model using a methodology from the category
        model = Model(
            model_name="Model With Methodology 2",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
            methodology_id=methodology_category["methodology1"].methodology_id
        )
        db_session.add(model)
        db_session.commit()

        category_id = methodology_category["category"].category_id
        response = client.delete(
            f"/methodology-library/categories/{category_id}?force=true",
            headers=admin_headers
        )
        assert response.status_code == 204


class TestCreateMethodology:
    """Tests for POST /methodology-library/methodologies endpoint."""

    def test_create_methodology_admin_success(self, client, admin_headers, methodology_category):
        """Test that admins can create methodologies."""
        category_id = methodology_category["category"].category_id
        response = client.post(
            "/methodology-library/methodologies",
            json={
                "category_id": category_id,
                "name": "New Methodology",
                "description": "A newly created methodology",
                "variants": "Option 1, Option 2",
                "sort_order": 10,
                "is_active": True
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Methodology"
        assert data["category_id"] == category_id

    def test_create_methodology_invalid_category(self, client, admin_headers):
        """Test that creating methodology with invalid category fails."""
        response = client.post(
            "/methodology-library/methodologies",
            json={
                "category_id": 99999,
                "name": "Invalid Category Methodology",
                "sort_order": 1
            },
            headers=admin_headers
        )
        assert response.status_code == 404
        assert "Category not found" in response.json()["detail"]

    def test_create_methodology_non_admin_forbidden(self, client, auth_headers, methodology_category):
        """Test that non-admin users cannot create methodologies."""
        category_id = methodology_category["category"].category_id
        response = client.post(
            "/methodology-library/methodologies",
            json={
                "category_id": category_id,
                "name": "Forbidden Methodology",
                "sort_order": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 403


class TestUpdateMethodology:
    """Tests for PATCH /methodology-library/methodologies/{id} endpoint."""

    def test_update_methodology_success(self, client, admin_headers, methodology_category):
        """Test that admins can update methodologies."""
        methodology_id = methodology_category["methodology1"].methodology_id
        response = client.patch(
            f"/methodology-library/methodologies/{methodology_id}",
            json={
                "name": "Updated Methodology Name",
                "description": "Updated description"
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Methodology Name"
        assert data["description"] == "Updated description"

    def test_toggle_methodology_active(self, client, admin_headers, methodology_category):
        """Test toggling methodology active status."""
        methodology_id = methodology_category["methodology1"].methodology_id
        # Deactivate
        response = client.patch(
            f"/methodology-library/methodologies/{methodology_id}",
            json={"is_active": False},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Reactivate
        response = client.patch(
            f"/methodology-library/methodologies/{methodology_id}",
            json={"is_active": True},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_update_methodology_not_found(self, client, admin_headers):
        """Test updating a non-existent methodology."""
        response = client.patch(
            "/methodology-library/methodologies/99999",
            json={"name": "Does Not Exist"},
            headers=admin_headers
        )
        assert response.status_code == 404


class TestDeleteMethodology:
    """Tests for DELETE /methodology-library/methodologies/{id} endpoint."""

    def test_delete_methodology_success(self, client, admin_headers, db_session, methodology_category):
        """Test that admins can delete methodologies."""
        from app.models.methodology import Methodology

        category_id = methodology_category["category"].category_id
        # Create a new methodology to delete
        methodology = Methodology(
            category_id=category_id,
            name="To Delete",
            sort_order=99,
            is_active=True
        )
        db_session.add(methodology)
        db_session.commit()
        methodology_id = methodology.methodology_id

        response = client.delete(
            f"/methodology-library/methodologies/{methodology_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

    def test_delete_methodology_not_found(self, client, admin_headers):
        """Test deleting a non-existent methodology."""
        response = client.delete(
            "/methodology-library/methodologies/99999",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_methodology_with_model_references_blocked(
        self, client, admin_headers, db_session, methodology_category, test_user, usage_frequency
    ):
        """Test that deletion is blocked when models reference the methodology."""
        from app.models.model import Model

        methodology_id = methodology_category["methodology1"].methodology_id

        # Create a model using this methodology
        model = Model(
            model_name="Model Using Methodology",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
            methodology_id=methodology_id
        )
        db_session.add(model)
        db_session.commit()

        response = client.delete(
            f"/methodology-library/methodologies/{methodology_id}",
            headers=admin_headers
        )
        assert response.status_code == 409
        assert "model(s) use this methodology" in response.json()["detail"]

    def test_delete_methodology_force_with_model_references(
        self, client, admin_headers, db_session, methodology_category, test_user, usage_frequency
    ):
        """Test that force=true allows deletion even with model references."""
        from app.models.model import Model
        from app.models.methodology import Methodology

        # Create a new methodology to test force delete
        methodology = Methodology(
            category_id=methodology_category["category"].category_id,
            name="Force Delete Me",
            sort_order=99,
            is_active=True
        )
        db_session.add(methodology)
        db_session.flush()
        methodology_id = methodology.methodology_id

        # Create a model using this methodology
        model = Model(
            model_name="Model Using Force Delete Methodology",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
            methodology_id=methodology_id
        )
        db_session.add(model)
        db_session.commit()

        response = client.delete(
            f"/methodology-library/methodologies/{methodology_id}?force=true",
            headers=admin_headers
        )
        assert response.status_code == 204


class TestModelMethodologyLinkage:
    """Tests for model-methodology linkage."""

    def test_create_model_with_methodology(
        self, client, admin_headers, db_session, methodology_category, usage_frequency
    ):
        """Test creating a model with a methodology assigned."""
        methodology_id = methodology_category["methodology1"].methodology_id
        response = client.post(
            "/models/",
            json={
                "model_name": "Model With Methodology",
                "description": "A model using a methodology",
                "development_type": "In-House",
                "status": "Active",
                "owner_id": 1,  # admin user
                "usage_frequency_id": usage_frequency["daily"].value_id,
                "methodology_id": methodology_id
            },
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["methodology_id"] == methodology_id
        assert data["methodology"]["name"] == "Test Methodology 1"

    def test_update_model_methodology(
        self, client, admin_headers, db_session, methodology_category, test_user, usage_frequency
    ):
        """Test updating a model's methodology."""
        from app.models.model import Model

        # Create a model without methodology
        model = Model(
            model_name="Model To Update",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model)
        db_session.commit()
        model_id = model.model_id

        # Update with methodology
        methodology_id = methodology_category["methodology1"].methodology_id
        response = client.patch(
            f"/models/{model_id}",
            json={"methodology_id": methodology_id},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["methodology_id"] == methodology_id

    def test_get_model_with_methodology(
        self, client, admin_headers, db_session, methodology_category, test_user, usage_frequency
    ):
        """Test that model detail includes methodology information."""
        from app.models.model import Model

        methodology_id = methodology_category["methodology1"].methodology_id
        model = Model(
            model_name="Model With Methodology Detail",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
            methodology_id=methodology_id
        )
        db_session.add(model)
        db_session.commit()
        model_id = model.model_id

        response = client.get(f"/models/{model_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["methodology_id"] == methodology_id
        assert data["methodology"]["name"] == "Test Methodology 1"
        assert data["methodology"]["category_id"] == methodology_category["category"].category_id
