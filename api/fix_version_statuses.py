"""
Fix existing model version statuses to align with their validation request statuses.

This script updates version statuses that were created before automatic transitions
were implemented.
"""
from app.core.database import SessionLocal
from app.models.model_version import ModelVersion
from app.models.validation import ValidationRequest

db = SessionLocal()

print("=" * 80)
print("FIXING MODEL VERSION STATUSES")
print("=" * 80)

try:
    updates = []

    # Get all versions linked to validation requests
    versions = db.query(ModelVersion).filter(
        ModelVersion.validation_request_id.isnot(None)
    ).all()

    print(f"\nChecking {len(versions)} versions with validation requests...\n")

    for version in versions:
        vr = db.query(ValidationRequest).filter(
            ValidationRequest.request_id == version.validation_request_id
        ).first()

        if not vr or not vr.current_status:
            continue

        val_status = vr.current_status.code
        ver_status = version.status
        new_status = None

        # Determine correct status based on validation status
        if val_status == "IN_PROGRESS":
            if ver_status == "DRAFT":
                new_status = "IN_VALIDATION"

        elif val_status == "APPROVED":
            if ver_status in ["DRAFT", "IN_VALIDATION"]:
                new_status = "APPROVED"

        elif val_status in ["CANCELLED", "ON_HOLD"]:
            if ver_status == "IN_VALIDATION":
                new_status = "DRAFT"

        # Apply update if needed
        if new_status:
            updates.append({
                'version_id': version.version_id,
                'version_number': version.version_number,
                'model_id': version.model_id,
                'old_status': ver_status,
                'new_status': new_status,
                'validation_status': val_status
            })

            version.status = new_status

    if updates:
        print(f"Updating {len(updates)} version statuses:\n")
        for upd in updates:
            print(f"✓ Version {upd['version_id']} ({upd['version_number']}) Model {upd['model_id']}")
            print(f"  {upd['old_status']} → {upd['new_status']}")
            print(f"  Validation Status: {upd['validation_status']}")
            print()

        db.commit()
        print(f"\n✅ Successfully updated {len(updates)} version(s)")
    else:
        print("✅ No updates needed - all versions are already correctly aligned!")

except Exception as e:
    db.rollback()
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
