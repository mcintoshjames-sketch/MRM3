"""
Seed script to create test data for revalidation banner UAT.

Creates 3 models that will trigger each banner type:
1. Red banner: Validation overdue
2. Orange banner: Validation due soon (< 60 days)
3. Yellow banner: Submission overdue but validation > 60 days out
"""

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.model import Model
from app.models.user import User
from app.models.taxonomy import TaxonomyValue
from app.models.validation import ValidationRequest, ValidationRequestModelVersion

def create_banner_test_data():
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

        # Get IN_PROGRESS status
        in_progress = db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
            TaxonomyValue.code == "IN_PROGRESS"
        ).first()

        today = date.today()

        print(f"Creating banner test data (Today: {today})")
        print("=" * 60)

        # ========================================
        # Test 1: RED BANNER - Validation Overdue
        # ========================================
        print("\n1. RED BANNER - Validation Overdue")
        print("-" * 60)

        # Last validation: 2023-01-15 (completed)
        # Frequency: 18 months → Submission due: 2024-07-15
        # Grace period: 3 months → Grace end: 2024-10-15
        # Lead time: 90 days → Validation due: 2025-01-13
        # Today (2025-11-20) is 311 days past validation due date

        model_1 = Model(
            model_name="Banner Test: Validation OVERDUE",
            description="Test model for RED banner (validation overdue)",
            development_type="In-House",
            owner_id=admin.user_id,
            risk_tier_id=tier_2.value_id,
            status="Active"
        )
        db.add(model_1)
        db.flush()

        # Prior validation (completed)
        prior_val_1 = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "MEDIUM"
            ).first().value_id,
            target_completion_date=date(2023, 1, 15),
            current_status_id=approved.value_id,
            created_at=datetime(2023, 1, 1, 0, 0, 0),
            updated_at=datetime(2023, 1, 15, 0, 0, 0)  # Completed date
        )
        db.add(prior_val_1)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=prior_val_1.request_id,
            model_id=model_1.model_id
        ))

        # Current revalidation request (in progress, overdue)
        current_val_1 = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "CRITICAL"
            ).first().value_id,
            target_completion_date=date(2025, 1, 13),
            current_status_id=in_progress.value_id,
            prior_validation_request_id=prior_val_1.request_id,
            submission_received_date=date(2024, 7, 15),  # On time
            created_at=datetime(2024, 7, 1, 0, 0, 0),
            updated_at=datetime.now()
        )
        db.add(current_val_1)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=current_val_1.request_id,
            model_id=model_1.model_id
        ))

        print(f"Created Model ID {model_1.model_id}: {model_1.model_name}")
        print(f"  Last validation: 2023-01-15")
        print(f"  Submission due: 2024-07-15 (18 months later)")
        print(f"  Grace period end: 2024-10-15 (+3 months)")
        print(f"  Validation due: 2025-01-13 (+90 days)")
        print(f"  Days overdue: ~311 days ← RED BANNER")

        # ========================================
        # Test 2: ORANGE BANNER - Due Soon
        # ========================================
        print("\n2. ORANGE BANNER - Validation Due Soon (< 60 days)")
        print("-" * 60)

        # Working backwards from target validation due: 2026-01-10 (51 days from today)
        # Lead time: 90 days → Grace end: 2025-10-12
        # Grace period: 3 months → Submission due: 2025-07-12
        # Frequency: 18 months → Last validation: 2024-01-12

        model_2 = Model(
            model_name="Banner Test: Due SOON",
            description="Test model for ORANGE banner (due soon)",
            development_type="In-House",
            owner_id=admin.user_id,
            risk_tier_id=tier_2.value_id,
            status="Active"
        )
        db.add(model_2)
        db.flush()

        # Prior validation (completed)
        prior_val_2 = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "MEDIUM"
            ).first().value_id,
            target_completion_date=date(2024, 1, 12),
            current_status_id=approved.value_id,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 12, 0, 0, 0)
        )
        db.add(prior_val_2)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=prior_val_2.request_id,
            model_id=model_2.model_id
        ))

        # Current revalidation request (in progress)
        current_val_2 = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "HIGH"
            ).first().value_id,
            target_completion_date=date(2026, 1, 10),
            current_status_id=in_progress.value_id,
            prior_validation_request_id=prior_val_2.request_id,
            submission_received_date=date(2025, 7, 12),  # On time
            created_at=datetime(2025, 7, 1, 0, 0, 0),
            updated_at=datetime.now()
        )
        db.add(current_val_2)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=current_val_2.request_id,
            model_id=model_2.model_id
        ))

        print(f"Created Model ID {model_2.model_id}: {model_2.model_name}")
        print(f"  Last validation: 2024-01-12")
        print(f"  Submission due: 2025-07-12")
        print(f"  Grace period end: 2025-10-12")
        print(f"  Validation due: 2026-01-10")
        print(f"  Days until due: ~51 days ← ORANGE BANNER")

        # ========================================
        # Test 3: YELLOW BANNER - Submission Overdue
        # ========================================
        print("\n3. YELLOW BANNER - Submission Overdue (but validation > 60 days)")
        print("-" * 60)

        # Working backwards from target validation due: 2026-02-01 (73 days from today)
        # Lead time: 90 days → Grace end: 2025-11-03
        # Grace period: 3 months → Submission due: 2025-08-03
        # Frequency: 18 months → Last validation: 2024-02-03

        model_3 = Model(
            model_name="Banner Test: Submission OVERDUE",
            description="Test model for YELLOW banner (submission overdue)",
            development_type="In-House",
            owner_id=admin.user_id,
            risk_tier_id=tier_2.value_id,
            status="Active"
        )
        db.add(model_3)
        db.flush()

        # Prior validation (completed)
        prior_val_3 = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "MEDIUM"
            ).first().value_id,
            target_completion_date=date(2024, 2, 3),
            current_status_id=approved.value_id,
            created_at=datetime(2024, 1, 20, 0, 0, 0),
            updated_at=datetime(2024, 2, 3, 0, 0, 0)
        )
        db.add(prior_val_3)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=prior_val_3.request_id,
            model_id=model_3.model_id
        ))

        # Current revalidation request (awaiting submission - NO submission_received_date)
        current_val_3 = ValidationRequest(
            requestor_id=admin.user_id,
            validation_type_id=comprehensive.value_id,
            priority_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "MEDIUM"
            ).first().value_id,
            target_completion_date=date(2026, 2, 1),
            current_status_id=db.query(TaxonomyValue).join(TaxonomyValue.taxonomy).filter(
                TaxonomyValue.code == "INTAKE"
            ).first().value_id,
            prior_validation_request_id=prior_val_3.request_id,
            submission_received_date=None,  # No submission yet!
            created_at=datetime(2025, 8, 1, 0, 0, 0),
            updated_at=datetime.now()
        )
        db.add(current_val_3)
        db.flush()

        # Link to model
        db.add(ValidationRequestModelVersion(
            request_id=current_val_3.request_id,
            model_id=model_3.model_id
        ))

        print(f"Created Model ID {model_3.model_id}: {model_3.model_name}")
        print(f"  Last validation: 2024-02-03")
        print(f"  Submission due: 2025-08-03 (~109 days ago)")
        print(f"  Grace period end: 2025-11-03 (~17 days ago)")
        print(f"  Validation due: 2026-02-01 (~73 days from now)")
        print(f"  Submission: NOT RECEIVED ← YELLOW BANNER")

        db.commit()

        print("\n" + "=" * 60)
        print("✓ Banner test data created successfully!")
        print("\nTo test, navigate to:")
        print(f"  - Model {model_1.model_id}: RED banner (validation overdue)")
        print(f"  - Model {model_2.model_id}: ORANGE banner (due soon)")
        print(f"  - Model {model_3.model_id}: YELLOW banner (submission overdue)")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error creating banner test data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_banner_test_data()
