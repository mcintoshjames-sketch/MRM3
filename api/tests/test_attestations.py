"""Tests for attestation workflow endpoints."""
import pytest
from datetime import date, timedelta
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model import Model
from app.models.region import Region
from app.models.attestation import (
    AttestationCycle,
    AttestationCycleStatus,
    AttestationRecord,
    AttestationRecordStatus,
    AttestationEvidence,
    AttestationSchedulingRule,
    AttestationSchedulingRuleType,
    AttestationFrequency,
    CoverageTarget,
    AttestationQuestionConfig,
)


@pytest.fixture
def attestation_taxonomy(db_session):
    """Create attestation-related taxonomies and question configs."""
    # Create Attestation Question taxonomy
    question_tax = Taxonomy(name="Attestation Question", is_system=True)
    db_session.add(question_tax)
    db_session.flush()

    # Create question values
    q1 = TaxonomyValue(
        taxonomy_id=question_tax.taxonomy_id,
        code="ATT_Q1_COMPLIANCE",
        label="Policy Compliance",
        description="Attest models comply with Model Risk Policy",
        sort_order=1
    )
    q2 = TaxonomyValue(
        taxonomy_id=question_tax.taxonomy_id,
        code="ATT_Q2_AWARENESS",
        label="Model Awareness",
        description="Made Model Validation aware of all models",
        sort_order=2
    )
    db_session.add_all([q1, q2])
    db_session.flush()

    # Create question configs
    config1 = AttestationQuestionConfig(
        question_value_id=q1.value_id,
        frequency_scope="BOTH",
        requires_comment_if_no=True
    )
    config2 = AttestationQuestionConfig(
        question_value_id=q2.value_id,
        frequency_scope="ANNUAL",  # Only for annual attestations
        requires_comment_if_no=False
    )
    db_session.add_all([config1, config2])
    db_session.commit()

    return {
        "taxonomy": question_tax,
        "q1": q1,
        "q2": q2,
        "config1": config1,
        "config2": config2
    }


