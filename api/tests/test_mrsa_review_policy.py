"""Tests for MRSA review policies and status tracking."""
from datetime import date, datetime, timedelta

import pytest

from app.core.mrsa_review_utils import calculate_mrsa_review_status
from app.schemas.mrsa_review_policy import MRSAReviewStatusEnum
from app.models import Model, Taxonomy, TaxonomyValue
from app.models.irp import IRP, IRPReview
from app.models.mrsa_review_policy import MRSAReviewPolicy, MRSAReviewException


def create_mrsa(
    db_session,
    owner_id: int,
    usage_frequency_id: int,
    risk_level: TaxonomyValue,
    created_at: datetime | None = None
) -> Model:
    """Create a minimal MRSA model for review status tests."""
    mrsa = Model(
        model_name="Test MRSA",
        description="MRSA for testing",
        development_type="In-House",
        status="Active",
        owner_id=owner_id,
        usage_frequency_id=usage_frequency_id,
        is_model=False,
        is_mrsa=True,
        mrsa_risk_level_id=risk_level.value_id,
        mrsa_risk_rationale="Test rationale",
        row_approval_status="approved"
    )
    if created_at:
        mrsa.created_at = created_at
    db_session.add(mrsa)
    db_session.commit()
    db_session.refresh(mrsa)
    return mrsa


@pytest.fixture
def mrsa_risk_levels(db_session):
    """Create MRSA Risk Level taxonomy values."""
    taxonomy = Taxonomy(name="MRSA Risk Level", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    high_risk = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="HIGH_RISK",
        label="High-Risk",
        sort_order=1,
        requires_irp=True
    )
    low_risk = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="LOW_RISK",
        label="Low-Risk",
        sort_order=2,
        requires_irp=False
    )
    db_session.add_all([high_risk, low_risk])
    db_session.commit()
    return {"high": high_risk, "low": low_risk}


@pytest.fixture
def irp_review_outcome(db_session):
    """Create a taxonomy value for IRP review outcomes."""
    taxonomy = Taxonomy(name="IRP Review Outcome", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()
    outcome = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="SATISFACTORY",
        label="Satisfactory",
        sort_order=1
    )
    db_session.add(outcome)
    db_session.commit()
    return outcome


