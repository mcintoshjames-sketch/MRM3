"""Tests for bulk update fields endpoint."""
import pytest
from app.models.model import Model
from app.models.user import User
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.role import Role
from app.core.roles import RoleCode
from app.core.security import get_password_hash


@pytest.fixture
def second_user(db_session, lob_hierarchy):
    """Create a second user for testing."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="second@example.com",
        full_name="Second User",
        password_hash=get_password_hash("test123"),
        role_id=role_id,
        lob_id=lob_hierarchy["credit"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def third_user(db_session, lob_hierarchy):
    """Create a third user for testing."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="third@example.com",
        full_name="Third User",
        password_hash=get_password_hash("test123"),
        role_id=role_id,
        lob_id=lob_hierarchy["deposits"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regulatory_categories(db_session):
    """Create regulatory category taxonomy values."""
    taxonomy = Taxonomy(name="Regulatory Category", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    cat1 = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="REG_CAT_1",
        label="Regulatory Category 1",
        sort_order=1,
        is_active=True
    )
    cat2 = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="REG_CAT_2",
        label="Regulatory Category 2",
        sort_order=2,
        is_active=True
    )
    cat3 = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="REG_CAT_3",
        label="Regulatory Category 3",
        sort_order=3,
        is_active=True
    )
    db_session.add_all([cat1, cat2, cat3])
    db_session.commit()
    return {"cat1": cat1, "cat2": cat2, "cat3": cat3}


@pytest.fixture
def test_models(db_session, test_user, second_user, usage_frequency):
    """Create multiple test models."""
    models = []
    for i in range(3):
        model = Model(
            model_name=f"Test Model {i+1}",
            description=f"Description for model {i+1}",
            development_type="In-House",
            status="Active",
            owner_id=test_user.user_id,
            developer_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
        )
        db_session.add(model)
        models.append(model)
    db_session.commit()
    for m in models:
        db_session.refresh(m)
    return models


