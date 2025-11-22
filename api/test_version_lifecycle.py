"""
Test script to verify automatic model version status transitions.

This script demonstrates the complete version lifecycle:
1. DRAFT -> IN_VALIDATION (when validation request moves to IN_PROGRESS)
2. IN_VALIDATION -> APPROVED (when validation request is APPROVED)
3. APPROVED -> ACTIVE (manual activation via endpoint)
4. Previous ACTIVE -> SUPERSEDED (when new version activated)
"""
from app.core.database import SessionLocal
from app.models.model_version import ModelVersion
from app.models.validation import ValidationRequest
from sqlalchemy import text

db = SessionLocal()

print("=" * 80)
print("MODEL VERSION LIFECYCLE STATUS VERIFICATION")
print("=" * 80)

try:
    # Check all model versions and their statuses
    versions = db.query(ModelVersion).join(
        ValidationRequest,
        ModelVersion.validation_request_id == ValidationRequest.request_id,
        isouter=True
    ).all()

    print(f"\nFound {len(versions)} model versions:\n")

    for version in versions:
        print(f"Version {version.version_id}: {version.version_number}")
        print(f"  Model ID: {version.model_id}")
        print(f"  Status: {version.status}")
        print(f"  Change Type: {version.change_type}")

        if version.validation_request_id:
            vr = db.query(ValidationRequest).get(version.validation_request_id)
            if vr and vr.current_status:
                print(f"  Validation Request: #{vr.request_id}")
                print(f"  Validation Status: {vr.current_status.label} ({vr.current_status.code})")
        else:
            print(f"  Validation Request: None")

        print()

    # Check for status alignment issues
    print("=" * 80)
    print("STATUS ALIGNMENT CHECK")
    print("=" * 80)

    # Find versions where status doesn't match validation status
    issues = []

    for version in versions:
        if not version.validation_request_id:
            continue

        vr = db.query(ValidationRequest).get(version.validation_request_id)
        if not vr or not vr.current_status:
            continue

        val_status = vr.current_status.code
        ver_status = version.status

        # Expected mappings
        expected = None
        if val_status == "IN_PROGRESS" and ver_status == "DRAFT":
            expected = "IN_VALIDATION"
        elif val_status == "APPROVED" and ver_status == "IN_VALIDATION":
            expected = "APPROVED"

        if expected:
            issues.append({
                'version_id': version.version_id,
                'version_number': version.version_number,
                'current_status': ver_status,
                'expected_status': expected,
                'validation_status': val_status
            })

    if issues:
        print(f"\n⚠️  Found {len(issues)} status alignment issues:\n")
        for issue in issues:
            print(f"Version {issue['version_id']} ({issue['version_number']}):")
            print(f"  Current Status: {issue['current_status']}")
            print(f"  Expected Status: {issue['expected_status']}")
            print(f"  Validation Status: {issue['validation_status']}")
            print()
    else:
        print("\n✅ No status alignment issues found!")

    # Lifecycle summary
    print("=" * 80)
    print("LIFECYCLE SUMMARY")
    print("=" * 80)

    status_counts = {}
    for version in versions:
        status_counts[version.status] = status_counts.get(version.status, 0) + 1

    print("\nVersion Status Distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("\n" + "=" * 80)
    print("AUTOMATIC TRANSITIONS ENABLED:")
    print("=" * 80)
    print("""
1. DRAFT → IN_VALIDATION
   Trigger: Validation request changes to IN_PROGRESS

2. IN_VALIDATION → APPROVED
   Trigger: Validation request changes to APPROVED

3. IN_VALIDATION → DRAFT
   Trigger: Validation request CANCELLED or ON_HOLD

4. APPROVED → ACTIVE
   Trigger: Manual activation via PATCH /versions/{id}/activate

5. Previous ACTIVE → SUPERSEDED
   Trigger: Automatic when new version activated
""")

finally:
    db.close()