class TestMRSAReviewStatusCalculation:
    """Unit tests for MRSA review status calculation."""

    def test_no_policy_returns_no_requirement(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["high"]
        )
        status, next_due, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=None,
            exception=None,
            latest_irp_review_date=None,
            today=date(2025, 1, 15)
        )

        assert status == MRSAReviewStatusEnum.NO_REQUIREMENT
        assert next_due is None
        assert days_until_due is None

    def test_requires_irp_without_coverage_returns_no_irp(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["high"].value_id,
            frequency_months=24,
            initial_review_months=3,
            warning_days=90,
            is_active=True
        )
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["high"]
        )

        status, next_due, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=None,
            latest_irp_review_date=None,
            today=date(2025, 1, 15)
        )

        assert status == MRSAReviewStatusEnum.NO_IRP
        assert next_due is None
        assert days_until_due is None

    def test_never_reviewed_before_due_returns_never_reviewed(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["low"].value_id,
            frequency_months=24,
            initial_review_months=3,
            warning_days=90,
            is_active=True
        )
        today = date(2025, 1, 15)
        created_at = datetime.combine(
            today - timedelta(days=policy.initial_review_months * 30 - 10),
            datetime.min.time()
        )
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["low"],
            created_at=created_at
        )

        status, next_due, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=None,
            latest_irp_review_date=None,
            today=today
        )

        assert status == MRSAReviewStatusEnum.NEVER_REVIEWED
        assert next_due is not None
        assert days_until_due == 10

    def test_never_reviewed_past_due_returns_overdue(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["low"].value_id,
            frequency_months=24,
            initial_review_months=3,
            warning_days=90,
            is_active=True
        )
        today = date(2025, 1, 15)
        created_at = datetime.combine(
            today - timedelta(days=policy.initial_review_months * 30 + 10),
            datetime.min.time()
        )
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["low"],
            created_at=created_at
        )

        status, next_due, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=None,
            latest_irp_review_date=None,
            today=today
        )

        assert status == MRSAReviewStatusEnum.OVERDUE
        assert next_due is not None
        assert days_until_due == -10

    def test_upcoming_status_when_due_within_warning_window(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["low"].value_id,
            frequency_months=12,
            initial_review_months=3,
            warning_days=30,
            is_active=True
        )
        today = date(2025, 1, 15)
        latest_review_date = today - timedelta(days=policy.frequency_months * 30 - 5)
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["low"]
        )

        status, next_due, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=None,
            latest_irp_review_date=latest_review_date,
            today=today
        )

        assert status == MRSAReviewStatusEnum.UPCOMING
        assert days_until_due == 5
        assert next_due == today + timedelta(days=5)

    def test_overdue_status_when_past_due(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["low"].value_id,
            frequency_months=12,
            initial_review_months=3,
            warning_days=30,
            is_active=True
        )
        today = date(2025, 1, 15)
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["low"]
        )

        overdue_review_date = today - timedelta(days=policy.frequency_months * 30 + 5)
        status, _, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=None,
            latest_irp_review_date=overdue_review_date,
            today=today
        )
        assert status == MRSAReviewStatusEnum.OVERDUE
        assert days_until_due == -5

    def test_exception_override_sets_next_due_date(
        self, db_session, admin_user, usage_frequency, mrsa_risk_levels
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["low"].value_id,
            frequency_months=12,
            initial_review_months=3,
            warning_days=30,
            is_active=True
        )
        today = date(2025, 1, 15)
        exception_due = today + timedelta(days=120)
        exception = MRSAReviewException(
            mrsa_id=1,
            override_due_date=exception_due,
            reason="Test exception",
            approved_by_id=1,
            is_active=True
        )
        mrsa = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["low"]
        )

        status, next_due, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=exception,
            latest_irp_review_date=today - timedelta(days=400),
            today=today
        )

        assert status == MRSAReviewStatusEnum.CURRENT
        assert next_due == exception_due
        assert days_until_due == 120


