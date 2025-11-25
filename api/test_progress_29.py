"""
Debug script to test progressing validation request 29.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.validation import ValidationRequest, ValidationAssignment
from app.models.taxonomy import TaxonomyValue
from app.core.validation_plan import validate_plan_compliance, request_requires_validation_plan

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/mrm_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def debug_request_29():
    db = SessionLocal()
    try:
        # Get validation request 29
        request = db.query(ValidationRequest).filter(
            ValidationRequest.request_id == 29
        ).first()

        if not request:
            print("❌ Validation request 29 not found")
            return

        print(f"✅ Request #{request.request_id}")
        print(f"   Current Status: {request.current_status.code if request.current_status else 'None'}")
        print(f"   Has outcome: {request.outcome is not None}")
        print(f"   Has plan: {request.validation_plan is not None}")
        print(f"   Regions: {[r.code for r in request.regions]}")

        # Check primary validator
        primary = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == 29,
            ValidationAssignment.is_primary == True
        ).first()
        print(f"   Primary validator: {primary.validator.full_name if primary else 'None'}")

        # Check reviewer
        reviewer = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == 29,
            ValidationAssignment.is_reviewer == True
        ).first()
        print(f"   Reviewer: {reviewer.validator.full_name if reviewer else 'None'}")

        # Check validation plan requirements
        requires_plan, plan_regions = request_requires_validation_plan(db, request)
        print(f"\n📋 Validation Plan Requirements:")
        print(f"   Requires plan: {requires_plan}")
        print(f"   Required regions: {plan_regions}")

        # Check plan compliance
        is_valid, errors = validate_plan_compliance(
            db, 29,
            require_plan=requires_plan,
            required_region_codes=plan_regions
        )
        print(f"\n✔️  Plan compliance:")
        print(f"   Valid: {is_valid}")
        if errors:
            print(f"   Errors:")
            for err in errors:
                print(f"      - {err}")

        # Try to find PENDING_APPROVAL status
        pending_approval = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == 'PENDING_APPROVAL'
        ).first()
        print(f"\n🔍 PENDING_APPROVAL status:")
        print(f"   Found: {pending_approval is not None}")
        if pending_approval:
            print(f"   ID: {pending_approval.value_id}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_request_29()
