"""Tests for Model Recommendations feature - TDD approach.

Covers all scenarios from FEATURE_DESIGN_RECOMMENDATIONS.md sections 15.1-15.11:
- 15.1 Recommendation Lifecycle
- 15.2 Priority & Approval Rules
- 15.3 Action Plan Tasks
- 15.4 Rebuttals
- 15.5 Closure Evidence
- 15.6 Status History & Audit
- 15.7 Validation & Constraints
- 15.8 Permissions & Roles
- 15.9 Retrieval & Filtering
- 15.10 Integration Touchpoints
- 15.11 Negative & Edge Cases
"""
import pytest
from datetime import date, datetime, timedelta
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.user import User
from app.models.model import Model
from app.models.region import Region
from app.models.model_region import ModelRegion
from app.core.security import get_password_hash, create_access_token


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def recommendation_taxonomies(db_session):
    """Create all recommendation-related taxonomy values."""
    # Recommendation Status
    status_tax = Taxonomy(name="Recommendation Status", is_system=True)
    db_session.add(status_tax)
    db_session.flush()

    draft = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_DRAFT", label="Draft", sort_order=1)
    pending_response = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_PENDING_RESPONSE", label="Pending Response", sort_order=2)
    in_rebuttal = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_IN_REBUTTAL", label="In Rebuttal", sort_order=3)
    dropped = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_DROPPED", label="Dropped", sort_order=4)
    pending_action_plan = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_PENDING_ACTION_PLAN", label="Pending Action Plan", sort_order=5)
    pending_validator_review = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_PENDING_VALIDATOR_REVIEW", label="Pending Validator Review", sort_order=6)
    pending_acknowledgement = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_PENDING_ACKNOWLEDGEMENT", label="Pending Acknowledgement", sort_order=7)
    open_status = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_OPEN", label="Open", sort_order=8)
    pending_closure_review = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_PENDING_CLOSURE_REVIEW", label="Pending Closure Review", sort_order=9)
    rework_required = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_REWORK_REQUIRED", label="Rework Required", sort_order=10)
    pending_final_approval = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_PENDING_FINAL_APPROVAL", label="Pending Final Approval", sort_order=11)
    closed = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REC_CLOSED", label="Closed", sort_order=12)

    # Recommendation Priority
    priority_tax = Taxonomy(name="Recommendation Priority", is_system=True)
    db_session.add(priority_tax)
    db_session.flush()

    high = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="HIGH", label="High", sort_order=1)
    medium = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="MEDIUM", label="Medium", sort_order=2)
    low = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="LOW", label="Low", sort_order=3)
    consideration = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="CONSIDERATION", label="Consideration", sort_order=4)

    # Recommendation Category
    category_tax = Taxonomy(name="Recommendation Category", is_system=True)
    db_session.add(category_tax)
    db_session.flush()

    cat_data = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_DATA", label="Data Quality", sort_order=1)
    cat_method = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_METHOD", label="Methodology", sort_order=2)
    cat_impl = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_IMPL", label="Implementation", sort_order=3)
    cat_doc = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_DOC", label="Documentation", sort_order=4)
    cat_monitor = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_MONITOR", label="Monitoring", sort_order=5)
    cat_govern = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_GOVERN", label="Governance", sort_order=6)
    cat_other = TaxonomyValue(taxonomy_id=category_tax.taxonomy_id, code="REC_CAT_OTHER", label="Other", sort_order=99)

    # Action Plan Task Status
    task_status_tax = Taxonomy(name="Action Plan Task Status", is_system=True)
    db_session.add(task_status_tax)
    db_session.flush()

    task_not_started = TaxonomyValue(taxonomy_id=task_status_tax.taxonomy_id, code="TASK_NOT_STARTED", label="Not Started", sort_order=1)
    task_in_progress = TaxonomyValue(taxonomy_id=task_status_tax.taxonomy_id, code="TASK_IN_PROGRESS", label="In Progress", sort_order=2)
    task_completed = TaxonomyValue(taxonomy_id=task_status_tax.taxonomy_id, code="TASK_COMPLETED", label="Completed", sort_order=3)

    db_session.add_all([
        draft, pending_response, in_rebuttal, dropped, pending_action_plan,
        pending_validator_review, pending_acknowledgement, open_status,
        pending_closure_review, rework_required, pending_final_approval, closed,
        high, medium, low, consideration,
        cat_data, cat_method, cat_impl, cat_doc, cat_monitor, cat_govern, cat_other,
        task_not_started, task_in_progress, task_completed
    ])
    db_session.commit()

    return {
        "status": {
            "draft": draft, "pending_response": pending_response, "in_rebuttal": in_rebuttal,
            "dropped": dropped, "pending_action_plan": pending_action_plan,
            "pending_validator_review": pending_validator_review,
            "pending_acknowledgement": pending_acknowledgement, "open": open_status,
            "pending_closure_review": pending_closure_review, "rework_required": rework_required,
            "pending_final_approval": pending_final_approval, "closed": closed
        },
        "priority": {"high": high, "medium": medium, "low": low, "consideration": consideration},
        "category": {
            "data": cat_data, "method": cat_method, "impl": cat_impl,
            "doc": cat_doc, "monitor": cat_monitor, "govern": cat_govern, "other": cat_other
        },
        "task_status": {
            "not_started": task_not_started, "in_progress": task_in_progress, "completed": task_completed
        }
    }


@pytest.fixture
def priority_configs(db_session, recommendation_taxonomies):
    """Create priority configurations for testing."""
    from app.models.recommendation import RecommendationPriorityConfig

    high_config = RecommendationPriorityConfig(
        priority_id=recommendation_taxonomies["priority"]["high"].value_id,
        requires_final_approval=True,
        requires_action_plan=True,
        description="High priority requires Global/Regional approvals"
    )
    medium_config = RecommendationPriorityConfig(
        priority_id=recommendation_taxonomies["priority"]["medium"].value_id,
        requires_final_approval=True,
        requires_action_plan=True,
        description="Medium priority requires Global/Regional approvals"
    )
    low_config = RecommendationPriorityConfig(
        priority_id=recommendation_taxonomies["priority"]["low"].value_id,
        requires_final_approval=False,
        requires_action_plan=True,
        description="Low priority closes with Validator approval only"
    )
    consideration_config = RecommendationPriorityConfig(
        priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
        requires_final_approval=False,
        requires_action_plan=False,
        description="Consideration priority - no action plan required, acknowledgement only"
    )

    db_session.add_all([high_config, medium_config, low_config, consideration_config])
    db_session.commit()

    return {"high": high_config, "medium": medium_config, "low": low_config, "consideration": consideration_config}