class TestMRSAReviewPolicyAPI:
    """API tests for MRSA review policy endpoints."""

    def test_admin_can_crud_policy(self, client, admin_headers, mrsa_risk_levels):
        payload = {
            "mrsa_risk_level_id": mrsa_risk_levels["high"].value_id,
            "frequency_months": 24,
            "initial_review_months": 3,
            "warning_days": 90,
            "is_active": True
        }

        create_response = client.post("/mrsa-review-policies/", json=payload, headers=admin_headers)
        assert create_response.status_code == 201
        policy_id = create_response.json()["policy_id"]

        update_response = client.patch(
            f"/mrsa-review-policies/{policy_id}",
            json={"frequency_months": 18},
            headers=admin_headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["frequency_months"] == 18

        list_response = client.get("/mrsa-review-policies/", headers=admin_headers)
        assert list_response.status_code == 200
        assert any(policy["policy_id"] == policy_id for policy in list_response.json())

        get_response = client.get(f"/mrsa-review-policies/{policy_id}", headers=admin_headers)
        assert get_response.status_code == 200

        delete_response = client.delete(f"/mrsa-review-policies/{policy_id}", headers=admin_headers)
        assert delete_response.status_code == 204

        missing_response = client.get(f"/mrsa-review-policies/{policy_id}", headers=admin_headers)
        assert missing_response.status_code == 404

    def test_non_admin_cannot_create_policy(self, client, auth_headers, mrsa_risk_levels):
        payload = {
            "mrsa_risk_level_id": mrsa_risk_levels["high"].value_id,
            "frequency_months": 24,
            "initial_review_months": 3,
            "warning_days": 90,
            "is_active": True
        }
        response = client.post("/mrsa-review-policies/", json=payload, headers=auth_headers)
        assert response.status_code == 403


class TestMRSAReviewStatusEndpoint:
    """API tests for MRSA review status endpoint."""

    def test_review_status_endpoint_returns_expected_statuses(
        self,
        client,
        admin_headers,
        db_session,
        admin_user,
        usage_frequency,
        mrsa_risk_levels,
        irp_review_outcome
    ):
        policy = MRSAReviewPolicy(
            mrsa_risk_level_id=mrsa_risk_levels["high"].value_id,
            frequency_months=24,
            initial_review_months=3,
            warning_days=90,
            is_active=True
        )
        db_session.add(policy)
        db_session.commit()

        mrsa_no_irp = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["high"]
        )
        mrsa_with_review = create_mrsa(
            db_session,
            admin_user.user_id,
            usage_frequency["daily"].value_id,
            mrsa_risk_levels["high"]
        )

        irp = IRP(
            process_name="Test IRP",
            contact_user_id=admin_user.user_id,
            description="Test IRP"
        )
        irp.covered_mrsas.append(mrsa_with_review)
        db_session.add(irp)
        db_session.flush()

        review_date = date.today()
        review = IRPReview(
            irp_id=irp.irp_id,
            review_date=review_date,
            outcome_id=irp_review_outcome.value_id,
            reviewed_by_user_id=admin_user.user_id
        )
        db_session.add(review)
        db_session.commit()

        response = client.get("/irps/mrsa-review-status", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        status_by_id = {item["mrsa_id"]: item for item in data}

        assert status_by_id[mrsa_no_irp.model_id]["status"] == "NO_IRP"
        assert status_by_id[mrsa_with_review.model_id]["status"] == "CURRENT"
        assert status_by_id[mrsa_with_review.model_id]["last_review_date"] == review_date.isoformat()
        assert status_by_id[mrsa_with_review.model_id]["owner"]["user_id"] == admin_user.user_id


class TestMRSAReviewIntegration:
    """Integration test for policy + MRSA + IRP review workflow."""

    def test_full_mrsa_review_flow(
        self,
        client,
        admin_headers,
        db_session,
        admin_user,
        usage_frequency,
        mrsa_risk_levels,
        irp_review_outcome
    ):
        policy_payload = {
            "mrsa_risk_level_id": mrsa_risk_levels["high"].value_id,
            "frequency_months": 24,
            "initial_review_months": 3,
            "warning_days": 90,
            "is_active": True
        }
        policy_response = client.post("/mrsa-review-policies/", json=policy_payload, headers=admin_headers)
        assert policy_response.status_code == 201

        model_payload = {
            "model_name": "Integration MRSA",
            "description": "Integration MRSA",
            "development_type": "In-House",
            "status": "Active",
            "owner_id": admin_user.user_id,
            "usage_frequency_id": usage_frequency["daily"].value_id,
            "is_model": False,
            "is_mrsa": True,
            "mrsa_risk_level_id": mrsa_risk_levels["high"].value_id,
            "mrsa_risk_rationale": "High risk due to critical use"
        }
        model_response = client.post("/models/", json=model_payload, headers=admin_headers)
        assert model_response.status_code == 201
        mrsa_id = model_response.json()["model_id"]

        irp_payload = {
            "process_name": "Integration IRP",
            "contact_user_id": admin_user.user_id,
            "description": "Integration IRP",
            "mrsa_ids": [mrsa_id]
        }
        irp_response = client.post("/irps/", json=irp_payload, headers=admin_headers)
        assert irp_response.status_code == 201
        irp_id = irp_response.json()["irp_id"]

        review_date = date.today()
        review_payload = {
            "review_date": review_date.isoformat(),
            "outcome_id": irp_review_outcome.value_id,
            "notes": "Initial review"
        }
        review_response = client.post(f"/irps/{irp_id}/reviews", json=review_payload, headers=admin_headers)
        assert review_response.status_code == 201

        status_response = client.get("/irps/mrsa-review-status", headers=admin_headers)
        assert status_response.status_code == 200
        status_map = {item["mrsa_id"]: item for item in status_response.json()}
        assert status_map[mrsa_id]["status"] == "CURRENT"
        assert status_map[mrsa_id]["last_review_date"] == review_date.isoformat()
        assert status_map[mrsa_id]["next_due_date"] is not None