@pytest.fixture
def attestation_cycle(db_session, admin_user):
    """Create a test attestation cycle."""
    cycle = AttestationCycle(
        cycle_name="Q4 2024 Attestation",
        period_start_date=date.today() - timedelta(days=30),
        period_end_date=date.today() + timedelta(days=60),
        submission_due_date=date.today() + timedelta(days=30),
        status=AttestationCycleStatus.PENDING.value,
        notes="Test cycle"
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


@pytest.fixture
def scheduling_rule(db_session, admin_user):
    """Create a global default scheduling rule."""
    rule = AttestationSchedulingRule(
        rule_name="Global Default",
        rule_type=AttestationSchedulingRuleType.GLOBAL_DEFAULT.value,
        frequency=AttestationFrequency.ANNUAL.value,
        priority=1,
        is_active=True,
        effective_date=date.today() - timedelta(days=365),
        created_by_user_id=admin_user.user_id
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


class TestAttestationCycles:
    """Tests for attestation cycle management."""

    def test_create_cycle_admin_only(self, client, admin_headers, auth_headers):
        """Only admins can create cycles."""
        cycle_data = {
            "cycle_name": "Test Cycle",
            "period_start_date": str(date.today()),
            "period_end_date": str(date.today() + timedelta(days=90)),
            "submission_due_date": str(date.today() + timedelta(days=60)),
        }

        # Admin can create
        response = client.post("/attestations/cycles", json=cycle_data, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["cycle_name"] == "Test Cycle"
        assert response.json()["status"] == "PENDING"

        # Regular user cannot
        response = client.post("/attestations/cycles", json=cycle_data, headers=auth_headers)
        assert response.status_code == 403

    def test_list_cycles(self, client, admin_headers, attestation_cycle):
        """Can list attestation cycles."""
        response = client.get("/attestations/cycles", headers=admin_headers)
        assert response.status_code == 200
        cycles = response.json()
        assert len(cycles) >= 1
        assert any(c["cycle_id"] == attestation_cycle.cycle_id for c in cycles)

    def test_open_cycle(self, client, admin_headers, attestation_cycle, sample_model, scheduling_rule, db_session):
        """Opening a cycle generates attestation records."""
        # Make sample_model approved so it's included
        sample_model.row_approval_status = None
        db_session.commit()

        response = client.post(
            f"/attestations/cycles/{attestation_cycle.cycle_id}/open",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "OPEN"

    def test_open_cycle_sets_applied_frequency(self, client, admin_headers, attestation_cycle, sample_model, scheduling_rule, db_session):
        """Opening a cycle stamps the applied rule/frequency on records."""
        sample_model.row_approval_status = None
        sample_model.status = "Active"
        db_session.commit()

        response = client.post(
            f"/attestations/cycles/{attestation_cycle.cycle_id}/open",
            headers=admin_headers
        )
        assert response.status_code == 200

        record = db_session.query(AttestationRecord).filter(
            AttestationRecord.cycle_id == attestation_cycle.cycle_id,
            AttestationRecord.model_id == sample_model.model_id
        ).first()
        assert record is not None
        assert record.applied_frequency == AttestationFrequency.ANNUAL.value
        assert record.applied_rule_id == scheduling_rule.rule_id

    def test_model_override_precedence_over_global_default(self, client, admin_headers, admin_user, attestation_cycle, sample_model, scheduling_rule, db_session):
        """Model Override rules should win over Global Default regardless of priority."""
        sample_model.row_approval_status = None
        sample_model.status = "Active"
        scheduling_rule.priority = 100
        db_session.commit()

        model_override = AttestationSchedulingRule(
            rule_name="Critical Model Override",
            rule_type=AttestationSchedulingRuleType.MODEL_OVERRIDE.value,
            frequency=AttestationFrequency.QUARTERLY.value,
            priority=1,
            is_active=True,
            model_id=sample_model.model_id,
            effective_date=date.today() - timedelta(days=10),
            created_by_user_id=admin_user.user_id
        )
        db_session.add(model_override)
        db_session.commit()
        db_session.refresh(model_override)

        response = client.post(
            f"/attestations/cycles/{attestation_cycle.cycle_id}/open",
            headers=admin_headers
        )
        assert response.status_code == 200

        record = db_session.query(AttestationRecord).filter(
            AttestationRecord.cycle_id == attestation_cycle.cycle_id,
            AttestationRecord.model_id == sample_model.model_id
        ).first()
        assert record is not None
        assert record.applied_rule_id == model_override.rule_id
        assert record.applied_frequency == AttestationFrequency.QUARTERLY.value

    def test_cannot_update_open_cycle(self, client, admin_headers, attestation_cycle, db_session):
        """Cannot update cycle after it's opened."""
        # Open the cycle
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        update_data = {"cycle_name": "Updated Name"}
        response = client.patch(
            f"/attestations/cycles/{attestation_cycle.cycle_id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "opened" in response.json()["detail"].lower()


class TestAttestationQuestions:
    """Tests for attestation question endpoints."""

    def test_list_questions(self, client, admin_headers, attestation_taxonomy):
        """Can list attestation questions."""
        response = client.get("/attestations/questions", headers=admin_headers)
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) >= 2

    def test_filter_questions_by_frequency(self, client, admin_headers, attestation_taxonomy):
        """Questions filter by frequency scope."""
        # q1 is BOTH, q2 is ANNUAL only

        # All questions
        response = client.get("/attestations/questions", headers=admin_headers)
        all_questions = response.json()

        # Annual questions (should include q1 BOTH and q2 ANNUAL)
        response = client.get("/attestations/questions?frequency=ANNUAL", headers=admin_headers)
        annual_questions = response.json()
        assert len(annual_questions) == 2

        # Quarterly questions (should include only q1 BOTH)
        response = client.get("/attestations/questions?frequency=QUARTERLY", headers=admin_headers)
        quarterly_questions = response.json()
        assert len(quarterly_questions) == 1
        assert quarterly_questions[0]["code"] == "ATT_Q1_COMPLIANCE"


class TestEvidenceEndpoints:
    """Tests for evidence management endpoints."""

    def test_add_evidence_requires_valid_url(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Evidence URL must start with http:// or https://."""
        # Create an attestation record
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        # Invalid URL
        response = client.post(
            f"/attestations/records/{record.attestation_id}/evidence",
            json={
                "evidence_type": "OTHER",
                "url": "ftp://example.com/file.pdf",
                "description": "Test evidence"
            },
            headers=admin_headers
        )
        assert response.status_code == 422  # Validation error

        # Valid URL
        response = client.post(
            f"/attestations/records/{record.attestation_id}/evidence",
            json={
                "evidence_type": "OTHER",
                "url": "https://example.com/file.pdf",
                "description": "Test evidence"
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["url"] == "https://example.com/file.pdf"

    def test_remove_evidence(self, client, admin_headers, attestation_cycle, sample_model, admin_user, db_session):
        """Can remove evidence from attestation."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.flush()

        evidence = AttestationEvidence(
            attestation_id=record.attestation_id,
            evidence_type="OTHER",
            url="https://example.com/doc.pdf",
            description="Test doc",
            added_by_user_id=admin_user.user_id
        )
        db_session.add(evidence)
        db_session.commit()
        db_session.refresh(evidence)

        # Remove evidence
        response = client.delete(
            f"/attestations/evidence/{evidence.evidence_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert "removed" in response.json()["message"].lower()

    def test_cannot_remove_evidence_from_accepted(self, client, admin_headers, attestation_cycle, sample_model, admin_user, db_session):
        """Cannot remove evidence from accepted attestation."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.ACCEPTED.value  # Already accepted
        )
        db_session.add(record)
        db_session.flush()

        evidence = AttestationEvidence(
            attestation_id=record.attestation_id,
            evidence_type="OTHER",
            url="https://example.com/doc.pdf",
            description="Test doc",
            added_by_user_id=admin_user.user_id
        )
        db_session.add(evidence)
        db_session.commit()
        db_session.refresh(evidence)

        # Try to remove
        response = client.delete(
            f"/attestations/evidence/{evidence.evidence_id}",
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "accepted" in response.json()["detail"].lower()


class TestAttestationSubmission:
    """Tests for attestation submission workflow."""

    def test_submit_attestation_validates_decision(self, client, auth_headers, attestation_cycle, attestation_taxonomy, sample_model, test_user, scheduling_rule, db_session):
        """Submission validates decision type."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=test_user.user_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        q1 = attestation_taxonomy["q1"]
        q2 = attestation_taxonomy["q2"]

        # Submit with I_ATTEST (all yes) - should work
        submission = {
            "decision": "I_ATTEST",
            "decision_comment": None,
            "responses": [
                {"question_id": q1.value_id, "answer": True, "comment": None},
                {"question_id": q2.value_id, "answer": True, "comment": None}
            ],
            "evidence": []
        }

        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json=submission,
            headers=auth_headers
        )
        assert response.status_code == 200
        # Clean attestations (all yes, no comments) are auto-accepted
        assert response.json()["status"] == "ACCEPTED"

    def test_submit_requires_comment_for_no_answer(self, client, auth_headers, attestation_cycle, attestation_taxonomy, sample_model, test_user, scheduling_rule, db_session):
        """Questions with requires_comment_if_no need comments when answered No."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=test_user.user_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        q1 = attestation_taxonomy["q1"]  # requires_comment_if_no = True
        q2 = attestation_taxonomy["q2"]  # requires_comment_if_no = False

        # Answer q1 as No without comment - should fail
        submission = {
            "decision": "I_ATTEST_WITH_UPDATES",
            "decision_comment": "Some changes needed",
            "responses": [
                {"question_id": q1.value_id, "answer": False, "comment": None},  # No comment!
                {"question_id": q2.value_id, "answer": True, "comment": None}
            ],
            "evidence": []
        }

        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json=submission,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "comment required" in response.json()["detail"].lower()

        # Add comment - should succeed
        submission["responses"][0]["comment"] = "Explanation for No answer"
        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json=submission,
            headers=auth_headers
        )
        assert response.status_code == 200


class TestAttestationReview:
    """Tests for admin attestation review."""

    def test_accept_attestation(self, client, admin_headers, attestation_cycle, sample_model, admin_user, db_session):
        """Admin can accept submitted attestation."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.SUBMITTED.value
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        response = client.post(
            f"/attestations/records/{record.attestation_id}/accept",
            json={"review_comment": "Looks good"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ACCEPTED"

    def test_reject_requires_comment(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Rejecting attestation requires a comment."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.SUBMITTED.value
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        # Reject without comment
        response = client.post(
            f"/attestations/records/{record.attestation_id}/reject",
            json={"review_comment": None},
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "comment required" in response.json()["detail"].lower()

        # Reject with comment
        response = client.post(
            f"/attestations/records/{record.attestation_id}/reject",
            json={"review_comment": "Missing documentation"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

    def test_resubmit_after_rejection(self, client, auth_headers, admin_headers, attestation_cycle, sample_model, attestation_taxonomy, db_session):
        """User can resubmit attestation after admin rejection."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        # Create a record in REJECTED status (simulating already rejected attestation)
        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.REJECTED.value,
            review_comment="Please provide more detail"
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        # Get questions for submission
        q1 = attestation_taxonomy["q1"]
        q2 = attestation_taxonomy["q2"]

        # Resubmit with updated response
        submission = {
            "decision": "I_ATTEST",
            "decision_comment": "I Attest",
            "responses": [
                {"question_id": q1.value_id, "answer": True, "comment": None},
                {"question_id": q2.value_id, "answer": True, "comment": None}
            ],
            "evidence": []
        }

        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json=submission,
            headers=auth_headers
        )
        assert response.status_code == 200
        # Resubmission should succeed - may go to SUBMITTED or ACCEPTED depending on auto-accept logic
        assert response.json()["status"] in ["SUBMITTED", "ACCEPTED"]

    def test_only_admin_can_review(self, client, auth_headers, admin_headers, attestation_cycle, sample_model, db_session):
        """Only admin can accept/reject attestations."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.SUBMITTED.value
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        # Regular user cannot accept
        response = client.post(
            f"/attestations/records/{record.attestation_id}/accept",
            json={"review_comment": "Test"},
            headers=auth_headers
        )
        assert response.status_code == 403


class TestSchedulingRules:
    """Tests for attestation scheduling rules."""

    def test_create_scheduling_rule(self, client, admin_headers):
        """Admin can create scheduling rules."""
        rule_data = {
            "rule_name": "High Volume Owners",
            "rule_type": "OWNER_THRESHOLD",
            "frequency": "QUARTERLY",
            "priority": 100,
            "is_active": True,
            "owner_model_count_min": 30,
            "effective_date": str(date.today())
        }

        response = client.post("/attestations/rules", json=rule_data, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["rule_name"] == "High Volume Owners"
        assert response.json()["frequency"] == "QUARTERLY"

    def test_model_override_requires_model_id(self, client, admin_headers):
        """MODEL_OVERRIDE rules require a model_id."""
        rule_data = {
            "rule_name": "Critical Model Override",
            "rule_type": "MODEL_OVERRIDE",
            "frequency": "QUARTERLY",
            "priority": 50,
            "is_active": True,
            "effective_date": str(date.today())
        }

        response = client.post("/attestations/rules", json=rule_data, headers=admin_headers)
        assert response.status_code == 400

    def test_prevent_overlapping_model_override_rules(self, client, admin_headers, sample_model):
        """Cannot create overlapping MODEL_OVERRIDE rules for the same model."""
        rule_data = {
            "rule_name": "Model Override A",
            "rule_type": "MODEL_OVERRIDE",
            "frequency": "QUARTERLY",
            "priority": 50,
            "is_active": True,
            "model_id": sample_model.model_id,
            "effective_date": str(date.today() - timedelta(days=30))
        }
        response = client.post("/attestations/rules", json=rule_data, headers=admin_headers)
        assert response.status_code == 200

        overlap_data = {
            "rule_name": "Model Override B",
            "rule_type": "MODEL_OVERRIDE",
            "frequency": "ANNUAL",
            "priority": 60,
            "is_active": True,
            "model_id": sample_model.model_id,
            "effective_date": str(date.today() - timedelta(days=10))
        }
        response = client.post("/attestations/rules", json=overlap_data, headers=admin_headers)
        assert response.status_code == 400

    def test_prevent_overlapping_regional_override_rules(self, client, admin_headers, db_session):
        """Cannot create overlapping REGIONAL_OVERRIDE rules for the same region."""
        region = Region(code="NA", name="North America", requires_regional_approval=False)
        db_session.add(region)
        db_session.commit()
        db_session.refresh(region)

        rule_data = {
            "rule_name": "Regional Override A",
            "rule_type": "REGIONAL_OVERRIDE",
            "frequency": "QUARTERLY",
            "priority": 50,
            "is_active": True,
            "region_id": region.region_id,
            "effective_date": str(date.today() - timedelta(days=30))
        }
        response = client.post("/attestations/rules", json=rule_data, headers=admin_headers)
        assert response.status_code == 200

        overlap_data = {
            "rule_name": "Regional Override B",
            "rule_type": "REGIONAL_OVERRIDE",
            "frequency": "ANNUAL",
            "priority": 60,
            "is_active": True,
            "region_id": region.region_id,
            "effective_date": str(date.today() - timedelta(days=10))
        }
        response = client.post("/attestations/rules", json=overlap_data, headers=admin_headers)
        assert response.status_code == 400

    def test_prevent_multiple_active_global_default_rules(self, client, admin_headers, scheduling_rule, db_session, admin_user):
        """Cannot activate a second GLOBAL_DEFAULT rule when one is already active."""
        secondary_rule = AttestationSchedulingRule(
            rule_name="Secondary Global Default",
            rule_type=AttestationSchedulingRuleType.GLOBAL_DEFAULT.value,
            frequency=AttestationFrequency.ANNUAL.value,
            priority=2,
            is_active=False,
            effective_date=date.today(),
            created_by_user_id=admin_user.user_id
        )
        db_session.add(secondary_rule)
        db_session.commit()
        db_session.refresh(secondary_rule)

        response = client.patch(
            f"/attestations/rules/{secondary_rule.rule_id}",
            json={"is_active": True},
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "GLOBAL_DEFAULT" in response.json()["detail"]

    def test_deactivate_rule(self, client, admin_headers, scheduling_rule):
        """Can deactivate a scheduling rule."""
        response = client.delete(
            f"/attestations/rules/{scheduling_rule.rule_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()


class TestDashboardEndpoints:
    """Tests for attestation dashboard."""

    def test_dashboard_stats(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Admin can get dashboard stats."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        # Add some records
        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/attestations/dashboard/stats", headers=admin_headers)
        assert response.status_code == 200
        stats = response.json()
        assert "pending_count" in stats
        assert "submitted_count" in stats
        assert "overdue_count" in stats
        assert "active_cycles" in stats


class TestLinkedChanges:
    """Tests for attestation linked changes (lightweight tracking)."""

    def test_create_model_edit_link(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Can create a MODEL_EDIT change link."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        # Create attestation record
        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/attestations/records/{record.attestation_id}/link-change",
            json={
                "change_type": "MODEL_EDIT",
                "model_id": sample_model.model_id
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "MODEL_EDIT"
        assert data["model"]["model_id"] == sample_model.model_id

    def test_create_new_model_link(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Can create a NEW_MODEL change link."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/attestations/records/{record.attestation_id}/link-change",
            json={
                "change_type": "NEW_MODEL",
                "model_id": sample_model.model_id  # Link to newly created model
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "NEW_MODEL"

    def test_create_decommission_link(self, client, admin_headers, attestation_cycle, sample_model, test_user, db_session):
        """Can create a DECOMMISSION change link."""
        from app.models.decommissioning import DecommissioningRequest
        from datetime import date

        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        # Create decommission reason taxonomy
        reason_taxonomy = Taxonomy(
            name="Model Decommission Reason",
            description="Reasons for decommissioning"
        )
        db_session.add(reason_taxonomy)
        db_session.flush()

        reason_value = TaxonomyValue(
            taxonomy_id=reason_taxonomy.taxonomy_id,
            code="OBSOLETE",
            label="Model Obsolete",
            sort_order=1
        )
        db_session.add(reason_value)
        db_session.flush()

        # Create a decommissioning request
        decom_request = DecommissioningRequest(
            model_id=sample_model.model_id,
            reason_id=reason_value.value_id,
            last_production_date=date.today(),
            archive_location="/archive/test",
            created_by_id=test_user.user_id
        )
        db_session.add(decom_request)
        db_session.flush()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/attestations/records/{record.attestation_id}/link-change",
            json={
                "change_type": "DECOMMISSION",
                "model_id": sample_model.model_id,
                "decommissioning_request_id": decom_request.request_id
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "DECOMMISSION"
        assert data["decommissioning_request_id"] == decom_request.request_id

    def test_get_linked_changes(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Can get linked changes for an attestation record."""
        from app.models.attestation import AttestationChangeLink

        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.flush()

        link = AttestationChangeLink(
            attestation_id=record.attestation_id,
            change_type="MODEL_EDIT",
            model_id=sample_model.model_id
        )
        db_session.add(link)
        db_session.commit()

        response = client.get(
            f"/attestations/records/{record.attestation_id}/linked-changes",
            headers=admin_headers
        )
        assert response.status_code == 200
        links = response.json()
        assert len(links) >= 1
        assert links[0]["change_type"] == "MODEL_EDIT"

    def test_cannot_link_changes_to_accepted_attestation(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Cannot add change links to accepted attestations."""
        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=sample_model.owner_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.ACCEPTED.value  # Already accepted
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/attestations/records/{record.attestation_id}/link-change",
            json={
                "change_type": "MODEL_EDIT",
                "model_id": sample_model.model_id
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "accepted" in response.json()["detail"].lower()

    def test_linked_changes_prevent_auto_accept(self, client, auth_headers, attestation_cycle, attestation_taxonomy, sample_model, test_user, scheduling_rule, db_session):
        """Attestations with linked changes should NOT be auto-accepted even if all answers are Yes."""
        from app.models.attestation import AttestationChangeLink

        attestation_cycle.status = AttestationCycleStatus.OPEN.value
        db_session.commit()

        # Create attestation record
        record = AttestationRecord(
            cycle_id=attestation_cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=test_user.user_id,
            due_date=attestation_cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.flush()

        # Create a linked change (MODEL_EDIT)
        link = AttestationChangeLink(
            attestation_id=record.attestation_id,
            change_type="MODEL_EDIT",
            model_id=sample_model.model_id
        )
        db_session.add(link)
        db_session.commit()
        db_session.refresh(record)

        # Submit with all "Yes" answers and no comments (would normally auto-accept)
        q1 = attestation_taxonomy["q1"]
        q2 = attestation_taxonomy["q2"]
        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json={
                "decision": "I_ATTEST",
                "decision_comment": None,
                "responses": [
                    {"question_id": q1.value_id, "answer": True, "comment": None},
                    {"question_id": q2.value_id, "answer": True, "comment": None}
                ],
                "evidence": []
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should be SUBMITTED, not ACCEPTED, because there are linked changes
        assert data["status"] == "SUBMITTED", "Attestation with linked changes should not be auto-accepted"


class TestBulkAttestation:
    """Tests for bulk attestation workflow."""

    @pytest.fixture
    def open_cycle_with_records(self, db_session, admin_user, test_user, sample_model, scheduling_rule):
        """Create an open cycle with attestation records for test_user."""
        from app.models.attestation import AttestationBulkSubmission, AttestationBulkSubmissionStatus

        # Clear any row_approval_status so the model is active
        sample_model.row_approval_status = None
        db_session.commit()

        cycle = AttestationCycle(
            cycle_name="Bulk Test Cycle",
            period_start_date=date.today() - timedelta(days=30),
            period_end_date=date.today() + timedelta(days=60),
            submission_due_date=date.today() + timedelta(days=30),
            status=AttestationCycleStatus.OPEN.value,
            notes="Test cycle for bulk attestation"
        )
        db_session.add(cycle)
        db_session.flush()

        # Create attestation record for sample_model (owned by test_user)
        record = AttestationRecord(
            cycle_id=cycle.cycle_id,
            model_id=sample_model.model_id,
            attesting_user_id=test_user.user_id,
            due_date=cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record)
        db_session.commit()

        return {
            "cycle": cycle,
            "record": record,
            "model": sample_model
        }

    def test_draft_validation_rejects_invalid_model_ids(
        self, client, auth_headers, open_cycle_with_records, db_session
    ):
        """Draft save rejects model IDs not available for attestation."""
        cycle = open_cycle_with_records["cycle"]

        # Try to save draft with invalid model ID
        response = client.post(
            f"/attestations/bulk/{cycle.cycle_id}/draft",
            json={
                "selected_model_ids": [99999],  # Invalid model ID
                "excluded_model_ids": [],
                "responses": [],
                "comment": "Test draft"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid selected model IDs" in response.json()["detail"]

    def test_draft_validation_rejects_invalid_excluded_ids(
        self, client, auth_headers, open_cycle_with_records, db_session
    ):
        """Draft save rejects excluded model IDs not available for attestation."""
        cycle = open_cycle_with_records["cycle"]

        # Try to save draft with invalid excluded model ID
        response = client.post(
            f"/attestations/bulk/{cycle.cycle_id}/draft",
            json={
                "selected_model_ids": [],
                "excluded_model_ids": [99999],  # Invalid model ID
                "responses": [],
                "comment": "Test draft"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid excluded model IDs" in response.json()["detail"]

    def test_draft_validation_rejects_overlap(
        self, client, auth_headers, open_cycle_with_records, db_session
    ):
        """Draft save rejects model IDs that are both selected and excluded."""
        cycle = open_cycle_with_records["cycle"]
        model = open_cycle_with_records["model"]

        # Try to save draft with same ID in both lists
        response = client.post(
            f"/attestations/bulk/{cycle.cycle_id}/draft",
            json={
                "selected_model_ids": [model.model_id],
                "excluded_model_ids": [model.model_id],  # Same ID - overlap!
                "responses": [],
                "comment": "Test draft"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "cannot be both selected and excluded" in response.json()["detail"]

    def test_draft_saves_valid_selections(
        self, client, auth_headers, open_cycle_with_records, db_session
    ):
        """Draft save succeeds with valid model IDs."""
        from app.models.attestation import AttestationBulkSubmission

        cycle = open_cycle_with_records["cycle"]
        model = open_cycle_with_records["model"]

        # Save valid draft
        response = client.post(
            f"/attestations/bulk/{cycle.cycle_id}/draft",
            json={
                "selected_model_ids": [model.model_id],
                "excluded_model_ids": [],
                "responses": [],
                "comment": "Test draft"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "bulk_submission_id" in response.json()

        # Verify draft was created
        draft = db_session.query(AttestationBulkSubmission).filter(
            AttestationBulkSubmission.cycle_id == cycle.cycle_id
        ).first()
        assert draft is not None
        assert draft.selected_model_ids == [model.model_id]

    def test_get_state_allowed_for_closed_cycle(
        self, client, auth_headers, open_cycle_with_records, db_session
    ):
        """GET bulk state is allowed for closed cycles (to view submission results)."""
        cycle = open_cycle_with_records["cycle"]
        record = open_cycle_with_records["record"]

        # Submit the record first
        record.status = AttestationRecordStatus.SUBMITTED.value
        db_session.commit()

        # Close the cycle
        cycle.status = AttestationCycleStatus.CLOSED.value
        db_session.commit()

        # GET should still work
        response = client.get(
            f"/attestations/bulk/{cycle.cycle_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["summary"]["submitted_count"] == 1

    def test_get_state_blocked_for_pending_cycle(
        self, client, auth_headers, db_session, test_user, sample_model, scheduling_rule
    ):
        """GET bulk state is blocked for PENDING (not yet opened) cycles."""
        sample_model.row_approval_status = None
        db_session.commit()

        cycle = AttestationCycle(
            cycle_name="Pending Cycle",
            period_start_date=date.today() - timedelta(days=30),
            period_end_date=date.today() + timedelta(days=60),
            submission_due_date=date.today() + timedelta(days=30),
            status=AttestationCycleStatus.PENDING.value,  # Not yet opened
            notes="Test"
        )
        db_session.add(cycle)
        db_session.commit()

        response = client.get(
            f"/attestations/bulk/{cycle.cycle_id}",
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()

    def test_cycle_close_cleans_up_draft_bulk_submissions(
        self, client, admin_headers, auth_headers, open_cycle_with_records, db_session
    ):
        """Closing a cycle deletes draft bulk submissions."""
        from app.models.attestation import AttestationBulkSubmission, AttestationBulkSubmissionStatus

        cycle = open_cycle_with_records["cycle"]
        model = open_cycle_with_records["model"]

        # Create a draft
        response = client.post(
            f"/attestations/bulk/{cycle.cycle_id}/draft",
            json={
                "selected_model_ids": [model.model_id],
                "excluded_model_ids": [],
                "responses": [],
                "comment": "Test draft"
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify draft exists
        draft = db_session.query(AttestationBulkSubmission).filter(
            AttestationBulkSubmission.cycle_id == cycle.cycle_id
        ).first()
        assert draft is not None
        assert draft.status == AttestationBulkSubmissionStatus.DRAFT.value

        # Close the cycle (force=True to bypass coverage checks)
        response = client.post(
            f"/attestations/cycles/{cycle.cycle_id}/close?force=true",
            headers=admin_headers
        )
        assert response.status_code == 200

        # Verify draft was deleted
        db_session.expire_all()
        draft = db_session.query(AttestationBulkSubmission).filter(
            AttestationBulkSubmission.cycle_id == cycle.cycle_id
        ).first()
        assert draft is None

    def test_cycle_close_resets_excluded_flags(
        self, client, admin_headers, auth_headers, open_cycle_with_records, db_session
    ):
        """Closing a cycle resets is_excluded flags on PENDING records."""
        cycle = open_cycle_with_records["cycle"]
        record = open_cycle_with_records["record"]
        model = open_cycle_with_records["model"]

        # Save draft with model excluded
        response = client.post(
            f"/attestations/bulk/{cycle.cycle_id}/draft",
            json={
                "selected_model_ids": [],
                "excluded_model_ids": [model.model_id],
                "responses": [],
                "comment": "Test"
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify excluded flag was set
        db_session.refresh(record)
        assert record.is_excluded is True

        # Close the cycle
        response = client.post(
            f"/attestations/cycles/{cycle.cycle_id}/close?force=true",
            headers=admin_headers
        )
        assert response.status_code == 200

        # Verify excluded flag was reset
        db_session.expire_all()
        db_session.refresh(record)
        assert record.is_excluded is False

    def test_individual_submit_clears_excluded_flag(
        self, client, auth_headers, open_cycle_with_records, attestation_taxonomy, db_session
    ):
        """Individual submission clears is_excluded flag."""
        cycle = open_cycle_with_records["cycle"]
        record = open_cycle_with_records["record"]
        model = open_cycle_with_records["model"]
        q1 = attestation_taxonomy["q1"]
        q2 = attestation_taxonomy["q2"]

        # Mark record as excluded
        record.is_excluded = True
        db_session.commit()

        # Submit individually
        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json={
                "decision": "I_ATTEST",
                "responses": [
                    {"question_id": q1.value_id, "answer": True},
                    {"question_id": q2.value_id, "answer": True}
                ],
                "evidence": []
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify excluded flag was cleared
        db_session.refresh(record)
        assert record.is_excluded is False

    def test_individual_submit_removes_from_draft_excluded_list(
        self, client, auth_headers, open_cycle_with_records, attestation_taxonomy, db_session, test_user, usage_frequency
    ):
        """Individual submission removes model from draft's excluded_model_ids."""
        from app.models.attestation import AttestationBulkSubmission, AttestationBulkSubmissionStatus

        cycle = open_cycle_with_records["cycle"]
        record = open_cycle_with_records["record"]
        model = open_cycle_with_records["model"]
        q1 = attestation_taxonomy["q1"]
        q2 = attestation_taxonomy["q2"]

        # Create a second model for the same owner
        model2 = Model(
            model_name="Second Test Model",
            description="Another test model",
            development_type="In-House",
            status="In Development",
            owner_id=test_user.user_id,
            row_approval_status=None,
            usage_frequency_id=usage_frequency["daily"].value_id
        )
        db_session.add(model2)
        db_session.flush()

        # Create second attestation record
        record2 = AttestationRecord(
            cycle_id=cycle.cycle_id,
            model_id=model2.model_id,
            attesting_user_id=test_user.user_id,
            due_date=cycle.submission_due_date,
            status=AttestationRecordStatus.PENDING.value
        )
        db_session.add(record2)
        db_session.commit()

        # Create draft with first model excluded
        draft = AttestationBulkSubmission(
            cycle_id=cycle.cycle_id,
            user_id=test_user.user_id,
            status=AttestationBulkSubmissionStatus.DRAFT.value,
            selected_model_ids=[model2.model_id],
            excluded_model_ids=[model.model_id]
        )
        db_session.add(draft)
        record.is_excluded = True
        db_session.commit()

        # Submit the excluded model individually
        response = client.post(
            f"/attestations/records/{record.attestation_id}/submit",
            json={
                "decision": "I_ATTEST",
                "responses": [
                    {"question_id": q1.value_id, "answer": True},
                    {"question_id": q2.value_id, "answer": True}
                ],
                "evidence": []
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify model was removed from excluded list
        db_session.refresh(draft)
        assert model.model_id not in draft.excluded_model_ids
