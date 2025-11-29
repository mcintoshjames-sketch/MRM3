"""Seed test data for SLA validation testing."""
from datetime import datetime, timedelta, date
from app.core.database import SessionLocal
from app.models import (
    User, Model, TaxonomyValue, ValidationRequest,
    ValidationStatusHistory, ValidationAssignment
)
from sqlalchemy.orm import Session


def seed_sla_test_data():
    """Create sample validation requests with various SLA states."""
    db = SessionLocal()

    try:
        # Get required taxonomy values
        intake_status = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.code == "INTAKE"
        ).first()

        planning_status = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.code == "PLANNING"
        ).first()

        in_progress_status = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.code == "IN_PROGRESS"
        ).first()

        pending_approval_status = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.code == "PENDING_APPROVAL"
        ).first()

        validation_type = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.taxonomy.has(name="Validation Type")
        ).first()

        priority_medium = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.taxonomy.has(name="Validation Priority"),
            TaxonomyValue.label == "Medium"
        ).first()

        priority_high = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.taxonomy.has(name="Validation Priority"),
            TaxonomyValue.label == "High"
        ).first()

        priority_critical = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.taxonomy.has(name="Validation Priority"),
            TaxonomyValue.label == "Critical"
        ).first()

        # Get admin user
        admin = db.query(User).filter(User.role == "Admin").first()
        validator = db.query(User).filter(User.role == "Validator").first()

        # Get first model
        model = db.query(Model).first()

        if not all([intake_status, planning_status, in_progress_status, pending_approval_status,
                   validation_type, priority_medium, priority_high, priority_critical,
                   admin, validator, model]):
            print(
                "Missing required data. Please ensure taxonomies and users are seeded first.")
            return

        print("Creating test validation requests with SLA violations...")

        # Test Case 1: Assignment Overdue (15 days in Intake, no assignment)
        req1 = ValidationRequest(
            model_id=model.model_id,
            requestor_id=admin.user_id,
            validation_type_id=validation_type.value_id,
            priority_id=priority_critical.value_id,
            target_completion_date=date.today() + timedelta(days=30),
            trigger_reason="Risk assessment update required",
            business_justification="Regulatory requirement",
            current_status_id=intake_status.value_id,
            created_at=datetime.utcnow() - timedelta(days=15),
            updated_at=datetime.utcnow() - timedelta(days=15)
        )
        db.add(req1)
        db.flush()

        # Add status history
        hist1 = ValidationStatusHistory(
            request_id=req1.request_id,
            old_status_id=None,
            new_status_id=intake_status.value_id,
            changed_by_id=admin.user_id,
            changed_at=datetime.utcnow() - timedelta(days=15),
            change_reason="Initial request"
        )
        db.add(hist1)
        print(
            f"✓ Created Request #{req1.request_id}: Assignment Overdue (15 days in Intake)")

        # Test Case 2: Begin Work Overdue (assigned 8 days ago, still in Planning)
        req2 = ValidationRequest(
            model_id=model.model_id,
            requestor_id=admin.user_id,
            validation_type_id=validation_type.value_id,
            priority_id=priority_high.value_id,
            target_completion_date=date.today() + timedelta(days=45),
            trigger_reason="Comprehensive review",
            business_justification="Scheduled validation",
            current_status_id=planning_status.value_id,
            created_at=datetime.utcnow() - timedelta(days=10),
            updated_at=datetime.utcnow() - timedelta(days=8)
        )
        db.add(req2)
        db.flush()

        # Add assignment (8 days ago)
        assign2 = ValidationAssignment(
            request_id=req2.request_id,
            validator_id=validator.user_id,
            is_primary=True,
            is_reviewer=False,
            assignment_date=date.today() - timedelta(days=8),
            estimated_hours=40.0,
            independence_attestation=True,
            created_at=datetime.utcnow() - timedelta(days=8)
        )
        db.add(assign2)

        # Status history
        hist2a = ValidationStatusHistory(
            request_id=req2.request_id,
            old_status_id=None,
            new_status_id=intake_status.value_id,
            changed_by_id=admin.user_id,
            changed_at=datetime.utcnow() - timedelta(days=10),
            change_reason="Initial request"
        )
        db.add(hist2a)

        hist2b = ValidationStatusHistory(
            request_id=req2.request_id,
            old_status_id=intake_status.value_id,
            new_status_id=planning_status.value_id,
            changed_by_id=validator.user_id,
            changed_at=datetime.utcnow() - timedelta(days=8),
            change_reason="Validator assigned"
        )
        db.add(hist2b)
        print(
            f"✓ Created Request #{req2.request_id}: Begin Work Overdue (8 days in Planning)")

        # Test Case 3: Work Completion Overdue (in progress for 95 days)
        req3 = ValidationRequest(
            model_id=model.model_id,
            requestor_id=admin.user_id,
            validation_type_id=validation_type.value_id,
            priority_id=priority_medium.value_id,
            target_completion_date=date.today() - timedelta(days=15),
            trigger_reason="Model update validation",
            business_justification="Code changes deployed",
            current_status_id=in_progress_status.value_id,
            created_at=datetime.utcnow() - timedelta(days=100),
            updated_at=datetime.utcnow() - timedelta(days=5)
        )
        db.add(req3)
        db.flush()

        # Add assignment (95 days ago)
        assign3 = ValidationAssignment(
            request_id=req3.request_id,
            validator_id=validator.user_id,
            is_primary=True,
            is_reviewer=False,
            assignment_date=date.today() - timedelta(days=95),
            estimated_hours=60.0,
            independence_attestation=True,
            created_at=datetime.utcnow() - timedelta(days=95)
        )
        db.add(assign3)

        # Status history
        hist3a = ValidationStatusHistory(
            request_id=req3.request_id,
            old_status_id=None,
            new_status_id=intake_status.value_id,
            changed_by_id=admin.user_id,
            changed_at=datetime.utcnow() - timedelta(days=100),
            change_reason="Initial request"
        )
        db.add(hist3a)

        hist3b = ValidationStatusHistory(
            request_id=req3.request_id,
            old_status_id=intake_status.value_id,
            new_status_id=planning_status.value_id,
            changed_by_id=validator.user_id,
            changed_at=datetime.utcnow() - timedelta(days=95),
            change_reason="Validator assigned"
        )
        db.add(hist3b)

        hist3c = ValidationStatusHistory(
            request_id=req3.request_id,
            old_status_id=planning_status.value_id,
            new_status_id=in_progress_status.value_id,
            changed_by_id=validator.user_id,
            changed_at=datetime.utcnow() - timedelta(days=90),
            change_reason="Started validation work"
        )
        db.add(hist3c)
        print(
            f"✓ Created Request #{req3.request_id}: Work Completion Overdue (95 days in progress)")

        # Test Case 4: Approval Overdue (in pending approval for 15 days)
        req4 = ValidationRequest(
            model_id=model.model_id,
            requestor_id=admin.user_id,
            validation_type_id=validation_type.value_id,
            priority_id=priority_critical.value_id,
            target_completion_date=date.today() - timedelta(days=5),
            trigger_reason="Regulatory compliance check",
            business_justification="Required by policy",
            current_status_id=pending_approval_status.value_id,
            created_at=datetime.utcnow() - timedelta(days=100),
            updated_at=datetime.utcnow() - timedelta(days=15)
        )
        db.add(req4)
        db.flush()

        # Add assignment
        assign4 = ValidationAssignment(
            request_id=req4.request_id,
            validator_id=validator.user_id,
            is_primary=True,
            is_reviewer=False,
            assignment_date=date.today() - timedelta(days=90),
            estimated_hours=50.0,
            independence_attestation=True,
            created_at=datetime.utcnow() - timedelta(days=90)
        )
        db.add(assign4)

        # Status history to pending approval (15 days ago)
        hist4d = ValidationStatusHistory(
            request_id=req4.request_id,
            old_status_id=in_progress_status.value_id,
            new_status_id=pending_approval_status.value_id,
            changed_by_id=validator.user_id,
            changed_at=datetime.utcnow() - timedelta(days=15),
            change_reason="Work completed, ready for approval"
        )
        db.add(hist4d)
        print(
            f"✓ Created Request #{req4.request_id}: Approval Overdue (15 days in Pending Approval)")

        # Test Case 5: On-time validation (in progress for 30 days, within SLA)
        req5 = ValidationRequest(
            model_id=model.model_id,
            requestor_id=admin.user_id,
            validation_type_id=validation_type.value_id,
            priority_id=priority_medium.value_id,
            target_completion_date=date.today() + timedelta(days=50),
            trigger_reason="Quarterly review",
            business_justification="Routine check",
            current_status_id=in_progress_status.value_id,
            created_at=datetime.utcnow() - timedelta(days=35),
            updated_at=datetime.utcnow() - timedelta(days=5)
        )
        db.add(req5)
        db.flush()

        # Add assignment (30 days ago)
        assign5 = ValidationAssignment(
            request_id=req5.request_id,
            validator_id=validator.user_id,
            is_primary=True,
            is_reviewer=False,
            assignment_date=date.today() - timedelta(days=30),
            estimated_hours=40.0,
            independence_attestation=True,
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        db.add(assign5)

        # Status history
        hist5c = ValidationStatusHistory(
            request_id=req5.request_id,
            old_status_id=planning_status.value_id,
            new_status_id=in_progress_status.value_id,
            changed_by_id=validator.user_id,
            changed_at=datetime.utcnow() - timedelta(days=28),
            change_reason="Started validation work"
        )
        db.add(hist5c)
        print(
            f"✓ Created Request #{req5.request_id}: On-Time (30 days in progress, within SLA)")

        db.commit()
        print("\n✓ Successfully created 5 test validation requests")
        print("  - 1 Assignment Overdue (CRITICAL)")
        print("  - 1 Begin Work Overdue (HIGH)")
        print("  - 1 Work Completion Overdue (CRITICAL)")
        print("  - 1 Approval Overdue (CRITICAL)")
        print("  - 1 On-Time (for comparison)")

    except Exception as e:
        db.rollback()
        print(f"Error seeding test data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_sla_test_data()