class TestBulkUpdateFieldsAccess:
    """Test access control for bulk update endpoint."""

    def test_admin_can_bulk_update(self, client, admin_headers, test_models, second_user):
        """Test that admin can perform bulk updates."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 3
        assert data["total_modified"] == 3
        assert data["total_failed"] == 0

    def test_non_admin_cannot_bulk_update(self, client, auth_headers, test_models, second_user):
        """Test that non-admin users cannot perform bulk updates."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=auth_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id
            }
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_unauthenticated_cannot_bulk_update(self, client, test_models):
        """Test that unauthenticated users cannot perform bulk updates."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            json={
                "model_ids": model_ids,
                "owner_id": 1
            }
        )
        assert response.status_code == 403


class TestBulkUpdateFieldsValidation:
    """Test validation for bulk update endpoint."""

    def test_no_fields_provided(self, client, admin_headers, test_models):
        """Test that request fails if no fields to update are provided."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids
            }
        )
        assert response.status_code == 400
        assert "No fields to update" in response.json()["detail"]

    def test_invalid_model_ids(self, client, admin_headers, test_models, second_user):
        """Test that request fails if model IDs don't exist."""
        model_ids = [m.model_id for m in test_models] + [99999]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id
            }
        )
        assert response.status_code == 400
        assert "Models not found" in response.json()["detail"]

    def test_invalid_user_id(self, client, admin_headers, test_models):
        """Test that request fails if user ID doesn't exist."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": 99999
            }
        )
        assert response.status_code == 400
        assert "Users not found" in response.json()["detail"]

    def test_owner_cannot_be_cleared(self, client, admin_headers, test_models):
        """Test that owner cannot be set to null."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": None
            }
        )
        assert response.status_code == 200
        data = response.json()
        # All should fail because owner cannot be cleared
        assert data["total_failed"] == 3
        for result in data["results"]:
            assert "required field" in result["error"].lower()

    def test_owner_and_shared_owner_cannot_be_same(self, client, admin_headers, test_models, second_user):
        """Test that owner and shared_owner cannot be the same user when both provided."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id,
                "shared_owner_id": second_user.user_id
            }
        )
        assert response.status_code == 400
        assert "same user" in response.json()["detail"].lower()


class TestBulkUpdateFieldsPeopleFields:
    """Test bulk update of people picker fields."""

    def test_update_owner(self, client, admin_headers, test_models, second_user, db_session):
        """Test bulk update of owner field."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify changes in database
        db_session.expire_all()
        for model_id in model_ids:
            model = db_session.query(Model).get(model_id)
            assert model.owner_id == second_user.user_id

    def test_update_shared_owner(self, client, admin_headers, test_models, second_user, db_session):
        """Test bulk update of shared_owner field."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "shared_owner_id": second_user.user_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify changes in database
        db_session.expire_all()
        for model_id in model_ids:
            model = db_session.query(Model).get(model_id)
            assert model.shared_owner_id == second_user.user_id

    def test_clear_shared_owner(self, client, admin_headers, test_models, second_user, db_session):
        """Test clearing shared_owner field."""
        # First set shared_owner
        for model in test_models:
            model.shared_owner_id = second_user.user_id
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "shared_owner_id": None
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify changes in database
        for model_id in model_ids:
            db_session.expire_all()
            model = db_session.query(Model).get(model_id)
            assert model.shared_owner_id is None

    def test_owner_conflicts_with_existing_shared_owner(
        self, client, admin_headers, test_models, second_user, db_session
    ):
        """Test that new owner conflicts with existing shared_owner on specific model."""
        # Set shared_owner on first model only
        test_models[0].shared_owner_id = second_user.user_id
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        # First model should fail, others should succeed
        assert data["total_modified"] == 2
        assert data["total_failed"] == 1

        # Find the failed result
        failed_result = next(r for r in data["results"] if not r["success"])
        assert "conflicts" in failed_result["error"].lower()


class TestBulkUpdateFieldsMultiSelect:
    """Test bulk update of multi-select fields."""

    def test_user_ids_add_mode(
        self, client, admin_headers, test_models, test_user, second_user, third_user, db_session
    ):
        """Test adding users in add mode (set union)."""
        # First set initial users on first model
        test_models[0].users = [test_user]
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "user_ids": [second_user.user_id, third_user.user_id],
                "user_ids_mode": "add"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify first model has all three users (original + added)
        db_session.expire_all()
        model = db_session.query(Model).get(test_models[0].model_id)
        user_ids = {u.user_id for u in model.users}
        assert test_user.user_id in user_ids
        assert second_user.user_id in user_ids
        assert third_user.user_id in user_ids

    def test_user_ids_replace_mode(
        self, client, admin_headers, test_models, test_user, second_user, db_session
    ):
        """Test replacing users in replace mode."""
        # First set initial users
        test_models[0].users = [test_user]
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "user_ids": [second_user.user_id],
                "user_ids_mode": "replace"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify first model only has the new user
        db_session.expire_all()
        model = db_session.query(Model).get(test_models[0].model_id)
        user_ids = [u.user_id for u in model.users]
        assert user_ids == [second_user.user_id]

    def test_user_ids_add_mode_no_duplicates(
        self, client, admin_headers, test_models, test_user, second_user, db_session
    ):
        """Test that add mode doesn't create duplicates."""
        # First set initial users
        test_models[0].users = [test_user, second_user]
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "user_ids": [test_user.user_id, second_user.user_id],  # Same users
                "user_ids_mode": "add"
            }
        )
        assert response.status_code == 200

        # Verify no duplicates
        db_session.expire_all()
        model = db_session.query(Model).get(test_models[0].model_id)
        user_ids = [u.user_id for u in model.users]
        assert len(user_ids) == len(set(user_ids))  # No duplicates

    def test_regulatory_categories_add_mode(
        self, client, admin_headers, test_models, regulatory_categories, db_session
    ):
        """Test adding regulatory categories in add mode."""
        # First set initial categories on first model
        test_models[0].regulatory_categories = [regulatory_categories["cat1"]]
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "regulatory_category_ids": [
                    regulatory_categories["cat2"].value_id,
                    regulatory_categories["cat3"].value_id
                ],
                "regulatory_category_ids_mode": "add"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify first model has all categories
        db_session.expire_all()
        model = db_session.query(Model).get(test_models[0].model_id)
        cat_ids = {c.value_id for c in model.regulatory_categories}
        assert regulatory_categories["cat1"].value_id in cat_ids
        assert regulatory_categories["cat2"].value_id in cat_ids
        assert regulatory_categories["cat3"].value_id in cat_ids

    def test_regulatory_categories_replace_mode(
        self, client, admin_headers, test_models, regulatory_categories, db_session
    ):
        """Test replacing regulatory categories in replace mode."""
        # First set initial categories
        test_models[0].regulatory_categories = [
            regulatory_categories["cat1"],
            regulatory_categories["cat2"]
        ]
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "regulatory_category_ids": [regulatory_categories["cat3"].value_id],
                "regulatory_category_ids_mode": "replace"
            }
        )
        assert response.status_code == 200

        # Verify first model only has the new category
        db_session.expire_all()
        model = db_session.query(Model).get(test_models[0].model_id)
        cat_ids = [c.value_id for c in model.regulatory_categories]
        assert cat_ids == [regulatory_categories["cat3"].value_id]