@pytest.fixture
def developer_user(db_session, lob_hierarchy):
    """Create a developer/owner user for recommendations."""
    user = User(
        email="developer@example.com",
        full_name="Developer User",
        password_hash=get_password_hash("developer123"),
        role="User",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def developer_headers(developer_user):
    """Get authorization headers for developer user."""
    token = create_access_token(data={"sub": developer_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def global_approver_user(db_session, lob_hierarchy):
    """Create a Global Approver user."""
    user = User(
        email="global_approver@example.com",
        full_name="Global Approver",
        password_hash=get_password_hash("approver123"),
        role="Global Approver",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def global_approver_headers(global_approver_user):
    """Get authorization headers for global approver."""
    token = create_access_token(data={"sub": global_approver_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regional_approver_user(db_session, lob_hierarchy):
    """Create a Regional Approver user."""
    user = User(
        email="regional_approver@example.com",
        full_name="Regional Approver",
        password_hash=get_password_hash("approver123"),
        role="Regional Approver",
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regional_approver_headers(regional_approver_user):
    """Get authorization headers for regional approver."""
    token = create_access_token(data={"sub": regional_approver_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_region(db_session):
    """Create a test region."""
    region = Region(
        code="US",
        name="United States",
        requires_regional_approval=True
    )
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


@pytest.fixture
def model_with_region(db_session, test_user, test_region, usage_frequency):
    """Create a model deployed to a region."""
    model = Model(
        model_name="Regional Model",
        description="Model deployed in a region",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status="approved",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.flush()

    model_region = ModelRegion(
        model_id=model.model_id,
        region_id=test_region.region_id
    )
    db_session.add(model_region)
    db_session.commit()
    db_session.refresh(model)
    return model


# ============================================================================
# 15.1 Recommendation Lifecycle Tests
# ============================================================================

class TestRecommendationLifecycle:
    """Test the full recommendation lifecycle state machine."""

    def test_create_draft_recommendation(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Create draft recommendation (validator) with required fields; default status = DRAFT."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Model calibration uses stale data",
                "description": "The calibration process references market data > 6 months old",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["current_status"]["code"] == "REC_DRAFT"
        assert data["recommendation_code"].startswith("REC-")
        assert data["title"] == "Model calibration uses stale data"
        assert "recommendation_id" in data

    def test_submit_to_developer_transitions_to_pending_response(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies, db_session
    ):
        """submit_to_developer moves DRAFT -> PENDING_RESPONSE; status history row written."""
        # Create draft
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Submit to developer
        response = client.post(
            f"/recommendations/{rec_id}/submit",
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_PENDING_RESPONSE"

    def test_submit_rebuttal_transitions_to_in_rebuttal(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """submit_rebuttal (developer) allowed only in PENDING_RESPONSE; status -> IN_REBUTTAL."""
        # Create and submit recommendation
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Developer submits rebuttal
        response = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={
                "rationale": "The data is within acceptable staleness per policy XYZ",
                "supporting_evidence": "https://example.com/evidence"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"]["current_status"]["code"] == "REC_IN_REBUTTAL"

    def test_accept_rebuttal_transitions_to_dropped(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """accept_rebuttal sets status -> DROPPED (terminal)."""
        # Setup: Create, submit, and rebuttal
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Valid reasoning", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]

        # Accept rebuttal
        response = client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "ACCEPT", "comments": "Developer's argument is valid"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"]["current_status"]["code"] == "REC_DROPPED"

    def test_override_rebuttal_transitions_to_pending_action_plan(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """override_rebuttal sets status -> PENDING_ACTION_PLAN; further rebuttals blocked."""
        # Setup
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Invalid reasoning", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]

        # Override rebuttal
        response = client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "OVERRIDE", "comments": "Policy does not apply"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"]["current_status"]["code"] == "REC_PENDING_ACTION_PLAN"

    def test_submit_action_plan_transitions_to_pending_validator_review(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """submit_action_plan (developer) allowed only in PENDING_ACTION_PLAN; status -> PENDING_VALIDATOR_REVIEW."""
        # Setup: Create, submit, rebuttal, override
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Reasoning", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]
        client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "OVERRIDE", "comments": "Must remediate"}
        )

        # Submit action plan
        task_target = (date.today() + timedelta(days=20)).isoformat()
        response = client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {
                        "description": "Update data pipeline",
                        "owner_id": developer_user.user_id,
                        "target_date": task_target
                    }
                ]
            }
        )
        assert response.status_code == 200

        # Verify status
        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        assert get_resp.json()["current_status"]["code"] == "REC_PENDING_VALIDATOR_REVIEW"

    def test_request_revisions_transitions_to_pending_response(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """request_revisions (validator) sends PENDING_VALIDATOR_REVIEW -> PENDING_RESPONSE."""
        # Setup: Get to PENDING_VALIDATOR_REVIEW via direct action plan submission
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Developer directly submits action plan (allowed from PENDING_RESPONSE)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )

        # Request revisions
        response = client.post(
            f"/recommendations/{rec_id}/action-plan/request-revisions",
            headers=validator_headers,
            json={"reason": "Tasks need more detail"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_PENDING_RESPONSE"

    def test_finalize_transitions_to_pending_acknowledgement(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """finalize (validator) sends PENDING_VALIDATOR_REVIEW -> PENDING_ACKNOWLEDGEMENT."""
        # Setup: Get to PENDING_VALIDATOR_REVIEW
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )

        # Finalize
        response = client.post(
            f"/recommendations/{rec_id}/finalize",
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_PENDING_ACKNOWLEDGEMENT"

    def test_acknowledge_transitions_to_open(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """acknowledge (developer) sends PENDING_ACKNOWLEDGEMENT -> OPEN."""
        # Setup: Get to PENDING_ACKNOWLEDGEMENT
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)

        # Acknowledge
        response = client.post(
            f"/recommendations/{rec_id}/acknowledge",
            headers=developer_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_OPEN"

    def test_decline_acknowledgement_returns_to_pending_validator_review(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """decline_acknowledgement sends PENDING_ACKNOWLEDGEMENT -> PENDING_VALIDATOR_REVIEW."""
        # Setup: Get to PENDING_ACKNOWLEDGEMENT
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)

        # Decline acknowledgement
        response = client.post(
            f"/recommendations/{rec_id}/decline-acknowledgement",
            headers=developer_headers,
            json={"reason": "Target dates are not feasible"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_PENDING_VALIDATOR_REVIEW"

    def test_submit_for_closure_transitions_to_pending_closure_review(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """submit_for_closure (developer) allowed only in OPEN; status -> PENDING_CLOSURE_REVIEW."""
        # Setup: Get to OPEN state
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,  # Low to skip approvals
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        # Mark task complete
        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )

        # Upload evidence
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={
                "file_name": "evidence.pdf",
                "file_path": "/uploads/evidence.pdf",
                "description": "Completion evidence"
            }
        )

        # Submit for closure
        response = client.post(
            f"/recommendations/{rec_id}/submit-closure",
            headers=developer_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_PENDING_CLOSURE_REVIEW"

    def test_return_for_rework_transitions_to_rework_required(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """return_for_rework (validator) sends PENDING_CLOSURE_REVIEW -> REWORK_REQUIRED."""
        # Setup: Get to PENDING_CLOSURE_REVIEW
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        # Mark task complete and add evidence
        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "evidence.pdf", "file_path": "/uploads/evidence.pdf", "description": "Evidence"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)

        # Return for rework
        response = client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "RETURN", "comments": "Missing documentation for task #1"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_REWORK_REQUIRED"

    def test_approve_closure_low_priority_directly_closes(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies, priority_configs
    ):
        """approve_closure (validator) sends PENDING_CLOSURE_REVIEW -> CLOSED for low priority."""
        # Setup: Get to PENDING_CLOSURE_REVIEW with low priority
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Low priority recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "evidence.pdf", "file_path": "/uploads/evidence.pdf", "description": "Evidence"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)

        # Approve closure
        response = client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "Satisfactory remediation", "closure_summary": "Issue resolved"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_CLOSED"

    def test_approve_closure_high_priority_creates_approvals(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies, priority_configs, model_with_region
    ):
        """approve_closure sets status -> PENDING_FINAL_APPROVAL for high priority and spawns approvals."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority recommendation",
                "description": "Test description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={
                "tasks": [
                    {"description": "Task 1", "owner_id": developer_user.user_id, "target_date": task_target}
                ]
            }
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "evidence.pdf", "file_path": "/uploads/evidence.pdf", "description": "Evidence"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)

        # Approve closure
        response = client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "Satisfactory", "closure_summary": "Resolved"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_status"]["code"] == "REC_PENDING_FINAL_APPROVAL"

        # Check approvals created
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=validator_headers)
        approvals = approvals_resp.json()
        assert len(approvals) >= 1  # At least Global approval


# ============================================================================
# 15.2 Priority & Approval Rules Tests
# ============================================================================

class TestPriorityAndApprovalRules:
    """Test priority configuration and approval requirements."""

    def test_priority_config_exists_for_all_levels(
        self, client, admin_headers, recommendation_taxonomies, priority_configs
    ):
        """Priority seeding: RecommendationPriorityConfig rows exist for High/Medium/Low/Consideration."""
        response = client.get("/recommendations/priority-config/", headers=admin_headers)
        assert response.status_code == 200
        configs = response.json()
        assert len(configs) == 4

        codes = [c["priority"]["code"] for c in configs]
        assert "HIGH" in codes
        assert "MEDIUM" in codes
        assert "LOW" in codes
        assert "CONSIDERATION" in codes

    def test_high_priority_requires_final_approval(
        self, client, admin_headers, recommendation_taxonomies, priority_configs
    ):
        """High/Medium priorities have requires_final_approval=True."""
        response = client.get("/recommendations/priority-config/", headers=admin_headers)
        configs = response.json()

        high_config = next(c for c in configs if c["priority"]["code"] == "HIGH")
        medium_config = next(c for c in configs if c["priority"]["code"] == "MEDIUM")

        assert high_config["requires_final_approval"] is True
        assert medium_config["requires_final_approval"] is True

    def test_low_priority_skips_final_approvals(
        self, client, admin_headers, recommendation_taxonomies, priority_configs
    ):
        """Low priority has requires_final_approval=False."""
        response = client.get("/recommendations/priority-config/", headers=admin_headers)
        configs = response.json()

        low_config = next(c for c in configs if c["priority"]["code"] == "LOW")
        assert low_config["requires_final_approval"] is False

    def test_consideration_priority_skips_action_plan(
        self, client, admin_headers, recommendation_taxonomies, priority_configs
    ):
        """Consideration priority has requires_action_plan=False and requires_final_approval=False."""
        response = client.get("/recommendations/priority-config/", headers=admin_headers)
        configs = response.json()

        consideration_config = next(c for c in configs if c["priority"]["code"] == "CONSIDERATION")
        assert consideration_config["requires_final_approval"] is False
        assert consideration_config["requires_action_plan"] is False

    def test_high_medium_low_require_action_plan(
        self, client, admin_headers, recommendation_taxonomies, priority_configs
    ):
        """High/Medium/Low priorities require action plan (requires_action_plan=True)."""
        response = client.get("/recommendations/priority-config/", headers=admin_headers)
        configs = response.json()

        high_config = next(c for c in configs if c["priority"]["code"] == "HIGH")
        medium_config = next(c for c in configs if c["priority"]["code"] == "MEDIUM")
        low_config = next(c for c in configs if c["priority"]["code"] == "LOW")

        assert high_config["requires_action_plan"] is True
        assert medium_config["requires_action_plan"] is True
        assert low_config["requires_action_plan"] is True

    def test_admin_can_update_priority_config(
        self, client, admin_headers, recommendation_taxonomies, priority_configs
    ):
        """Admins can modify priority configuration."""
        priority_id = recommendation_taxonomies["priority"]["low"].value_id

        response = client.patch(
            f"/recommendations/priority-config/{priority_id}",
            headers=admin_headers,
            json={"requires_final_approval": True, "description": "Updated to require approval"}
        )
        assert response.status_code == 200
        assert response.json()["requires_final_approval"] is True

    def test_approval_creation_includes_global_and_regional(
        self, client, validator_headers, developer_headers, admin_headers,
        model_with_region, developer_user, recommendation_taxonomies, priority_configs
    ):
        """High priority creates Global + Regional approvals based on model deployment."""
        # Full workflow to PENDING_FINAL_APPROVAL
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress through workflow
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Check approvals
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        approvals = approvals_resp.json()

        approval_types = [a["approval_type"] for a in approvals]
        assert "GLOBAL" in approval_types
        assert "REGIONAL" in approval_types


# ============================================================================
# 15.3 Action Plan Tasks Tests
# ============================================================================

class TestActionPlanTasks:
    """Test action plan task management."""

    def test_create_task_requires_owner_and_target_date(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Create task requires owner and target_date."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Submit action plan without owner_id - should fail
        response = client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task without owner", "target_date": target_date}]}
        )
        assert response.status_code == 422  # Validation error

    def test_task_default_status_is_not_started(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Default task status = NOT_STARTED."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task = get_resp.json()["action_plan_tasks"][0]
        assert task["completion_status"]["code"] == "TASK_NOT_STARTED"

    def test_task_status_flow_not_started_to_in_progress_to_completed(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Update task status flow: NOT_STARTED -> IN_PROGRESS -> COMPLETED."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]

        # Progress to IN_PROGRESS
        resp1 = client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["in_progress"].value_id}
        )
        assert resp1.status_code == 200
        assert resp1.json()["completion_status"]["code"] == "TASK_IN_PROGRESS"

        # Progress to COMPLETED
        resp2 = client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        assert resp2.status_code == 200
        assert resp2.json()["completion_status"]["code"] == "TASK_COMPLETED"

    def test_completed_task_has_completed_date(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """completed_at set when marked COMPLETED."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]

        resp = client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        assert resp.json()["completed_date"] is not None


# ============================================================================
# 15.4 Rebuttals Tests
# ============================================================================

class TestRebuttals:
    """Test rebuttal submission and one-strike rule."""

    def test_rebuttal_blocked_after_override_one_strike_rule(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Only one rebuttal allowed; second submission blocked after override (one-strike rule)."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # First rebuttal
        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "First attempt", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]

        # Override first rebuttal
        client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "OVERRIDE", "comments": "Not valid"}
        )

        # Second rebuttal should fail
        response = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Second attempt", "supporting_evidence": "https://example.com/evidence"}
        )
        assert response.status_code == 400
        assert "action plan" in response.json()["detail"].lower() or "rebuttal" in response.json()["detail"].lower()

    def test_rebuttal_review_records_reviewer_and_decision(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, validator_user, recommendation_taxonomies
    ):
        """Rebuttal review records reviewed_by and decision."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Valid reason", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]

        review_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "ACCEPT", "comments": "Valid argument"}
        )

        data = review_resp.json()
        assert data["review_decision"] == "ACCEPT"
        assert data["reviewed_by"]["user_id"] == validator_user.user_id
        assert data["reviewed_at"] is not None


# ============================================================================
# 15.5 Closure Evidence Tests
# ============================================================================

class TestClosureEvidence:
    """Test closure evidence upload and requirements."""

    def test_upload_evidence_allowed_in_open_status(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Upload evidence (developer) allowed when status in OPEN."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        # Upload evidence
        response = client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={
                "file_name": "evidence.pdf",
                "file_path": "/uploads/evidence.pdf",
                "description": "Completion evidence"
            }
        )
        assert response.status_code == 201
        assert response.json()["file_name"] == "evidence.pdf"

    def test_closure_submission_allowed_without_evidence(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Evidence optional: submitting for closure without evidence returns 200."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        # Mark task complete but don't add evidence
        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )

        # Try to submit for closure
        response = client.post(
            f"/recommendations/{rec_id}/submit-closure",
            headers=developer_headers
        )
        assert response.status_code == 200
        assert response.json()["current_status"]["code"] == "REC_PENDING_CLOSURE_REVIEW"


# ============================================================================
# 15.6 Status History & Audit Tests
# ============================================================================

class TestStatusHistoryAndAudit:
    """Test status history tracking and audit logging."""

    def test_status_transition_creates_history_row(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Every status transition creates RecommendationStatusHistory."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Submit to developer
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Check status history
        get_resp = client.get(f"/recommendations/{rec_id}", headers=validator_headers)
        status_history = get_resp.json()["status_history"]

        assert len(status_history) >= 2  # Creation + submit
        assert status_history[0]["new_status"]["code"] == "REC_PENDING_RESPONSE"  # Most recent first

    def test_status_history_ordered_by_changed_at_descending(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Status history ordered descending by changed_at."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )

        get_resp = client.get(f"/recommendations/{rec_id}", headers=validator_headers)
        history = get_resp.json()["status_history"]

        # Verify descending order
        timestamps = [h["changed_at"] for h in history]
        assert timestamps == sorted(timestamps, reverse=True)


# ============================================================================
# 15.7 Validation & Constraints Tests
# ============================================================================

class TestValidationAndConstraints:
    """Test field validation and constraints."""

    def test_required_fields_validated(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Required fields validated: title, description, priority, category, model_id, assigned_to_id."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Missing title
        response = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert response.status_code == 422

    def test_invalid_taxonomy_id_returns_error(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Priority/category taxonomy IDs must exist; invalid IDs return 404."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        response = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": 99999,  # Invalid
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert response.status_code in [400, 404]

    def test_recommendation_code_uniqueness(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Recommendation code uniqueness enforced."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create two recommendations
        resp1 = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test 1",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        resp2 = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test 2",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )

        # Codes should be unique
        assert resp1.json()["recommendation_code"] != resp2.json()["recommendation_code"]


# ============================================================================
# 15.8 Permissions & Roles Tests
# ============================================================================

class TestPermissionsAndRoles:
    """Test role-based access control."""

    def test_validator_only_can_create_recommendation(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Validator-only: create recommendation."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Validator can create
        val_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert val_resp.status_code == 201

        # Developer cannot create
        dev_resp = client.post(
            "/recommendations/",
            headers=developer_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert dev_resp.status_code == 403

    def test_developer_cannot_review_rebuttal(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Developer cannot review rebuttal."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Reason", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]

        # Developer tries to review own rebuttal
        response = client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=developer_headers,
            json={"decision": "ACCEPT", "comments": "Self-approval"}
        )
        assert response.status_code == 403

    def test_validator_cannot_submit_rebuttal(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Validator cannot submit rebuttal."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        response = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=validator_headers,
            json={"rationale": "Reason", "supporting_evidence": "https://example.com/evidence"}
        )
        assert response.status_code == 403

    def test_admin_can_perform_any_action(
        self, client, admin_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Admin bypass: can perform any workflow action."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Admin creates
        create_resp = client.post(
            "/recommendations/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert create_resp.status_code == 201
        rec_id = create_resp.json()["recommendation_id"]

        # Admin submits
        submit_resp = client.post(f"/recommendations/{rec_id}/submit", headers=admin_headers)
        assert submit_resp.status_code == 200

        # Admin submits rebuttal (on behalf)
        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=admin_headers,
            json={"rationale": "Reason", "supporting_evidence": "https://example.com/evidence"}
        )
        assert rebuttal_resp.status_code == 200

    def test_unauthenticated_request_returns_401_or_403(
        self, client, sample_model, recommendation_taxonomies
    ):
        """Tokenless requests return 401/403."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        response = client.post(
            "/recommendations/",
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": 1,
                "original_target_date": target_date
            }
        )
        assert response.status_code in [401, 403]


# ============================================================================
# 15.9 Retrieval & Filtering Tests
# ============================================================================

class TestRetrievalAndFiltering:
    """Test list endpoint filters and pagination."""

    def test_list_filters_by_status(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """List endpoint supports filter by status."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create and leave in draft
        client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )

        # Create and submit
        resp2 = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Submitted rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec2_id = resp2.json()["recommendation_id"]
        client.post(f"/recommendations/{rec2_id}/submit", headers=validator_headers)

        # Filter by draft status
        draft_status_id = recommendation_taxonomies["status"]["draft"].value_id
        response = client.get(
            f"/recommendations/?status_id={draft_status_id}",
            headers=validator_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(r["current_status"]["code"] == "REC_DRAFT" for r in data)

    def test_list_supports_pagination(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Pagination (limit/offset) works."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create 3 recommendations
        for i in range(3):
            client.post(
                "/recommendations/",
                headers=validator_headers,
                json={
                    "model_id": sample_model.model_id,
                    "title": f"Rec {i}",
                    "description": "Desc",
                    "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                    "category_id": recommendation_taxonomies["category"]["data"].value_id,
                    "assigned_to_id": developer_user.user_id,
                    "original_target_date": target_date
                }
            )

        # Get with limit
        response = client.get(
            "/recommendations/?limit=2&offset=0",
            headers=validator_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_detail_includes_nested_relationships(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Detail endpoint includes nested action plan tasks, rebuttal, evidence, history, approvals."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )

        get_resp = client.get(f"/recommendations/{rec_id}", headers=validator_headers)
        data = get_resp.json()

        assert "action_plan_tasks" in data
        assert "status_history" in data
        assert "model" in data


# ============================================================================
# 15.10 Integration Touchpoints Tests
# ============================================================================

class TestIntegrationTouchpoints:
    """Test integration with validation requests and model regions."""

    def test_recommendation_can_link_to_validation_request(
        self, client, validator_headers, admin_headers, sample_model,
        developer_user, recommendation_taxonomies, db_session
    ):
        """Recommendation may reference validation_request_id."""
        from app.models.taxonomy import Taxonomy, TaxonomyValue
        from app.models.validation import ValidationRequest

        # Create validation request taxonomy values
        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        type_tax = Taxonomy(name="Validation Type", is_system=True)
        priority_tax = Taxonomy(name="Validation Priority", is_system=True)
        db_session.add_all([status_tax, type_tax, priority_tax])
        db_session.flush()

        intake = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="INTAKE", label="Intake", sort_order=1)
        initial = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id, code="INITIAL", label="Initial", sort_order=1)
        high_val = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="HIGH", label="High", sort_order=1)
        db_session.add_all([intake, initial, high_val])
        db_session.flush()

        # Create validation request directly in DB
        val_request = ValidationRequest(
            validation_type_id=initial.value_id,
            priority_id=high_val.value_id,
            current_status_id=intake.value_id,
            target_completion_date=date.today() + timedelta(days=30),
            requestor_id=developer_user.user_id
        )
        db_session.add(val_request)
        db_session.commit()
        db_session.refresh(val_request)

        target_date = (date.today() + timedelta(days=30)).isoformat()

        response = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "validation_request_id": val_request.request_id,
                "title": "Linked to validation",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert response.status_code == 201
        assert response.json()["validation_request_id"] == val_request.request_id


# ============================================================================
# 15.11 Negative & Edge Cases Tests
# ============================================================================

class TestNegativeAndEdgeCases:
    """Test negative scenarios and edge cases."""

    def test_cannot_transition_from_terminal_state_dropped(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Cannot transition from terminal states (DROPPED)."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        rebuttal_resp = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Valid", "supporting_evidence": "https://example.com/evidence"}
        )
        rebuttal_id = rebuttal_resp.json()["rebuttal_id"]

        # Accept rebuttal -> DROPPED
        client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "ACCEPT", "comments": "Valid"}
        )

        # Try to submit again
        response = client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        assert response.status_code == 400

    def test_cannot_transition_from_terminal_state_closed(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies, priority_configs
    ):
        """Cannot transition from terminal states (CLOSED)."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Low priority test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Verify closed
        verify_resp = client.get(f"/recommendations/{rec_id}", headers=validator_headers)
        assert verify_resp.json()["current_status"]["code"] == "REC_CLOSED"

        # Try to submit again
        response = client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        assert response.status_code == 400

    def test_cannot_submit_rebuttal_twice_while_pending(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Cannot submit rebuttal twice while one is pending review."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # First rebuttal
        client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "First", "supporting_evidence": "https://example.com/evidence"}
        )

        # Second rebuttal while first is pending - should fail
        response = client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Second", "supporting_evidence": "https://example.com/evidence"}
        )
        assert response.status_code == 400

    def test_closure_blocked_with_incomplete_tasks(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Closure submission blocked if tasks incomplete."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        # Add evidence but don't complete task
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )

        # Try to submit for closure
        response = client.post(
            f"/recommendations/{rec_id}/submit-closure",
            headers=developer_headers
        )
        assert response.status_code == 400
        assert "task" in response.json()["detail"].lower()

    def test_approve_already_approved_approval_returns_error(
        self, client, validator_headers, developer_headers, admin_headers,
        global_approver_headers, model_with_region, developer_user,
        recommendation_taxonomies, priority_configs
    ):
        """Approving already-approved approval returns 400."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get approvals
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "GLOBAL")
        approval_id = global_approval["approval_id"]

        # Approve once
        client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/approve",
            headers=global_approver_headers,
            json={"comments": "Approved"}
        )

        # Try to approve again
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/approve",
            headers=global_approver_headers,
            json={"comments": "Double approve"}
        )
        assert response.status_code == 400


# ============================================================================
# 15.12 Approval Authorization and Reject/Void Tests
# ============================================================================

class TestApprovalAuthorizationAndSecurity:
    """Test approval authorization security and reject/void endpoints."""

    def test_regular_user_cannot_approve_global_approval(
        self, client, validator_headers, developer_headers, admin_headers,
        model_with_region, developer_user, recommendation_taxonomies, priority_configs
    ):
        """Regular user cannot approve a GLOBAL approval."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get global approval
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "GLOBAL")
        approval_id = global_approval["approval_id"]

        # Developer (regular user) tries to approve global - should fail
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/approve",
            headers=developer_headers,
            json={"comments": "Trying to approve"}
        )
        assert response.status_code == 403
        assert "Global Approvers" in response.json()["detail"]

    def test_regional_approver_cannot_approve_wrong_region(
        self, client, validator_headers, developer_headers, admin_headers,
        regional_approver_headers, db_session, model_with_region, developer_user,
        recommendation_taxonomies, priority_configs
    ):
        """Regional approver cannot approve for a region they're not assigned to."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        # Create a second region that the regional approver is NOT assigned to
        different_region = Region(
            code="EU",
            name="Europe",
            requires_regional_approval=True
        )
        db_session.add(different_region)
        db_session.flush()

        # Add different region to the model
        different_model_region = ModelRegion(
            model_id=model_with_region.model_id,
            region_id=different_region.region_id
        )
        db_session.add(different_model_region)
        db_session.commit()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get the EU regional approval (not assigned to regional_approver_user)
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        eu_approval = next(
            (a for a in approvals_resp.json()
             if a["approval_type"] == "REGIONAL" and a.get("region", {}).get("code") == "EU"),
            None
        )
        assert eu_approval is not None, "EU regional approval should exist"
        approval_id = eu_approval["approval_id"]

        # Regional approver (assigned to US) tries to approve EU - should fail
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/approve",
            headers=regional_approver_headers,
            json={"comments": "Trying to approve wrong region"}
        )
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    def test_reject_approval_returns_to_rework_required(
        self, client, validator_headers, developer_headers, admin_headers,
        global_approver_headers, model_with_region, developer_user,
        recommendation_taxonomies, priority_configs
    ):
        """Rejecting an approval returns recommendation to REWORK_REQUIRED."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get global approval
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "GLOBAL")
        approval_id = global_approval["approval_id"]

        # Reject the approval
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/reject",
            headers=global_approver_headers,
            json={"rejection_reason": "Insufficient evidence for closure"}
        )
        assert response.status_code == 200
        assert response.json()["approval_status"] == "REJECTED"

        # Verify recommendation is back in REWORK_REQUIRED
        rec_resp = client.get(f"/recommendations/{rec_id}", headers=admin_headers)
        assert rec_resp.json()["current_status"]["code"] == "REC_REWORK_REQUIRED"

    def test_reject_requires_reason(
        self, client, validator_headers, developer_headers, admin_headers,
        global_approver_headers, model_with_region, developer_user,
        recommendation_taxonomies, priority_configs
    ):
        """Rejecting an approval requires a reason."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL (abbreviated for clarity)
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get global approval
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "GLOBAL")
        approval_id = global_approval["approval_id"]

        # Reject without reason - should fail
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/reject",
            headers=global_approver_headers,
            json={"rejection_reason": ""}
        )
        assert response.status_code == 400
        assert "reason" in response.json()["detail"].lower()

    def test_void_approval_admin_only(
        self, client, validator_headers, developer_headers, admin_headers,
        global_approver_headers, model_with_region, developer_user,
        recommendation_taxonomies, priority_configs
    ):
        """Only admin can void an approval requirement."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get global approval
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "GLOBAL")
        approval_id = global_approval["approval_id"]

        # Global approver tries to void - should fail
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/void",
            headers=global_approver_headers,
            json={"rejection_reason": "Not needed"}
        )
        assert response.status_code == 403

        # Admin voids - should succeed
        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/void",
            headers=admin_headers,
            json={"rejection_reason": "Approver unavailable, voiding requirement"}
        )
        assert response.status_code == 200
        assert response.json()["approval_status"] == "VOIDED"

    def test_void_all_approvals_closes_recommendation(
        self, client, validator_headers, developer_headers, admin_headers,
        model_with_region, developer_user, recommendation_taxonomies, priority_configs
    ):
        """Voiding all pending approvals results in recommendation closure."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get all approvals
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        approvals = approvals_resp.json()

        # Void all approvals
        for approval in approvals:
            client.post(
                f"/recommendations/{rec_id}/approvals/{approval['approval_id']}/void",
                headers=admin_headers,
                json={"rejection_reason": "Emergency closure"}
            )

        # Verify recommendation is now CLOSED
        rec_resp = client.get(f"/recommendations/{rec_id}", headers=admin_headers)
        assert rec_resp.json()["current_status"]["code"] == "REC_CLOSED"

    def test_admin_approval_requires_evidence_attestation(
        self, client, validator_headers, developer_headers, admin_headers,
        model_with_region, developer_user, recommendation_taxonomies, priority_configs
    ):
        """Admin approval requires approval_evidence attestation."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        approval_id = approvals_resp.json()[0]["approval_id"]

        response = client.post(
            f"/recommendations/{rec_id}/approvals/{approval_id}/approve",
            headers=admin_headers,
            json={"comments": "Admin approval without evidence"}
        )
        assert response.status_code == 400
        assert "approval_evidence" in response.json()["detail"]

    def test_admin_can_approve_any_approval_type(
        self, client, validator_headers, developer_headers, admin_headers,
        model_with_region, developer_user, recommendation_taxonomies, priority_configs
    ):
        """Admin can approve both GLOBAL and REGIONAL approvals."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "High priority rec",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf", "description": "Ev"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Get all approvals
        approvals_resp = client.get(f"/recommendations/{rec_id}/approvals", headers=admin_headers)
        approvals = approvals_resp.json()

        # Admin approves all
        for approval in approvals:
            response = client.post(
                f"/recommendations/{rec_id}/approvals/{approval['approval_id']}/approve",
                headers=admin_headers,
                json={
                    "comments": f"Admin approved {approval['approval_type']}",
                    "approval_evidence": "Approval email retained by Admin"
                }
            )
            assert response.status_code == 200

        # Verify recommendation is now CLOSED
        rec_resp = client.get(f"/recommendations/{rec_id}", headers=admin_headers)
        assert rec_resp.json()["current_status"]["code"] == "REC_CLOSED"


# ============================================================================
# 15.12 Dashboard & Reports
# ============================================================================

class TestDashboardAndReports:
    """Tests for dashboard and reporting endpoints."""

    def test_my_tasks_developer_sees_assigned_tasks(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Developer sees recommendations assigned to them requiring action."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create recommendation and submit to developer
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Dev task test",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Developer should see this in their tasks
        response = client.get("/recommendations/my-tasks", headers=developer_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] >= 1
        task_ids = [t["recommendation_id"] for t in data["tasks"]]
        assert rec_id in task_ids

        # Find the task and verify details
        task = next(t for t in data["tasks"] if t["recommendation_id"] == rec_id)
        assert task["task_type"] == "ACTION_REQUIRED"
        assert "rebuttal" in task["action_description"].lower() or "action plan" in task["action_description"].lower()

    def test_my_tasks_validator_sees_review_tasks(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, validator_user, recommendation_taxonomies
    ):
        """Validator sees recommendations they created awaiting their review."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create recommendation, submit, and have developer submit action plan
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Validator review test",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["method"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task 1", "owner_id": developer_user.user_id, "target_date": target_date}]}
        )

        # Validator should see this in their tasks
        response = client.get("/recommendations/my-tasks", headers=validator_headers)
        assert response.status_code == 200
        data = response.json()
        task_ids = [t["recommendation_id"] for t in data["tasks"]]
        assert rec_id in task_ids

        task = next(t for t in data["tasks"] if t["recommendation_id"] == rec_id)
        assert task["task_type"] == "REVIEW_PENDING"

    def test_my_tasks_approver_sees_pending_approvals(
        self, client, validator_headers, developer_headers, admin_headers,
        global_approver_headers, model_with_region, developer_user,
        recommendation_taxonomies, priority_configs
    ):
        """Global/Regional approvers see pending approvals in their tasks."""
        target_date = (date.today() + timedelta(days=30)).isoformat()
        task_target = (date.today() + timedelta(days=20)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_with_region.model_id,
                "title": "Approver task test",
                "description": "Desc",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress through workflow to PENDING_FINAL_APPROVAL
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": task_target}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Global approver should see pending approval
        response = client.get("/recommendations/my-tasks", headers=global_approver_headers)
        assert response.status_code == 200
        data = response.json()
        task_ids = [t["recommendation_id"] for t in data["tasks"]]
        assert rec_id in task_ids

        task = next(t for t in data["tasks"] if t["recommendation_id"] == rec_id)
        assert task["task_type"] == "APPROVAL_PENDING"
        assert "global" in task["action_description"].lower()

    def test_my_tasks_overdue_tracking(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies, db_session
    ):
        """Tasks with past due dates are marked as overdue and counted."""
        # Create with future date (API validation requires this)
        future_date = (date.today() + timedelta(days=5)).isoformat()

        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Overdue task test",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": future_date
            }
        )
        assert create_resp.status_code == 201, f"Create failed: {create_resp.json()}"
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Update target date to past to make it overdue (bypass API validation for testing)
        from app.models.recommendation import Recommendation
        rec = db_session.query(Recommendation).filter(Recommendation.recommendation_id == rec_id).first()
        past_date = date.today() - timedelta(days=5)
        rec.current_target_date = past_date
        rec.original_target_date = past_date
        db_session.commit()

        response = client.get("/recommendations/my-tasks", headers=developer_headers)
        assert response.status_code == 200
        data = response.json()

        task = next((t for t in data["tasks"] if t["recommendation_id"] == rec_id), None)
        assert task is not None
        assert task["is_overdue"] is True
        assert task["days_until_due"] < 0
        assert data["overdue_count"] >= 1

    def test_dashboard_open_recommendations_summary(
        self, client, validator_headers, developer_headers, admin_headers,
        sample_model, developer_user, recommendation_taxonomies
    ):
        """Dashboard returns summary of open recommendations by status and priority."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create a few recommendations in different states
        for i, priority_key in enumerate(["high", "medium", "low"]):
            create_resp = client.post(
                "/recommendations/",
                headers=validator_headers,
                json={
                    "model_id": sample_model.model_id,
                    "title": f"Dashboard test {i}",
                    "description": "Description",
                    "priority_id": recommendation_taxonomies["priority"][priority_key].value_id,
                    "assigned_to_id": developer_user.user_id,
                    "original_target_date": target_date
                }
            )
            # Submit first two to different states
            rec_id = create_resp.json()["recommendation_id"]
            if i < 2:
                client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        response = client.get("/recommendations/dashboard/open", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()

        assert "total_open" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert data["total_open"] >= 3
        assert len(data["by_status"]) > 0
        assert len(data["by_priority"]) > 0

        # Verify structure
        status = data["by_status"][0]
        assert "status_code" in status
        assert "status_label" in status
        assert "count" in status

        priority = data["by_priority"][0]
        assert "priority_code" in priority
        assert "priority_label" in priority
        assert "count" in priority

    def test_dashboard_overdue_recommendations(
        self, client, validator_headers, developer_headers, admin_headers,
        sample_model, developer_user, recommendation_taxonomies, db_session
    ):
        """Dashboard returns list of overdue recommendations."""
        future_date = (date.today() + timedelta(days=30)).isoformat()

        # Create recommendation with future date (API validation requires this)
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Overdue rec",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["high"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": future_date
            }
        )
        assert create_resp.status_code == 201, f"Create failed: {create_resp.json()}"
        overdue_rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{overdue_rec_id}/submit", headers=validator_headers)

        # Update target date to past to make it overdue (bypass API validation for testing)
        from app.models.recommendation import Recommendation
        rec = db_session.query(Recommendation).filter(Recommendation.recommendation_id == overdue_rec_id).first()
        past_date = date.today() - timedelta(days=10)
        rec.current_target_date = past_date
        rec.original_target_date = past_date
        db_session.commit()

        # Create on-time recommendation
        client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "On time rec",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": future_date
            }
        )

        response = client.get("/recommendations/dashboard/overdue", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()

        assert "total_overdue" in data
        assert "by_priority" in data
        assert "recommendations" in data
        assert data["total_overdue"] >= 1

        # Verify overdue rec is in the list
        rec_ids = [r["recommendation_id"] for r in data["recommendations"]]
        assert overdue_rec_id in rec_ids

        # Verify days_overdue calculation
        overdue_rec = next(r for r in data["recommendations"] if r["recommendation_id"] == overdue_rec_id)
        assert overdue_rec["days_overdue"] >= 10

    def test_dashboard_by_model(
        self, client, validator_headers, admin_headers, sample_model,
        developer_user, recommendation_taxonomies, db_session
    ):
        """Get recommendations for a specific model."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create recommendation for sample_model
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Model-specific rec",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        response = client.get(
            f"/recommendations/dashboard/by-model/{sample_model.model_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        rec_ids = [r["recommendation_id"] for r in data]
        assert rec_id in rec_ids

    def test_dashboard_by_model_include_closed(
        self, client, validator_headers, developer_headers, admin_headers,
        sample_model, developer_user, recommendation_taxonomies, priority_configs
    ):
        """Include closed recommendations when flag is set."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create and close a low-priority recommendation (direct closure)
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Closed rec",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Progress to closure
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/action-plan",
            headers=developer_headers,
            json={"tasks": [{"description": "Task", "owner_id": developer_user.user_id, "target_date": target_date}]}
        )
        client.post(f"/recommendations/{rec_id}/finalize", headers=validator_headers)
        client.post(f"/recommendations/{rec_id}/acknowledge", headers=developer_headers)

        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        task_id = get_resp.json()["action_plan_tasks"][0]["task_id"]
        client.patch(
            f"/recommendations/{rec_id}/tasks/{task_id}",
            headers=developer_headers,
            json={"completion_status_id": recommendation_taxonomies["task_status"]["completed"].value_id}
        )
        client.post(
            f"/recommendations/{rec_id}/evidence",
            headers=developer_headers,
            json={"file_name": "ev.pdf", "file_path": "/ev.pdf"}
        )
        client.post(f"/recommendations/{rec_id}/submit-closure", headers=developer_headers)
        client.post(
            f"/recommendations/{rec_id}/closure-review",
            headers=validator_headers,
            json={"decision": "APPROVE", "comments": "OK", "closure_summary": "Done"}
        )

        # Without flag, closed rec should not be included
        response = client.get(
            f"/recommendations/dashboard/by-model/{sample_model.model_id}",
            headers=admin_headers
        )
        rec_ids = [r["recommendation_id"] for r in response.json()]
        assert rec_id not in rec_ids

        # With flag, closed rec should be included
        response = client.get(
            f"/recommendations/dashboard/by-model/{sample_model.model_id}?include_closed=true",
            headers=admin_headers
        )
        rec_ids = [r["recommendation_id"] for r in response.json()]
        assert rec_id in rec_ids

    def test_dashboard_by_model_not_found(self, client, admin_headers):
        """Returns 404 for non-existent model."""
        response = client.get(
            "/recommendations/dashboard/by-model/99999",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_my_tasks_empty_for_new_user(
        self, client, db_session, recommendation_taxonomies, lob_hierarchy
    ):
        """New user with no assignments sees empty task list."""
        # Create a fresh user
        new_user = User(
            email="newuser@example.com",
            full_name="New User",
            password_hash=get_password_hash("pass123"),
            role="User",
            lob_id=lob_hierarchy["retail"].lob_id
        )
        db_session.add(new_user)
        db_session.commit()

        token = create_access_token({"sub": new_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/recommendations/my-tasks", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 0
        assert data["overdue_count"] == 0
        assert data["tasks"] == []

    def test_dashboard_open_excludes_terminal_states(
        self, client, validator_headers, developer_headers, admin_headers,
        sample_model, developer_user, recommendation_taxonomies
    ):
        """Open dashboard excludes DROPPED and CLOSED recommendations."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create a recommendation and drop it via rebuttal accept
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "To be dropped",
                "description": "Description",
                "priority_id": recommendation_taxonomies["priority"]["low"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)
        client.post(
            f"/recommendations/{rec_id}/rebuttal",
            headers=developer_headers,
            json={"rationale": "Not valid", "supporting_evidence": "https://example.com/evidence"}
        )
        # Get rebuttal ID
        rec_resp = client.get(f"/recommendations/{rec_id}", headers=admin_headers)
        rebuttal_id = rec_resp.json()["rebuttals"][0]["rebuttal_id"]
        # Accept rebuttal to drop recommendation
        client.post(
            f"/recommendations/{rec_id}/rebuttal/{rebuttal_id}/review",
            headers=validator_headers,
            json={"decision": "ACCEPT", "comments": "Valid point"}
        )

        # Get open dashboard
        response = client.get("/recommendations/dashboard/open", headers=admin_headers)
        data = response.json()

        # Dropped rec should not be in totals
        status_codes = [s["status_code"] for s in data["by_status"]]
        assert "REC_DROPPED" not in status_codes
        assert "REC_CLOSED" not in status_codes


