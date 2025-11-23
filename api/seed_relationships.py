"""
Seed script for model relationships (hierarchy and dependencies).
Run after main seed.py to add example relationship data for UAT.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Model, ModelHierarchy, ModelFeedDependency, TaxonomyValue, Taxonomy


def seed_relationships():
    """Seed model hierarchy and dependency relationships."""
    db: Session = SessionLocal()

    try:
        print("Starting relationship seed...")

        # Get taxonomy values
        hierarchy_type = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Model Hierarchy Type",
            TaxonomyValue.code == "SUB_MODEL"
        ).first()

        if not hierarchy_type:
            print("ERROR: Model Hierarchy Type taxonomy not found. Run main seed first.")
            return

        dependency_types = {
            "INPUT_DATA": db.query(TaxonomyValue).join(Taxonomy).filter(
                Taxonomy.name == "Model Dependency Type",
                TaxonomyValue.code == "INPUT_DATA"
            ).first(),
            "SCORE": db.query(TaxonomyValue).join(Taxonomy).filter(
                Taxonomy.name == "Model Dependency Type",
                TaxonomyValue.code == "SCORE"
            ).first(),
            "PARAMETER": db.query(TaxonomyValue).join(Taxonomy).filter(
                Taxonomy.name == "Model Dependency Type",
                TaxonomyValue.code == "PARAMETER"
            ).first(),
        }

        if not all(dependency_types.values()):
            print("ERROR: Model Dependency Type taxonomy not found. Run main seed first.")
            return

        # Get or create models for relationships
        models = {}
        model_data = [
            {"name": "Enterprise Credit Risk Model", "desc": "Composite model for enterprise-wide credit risk"},
            {"name": "Probability of Default (PD) Model", "desc": "Sub-model: Estimates probability of borrower default"},
            {"name": "Loss Given Default (LGD) Model", "desc": "Sub-model: Estimates loss severity upon default"},
            {"name": "Exposure at Default (EAD) Model", "desc": "Sub-model: Estimates exposure amount at default"},
            {"name": "Market Data Feed", "desc": "Upstream: Provides market rates and indices"},
            {"name": "Pricing Engine", "desc": "Mid-stream: Calculates fair value pricing"},
            {"name": "Portfolio VaR Model", "desc": "Downstream: Computes portfolio Value at Risk"},
            {"name": "Collateral Valuation Model", "desc": "Provides collateral values"},
            {"name": "Stress Testing Model", "desc": "Uses outputs from multiple models"},
        ]

        for i, md in enumerate(model_data, start=1):
            existing = db.query(Model).filter(Model.model_name == md["name"]).first()
            if existing:
                models[md["name"]] = existing
                print(f"Using existing model: {md['name']}")
            else:
                # Get first user for ownership
                from app.models.user import User
                owner = db.query(User).filter(User.role == "Admin").first()
                if not owner:
                    owner = db.query(User).first()

                model = Model(
                    model_name=md["name"],
                    description=md["desc"],
                    development_type="In-House",
                    status="Active",
                    owner_id=owner.user_id,
                    row_approval_status="approved"
                )
                db.add(model)
                db.flush()
                models[md["name"]] = model
                print(f"Created model: {md['name']}")

        db.commit()

        # Create Hierarchy Relationships
        print("\n=== Creating Hierarchy Relationships ===")

        hierarchy_relationships = [
            {
                "parent": "Enterprise Credit Risk Model",
                "child": "Probability of Default (PD) Model",
                "notes": "PD component of composite credit risk framework"
            },
            {
                "parent": "Enterprise Credit Risk Model",
                "child": "Loss Given Default (LGD) Model",
                "notes": "LGD component of composite credit risk framework"
            },
            {
                "parent": "Enterprise Credit Risk Model",
                "child": "Exposure at Default (EAD) Model",
                "notes": "EAD component of composite credit risk framework"
            },
        ]

        for rel in hierarchy_relationships:
            parent = models.get(rel["parent"])
            child = models.get(rel["child"])

            if not parent or not child:
                print(f"WARNING: Skipping hierarchy {rel['parent']} → {rel['child']} (models not found)")
                continue

            # Check if relationship already exists
            existing = db.query(ModelHierarchy).filter(
                ModelHierarchy.parent_model_id == parent.model_id,
                ModelHierarchy.child_model_id == child.model_id
            ).first()

            if existing:
                print(f"Hierarchy already exists: {rel['parent']} → {rel['child']}")
                continue

            hierarchy = ModelHierarchy(
                parent_model_id=parent.model_id,
                child_model_id=child.model_id,
                relation_type_id=hierarchy_type.value_id,
                effective_date=date.today() - timedelta(days=180),
                notes=rel["notes"]
            )
            db.add(hierarchy)
            print(f"✓ Created hierarchy: {rel['parent']} → {rel['child']}")

        db.commit()

        # Create Dependency Relationships
        print("\n=== Creating Dependency Relationships ===")

        dependency_relationships = [
            {
                "feeder": "Market Data Feed",
                "consumer": "Pricing Engine",
                "type": "INPUT_DATA",
                "desc": "Market rates and yield curves for pricing calculations"
            },
            {
                "feeder": "Pricing Engine",
                "consumer": "Portfolio VaR Model",
                "type": "SCORE",
                "desc": "Fair value prices used in VaR calculations"
            },
            {
                "feeder": "Collateral Valuation Model",
                "consumer": "Loss Given Default (LGD) Model",
                "type": "INPUT_DATA",
                "desc": "Collateral values reduce loss given default"
            },
            {
                "feeder": "Probability of Default (PD) Model",
                "consumer": "Stress Testing Model",
                "type": "SCORE",
                "desc": "PD scores used in stress scenario analysis"
            },
            {
                "feeder": "Portfolio VaR Model",
                "consumer": "Stress Testing Model",
                "type": "INPUT_DATA",
                "desc": "VaR metrics feed into comprehensive stress tests"
            },
            {
                "feeder": "Market Data Feed",
                "consumer": "Stress Testing Model",
                "type": "PARAMETER",
                "desc": "Market parameters for stress scenario calibration"
            },
        ]

        for rel in dependency_relationships:
            feeder = models.get(rel["feeder"])
            consumer = models.get(rel["consumer"])
            dep_type = dependency_types.get(rel["type"])

            if not feeder or not consumer or not dep_type:
                print(f"WARNING: Skipping dependency {rel['feeder']} → {rel['consumer']} (models/type not found)")
                continue

            # Check if relationship already exists
            existing = db.query(ModelFeedDependency).filter(
                ModelFeedDependency.feeder_model_id == feeder.model_id,
                ModelFeedDependency.consumer_model_id == consumer.model_id,
                ModelFeedDependency.dependency_type_id == dep_type.value_id
            ).first()

            if existing:
                print(f"Dependency already exists: {rel['feeder']} → {rel['consumer']}")
                continue

            dependency = ModelFeedDependency(
                feeder_model_id=feeder.model_id,
                consumer_model_id=consumer.model_id,
                dependency_type_id=dep_type.value_id,
                description=rel["desc"],
                effective_date=date.today() - timedelta(days=90),
                is_active=True
            )
            db.add(dependency)
            print(f"✓ Created dependency: {rel['feeder']} → {rel['consumer']} ({rel['type']})")

        db.commit()

        # Print summary
        print("\n=== Seeding Complete ===")
        total_hierarchies = db.query(ModelHierarchy).count()
        total_dependencies = db.query(ModelFeedDependency).count()
        print(f"Total hierarchies: {total_hierarchies}")
        print(f"Total dependencies: {total_dependencies}")

        print("\n=== Example Models for UAT ===")
        print(f"1. View 'Enterprise Credit Risk Model' (ID: {models['Enterprise Credit Risk Model'].model_id})")
        print("   - Has 3 sub-models (PD, LGD, EAD)")
        print(f"\n2. View 'Portfolio VaR Model' (ID: {models['Portfolio VaR Model'].model_id})")
        print("   - Has inbound dependency from Pricing Engine")
        print("   - Has outbound dependency to Stress Testing Model")
        print(f"\n3. View 'Stress Testing Model' (ID: {models['Stress Testing Model'].model_id})")
        print("   - Has multiple inbound dependencies (shows data lineage)")

    except Exception as e:
        print(f"ERROR during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_relationships()
