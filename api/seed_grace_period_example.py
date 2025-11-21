"""
Create a model in grace period to demonstrate the "In Grace Period" state.
"""

from datetime import date, datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.model import Model
from app.models.user import User
from app.models.taxonomy import TaxonomyValue
from app.models.validation import ValidationRequest, ValidationRequestModelVersion

def create_grace_period_example():
    db = SessionLocal()

    try:
        # Get admin user (ID 1)
        admin = db.query(User).filter(User.user_id == 1).first()

        # Get Tier 2 risk tier
        tier_2 = db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
            TaxonomyValue.label == "Tier 2 - Medium Risk"
        ).first()

        # Get Comprehensive validation type
        comprehensive = db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
            TaxonomyValue.code == "COMPREHENSIVE"
        ).first()

        # Get APPROVED status
        approved = db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
            TaxonomyValue.code == "APPROVED"
        ).first()

        # Get INTAKE status
        intake = db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
            TaxonomyValue.code == "INTAKE"
        ).first()

        today = date.today()

        print(f"Creating grace period example (Today: {today})")
        print("=" * 60)

        # Create model
        # Working backwards from desired dates:
        # Grace period end: 2025-12-15 (25 days from now - still in future)
        # Submission due: 2025-09-15 (66 days ago - past due!)
        # Last validation: 2024-03-15 (18 months before submission due)

        model = Model(
            model_name="Grace Period Example: Submission DUE",
            description="Test model for IN GRACE PERIOD status",
            development_type="In-House",
            owner_id=admin.user_id,
            risk_tier_id=tier_2.value_id,
            status="Active"
        )
        db.add(model)
        db.flush()

        # Prior validation (completed)
        prior_val = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "MEDIUM"
            ).first().value_id,
            target_completion_date=date(2024, 3, 15),
            current_status_id=approved.value_id,
            created_at=datetime(2024, 3, 1, 0, 0, 0),
            updated_at=datetime(2024, 3, 15, 0, 0, 0)
        )
        db.add(prior_val)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=prior_val.request_id,
            model_id=model.model_id
        ))

        # Current revalidation request (awaiting submission - IN GRACE PERIOD)
        # submission_due_date will be 18 months after 2024-03-15 = 2025-09-15 (66 days ago)
        # grace_period_end will be 3 months later = 2025-12-15 (25 days from now)
        # validation_due_date will be 90 days after grace end = 2026-03-15
        current_val = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "HIGH"
            ).first().value_id,
            target_completion_date=date(2026, 3, 15),
            current_status_id=intake.value_id,
            prior_validation_request_id=prior_val.request_id,
            submission_received_date=None,  # No submission yet!
            created_at=datetime(2025, 9, 1, 0, 0, 0),
            updated_at=datetime.now()
        )
        db.add(current_val)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=current_val.request_id,
            model_id=model.model_id
        ))

        db.commit()

        print(f"\nCreated Model ID {model.model_id}: {model.model_name}")
        print(f"  Last validation: 2024-03-15")
        print(f"  Submission due: 2025-09-15 (~66 days ago)")
        print(f"  Grace period end: 2025-12-15 (~25 days from now)")
        print(f"  Validation due: 2026-03-15")
        print(f"  Status: IN GRACE PERIOD ✓")
        print("\n" + "=" * 60)
        print("✓ Grace period example created successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error creating grace period example: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_grace_period_example()