# ============================================================================
# Phase 7: Regional Override Tests (TDD)
# ============================================================================

@pytest.fixture
def multiple_regions(db_session):
    """Create multiple regions for testing regional overrides."""
    us_region = Region(code="US", name="United States", requires_regional_approval=True)
    emea_region = Region(code="EMEA", name="Europe, Middle East & Africa", requires_regional_approval=True)
    apac_region = Region(code="APAC", name="Asia Pacific", requires_regional_approval=True)
    global_region = Region(code="GLOBAL", name="Global", requires_regional_approval=False)

    db_session.add_all([us_region, emea_region, apac_region, global_region])
    db_session.commit()
    db_session.refresh(us_region)
    db_session.refresh(emea_region)
    db_session.refresh(apac_region)
    db_session.refresh(global_region)

    return {"us": us_region, "emea": emea_region, "apac": apac_region, "global": global_region}


@pytest.fixture
def model_deployed_us(db_session, test_user, multiple_regions, usage_frequency):
    """Create a model deployed to US region only."""
    model = Model(
        model_name="US Model",
        description="Model deployed only in US",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status="approved",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.flush()

    model_region = ModelRegion(
        model_id=model.model_id,
        region_id=multiple_regions["us"].region_id
    )
    db_session.add(model_region)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def model_deployed_us_emea(db_session, test_user, multiple_regions, usage_frequency):
    """Create a model deployed to US and EMEA regions."""
    model = Model(
        model_name="US EMEA Model",
        description="Model deployed in US and EMEA",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status="approved",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.flush()

    us_region = ModelRegion(model_id=model.model_id, region_id=multiple_regions["us"].region_id)
    emea_region = ModelRegion(model_id=model.model_id, region_id=multiple_regions["emea"].region_id)
    db_session.add_all([us_region, emea_region])
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def model_global_only(db_session, test_user, usage_frequency):
    """Create a model with no regional deployments (global only)."""
    model = Model(
        model_name="Global Model",
        description="Model with no specific regional deployment",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status="approved",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class TestRegionalOverrideModel:
    """Test the RecommendationPriorityRegionalOverride model."""

    def test_create_regional_override(
        self, db_session, recommendation_taxonomies, multiple_regions
    ):
        """Can create a regional override for a priority-region combination."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True,  # Override: US requires action plan for CONSIDERATION
            requires_final_approval=None,  # Inherit from base
            description="US regulations require action plan even for Consideration priority"
        )
        db_session.add(override)
        db_session.commit()
        db_session.refresh(override)

        assert override.override_id is not None
        assert override.requires_action_plan is True
        assert override.requires_final_approval is None

    def test_unique_constraint_priority_region(
        self, db_session, recommendation_taxonomies, multiple_regions
    ):
        """Cannot create duplicate override for same priority-region combination."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride
        from sqlalchemy.exc import IntegrityError

        override1 = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["low"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=False
        )
        db_session.add(override1)
        db_session.commit()

        override2 = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["low"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        db_session.add(override2)

        with pytest.raises(IntegrityError):
            db_session.commit()


def _generate_rec_code(db_session):
    """Generate a unique recommendation code for tests."""
    from app.models.recommendation import Recommendation
    count = db_session.query(Recommendation).count()
    return f"REC-TEST-{count + 1:05d}"


class TestRegionalOverrideLogic:
    """Test the regional override resolution logic in check_requires_action_plan."""

    def test_no_override_uses_base_config(
        self, db_session, recommendation_taxonomies, priority_configs, model_deployed_us, developer_user
    ):
        """When no regional override exists, use base priority config."""
        from app.models.recommendation import Recommendation
        from app.api.recommendations import check_requires_action_plan

        # CONSIDERATION base config has requires_action_plan=False
        target = date.today() + timedelta(days=30)
        rec = Recommendation(
            recommendation_code=_generate_rec_code(db_session),
            model_id=model_deployed_us.model_id,
            title="Test",
            description="Test",
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            current_status_id=recommendation_taxonomies["status"]["draft"].value_id,
            created_by_id=developer_user.user_id,
            assigned_to_id=developer_user.user_id,
            original_target_date=target,
            current_target_date=target
        )
        db_session.add(rec)
        db_session.commit()
        db_session.refresh(rec)

        # No regional override exists, so use base config (requires_action_plan=False)
        result = check_requires_action_plan(db_session, rec)
        assert result is False

    def test_regional_override_requires_action_plan(
        self, db_session, recommendation_taxonomies, priority_configs,
        model_deployed_us, multiple_regions, developer_user
    ):
        """Regional override can require action plan when base config doesn't."""
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.api.recommendations import check_requires_action_plan

        # Create US override requiring action plan for CONSIDERATION
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True,
            description="US requires action plan for all priorities"
        )
        db_session.add(us_override)
        db_session.commit()

        # Create CONSIDERATION recommendation for US-deployed model
        target = date.today() + timedelta(days=30)
        rec = Recommendation(
            recommendation_code=_generate_rec_code(db_session),
            model_id=model_deployed_us.model_id,
            title="Test",
            description="Test",
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            current_status_id=recommendation_taxonomies["status"]["draft"].value_id,
            created_by_id=developer_user.user_id,
            assigned_to_id=developer_user.user_id,
            original_target_date=target,
            current_target_date=target
        )
        db_session.add(rec)
        db_session.commit()
        db_session.refresh(rec)

        # US override should require action plan
        result = check_requires_action_plan(db_session, rec)
        assert result is True

    def test_most_restrictive_wins_multiple_regions(
        self, db_session, recommendation_taxonomies, priority_configs,
        model_deployed_us_emea, multiple_regions, developer_user
    ):
        """When model deployed in multiple regions, most restrictive override wins."""
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.api.recommendations import check_requires_action_plan

        # US override: requires action plan
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        # EMEA override: does NOT require action plan
        emea_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["emea"].region_id,
            requires_action_plan=False
        )
        db_session.add_all([us_override, emea_override])
        db_session.commit()

        # Model is deployed in both US and EMEA
        target = date.today() + timedelta(days=30)
        rec = Recommendation(
            recommendation_code=_generate_rec_code(db_session),
            model_id=model_deployed_us_emea.model_id,
            title="Test",
            description="Test",
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            current_status_id=recommendation_taxonomies["status"]["draft"].value_id,
            created_by_id=developer_user.user_id,
            assigned_to_id=developer_user.user_id,
            original_target_date=target,
            current_target_date=target
        )
        db_session.add(rec)
        db_session.commit()
        db_session.refresh(rec)

        # Most restrictive wins: US requires, so result is True
        result = check_requires_action_plan(db_session, rec)
        assert result is True

    def test_all_overrides_false_returns_false(
        self, db_session, recommendation_taxonomies, priority_configs,
        model_deployed_us_emea, multiple_regions, developer_user
    ):
        """When all applicable regional overrides say no action plan, return False."""
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.api.recommendations import check_requires_action_plan

        # Both regions explicitly don't require action plan
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["high"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=False
        )
        emea_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["high"].value_id,
            region_id=multiple_regions["emea"].region_id,
            requires_action_plan=False
        )
        db_session.add_all([us_override, emea_override])
        db_session.commit()

        # HIGH priority base config has requires_action_plan=True
        target = date.today() + timedelta(days=30)
        rec = Recommendation(
            recommendation_code=_generate_rec_code(db_session),
            model_id=model_deployed_us_emea.model_id,
            title="Test",
            description="Test",
            priority_id=recommendation_taxonomies["priority"]["high"].value_id,
            current_status_id=recommendation_taxonomies["status"]["draft"].value_id,
            created_by_id=developer_user.user_id,
            assigned_to_id=developer_user.user_id,
            original_target_date=target,
            current_target_date=target
        )
        db_session.add(rec)
        db_session.commit()
        db_session.refresh(rec)

        # All overrides say False, so result is False (even though base says True)
        result = check_requires_action_plan(db_session, rec)
        assert result is False

    def test_global_only_model_uses_base_config(
        self, db_session, recommendation_taxonomies, priority_configs,
        model_global_only, multiple_regions, developer_user
    ):
        """Model with no regional deployments uses base config only."""
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.api.recommendations import check_requires_action_plan

        # Create a US override (should be ignored for global-only model)
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        db_session.add(us_override)
        db_session.commit()

        # CONSIDERATION for global model (no regions)
        target = date.today() + timedelta(days=30)
        rec = Recommendation(
            recommendation_code=_generate_rec_code(db_session),
            model_id=model_global_only.model_id,
            title="Test",
            description="Test",
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            current_status_id=recommendation_taxonomies["status"]["draft"].value_id,
            created_by_id=developer_user.user_id,
            assigned_to_id=developer_user.user_id,
            original_target_date=target,
            current_target_date=target
        )
        db_session.add(rec)
        db_session.commit()
        db_session.refresh(rec)

        # Model has no regions, so US override is ignored; base config is False
        result = check_requires_action_plan(db_session, rec)
        assert result is False

    def test_null_override_inherits_from_base(
        self, db_session, recommendation_taxonomies, priority_configs,
        model_deployed_us, multiple_regions, developer_user
    ):
        """Override with NULL requires_action_plan inherits from base config."""
        from app.models.recommendation import Recommendation, RecommendationPriorityRegionalOverride
        from app.api.recommendations import check_requires_action_plan

        # US override with NULL (inherits from base)
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["high"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=None,  # Inherit
            requires_final_approval=False  # Only override final approval
        )
        db_session.add(us_override)
        db_session.commit()

        # HIGH priority base config has requires_action_plan=True
        target = date.today() + timedelta(days=30)
        rec = Recommendation(
            recommendation_code=_generate_rec_code(db_session),
            model_id=model_deployed_us.model_id,
            title="Test",
            description="Test",
            priority_id=recommendation_taxonomies["priority"]["high"].value_id,
            current_status_id=recommendation_taxonomies["status"]["draft"].value_id,
            created_by_id=developer_user.user_id,
            assigned_to_id=developer_user.user_id,
            original_target_date=target,
            current_target_date=target
        )
        db_session.add(rec)
        db_session.commit()
        db_session.refresh(rec)

        # NULL override is ignored for action_plan; base config is True
        result = check_requires_action_plan(db_session, rec)
        assert result is True


class TestRegionalOverrideAPI:
    """Test API endpoints for managing regional overrides."""

    def test_list_regional_overrides(
        self, client, admin_headers, db_session, recommendation_taxonomies, multiple_regions
    ):
        """Admin can list all regional overrides."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        # Create some overrides
        override1 = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        override2 = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["low"].value_id,
            region_id=multiple_regions["emea"].region_id,
            requires_action_plan=False
        )
        db_session.add_all([override1, override2])
        db_session.commit()

        response = client.get(
            "/recommendations/priority-config/regional-overrides/",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_create_regional_override(
        self, client, admin_headers, recommendation_taxonomies, multiple_regions, priority_configs
    ):
        """Admin can create a regional override."""
        response = client.post(
            "/recommendations/priority-config/regional-overrides/",
            headers=admin_headers,
            json={
                "priority_id": recommendation_taxonomies["priority"]["consideration"].value_id,
                "region_id": multiple_regions["us"].region_id,
                "requires_action_plan": True,
                "requires_final_approval": None,
                "description": "US requires action plan for Consideration"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["requires_action_plan"] is True
        assert data["region"]["region_id"] == multiple_regions["us"].region_id

    def test_update_regional_override(
        self, client, admin_headers, db_session, recommendation_taxonomies, multiple_regions
    ):
        """Admin can update a regional override."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        db_session.add(override)
        db_session.commit()
        db_session.refresh(override)

        response = client.patch(
            f"/recommendations/priority-config/regional-overrides/{override.override_id}",
            headers=admin_headers,
            json={"requires_action_plan": False, "description": "Updated"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_action_plan"] is False
        assert data["description"] == "Updated"

    def test_delete_regional_override(
        self, client, admin_headers, db_session, recommendation_taxonomies, multiple_regions
    ):
        """Admin can delete a regional override."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        db_session.add(override)
        db_session.commit()
        db_session.refresh(override)

        response = client.delete(
            f"/recommendations/priority-config/regional-overrides/{override.override_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify deleted
        deleted = db_session.query(RecommendationPriorityRegionalOverride).filter(
            RecommendationPriorityRegionalOverride.override_id == override.override_id
        ).first()
        assert deleted is None

    def test_non_admin_cannot_create_override(
        self, client, auth_headers, recommendation_taxonomies, multiple_regions, priority_configs
    ):
        """Non-admin users cannot create regional overrides."""
        response = client.post(
            "/recommendations/priority-config/regional-overrides/",
            headers=auth_headers,
            json={
                "priority_id": recommendation_taxonomies["priority"]["consideration"].value_id,
                "region_id": multiple_regions["us"].region_id,
                "requires_action_plan": True
            }
        )
        assert response.status_code == 403

    def test_list_overrides_for_specific_priority(
        self, client, admin_headers, db_session, recommendation_taxonomies, multiple_regions
    ):
        """Can list regional overrides for a specific priority."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        # Create overrides for different priorities
        consideration_us = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        consideration_emea = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["emea"].region_id,
            requires_action_plan=True
        )
        low_us = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["low"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=False
        )
        db_session.add_all([consideration_us, consideration_emea, low_us])
        db_session.commit()

        # Get only CONSIDERATION overrides
        response = client.get(
            f"/recommendations/priority-config/{recommendation_taxonomies['priority']['consideration'].value_id}/regional-overrides/",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # US and EMEA for CONSIDERATION


class TestCanSkipActionPlanWithRegionalOverride:
    """Test can-skip-action-plan endpoint with regional overrides."""

    def test_can_skip_action_plan_respects_regional_override(
        self, client, validator_headers, developer_headers, db_session,
        recommendation_taxonomies, priority_configs, model_deployed_us,
        multiple_regions, developer_user
    ):
        """can-skip-action-plan endpoint considers regional overrides."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        # Create US override requiring action plan for CONSIDERATION
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        db_session.add(us_override)
        db_session.commit()

        # Create CONSIDERATION recommendation for US-deployed model
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_deployed_us.model_id,
                "title": "Test",
                "description": "Test",
                "priority_id": recommendation_taxonomies["priority"]["consideration"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Check can-skip-action-plan
        response = client.get(
            f"/recommendations/{rec_id}/can-skip-action-plan",
            headers=developer_headers
        )
        assert response.status_code == 200
        data = response.json()
        # US override requires action plan, so can_skip should be False
        assert data["can_skip_action_plan"] is False
        assert data["requires_action_plan"] is True

    def test_skip_action_plan_blocked_by_regional_override(
        self, client, validator_headers, developer_headers, db_session,
        recommendation_taxonomies, priority_configs, model_deployed_us,
        multiple_regions, developer_user
    ):
        """skip-action-plan endpoint is blocked when regional override requires it."""
        from app.models.recommendation import RecommendationPriorityRegionalOverride

        # Create US override requiring action plan for CONSIDERATION
        us_override = RecommendationPriorityRegionalOverride(
            priority_id=recommendation_taxonomies["priority"]["consideration"].value_id,
            region_id=multiple_regions["us"].region_id,
            requires_action_plan=True
        )
        db_session.add(us_override)
        db_session.commit()

        # Create and submit CONSIDERATION recommendation for US-deployed model
        target_date = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": model_deployed_us.model_id,
                "title": "Test",
                "description": "Test",
                "priority_id": recommendation_taxonomies["priority"]["consideration"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]
        client.post(f"/recommendations/{rec_id}/submit", headers=validator_headers)

        # Attempt to skip action plan (should fail)
        response = client.post(
            f"/recommendations/{rec_id}/skip-action-plan",
            headers=developer_headers
        )
        assert response.status_code == 400
        assert "requires an action plan" in response.json()["detail"]


# ============================================================================
# DRAFT Visibility Tests - Recommendations in DRAFT status should not be
# visible to the assigned owner (validation team is still deciding)
# ============================================================================

class TestDraftVisibilityRestriction:
    """Test that DRAFT recommendations are hidden from non-validation team users."""

    def test_validator_can_see_draft_recommendation_in_list(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Validators can see DRAFT recommendations in the list."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        assert create_resp.status_code == 201
        rec_id = create_resp.json()["recommendation_id"]

        # Validator should see DRAFT in list
        list_resp = client.get("/recommendations/", headers=validator_headers)
        assert list_resp.status_code == 200
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id in rec_ids

    def test_validator_can_access_draft_recommendation_by_id(
        self, client, validator_headers, sample_model, developer_user, recommendation_taxonomies
    ):
        """Validators can access DRAFT recommendations by ID."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Validator should access DRAFT by ID
        get_resp = client.get(f"/recommendations/{rec_id}", headers=validator_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["current_status"]["code"] == "REC_DRAFT"

    def test_admin_can_see_draft_recommendation(
        self, client, admin_headers, validator_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Admins can see DRAFT recommendations."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Admin should see DRAFT in list
        list_resp = client.get("/recommendations/", headers=admin_headers)
        assert list_resp.status_code == 200
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id in rec_ids

        # Admin should access DRAFT by ID
        get_resp = client.get(f"/recommendations/{rec_id}", headers=admin_headers)
        assert get_resp.status_code == 200

    def test_developer_cannot_see_draft_recommendation_in_list(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Developers (assigned owners) cannot see DRAFT recommendations in list."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation assigned to developer
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Developer should NOT see DRAFT in list
        list_resp = client.get("/recommendations/", headers=developer_headers)
        assert list_resp.status_code == 200
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id not in rec_ids

    def test_developer_cannot_access_draft_recommendation_by_id(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Developers cannot access DRAFT recommendations by ID."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Developer should get 404 for DRAFT recommendation
        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        assert get_resp.status_code == 404

    def test_developer_can_see_recommendation_after_finalization(
        self, client, validator_headers, developer_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Developers can see recommendations once finalized (not DRAFT)."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Before finalization, developer cannot see
        list_resp = client.get("/recommendations/", headers=developer_headers)
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id not in rec_ids

        # Submit the recommendation (DRAFT -> PENDING_RESPONSE)
        submit_resp = client.post(
            f"/recommendations/{rec_id}/submit",
            headers=validator_headers
        )
        assert submit_resp.status_code == 200

        # After submission, developer should see in list
        list_resp = client.get("/recommendations/", headers=developer_headers)
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id in rec_ids

        # Developer should access by ID
        get_resp = client.get(f"/recommendations/{rec_id}", headers=developer_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["current_status"]["code"] == "REC_PENDING_RESPONSE"

    def test_model_owner_cannot_see_draft_recommendations_for_their_model(
        self, client, validator_headers, sample_model, test_user, auth_headers,
        developer_user, recommendation_taxonomies
    ):
        """Model owner (who is not the assigned_to) also cannot see DRAFT recommendations."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # test_user is the model owner, developer_user is assigned_to
        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Model owner should NOT see DRAFT in list (auth_headers is for test_user)
        list_resp = client.get("/recommendations/", headers=auth_headers)
        assert list_resp.status_code == 200
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id not in rec_ids

        # Model owner should get 404 for DRAFT recommendation
        get_resp = client.get(f"/recommendations/{rec_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_global_approver_can_see_draft_recommendation(
        self, client, validator_headers, global_approver_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Global Approvers can see DRAFT recommendations."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Global approver should see DRAFT in list
        list_resp = client.get("/recommendations/", headers=global_approver_headers)
        assert list_resp.status_code == 200
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id in rec_ids

        # Global approver should access DRAFT by ID
        get_resp = client.get(f"/recommendations/{rec_id}", headers=global_approver_headers)
        assert get_resp.status_code == 200

    def test_regional_approver_can_see_draft_recommendation(
        self, client, validator_headers, regional_approver_headers, sample_model,
        developer_user, recommendation_taxonomies
    ):
        """Regional Approvers can see DRAFT recommendations."""
        target_date = (date.today() + timedelta(days=30)).isoformat()

        # Create draft recommendation
        create_resp = client.post(
            "/recommendations/",
            headers=validator_headers,
            json={
                "model_id": sample_model.model_id,
                "title": "Draft Test",
                "description": "Draft recommendation for visibility test",
                "priority_id": recommendation_taxonomies["priority"]["medium"].value_id,
                "category_id": recommendation_taxonomies["category"]["data"].value_id,
                "assigned_to_id": developer_user.user_id,
                "original_target_date": target_date
            }
        )
        rec_id = create_resp.json()["recommendation_id"]

        # Regional approver should see DRAFT in list
        list_resp = client.get("/recommendations/", headers=regional_approver_headers)
        assert list_resp.status_code == 200
        rec_ids = [r["recommendation_id"] for r in list_resp.json()]
        assert rec_id in rec_ids

        # Regional approver should access DRAFT by ID
        get_resp = client.get(f"/recommendations/{rec_id}", headers=regional_approver_headers)
        assert get_resp.status_code == 200
