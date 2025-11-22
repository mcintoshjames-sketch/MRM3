"""
Fix invalid change_type values in model_versions table.
Changes "Initial", "Major", "Minor" to "MAJOR" or "MINOR".
"""
from app.core.database import SessionLocal
from app.models.model_version import ModelVersion

db = SessionLocal()

try:
    print("Fixing invalid change_type values...")

    # Get all versions with invalid change_type
    versions = db.query(ModelVersion).filter(
        ModelVersion.change_type.in_(['Initial', 'Major', 'Minor'])
    ).all()

    print(f"Found {len(versions)} versions with invalid change_type values")

    for version in versions:
        old_value = version.change_type

        # Map to uppercase values
        if old_value in ['Initial', 'Major']:
            version.change_type = 'MAJOR'
        elif old_value == 'Minor':
            version.change_type = 'MINOR'

        print(f"  Version {version.version_id}: {old_value} -> {version.change_type}")

    db.commit()
    print(f"\n✅ Fixed {len(versions)} change_type values")

except Exception as e:
    db.rollback()
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
