"""Tests for model hierarchy endpoints."""
import pytest
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model import Model
from app.models.model_hierarchy import ModelHierarchy
from app.models.audit_log import AuditLog


@pytest.fixture
def hierarchy_taxonomy(db_session):
    """Create Model Hierarchy Type taxonomy."""
    taxonomy = Taxonomy(name="Model Hierarchy Type", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    sub_model = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="SUB_MODEL",
        label="Sub-Model",
        description="Child model that is a component or subset of a parent model",
        sort_order=1
    )
    db_session.add(sub_model)
    db_session.commit()
    db_session.refresh(sub_model)

    return sub_model


@pytest.fixture
def parent_model(db_session, test_user):
    """Create a parent model."""
    model = Model(
        model_name="Parent Model",
        description="Parent model for hierarchy testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def child_model(db_session, test_user):
    """Create a child model."""
    model = Model(
        model_name="Child Model",
        description="Child model for hierarchy testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def another_child_model(db_session, test_user):
    """Create another child model."""
    model = Model(
        model_name="Another Child Model",
        description="Another child model for hierarchy testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class TestListChildren:
    """Test GET /models/{model_id}/hierarchy/children endpoint."""

    def test_list_children_empty(self, client, auth_headers, parent_model, hierarchy_taxonomy):
        """Test listing children when none exist."""
        response = client.get(
            f"/models/{parent_model.model_id}/hierarchy/children",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_children_with_data(self, client, auth_headers, parent_model, child_model, hierarchy_taxonomy, db_session):
        """Test listing children returns all child models."""
        # Create hierarchy relationship
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id
        )
        db_session.add(hierarchy)
        db_session.commit()

        response = client.get(
            f"/models/{parent_model.model_id}/hierarchy/children",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == child_model.model_id
        assert data[0]["model_name"] == "Child Model"
        assert data[0]["relation_type"] == "Sub-Model"

    def test_list_children_multiple(self, client, auth_headers, parent_model, child_model, another_child_model, hierarchy_taxonomy, db_session):
        """Test listing multiple children."""
        # Create two hierarchy relationships
        hierarchy1 = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id
        )
        hierarchy2 = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=another_child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id
        )
        db_session.add_all([hierarchy1, hierarchy2])
        db_session.commit()

        response = client.get(
            f"/models/{parent_model.model_id}/hierarchy/children",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        child_ids = [item["model_id"] for item in data]
        assert child_model.model_id in child_ids
        assert another_child_model.model_id in child_ids

    def test_list_children_exclude_inactive(self, client, auth_headers, parent_model, child_model, hierarchy_taxonomy, db_session):
        """Test that ended relationships are excluded by default."""
        from datetime import date, timedelta

        # Create hierarchy relationship that has ended
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id,
            effective_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=1)  # Ended yesterday
        )
        db_session.add(hierarchy)
        db_session.commit()

        response = client.get(
            f"/models/{parent_model.model_id}/hierarchy/children",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_children_include_inactive(self, client, auth_headers, parent_model, child_model, hierarchy_taxonomy, db_session):
        """Test that ended relationships are included when requested."""
        from datetime import date, timedelta

        # Create hierarchy relationship that has ended
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id,
            effective_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=1)
        )
        db_session.add(hierarchy)
        db_session.commit()

        response = client.get(
            f"/models/{parent_model.model_id}/hierarchy/children?include_inactive=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == child_model.model_id

    def test_list_children_nonexistent_model(self, client, auth_headers):
        """Test listing children of nonexistent model returns 404."""
        response = client.get(
            "/models/99999/hierarchy/children",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_list_children_unauthenticated(self, client, parent_model):
        """Test listing children without auth fails."""
        response = client.get(f"/models/{parent_model.model_id}/hierarchy/children")
        assert response.status_code == 403


class TestListParents:
    """Test GET /models/{model_id}/hierarchy/parents endpoint."""

    def test_list_parents_empty(self, client, auth_headers, child_model, hierarchy_taxonomy):
        """Test listing parents when none exist."""
        response = client.get(
            f"/models/{child_model.model_id}/hierarchy/parents",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_parents_with_data(self, client, auth_headers, parent_model, child_model, hierarchy_taxonomy, db_session):
        """Test listing parents returns all parent models."""
        # Create hierarchy relationship
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id
        )
        db_session.add(hierarchy)
        db_session.commit()

        response = client.get(
            f"/models/{child_model.model_id}/hierarchy/parents",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == parent_model.model_id
        assert data[0]["model_name"] == "Parent Model"
        assert data[0]["relation_type"] == "Sub-Model"


class TestCreateHierarchy:
    """Test POST /models/{model_id}/hierarchy endpoint."""

    def test_create_hierarchy_success(self, client, admin_headers, parent_model, child_model, hierarchy_taxonomy):
        """Test creating a hierarchy relationship."""
        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["parent_model_id"] == parent_model.model_id
        assert data["child_model_id"] == child_model.model_id
        assert data["relation_type_id"] == hierarchy_taxonomy.value_id
        assert data["parent_model"]["model_name"] == "Parent Model"
        assert data["child_model"]["model_name"] == "Child Model"
        assert data["relation_type"]["label"] == "Sub-Model"

    def test_create_hierarchy_with_dates(self, client, admin_headers, parent_model, child_model, hierarchy_taxonomy):
        """Test creating hierarchy with effective and end dates."""
        from datetime import date, timedelta

        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id,
                "effective_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=365))
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["effective_date"] == str(date.today())
        assert data["end_date"] == str(date.today() + timedelta(days=365))

    def test_create_hierarchy_self_reference_blocked(self, client, admin_headers, parent_model, hierarchy_taxonomy):
        """Test that model cannot be its own child."""
        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": parent_model.model_id,  # Same as parent
                "relation_type_id": hierarchy_taxonomy.value_id
            }
        )
        assert response.status_code == 400
        assert "self-reference" in response.json()["detail"].lower()

    def test_create_hierarchy_invalid_date_range(self, client, admin_headers, parent_model, child_model, hierarchy_taxonomy):
        """Test that end date before effective date is rejected."""
        from datetime import date, timedelta

        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id,
                "effective_date": str(date.today()),
                "end_date": str(date.today() - timedelta(days=1))  # Before effective date
            }
        )
        assert response.status_code == 400
        assert "end date" in response.json()["detail"].lower()

    def test_create_hierarchy_duplicate_blocked(self, client, admin_headers, parent_model, child_model, hierarchy_taxonomy, db_session):
        """Test that duplicate relationships are blocked."""
        from datetime import date

        # Create first hierarchy
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id,
            effective_date=date.today()
        )
        db_session.add(hierarchy)
        db_session.commit()

        # Try to create duplicate
        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id,
                "effective_date": str(date.today())
            }
        )
        assert response.status_code == 400
        assert "already has a parent" in response.json()["detail"].lower()

    def test_create_hierarchy_nonexistent_parent(self, client, admin_headers, child_model, hierarchy_taxonomy):
        """Test creating hierarchy with nonexistent parent returns 404."""
        response = client.post(
            "/models/99999/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id
            }
        )
        assert response.status_code == 404
        assert "parent" in response.json()["detail"].lower()

    def test_create_hierarchy_nonexistent_child(self, client, admin_headers, parent_model, hierarchy_taxonomy):
        """Test creating hierarchy with nonexistent child returns 404."""
        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": 99999,
                "relation_type_id": hierarchy_taxonomy.value_id
            }
        )
        assert response.status_code == 404
        assert "child" in response.json()["detail"].lower()

    def test_create_hierarchy_non_admin_blocked(self, client, auth_headers, parent_model, child_model, hierarchy_taxonomy):
        """Test that non-admin users cannot create hierarchy relationships."""
        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=auth_headers,  # Regular user, not admin
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id
            }
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_create_hierarchy_creates_audit_log(self, client, admin_headers, parent_model, child_model, hierarchy_taxonomy, db_session, admin_user):
        """Test that creating hierarchy creates an audit log entry."""
        response = client.post(
            f"/models/{parent_model.model_id}/hierarchy",
            headers=admin_headers,
            json={
                "child_model_id": child_model.model_id,
                "relation_type_id": hierarchy_taxonomy.value_id
            }
        )
        assert response.status_code == 201

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelHierarchy",
            AuditLog.action == "CREATE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id
        assert "parent_model_name" in audit_log.changes
        assert audit_log.changes["parent_model_name"] == "Parent Model"


