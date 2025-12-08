"""Tests for model dependency endpoints with cycle detection."""
import pytest
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model import Model
from app.models.model_feed_dependency import ModelFeedDependency
from app.models.audit_log import AuditLog


@pytest.fixture
def dependency_taxonomy(db_session):
    """Create Model Dependency Type taxonomy."""
    taxonomy = Taxonomy(name="Model Dependency Type", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    input_data = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="INPUT_DATA",
        label="Input Data",
        description="Feeder model provides input data to consumer model",
        sort_order=1
    )
    score = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="SCORE",
        label="Score/Output",
        description="Feeder model provides scores or outputs to consumer model",
        sort_order=2
    )
    db_session.add_all([input_data, score])
    db_session.commit()
    db_session.refresh(input_data)
    db_session.refresh(score)

    return {"input_data": input_data, "score": score}


@pytest.fixture
def model_a(db_session, test_user, usage_frequency):
    """Create Model A."""
    model = Model(
        model_name="Model A",
        description="Model A for dependency testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def model_b(db_session, test_user, usage_frequency):
    """Create Model B."""
    model = Model(
        model_name="Model B",
        description="Model B for dependency testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def model_c(db_session, test_user, usage_frequency):
    """Create Model C."""
    model = Model(
        model_name="Model C",
        description="Model C for dependency testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def model_d(db_session, test_user, usage_frequency):
    """Create Model D."""
    model = Model(
        model_name="Model D",
        description="Model D for dependency testing",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class TestListInboundDependencies:
    """Test GET /models/{model_id}/dependencies/inbound endpoint."""

    def test_list_inbound_empty(self, client, auth_headers, model_a, dependency_taxonomy):
        """Test listing inbound dependencies when none exist."""
        response = client.get(
            f"/models/{model_a.model_id}/dependencies/inbound",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_inbound_with_data(self, client, auth_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test listing inbound dependencies (feeders)."""
        # Create dependency: B feeds data to A
        dependency = ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_a.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            description="B provides input to A",
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()

        response = client.get(
            f"/models/{model_a.model_id}/dependencies/inbound",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == model_b.model_id
        assert data[0]["model_name"] == "Model B"
        assert data[0]["dependency_type"] == "Input Data"
        assert data[0]["description"] == "B provides input to A"
        assert data[0]["is_active"] is True

    def test_list_inbound_exclude_inactive(self, client, auth_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test that inactive dependencies are excluded by default."""
        # Create inactive dependency
        dependency = ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_a.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=False
        )
        db_session.add(dependency)
        db_session.commit()

        response = client.get(
            f"/models/{model_a.model_id}/dependencies/inbound",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_inbound_include_inactive(self, client, auth_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test that inactive dependencies can be included."""
        # Create inactive dependency
        dependency = ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_a.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=False
        )
        db_session.add(dependency)
        db_session.commit()

        response = client.get(
            f"/models/{model_a.model_id}/dependencies/inbound?include_inactive=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_active"] is False


class TestListOutboundDependencies:
    """Test GET /models/{model_id}/dependencies/outbound endpoint."""

    def test_list_outbound_empty(self, client, auth_headers, model_a, dependency_taxonomy):
        """Test listing outbound dependencies when none exist."""
        response = client.get(
            f"/models/{model_a.model_id}/dependencies/outbound",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_outbound_with_data(self, client, auth_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test listing outbound dependencies (consumers)."""
        # Create dependency: A feeds data to B
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["score"].value_id,
            description="A provides scores to B",
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()

        response = client.get(
            f"/models/{model_a.model_id}/dependencies/outbound",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == model_b.model_id
        assert data[0]["model_name"] == "Model B"
        assert data[0]["dependency_type"] == "Score/Output"
        assert data[0]["description"] == "A provides scores to B"


class TestCreateDependency:
    """Test POST /models/{model_id}/dependencies endpoint."""

    def test_create_dependency_success(self, client, admin_headers, model_a, model_b, dependency_taxonomy):
        """Test creating a dependency relationship."""
        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_b.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "description": "A feeds B",
                "is_active": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["feeder_model_id"] == model_a.model_id
        assert data["consumer_model_id"] == model_b.model_id
        assert data["dependency_type_id"] == dependency_taxonomy["input_data"].value_id
        assert data["description"] == "A feeds B"
        assert data["is_active"] is True
        assert data["feeder_model"]["model_name"] == "Model A"
        assert data["consumer_model"]["model_name"] == "Model B"
        assert data["dependency_type"]["label"] == "Input Data"

    def test_create_dependency_with_dates(self, client, admin_headers, model_a, model_b, dependency_taxonomy):
        """Test creating dependency with effective and end dates."""
        from datetime import date, timedelta

        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_b.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "effective_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=365)),
                "is_active": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["effective_date"] == str(date.today())
        assert data["end_date"] == str(date.today() + timedelta(days=365))

    def test_create_dependency_self_reference_blocked(self, client, admin_headers, model_a, dependency_taxonomy):
        """Test that model cannot depend on itself."""
        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,  # Same as feeder
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 400
        assert "self-reference" in response.json()["detail"].lower()

    def test_create_dependency_invalid_date_range(self, client, admin_headers, model_a, model_b, dependency_taxonomy):
        """Test that end date before effective date is rejected."""
        from datetime import date, timedelta

        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_b.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "effective_date": str(date.today()),
                "end_date": str(date.today() - timedelta(days=1)),
                "is_active": True
            }
        )
        assert response.status_code == 400
        assert "end date" in response.json()["detail"].lower()

    def test_create_dependency_duplicate_blocked(self, client, admin_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test that duplicate dependencies are blocked."""
        # Create first dependency
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()

        # Try to create duplicate
        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_b.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_dependency_non_admin_blocked(self, client, auth_headers, model_a, model_b, dependency_taxonomy):
        """Test that non-admin users cannot create dependencies."""
        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=auth_headers,
            json={
                "consumer_model_id": model_b.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_create_dependency_creates_audit_log(self, client, admin_headers, model_a, model_b, dependency_taxonomy, db_session, admin_user):
        """Test that creating dependency creates audit log."""
        response = client.post(
            f"/models/{model_a.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_b.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 201

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelFeedDependency",
            AuditLog.action == "CREATE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id
        assert "feeder_model_name" in audit_log.changes
        assert audit_log.changes["feeder_model_name"] == "Model A"


class TestCycleDetection:
    """Test cycle detection in dependency graph."""

    def test_simple_cycle_blocked(self, client, admin_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test that simple 2-node cycle is blocked (A→B, then B→A)."""
        # Create A → B
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()

        # Try to create B → A (would create cycle)
        response = client.post(
            f"/models/{model_b.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "dependency_cycle_detected"
        assert "cycle" in detail["message"].lower()
        assert detail["cycle_path"] == [model_a.model_id, model_b.model_id, model_a.model_id]
        assert "Model A" in detail["cycle_description"]
        assert "Model B" in detail["cycle_description"]

    def test_three_node_cycle_blocked(self, client, admin_headers, model_a, model_b, model_c, dependency_taxonomy, db_session):
        """Test that 3-node cycle is blocked (A→B→C, then C→A)."""
        # Create A → B
        dep1 = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        # Create B → C
        dep2 = ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_c.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add_all([dep1, dep2])
        db_session.commit()

        # Try to create C → A (would create cycle)
        response = client.post(
            f"/models/{model_c.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "dependency_cycle_detected"
        # Cycle path: A → B → C → A
        assert len(detail["cycle_path"]) == 4
        assert detail["cycle_path"][0] == model_a.model_id
        assert detail["cycle_path"][-1] == model_a.model_id

    def test_complex_cycle_blocked(self, client, admin_headers, model_a, model_b, model_c, model_d, dependency_taxonomy, db_session):
        """Test complex cycle detection (A→B, A→C, B→D, C→D, then D→A)."""
        # Create diamond pattern with cycle
        # A → B
        # A → C
        # B → D
        # C → D
        dep1 = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        dep2 = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_c.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        dep3 = ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_d.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        dep4 = ModelFeedDependency(
            feeder_model_id=model_c.model_id,
            consumer_model_id=model_d.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add_all([dep1, dep2, dep3, dep4])
        db_session.commit()

        # Try to create D → A (would create cycle through B or C)
        response = client.post(
            f"/models/{model_d.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "dependency_cycle_detected"

    def test_dag_allowed(self, client, admin_headers, model_a, model_b, model_c, model_d, dependency_taxonomy, db_session):
        """Test that valid DAG (no cycles) is allowed."""
        # Create valid DAG:
        # A → B
        # A → C
        # B → D
        # C → D
        dep1 = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        dep2 = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_c.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        dep3 = ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_d.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add_all([dep1, dep2, dep3])
        db_session.commit()

        # Try to create C → D (should work, no cycle)
        response = client.post(
            f"/models/{model_c.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_d.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 201

    def test_inactive_dependencies_ignored_in_cycle_detection(self, client, admin_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test that inactive dependencies don't prevent valid edges."""
        # Create inactive A → B
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=False  # Inactive
        )
        db_session.add(dependency)
        db_session.commit()

        # Creating B → A should work since A → B is inactive
        response = client.post(
            f"/models/{model_b.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 201


class TestUpdateDependency:
    """Test PATCH /dependencies/{dependency_id} endpoint."""

    @pytest.fixture
    def existing_dependency(self, db_session, model_a, model_b, dependency_taxonomy):
        """Create an existing dependency."""
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            description="Original description",
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()
        db_session.refresh(dependency)
        return dependency

    def test_update_dependency_description(self, client, admin_headers, existing_dependency):
        """Test updating dependency description."""
        response = client.patch(
            f"/dependencies/{existing_dependency.id}",
            headers=admin_headers,
            json={"description": "Updated description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_dependency_is_active(self, client, admin_headers, existing_dependency):
        """Test deactivating a dependency."""
        response = client.patch(
            f"/dependencies/{existing_dependency.id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_dependency_non_admin_blocked(self, client, auth_headers, existing_dependency):
        """Test that non-admin users cannot update dependencies."""
        response = client.patch(
            f"/dependencies/{existing_dependency.id}",
            headers=auth_headers,
            json={"description": "Should not work"}
        )
        assert response.status_code == 403

    def test_update_dependency_creates_audit_log(self, client, admin_headers, existing_dependency, db_session, admin_user):
        """Test that updating dependency creates audit log."""
        response = client.patch(
            f"/dependencies/{existing_dependency.id}",
            headers=admin_headers,
            json={"description": "Changed"}
        )
        assert response.status_code == 200

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelFeedDependency",
            AuditLog.action == "UPDATE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id


class TestDeleteDependency:
    """Test DELETE /dependencies/{dependency_id} endpoint."""

    @pytest.fixture
    def existing_dependency(self, db_session, model_a, model_b, dependency_taxonomy):
        """Create an existing dependency."""
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()
        db_session.refresh(dependency)
        return dependency

    def test_delete_dependency_success(self, client, admin_headers, existing_dependency, db_session):
        """Test deleting a dependency."""
        response = client.delete(
            f"/dependencies/{existing_dependency.id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify deleted
        deleted = db_session.query(ModelFeedDependency).filter(
            ModelFeedDependency.id == existing_dependency.id
        ).first()
        assert deleted is None

    def test_delete_dependency_non_admin_blocked(self, client, auth_headers, existing_dependency):
        """Test that non-admin users cannot delete dependencies."""
        response = client.delete(
            f"/dependencies/{existing_dependency.id}",
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_delete_dependency_creates_audit_log(self, client, admin_headers, existing_dependency, db_session, admin_user):
        """Test that deleting dependency creates audit log."""
        response = client.delete(
            f"/dependencies/{existing_dependency.id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "ModelFeedDependency",
            AuditLog.action == "DELETE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id

    def test_delete_dependency_allows_previously_blocked_edge(self, client, admin_headers, model_a, model_b, dependency_taxonomy, db_session):
        """Test that deleting dependency allows previously blocked edges."""
        # Create A → B
        dependency = ModelFeedDependency(
            feeder_model_id=model_a.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            is_active=True
        )
        db_session.add(dependency)
        db_session.commit()
        db_session.refresh(dependency)

        # B → A would create cycle, so it's blocked
        response = client.post(
            f"/models/{model_b.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 400

        # Delete A → B
        client.delete(f"/dependencies/{dependency.id}", headers=admin_headers)

        # Now B → A should work
        response = client.post(
            f"/models/{model_b.model_id}/dependencies",
            headers=admin_headers,
            json={
                "consumer_model_id": model_a.model_id,
                "dependency_type_id": dependency_taxonomy["input_data"].value_id,
                "is_active": True
            }
        )
        assert response.status_code == 201
