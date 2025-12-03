"""Tests for attestation workflow endpoints."""
import pytest
from datetime import date, timedelta
from app.models.taxonomy import Taxonomy, TaxonomyValue
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
        assert response.json()["status"] == "SUBMITTED"

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


class TestChangeProposals:
    """Tests for attestation change proposal workflow."""

    def test_create_update_proposal(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Can create an UPDATE_EXISTING change proposal."""
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
            f"/attestations/records/{record.attestation_id}/changes",
            json={
                "change_type": "UPDATE_EXISTING",
                "model_id": sample_model.model_id,
                "proposed_data": {"description": "Updated description from attestation"}
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "UPDATE_EXISTING"
        assert data["status"] == "PENDING"
        assert data["model"]["model_id"] == sample_model.model_id

    def test_create_new_model_proposal(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Can create a NEW_MODEL change proposal."""
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
            f"/attestations/records/{record.attestation_id}/changes",
            json={
                "change_type": "NEW_MODEL",
                "proposed_data": {"model_name": "New Model from Attestation", "description": "Test model"}
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "NEW_MODEL"
        assert data["proposed_data"]["model_name"] == "New Model from Attestation"

    def test_create_decommission_proposal(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Can create a DECOMMISSION change proposal."""
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
            f"/attestations/records/{record.attestation_id}/changes",
            json={
                "change_type": "DECOMMISSION",
                "model_id": sample_model.model_id,
                "proposed_data": {"reason": "No longer in use"}
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "DECOMMISSION"

    def test_list_change_proposals(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Admin can list change proposals."""
        from app.models.attestation import AttestationChangeProposal, AttestationChangeStatus

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

        proposal = AttestationChangeProposal(
            attestation_id=record.attestation_id,
            change_type="UPDATE_EXISTING",
            model_id=sample_model.model_id,
            proposed_data={"description": "Test"},
            status=AttestationChangeStatus.PENDING.value
        )
        db_session.add(proposal)
        db_session.commit()

        response = client.get("/attestations/changes", headers=admin_headers)
        assert response.status_code == 200
        proposals = response.json()
        assert len(proposals) >= 1

    def test_accept_proposal(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Admin can accept a change proposal."""
        from app.models.attestation import AttestationChangeProposal, AttestationChangeStatus

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

        proposal = AttestationChangeProposal(
            attestation_id=record.attestation_id,
            change_type="UPDATE_EXISTING",
            model_id=sample_model.model_id,
            proposed_data={"description": "Accepted change"},
            status=AttestationChangeStatus.PENDING.value
        )
        db_session.add(proposal)
        db_session.commit()

        response = client.post(
            f"/attestations/changes/{proposal.proposal_id}/accept",
            json={"admin_comment": "Approved"},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACCEPTED"

    def test_reject_proposal_requires_comment(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Rejecting a proposal requires a comment."""
        from app.models.attestation import AttestationChangeProposal, AttestationChangeStatus

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

        proposal = AttestationChangeProposal(
            attestation_id=record.attestation_id,
            change_type="UPDATE_EXISTING",
            model_id=sample_model.model_id,
            proposed_data={"description": "Test"},
            status=AttestationChangeStatus.PENDING.value
        )
        db_session.add(proposal)
        db_session.commit()

        # Try without comment - should fail
        response = client.post(
            f"/attestations/changes/{proposal.proposal_id}/reject",
            json={},
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "comment required" in response.json()["detail"].lower()

    def test_cannot_propose_changes_to_accepted_attestation(self, client, admin_headers, attestation_cycle, sample_model, db_session):
        """Cannot add change proposals to accepted attestations."""
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
            f"/attestations/records/{record.attestation_id}/changes",
            json={
                "change_type": "UPDATE_EXISTING",
                "model_id": sample_model.model_id,
                "proposed_data": {"description": "Should fail"}
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "accepted" in response.json()["detail"].lower()