class TestUpdateHierarchy:
    """Test PATCH /hierarchy/{hierarchy_id} endpoint."""

    @pytest.fixture
    def existing_hierarchy(self, db_session, parent_model, child_model, hierarchy_taxonomy):
        """Create an existing hierarchy relationship."""
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id,
            notes="Original notes"
        )
        db_session.add(hierarchy)
        db_session.commit()
        db_session.refresh(hierarchy)
        return hierarchy

    def test_update_hierarchy_notes(self, client, admin_headers, existing_hierarchy):
        """Test updating hierarchy notes."""
        response = client.patch(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=admin_headers,
            json={"notes": "Updated notes"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"

    def test_update_hierarchy_dates(self, client, admin_headers, existing_hierarchy):
        """Test updating hierarchy dates."""
        from datetime import date, timedelta

        response = client.patch(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=admin_headers,
            json={
                "effective_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=180))
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["effective_date"] == str(date.today())
        assert data["end_date"] == str(date.today() + timedelta(days=180))

    def test_update_hierarchy_non_admin_blocked(self, client, auth_headers, existing_hierarchy):
        """Test that non-admin users cannot update hierarchy."""
        response = client.patch(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=auth_headers,
            json={"notes": "Should not work"}
        )
        assert response.status_code == 403

    def test_update_hierarchy_creates_audit_log(self, client, admin_headers, existing_hierarchy, db_session, admin_user):
        """Test that updating hierarchy creates audit log."""
        response = client.patch(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=admin_headers,
            json={"notes": "Changed notes"}
        )
        assert response.status_code == 200

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelHierarchy",
            AuditLog.action == "UPDATE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id


class TestDeleteHierarchy:
    """Test DELETE /hierarchy/{hierarchy_id} endpoint."""

    @pytest.fixture
    def existing_hierarchy(self, db_session, parent_model, child_model, hierarchy_taxonomy):
        """Create an existing hierarchy relationship."""
        hierarchy = ModelHierarchy(
            parent_model_id=parent_model.model_id,
            child_model_id=child_model.model_id,
            relation_type_id=hierarchy_taxonomy.value_id
        )
        db_session.add(hierarchy)
        db_session.commit()
        db_session.refresh(hierarchy)
        return hierarchy

    def test_delete_hierarchy_success(self, client, admin_headers, existing_hierarchy, db_session):
        """Test deleting a hierarchy relationship."""
        response = client.delete(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify deleted
        deleted = db_session.query(ModelHierarchy).filter(
            ModelHierarchy.id == existing_hierarchy.id
        ).first()
        assert deleted is None

    def test_delete_hierarchy_non_admin_blocked(self, client, auth_headers, existing_hierarchy):
        """Test that non-admin users cannot delete hierarchy."""
        response = client.delete(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_delete_hierarchy_creates_audit_log(self, client, admin_headers, existing_hierarchy, db_session, admin_user):
        """Test that deleting hierarchy creates audit log."""
        response = client.delete(
            f"/hierarchy/{existing_hierarchy.id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelHierarchy",
            AuditLog.action == "DELETE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id

    def test_delete_nonexistent_hierarchy(self, client, admin_headers):
        """Test deleting nonexistent hierarchy returns 404."""
        response = client.delete(
            "/hierarchy/99999",
            headers=admin_headers
        )
        assert response.status_code == 404