class TestBulkUpdateFieldsTextField:
    """Test bulk update of text fields."""

    def test_update_products_covered(self, client, admin_headers, test_models, db_session):
        """Test bulk update of products_covered field."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "products_covered": "New products covered text"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify changes in database
        for model_id in model_ids:
            db_session.expire_all()
            model = db_session.query(Model).get(model_id)
            assert model.products_covered == "New products covered text"

    def test_clear_products_covered(self, client, admin_headers, test_models, db_session):
        """Test clearing products_covered field."""
        # First set products_covered
        for model in test_models:
            model.products_covered = "Initial products"
        db_session.commit()

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "products_covered": None
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify changes in database
        for model_id in model_ids:
            db_session.expire_all()
            model = db_session.query(Model).get(model_id)
            assert model.products_covered is None


class TestBulkUpdateFieldsAuditLog:
    """Test audit logging for bulk updates."""

    def test_audit_log_created_per_model(
        self, client, admin_headers, test_models, second_user, db_session
    ):
        """Test that individual audit log entries are created per model."""
        from app.models.audit_log import AuditLog

        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id
            }
        )
        assert response.status_code == 200

        # Check audit logs
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Model",
            AuditLog.action == "BULK_UPDATE",
            AuditLog.entity_id.in_(model_ids)
        ).all()

        assert len(audit_logs) == 3  # One per model
        for log in audit_logs:
            assert log.changes is not None
            assert "owner_id" in log.changes


class TestBulkUpdateFieldsMultipleFields:
    """Test bulk update of multiple fields at once."""

    def test_update_multiple_fields(
        self, client, admin_headers, test_models, second_user, third_user, regulatory_categories, db_session
    ):
        """Test bulk update of multiple fields in one request."""
        model_ids = [m.model_id for m in test_models]
        response = client.post(
            "/models/bulk-update-fields",
            headers=admin_headers,
            json={
                "model_ids": model_ids,
                "owner_id": second_user.user_id,
                "monitoring_manager_id": third_user.user_id,
                "products_covered": "Multiple field update",
                "regulatory_category_ids": [regulatory_categories["cat1"].value_id],
                "regulatory_category_ids_mode": "replace"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_modified"] == 3

        # Verify all changes in database
        db_session.expire_all()
        for model_id in model_ids:
            model = db_session.query(Model).get(model_id)
            assert model.owner_id == second_user.user_id
            assert model.monitoring_manager_id == third_user.user_id
            assert model.products_covered == "Multiple field update"
            assert len(model.regulatory_categories) == 1
            assert model.regulatory_categories[0].value_id == regulatory_categories["cat1"].value_id
