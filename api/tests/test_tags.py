"""Tests for model tagging functionality."""
import pytest
from fastapi.testclient import TestClient

from app.models.tag import TagCategory, Tag, ModelTag, ModelTagHistory
from app.models.model import Model


# ============================================================================
# Category CRUD Tests
# ============================================================================

def test_create_category_admin_only(client: TestClient, admin_headers, auth_headers):
    """Test that only admins can create categories."""
    category_data = {
        "name": "Regulatory",
        "description": "Regulatory compliance tags",
        "color": "#DC2626"
    }

    # Non-admin should fail
    response = client.post("/tags/categories", json=category_data, headers=auth_headers)
    assert response.status_code == 403

    # Admin should succeed
    response = client.post("/tags/categories", json=category_data, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Regulatory"
    assert data["color"] == "#DC2626"
    assert data["is_system"] is False
    assert "category_id" in data


def test_list_categories(client: TestClient, db_session, admin_headers):
    """Test listing categories."""
    # Create test categories
    cat1 = TagCategory(name="Category A", color="#FF0000", sort_order=1)
    cat2 = TagCategory(name="Category B", color="#00FF00", sort_order=2)
    db_session.add_all([cat1, cat2])
    db_session.commit()

    response = client.get("/tags/categories", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = [c["name"] for c in data]
    assert "Category A" in names
    assert "Category B" in names


def test_get_category_with_tags(client: TestClient, db_session, admin_headers):
    """Test getting a category with its tags."""
    category = TagCategory(name="Test Category", color="#0000FF", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag1 = Tag(category_id=category.category_id, name="Tag 1", sort_order=1)
    tag2 = Tag(category_id=category.category_id, name="Tag 2", sort_order=2)
    db_session.add_all([tag1, tag2])
    db_session.commit()

    response = client.get(f"/tags/categories/{category.category_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Category"
    assert len(data["tags"]) == 2


def test_update_category(client: TestClient, db_session, admin_headers):
    """Test updating a category."""
    category = TagCategory(name="Original", color="#000000", sort_order=1)
    db_session.add(category)
    db_session.commit()

    response = client.patch(
        f"/tags/categories/{category.category_id}",
        json={"name": "Updated", "color": "#FFFFFF"},
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["color"] == "#FFFFFF"


def test_delete_category(client: TestClient, db_session, admin_headers):
    """Test deleting a category."""
    category = TagCategory(name="To Delete", color="#AABBCC", sort_order=1)
    db_session.add(category)
    db_session.commit()

    response = client.delete(f"/tags/categories/{category.category_id}", headers=admin_headers)
    assert response.status_code == 204

    # Verify it's deleted
    response = client.get(f"/tags/categories/{category.category_id}", headers=admin_headers)
    assert response.status_code == 404


def test_cannot_delete_category_with_tags_in_use(client: TestClient, db_session, admin_headers, sample_model):
    """Test that categories with tags assigned to models cannot be deleted."""
    category = TagCategory(name="Has Tags In Use", color="#123456", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Blocking Tag", sort_order=1)
    db_session.add(tag)
    db_session.flush()

    # Assign the tag to a model
    model_tag = ModelTag(model_id=sample_model.model_id, tag_id=tag.tag_id)
    db_session.add(model_tag)
    db_session.commit()

    response = client.delete(f"/tags/categories/{category.category_id}", headers=admin_headers)
    assert response.status_code == 400
    assert "assigned to models" in response.json()["detail"]


def test_can_delete_category_with_unused_tags(client: TestClient, db_session, admin_headers):
    """Test that categories with tags NOT assigned to models can be deleted (cascade)."""
    category = TagCategory(name="Has Unused Tags", color="#654321", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Unused Tag", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    # Category has tags but none are assigned to models, so deletion should succeed
    response = client.delete(f"/tags/categories/{category.category_id}", headers=admin_headers)
    assert response.status_code == 204


# ============================================================================
# Tag CRUD Tests
# ============================================================================

def test_create_tag(client: TestClient, db_session, admin_headers):
    """Test creating a tag."""
    category = TagCategory(name="Test Cat", color="#FF0000", sort_order=1)
    db_session.add(category)
    db_session.commit()

    tag_data = {
        "category_id": category.category_id,
        "name": "New Tag",
        "description": "A test tag",
        "color": "#00FF00"
    }

    response = client.post("/tags/", json=tag_data, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Tag"
    assert data["color"] == "#00FF00"
    assert data["effective_color"] == "#00FF00"


def test_tag_inherits_category_color(client: TestClient, db_session, admin_headers):
    """Test that tags without color inherit category color."""
    category = TagCategory(name="Color Cat", color="#ABCDEF", sort_order=1)
    db_session.add(category)
    db_session.commit()

    tag_data = {
        "category_id": category.category_id,
        "name": "No Color Tag"
    }

    response = client.post("/tags/", json=tag_data, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["color"] is None
    assert data["effective_color"] == "#ABCDEF"


def test_list_tags(client: TestClient, db_session, admin_headers):
    """Test listing tags with category filter."""
    cat1 = TagCategory(name="Cat1", color="#111111", sort_order=1)
    cat2 = TagCategory(name="Cat2", color="#222222", sort_order=2)
    db_session.add_all([cat1, cat2])
    db_session.flush()

    tag1 = Tag(category_id=cat1.category_id, name="Tag in Cat1", sort_order=1)
    tag2 = Tag(category_id=cat2.category_id, name="Tag in Cat2", sort_order=1)
    db_session.add_all([tag1, tag2])
    db_session.commit()

    # List all tags
    response = client.get("/tags/", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2

    # Filter by category
    response = client.get(f"/tags/?category_id={cat1.category_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Tag in Cat1"


def test_list_active_tags_only(client: TestClient, db_session, admin_headers):
    """Test filtering active tags only."""
    category = TagCategory(name="Mixed Cat", color="#333333", sort_order=1)
    db_session.add(category)
    db_session.flush()

    active_tag = Tag(category_id=category.category_id, name="Active", is_active=True, sort_order=1)
    inactive_tag = Tag(category_id=category.category_id, name="Inactive", is_active=False, sort_order=2)
    db_session.add_all([active_tag, inactive_tag])
    db_session.commit()

    response = client.get("/tags/?is_active=true", headers=admin_headers)
    assert response.status_code == 200
    names = [t["name"] for t in response.json()]
    assert "Active" in names
    assert "Inactive" not in names


def test_update_tag(client: TestClient, db_session, admin_headers):
    """Test updating a tag."""
    category = TagCategory(name="Update Cat", color="#444444", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Original Tag", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    response = client.patch(
        f"/tags/{tag.tag_id}",
        json={"name": "Updated Tag", "is_active": False},
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Tag"
    assert data["is_active"] is False


def test_delete_tag(client: TestClient, db_session, admin_headers):
    """Test deleting a tag."""
    category = TagCategory(name="Delete Cat", color="#555555", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="To Delete", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    response = client.delete(f"/tags/{tag.tag_id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/tags/{tag.tag_id}", headers=admin_headers)
    assert response.status_code == 404


# ============================================================================
# Model Tag Assignment Tests
# ============================================================================

def test_add_tags_to_model(client: TestClient, db_session, admin_headers, sample_model):
    """Test adding tags to a model."""
    category = TagCategory(name="Assign Cat", color="#666666", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag1 = Tag(category_id=category.category_id, name="Tag A", sort_order=1)
    tag2 = Tag(category_id=category.category_id, name="Tag B", sort_order=2)
    db_session.add_all([tag1, tag2])
    db_session.commit()

    response = client.post(
        f"/tags/models/{sample_model.model_id}/tags",
        json={"tag_ids": [tag1.tag_id, tag2.tag_id]},
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == sample_model.model_id
    assert len(data["tags"]) == 2


def test_get_model_tags(client: TestClient, db_session, admin_headers, sample_model):
    """Test getting tags for a model."""
    category = TagCategory(name="Get Cat", color="#777777", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Model Tag", sort_order=1)
    db_session.add(tag)
    db_session.flush()

    model_tag = ModelTag(model_id=sample_model.model_id, tag_id=tag.tag_id)
    db_session.add(model_tag)
    db_session.commit()

    response = client.get(f"/tags/models/{sample_model.model_id}/tags", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == sample_model.model_id
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "Model Tag"


def test_remove_tag_from_model(client: TestClient, db_session, admin_headers, sample_model):
    """Test removing a tag from a model."""
    category = TagCategory(name="Remove Cat", color="#888888", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="To Remove", sort_order=1)
    db_session.add(tag)
    db_session.flush()

    model_tag = ModelTag(model_id=sample_model.model_id, tag_id=tag.tag_id)
    db_session.add(model_tag)
    db_session.commit()

    response = client.delete(
        f"/tags/models/{sample_model.model_id}/tags/{tag.tag_id}",
        headers=admin_headers
    )
    assert response.status_code == 204

    # Verify tag is removed
    response = client.get(f"/tags/models/{sample_model.model_id}/tags", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()["tags"]) == 0


def test_duplicate_tag_assignment_ignored(client: TestClient, db_session, admin_headers, sample_model):
    """Test that duplicate tag assignments are handled gracefully."""
    category = TagCategory(name="Dup Cat", color="#999999", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Dup Tag", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    # First assignment
    response = client.post(
        f"/tags/models/{sample_model.model_id}/tags",
        json={"tag_ids": [tag.tag_id]},
        headers=admin_headers
    )
    assert response.status_code == 200
    assert len(response.json()["tags"]) == 1

    # Second assignment (same tag) - should not duplicate
    response = client.post(
        f"/tags/models/{sample_model.model_id}/tags",
        json={"tag_ids": [tag.tag_id]},
        headers=admin_headers
    )
    assert response.status_code == 200
    assert len(response.json()["tags"]) == 1


# ============================================================================
# Bulk Operations Tests
# ============================================================================

def test_bulk_assign_tag(client: TestClient, db_session, admin_headers, test_user, usage_frequency):
    """Test bulk assigning a tag to multiple models."""
    category = TagCategory(name="Bulk Cat", color="#AAAAAA", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Bulk Tag", sort_order=1)
    db_session.add(tag)
    db_session.flush()

    # Create multiple models
    model1 = Model(
        model_name="Bulk Model 1",
        description="Test",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    model2 = Model(
        model_name="Bulk Model 2",
        description="Test",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add_all([model1, model2])
    db_session.commit()

    response = client.post(
        "/tags/bulk-assign",
        json={"tag_id": tag.tag_id, "model_ids": [model1.model_id, model2.model_id]},
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tag_id"] == tag.tag_id
    assert data["total_requested"] == 2
    assert data["total_modified"] == 2


def test_bulk_remove_tag(client: TestClient, db_session, admin_headers, test_user, usage_frequency):
    """Test bulk removing a tag from multiple models."""
    category = TagCategory(name="Bulk Remove Cat", color="#BBBBBB", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Bulk Remove Tag", sort_order=1)
    db_session.add(tag)
    db_session.flush()

    model1 = Model(
        model_name="Bulk Remove Model 1",
        description="Test",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    model2 = Model(
        model_name="Bulk Remove Model 2",
        description="Test",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add_all([model1, model2])
    db_session.flush()

    # Pre-assign tags
    db_session.add_all([
        ModelTag(model_id=model1.model_id, tag_id=tag.tag_id),
        ModelTag(model_id=model2.model_id, tag_id=tag.tag_id)
    ])
    db_session.commit()

    response = client.post(
        "/tags/bulk-remove",
        json={"tag_id": tag.tag_id, "model_ids": [model1.model_id, model2.model_id]},
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_modified"] == 2


# ============================================================================
# Tag History Tests
# ============================================================================

def test_tag_history_recorded(client: TestClient, db_session, admin_headers, sample_model, admin_user):
    """Test that tag assignment history is recorded."""
    category = TagCategory(name="History Cat", color="#CCCCCC", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="History Tag", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    # Add tag
    client.post(
        f"/tags/models/{sample_model.model_id}/tags",
        json={"tag_ids": [tag.tag_id]},
        headers=admin_headers
    )

    # Check history
    response = client.get(
        f"/tags/models/{sample_model.model_id}/tags/history",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == sample_model.model_id
    assert len(data["history"]) >= 1
    assert data["history"][0]["action"] == "ADDED"
    assert data["history"][0]["tag_name"] == "History Tag"


def test_tag_removal_recorded_in_history(client: TestClient, db_session, admin_headers, sample_model):
    """Test that tag removal is recorded in history."""
    category = TagCategory(name="Remove History Cat", color="#DDDDDD", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Remove History Tag", sort_order=1)
    db_session.add(tag)
    db_session.flush()

    model_tag = ModelTag(model_id=sample_model.model_id, tag_id=tag.tag_id)
    db_session.add(model_tag)
    db_session.commit()

    # Remove tag
    client.delete(
        f"/tags/models/{sample_model.model_id}/tags/{tag.tag_id}",
        headers=admin_headers
    )

    # Check history
    response = client.get(
        f"/tags/models/{sample_model.model_id}/tags/history",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    removal_entries = [h for h in data["history"] if h["action"] == "REMOVED"]
    assert len(removal_entries) >= 1


# ============================================================================
# Usage Statistics Tests
# ============================================================================

def test_usage_statistics(client: TestClient, db_session, admin_headers, sample_model):
    """Test getting tag usage statistics."""
    category = TagCategory(name="Stats Cat", color="#EEEEEE", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag1 = Tag(category_id=category.category_id, name="Stats Tag 1", sort_order=1)
    tag2 = Tag(category_id=category.category_id, name="Stats Tag 2", is_active=False, sort_order=2)
    db_session.add_all([tag1, tag2])
    db_session.flush()

    model_tag = ModelTag(model_id=sample_model.model_id, tag_id=tag1.tag_id)
    db_session.add(model_tag)
    db_session.commit()

    response = client.get("/tags/usage-statistics", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_tags"] >= 2
    assert data["total_active_tags"] >= 1
    assert data["total_categories"] >= 1
    assert data["total_model_associations"] >= 1
    assert len(data["tags_by_category"]) >= 1


# ============================================================================
# Access Control Tests
# ============================================================================

def test_regular_user_can_read_tags(client: TestClient, db_session, auth_headers):
    """Test that regular users can read tags."""
    category = TagCategory(name="Read Cat", color="#FFFFFF", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="Readable Tag", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    # Regular user can list tags
    response = client.get("/tags/", headers=auth_headers)
    assert response.status_code == 200

    # Regular user can list categories
    response = client.get("/tags/categories", headers=auth_headers)
    assert response.status_code == 200


def test_regular_user_cannot_create_tags(client: TestClient, db_session, auth_headers):
    """Test that regular users cannot create tags."""
    category = TagCategory(name="No Create Cat", color="#000001", sort_order=1)
    db_session.add(category)
    db_session.commit()

    response = client.post(
        "/tags/",
        json={"category_id": category.category_id, "name": "Blocked Tag"},
        headers=auth_headers
    )
    assert response.status_code == 403


def test_regular_user_cannot_bulk_assign(client: TestClient, db_session, auth_headers, sample_model):
    """Test that regular users cannot use bulk operations."""
    category = TagCategory(name="No Bulk Cat", color="#000002", sort_order=1)
    db_session.add(category)
    db_session.flush()

    tag = Tag(category_id=category.category_id, name="No Bulk Tag", sort_order=1)
    db_session.add(tag)
    db_session.commit()

    response = client.post(
        "/tags/bulk-assign",
        json={"tag_id": tag.tag_id, "model_ids": [sample_model.model_id]},
        headers=auth_headers
    )
    assert response.status_code == 403
