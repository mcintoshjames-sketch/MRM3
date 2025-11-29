"""
Seed script to demonstrate reviewer send-back workflow for request #3.

This script:
1. Moves request #3 through the workflow to Review status
2. Creates a validation outcome
3. Creates a review outcome with SEND_BACK decision
4. Creates proper status history showing who sent it back and why
5. Moves request back to In Progress (as would happen in real workflow)

Run with: python seed_reviewer_sendback_demo.py
"""

import sys
from pathlib import Path
from datetime import datetime, date

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import engine
from app.core.time import utc_now
from app.models.validation import (
    ValidationRequest,
    ValidationStatusHistory,
    ValidationOutcome,
    ValidationReviewOutcome
)
from app.models.taxonomy import TaxonomyValue
from app.models.user import User


def get_taxonomy_value_by_code(db: Session, taxonomy_name: str, code: str) -> TaxonomyValue:
    """Get taxonomy value by taxonomy name and code."""
    return db.query(TaxonomyValue).join(
        TaxonomyValue.taxonomy
    ).filter(
        TaxonomyValue.taxonomy.has(name=taxonomy_name),
        TaxonomyValue.code == code
    ).first()


def seed_reviewer_sendback():
    """Seed reviewer send-back workflow for request #3."""

    with Session(engine) as db:
        try:
            # Get request #3
            request = db.query(ValidationRequest).filter(
                ValidationRequest.request_id == 3
            ).first()

            if not request:
                print("❌ Request #3 not found")
                return

            print(f"✓ Found request #{request.request_id}")

            # Get required taxonomy values
            review_status = get_taxonomy_value_by_code(db, "Validation Request Status", "REVIEW")
            in_progress_status = get_taxonomy_value_by_code(db, "Validation Request Status", "IN_PROGRESS")
            pass_with_findings = get_taxonomy_value_by_code(db, "Overall Rating", "FIT_WITH_CONDITIONS")

            # Get reviewer user (let's use Emily Davis as the reviewer)
            reviewer = db.query(User).filter(User.email == "emily.davis@contoso.com").first()
            if not reviewer:
                print("❌ Reviewer user not found")
                return

            print(f"✓ Using {reviewer.full_name} as reviewer")

            # Step 1: Move to Review status (simulate workflow progression)
            print("\n📝 Creating workflow history...")

            # Record old status for history
            old_status_id = request.current_status_id

            # Move to Review
            request.current_status_id = review_status.value_id
            request.updated_at = utc_now()

            # Create status history for move to Review
            review_history = ValidationStatusHistory(
                request_id=request.request_id,
                old_status_id=old_status_id,
                new_status_id=review_status.value_id,
                changed_by_id=reviewer.user_id,
                changed_at=utc_now(),
                change_reason="Moved to Review for quality check"
            )
            db.add(review_history)
            db.flush()

            print(f"  ✓ Moved to Review status")

            # Step 2: Create validation outcome (required before review)
            print("\n📊 Creating validation outcome...")

            outcome = ValidationOutcome(
                request_id=request.request_id,
                overall_rating_id=pass_with_findings.value_id,
                executive_summary="Initial validation completed with several findings that need to be addressed.\n\nKey Findings:\n1. Model documentation incomplete in sections 3.5 and 4.2\n2. Back-testing results need additional explanation\n3. Governance approval signature missing\n\nRecommendations:\nUpdate documentation, provide detailed back-testing analysis, obtain required signatures.",
                recommended_review_frequency=12,  # 12 months
                effective_date=date.today(),
                expiration_date=None,
                created_at=utc_now()
            )
            db.add(outcome)
            db.flush()

            print(f"  ✓ Created validation outcome (ID: {outcome.outcome_id})")

            # Step 3: Create review outcome with SEND_BACK decision
            print("\n🔄 Creating send-back decision...")

            review_outcome = ValidationReviewOutcome(
                request_id=request.request_id,
                reviewer_id=reviewer.user_id,
                decision="SEND_BACK",
                comments="Documentation gaps identified that must be addressed before approval. Model owner needs to:\n1. Complete sections 3.5 and 4.2 with detailed methodology\n2. Provide explanation for back-testing anomalies in Q3 2024\n3. Obtain final governance sign-off from Risk Committee",
                review_date=utc_now()
            )
            db.add(review_outcome)
            db.flush()

            print(f"  ✓ Created review outcome (ID: {review_outcome.review_outcome_id})")

            # Step 4: Move back to In Progress with proper history
            print("\n⏮️  Moving back to In Progress...")

            old_review_status_id = request.current_status_id
            request.current_status_id = in_progress_status.value_id
            request.updated_at = utc_now()

            # Create status history for send-back
            sendback_history = ValidationStatusHistory(
                request_id=request.request_id,
                old_status_id=old_review_status_id,
                new_status_id=in_progress_status.value_id,
                changed_by_id=reviewer.user_id,
                changed_at=utc_now(),
                change_reason=f"Reviewer sent back for revision: {review_outcome.comments}"
            )
            db.add(sendback_history)

            print(f"  ✓ Created send-back status history")

            # Commit all changes
            db.commit()

            print("\n✅ Successfully seeded reviewer send-back workflow for request #3")
            print(f"\nActivity History should now show:")
            print(f"  - {reviewer.full_name} moved to Review status")
            print(f"  - Validation outcome created with findings")
            print(f"  - {reviewer.full_name} sent back for revision with detailed comments")
            print(f"  - Current status: In Progress")

        except Exception as e:
            db.rollback()
            print(f"\n❌ Error seeding data: {str(e)}")
            raise


if __name__ == "__main__":
    print("=" * 80)
    print("Seeding Reviewer Send-Back Workflow for Request #3")
    print("=" * 80)
    seed_reviewer_sendback()
    print("=" * 80)
