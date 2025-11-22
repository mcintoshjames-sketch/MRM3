"""
Seed script for Regional Compliance Report demonstration data.

This script creates:
- Model versions
- Deployed versions to regions
- Validation requests for those versions
- Regional approvals linked to specific regions
"""
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.user import User
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.validation import ValidationRequest, ValidationApproval, ValidationRequestModelVersion
from app.models.taxonomy import TaxonomyValue, Taxonomy


def seed_regional_demo():
    """Seed demonstration data for regional compliance report."""
    db = SessionLocal()

    try:
        print("Starting regional compliance demo data seeding...")

        # Get required users
        admin = db.query(User).filter(User.email == 'admin@example.com').first()
        if not admin:
            print("Error: Admin user not found. Please run main seed script first.")
            return

        # Get or create a validator user for approvals
        validator = db.query(User).filter(User.role == 'Validator').first()
        if not validator:
            print("Error: No validator user found. Please run main seed script first.")
            return

        # Get regions
        us_region = db.query(Region).filter(Region.code == 'US').first()
        eu_region = db.query(Region).filter(Region.code == 'EU').first()
        uk_region = db.query(Region).filter(Region.code == 'UK').first()

        if not (us_region and eu_region and uk_region):
            print("Error: Required regions not found. Please run main seed script first.")
            return

        # Get taxonomy values
        approved_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == 'Validation Request Status',
            TaxonomyValue.code == 'APPROVED'
        ).first()

        in_progress_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == 'Validation Request Status',
            TaxonomyValue.code == 'IN_PROGRESS'
        ).first()

        # Get validation type (Comprehensive)
        comprehensive_type = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == 'Validation Type',
            TaxonomyValue.code == 'COMPREHENSIVE'
        ).first()

        # Get priority (Medium)
        medium_priority = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == 'Validation Priority',
            TaxonomyValue.code == 'MEDIUM'
        ).first()

        if not (approved_status and in_progress_status and comprehensive_type and medium_priority):
            print("Error: Required taxonomy values not found.")
            return

        # Get existing models
        credit_model = db.query(Model).filter(Model.model_name.like('%Credit%')).first()
        if not credit_model:
            print("Error: No credit risk model found. Please run main seed script first.")
            return

        print(f"Found model: {credit_model.model_name} (ID: {credit_model.model_id})")

        # Create model versions
        print("\nCreating model versions...")

        version_1_0 = ModelVersion(
            model_id=credit_model.model_id,
            version_number="1.0.0",
            change_type="MAJOR",
            change_description="Initial production version",
            created_by_id=admin.user_id,
            created_at=datetime.utcnow() - timedelta(days=180)
        )
        db.add(version_1_0)
        db.flush()
        print(f"Created version 1.0.0 (ID: {version_1_0.version_id})")

        version_2_0 = ModelVersion(
            model_id=credit_model.model_id,
            version_number="2.0.0",
            change_type="MAJOR",
            change_description="Major algorithm update with new risk factors",
            created_by_id=admin.user_id,
            created_at=datetime.utcnow() - timedelta(days=90)
        )
        db.add(version_2_0)
        db.flush()
        print(f"Created version 2.0.0 (ID: {version_2_0.version_id})")

        version_2_1 = ModelVersion(
            model_id=credit_model.model_id,
            version_number="2.1.0",
            change_type="MINOR",
            change_description="Performance improvements and bug fixes",
            created_by_id=admin.user_id,
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        db.add(version_2_1)
        db.flush()
        print(f"Created version 2.1.0 (ID: {version_2_1.version_id})")

        # Create validation requests
        print("\nCreating validation requests...")

        # Validation for version 2.0.0 - APPROVED
        validation_v2 = ValidationRequest(
            current_status_id=approved_status.value_id,
            validation_type_id=comprehensive_type.value_id,
            priority_id=medium_priority.value_id,
            requestor_id=admin.user_id,
            request_date=datetime.utcnow() - timedelta(days=85),
            target_completion_date=datetime.utcnow() - timedelta(days=45),
            created_at=datetime.utcnow() - timedelta(days=85),
            updated_at=datetime.utcnow() - timedelta(days=80)
        )
        db.add(validation_v2)
        db.flush()
        print(f"Created validation request {validation_v2.request_id} for v2.0.0 (APPROVED)")

        # Link validation to version
        link_v2 = ValidationRequestModelVersion(
            request_id=validation_v2.request_id,
            model_id=credit_model.model_id,
            version_id=version_2_0.version_id
        )
        db.add(link_v2)

        # Update version with validation request ID
        version_2_0.validation_request_id = validation_v2.request_id

        # Validation for version 2.1.0 - IN PROGRESS
        validation_v2_1 = ValidationRequest(
            current_status_id=in_progress_status.value_id,
            validation_type_id=comprehensive_type.value_id,
            priority_id=medium_priority.value_id,
            requestor_id=admin.user_id,
            request_date=datetime.utcnow() - timedelta(days=25),
            target_completion_date=datetime.utcnow() + timedelta(days=15),
            created_at=datetime.utcnow() - timedelta(days=25),
            updated_at=datetime.utcnow() - timedelta(days=5)
        )
        db.add(validation_v2_1)
        db.flush()
        print(f"Created validation request {validation_v2_1.request_id} for v2.1.0 (IN PROGRESS)")

        # Link validation to version
        link_v2_1 = ValidationRequestModelVersion(
            request_id=validation_v2_1.request_id,
            model_id=credit_model.model_id,
            version_id=version_2_1.version_id
        )
        db.add(link_v2_1)

        # Update version with validation request ID
        version_2_1.validation_request_id = validation_v2_1.request_id

        # Create regional approvals for v2.0.0 validation
        print("\nCreating regional approvals...")

        # US Regional Approval - APPROVED
        approval_us = ValidationApproval(
            request_id=validation_v2.request_id,
            approver_id=validator.user_id,
            approver_role="Regional Validator - Americas",
            approval_type="Regional",
            region_id=us_region.region_id,
            is_required=True,
            approval_status="Approved",
            comments="Approved for US deployment after comprehensive review",
            approved_at=datetime.utcnow() - timedelta(days=80),
            created_at=datetime.utcnow() - timedelta(days=82)
        )
        db.add(approval_us)
        print(f"Created US regional approval (Approved)")

        # EU Regional Approval - APPROVED
        approval_eu = ValidationApproval(
            request_id=validation_v2.request_id,
            approver_id=validator.user_id,
            approver_role="Regional Validator - EMEA",
            approval_type="Regional",
            region_id=eu_region.region_id,
            is_required=True,
            approval_status="Approved",
            comments="Approved for EU deployment with GDPR compliance confirmed",
            approved_at=datetime.utcnow() - timedelta(days=79),
            created_at=datetime.utcnow() - timedelta(days=82)
        )
        db.add(approval_eu)
        print(f"Created EU regional approval (Approved)")

        # UK Regional Approval - PENDING (for v2.1.0)
        approval_uk = ValidationApproval(
            request_id=validation_v2_1.request_id,
            approver_id=validator.user_id,
            approver_role="Regional Validator - UK",
            approval_type="Regional",
            region_id=uk_region.region_id,
            is_required=True,
            approval_status="Pending",
            comments=None,
            approved_at=None,
            created_at=datetime.utcnow() - timedelta(days=25)
        )
        db.add(approval_uk)
        print(f"Created UK regional approval (Pending)")

        # Deploy versions to regions
        print("\nDeploying versions to regions...")

        # Create model_region records with deployed versions

        # US deployment - v2.0.0
        mr_us = ModelRegion(
            model_id=credit_model.model_id,
            region_id=us_region.region_id,
            version_id=version_2_0.version_id,
            deployed_at=datetime.utcnow() - timedelta(days=75),
            deployment_notes="Production deployment following validation approval"
        )
        db.add(mr_us)
        print(f"Deployed v2.0.0 to US region")

        # EU deployment - v2.0.0
        mr_eu = ModelRegion(
            model_id=credit_model.model_id,
            region_id=eu_region.region_id,
            version_id=version_2_0.version_id,
            deployed_at=datetime.utcnow() - timedelta(days=74),
            deployment_notes="Production deployment with GDPR compliance"
        )
        db.add(mr_eu)
        print(f"Deployed v2.0.0 to EU region")

        # UK deployment - v1.0.0 (legacy)
        mr_uk = ModelRegion(
            model_id=credit_model.model_id,
            region_id=uk_region.region_id,
            version_id=version_1_0.version_id,
            deployed_at=datetime.utcnow() - timedelta(days=170),
            deployment_notes="Legacy version pending upgrade to v2.1.0"
        )
        db.add(mr_uk)
        print(f"Deployed v1.0.0 to UK region (legacy)")

        db.commit()
        print("\n✅ Regional compliance demo data seeded successfully!")
        print("\nSummary:")
        print(f"- Created 3 model versions: 1.0.0, 2.0.0, 2.1.0")
        print(f"- Created 2 validation requests (1 APPROVED, 1 IN PROGRESS)")
        print(f"- Created 3 regional approvals (2 Approved, 1 Pending)")
        print(f"- Deployed versions to 3 regions (US: v2.0.0, EU: v2.0.0, UK: v1.0.0)")
        print("\nYou can now view the Regional Compliance Report at /reports/regional-compliance")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding data: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_regional_demo()
