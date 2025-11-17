"""Seed minimal reference data."""
import re
from datetime import datetime
from typing import Dict, List
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import User, UserRole, Vendor, EntraUser, Taxonomy, TaxonomyValue


REGULATORY_CATEGORY_VALUES = [
    {"label": "CCAR / DFAST Stress Testing",
        "description": "Models used for Federal Reserve stress tests and internal CCAR projections."},
    {"label": "Basel Regulatory Capital – Credit Risk (RWA)",
     "description": "Calculates Basel risk-weighted assets for credit portfolios (PD/LGD/EAD)."},
    {"label": "Market Risk Capital (VaR / FRTB / Stressed VaR / RNIV)",
     "description": "Trading book capital models including VaR, stressed VaR, RNIV, and FRTB."},
    {"label": "Counterparty Credit Risk / CVA Capital",
        "description": "Exposure, PFE, and CVA models supporting counterparty credit risk capital."},
    {"label": "Internal Economic Capital / ICAAP",
        "description": "Economic capital and ICAAP models beyond regulatory minima."},
    {"label": "CECL / Allowance for Credit Losses (ACL)",
     "description": "Expected credit loss and allowance models under U.S. GAAP CECL."},
    {"label": "IFRS 9 Expected Credit Loss",
        "description": "IFRS 9 staging and expected credit loss models for non-U.S. entities."},
    {"label": "Fair Value / Valuation for Financial Reporting",
        "description": "ASC 820 fair value and valuation models for financial reporting."},
    {"label": "Liquidity Risk & LCR / NSFR",
        "description": "Liquidity coverage, NSFR, and cashflow forecasting models."},
    {"label": "Interest Rate Risk in the Banking Book (IRRBB)",
     "description": "IRRBB models for EVE/NII metrics and customer behaviour assumptions."},
    {"label": "Asset/Liability Management (ALM) / FTP",
     "description": "Structural balance sheet, FTP, and hedge optimization models."},
    {"label": "AML / Sanctions / Transaction Monitoring",
        "description": "AML/BSA transaction monitoring, sanctions screening, and customer risk scoring."},
    {"label": "Fraud Detection",
        "description": "Fraud detection across cards, payments, and digital channels."},
    {"label": "Conduct Risk / Fair Lending / UDAAP",
        "description": "Models supporting conduct, fair lending, and UDAAP surveillance."},
    {"label": "Operational Risk Capital / Scenario Models",
        "description": "Operational risk capital, LDA, and scenario aggregation models."},
    {"label": "Regulatory Reporting (FFIEC, FR Y-9C, FR Y-14, Call Reports, etc.)",
     "description": "Models feeding data to regulatory reports and schedules."},
    {"label": "Internal Risk & Board Reporting",
        "description": "Models that drive internal risk dashboards and board reporting."},
    {"label": "Pricing & Valuation – Internal / Customer",
        "description": "Pricing and valuation models used primarily for business decisioning."},
    {"label": "Margin & Collateral Models (IM / VM / Haircuts)",
     "description": "Margin, collateral, and haircut models for IM/VM and eligibility."},
    {"label": "Model Risk Management / Meta-Models",
        "description": "Models that quantify or aggregate model risk (scores, capital add-ons)."},
    {"label": "Non-Regulatory / Business Only",
        "description": "Business-impacting models with no direct regulatory regime linkage."},
]


MODEL_TYPE_VALUES = [
    {"label": "Retail PD Model",
        "description": "Predicts probability of default for retail exposures."},
    {"label": "Wholesale PD Model",
        "description": "Predicts probability of default for wholesale obligors."},
    {"label": "LGD Model (Loss Given Default)",
     "description": "Estimates loss severity conditional on default."},
    {"label": "EAD / CCF Model (Exposure at Default / Credit Conversion Factor)",
     "description": "Estimates exposure or credit conversion factors at default."},
    {"label": "Application Scorecard",
        "description": "Origination scorecard for approve/decline, limits, and pricing."},
    {"label": "Behavioural Scorecard",
        "description": "Scores existing accounts based on recent behaviour."},
    {"label": "Collections Scorecard",
        "description": "Prioritizes delinquent accounts for collections strategies."},
    {"label": "Internal Rating Model – Obligor / Facility",
        "description": "Assigns internal ratings mapped to PD/LGD bands."},
    {"label": "Transition / Migration / Roll-Rate Model",
        "description": "Projects migrations between delinquency or rating states."},
    {"label": "Prepayment / Early Termination Model",
        "description": "Predicts early payoff, refinance, or attrition."},
    {"label": "Cure / Recovery Process Model",
        "description": "Models probability, timing, and magnitude of cure or recovery."},
    {"label": "Pricing Model – Linear Instruments",
        "description": "Values bonds, swaps, forwards, and other linear instruments."},
    {"label": "Pricing Model – Options & Exotics",
        "description": "Values options and structured products using advanced methods."},
    {"label": "Curve / Surface Construction Model",
        "description": "Builds discount curves, credit curves, vol surfaces, and correlations."},
    {"label": "VaR / Expected Shortfall (ES) Model",
     "description": "Computes market risk via VaR or ES methodologies."},
    {"label": "Sensitivity / Greeks Aggregation Model",
        "description": "Aggregates position sensitivities for hedging or limits."},
    {"label": "XVA Model (CVA / DVA / FVA / MVA)",
     "description": "Calculates derivative valuation adjustments."},
    {"label": "Risk Factor Simulation / Scenario Generator",
        "description": "Simulates joint paths of market risk factors."},
    {"label": "Non-Maturity Deposit (NMD) Model",
     "description": "Models NMD balances, stability, and rate sensitivity."},
    {"label": "Liquidity Runoff / Survival Horizon Model",
        "description": "Projects stressed inflows/outflows and survival horizons."},
    {"label": "Balance Sheet Evolution / Dynamic Balance Sheet Model",
        "description": "Simulates balance sheet composition under scenarios."},
    {"label": "IRRBB Model (EVE / NII Simulation)",
     "description": "Projects EVE/NII impacts under rate scenarios."},
    {"label": "Funds Transfer Pricing (FTP) Model",
     "description": "Allocates funding and liquidity costs across products."},
    {"label": "Lifetime Loss / Expected Credit Loss (ECL) Engine",
     "description": "Combines components to produce lifetime expected losses."},
    {"label": "Provision / Reserve Allocation Model",
        "description": "Allocates allowance or reserves across portfolios."},
    {"label": "Economic Capital / Unexpected Loss Model",
        "description": "Computes economic capital via loss distributions and correlations."},
    {"label": "Stress Testing Projection Model (Top-Down / Bottom-Up)",
     "description": "Generates stressed projections of PPNR, losses, and capital."},
    {"label": "Regulatory Metric Calculation Engine",
        "description": "Calculates regulatory ratios such as capital, leverage, or liquidity."},
    {"label": "Transaction Monitoring / Alert Generation Model (AML)",
     "description": "Scores transactions or accounts and issues AML alerts."},
    {"label": "Customer Risk Rating (CRR) Model – AML/KYC",
     "description": "Assigns inherent AML risk scores to customers."},
    {"label": "Sanctions Screening Matching Model",
        "description": "Performs sanctions list matching and similarity scoring."},
    {"label": "Fraud Detection Model",
        "description": "Detects fraudulent transactions or accounts across channels."},
    {"label": "Fair Lending / Fairness Assessment Model",
        "description": "Quantifies disparate impact or bias in credit processes."},
    {"label": "Operational Risk Capital Model (Loss Distribution Approach)",
     "description": "Fits severity/frequency and computes op-risk capital."},
    {"label": "Operational Risk Scenario Model",
        "description": "Aggregates scenario-based operational risk losses."},
    {"label": "Conduct Risk / Complaints Scoring Model",
        "description": "Scores complaints or events for conduct risk severity."},
    {"label": "Vendor / Third-Party Risk Scoring Model",
        "description": "Scores third parties based on inherent risk and controls."},
    {"label": "Propensity / Next-Best-Offer Model",
        "description": "Predicts acceptance likelihood for offers or products."},
    {"label": "Churn / Attrition Model",
        "description": "Predicts likelihood a customer will leave or reduce activity."},
    {"label": "Pricing & Elasticity Model",
        "description": "Estimates demand or margin sensitivity to pricing changes."},
    {"label": "Segmentation / Clustering Model",
        "description": "Groups customers or exposures into segments."},
    {"label": "Forecasting Model – Volumes / Revenues / KPIs",
        "description": "Forecasts balances, volumes, revenues, or KPIs."},
    {"label": "Aggregation / Composite Index Model",
        "description": "Combines multiple inputs into composite indices."},
    {"label": "Mapping / Allocation Model",
        "description": "Allocates metrics between dimensions or entities."},
    {"label": "Model Risk Scoring / Model Tiering Model",
        "description": "Scores models to determine tiering and validation intensity."},
]


def _code_from_label(label: str) -> str:
    """Create a deterministic code from a taxonomy label."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")
    return slug.upper()[:50] or "VALUE"


def _upsert_taxonomy_with_values(
    db,
    *,
    name: str,
    description: str,
    values: List[Dict[str, str]],
    is_system: bool = True,
):
    """Create or update a taxonomy and its managed values."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.name == name).first()
    created = False
    if not taxonomy:
        taxonomy = Taxonomy(
            name=name,
            description=description,
            is_system=is_system,
            created_at=datetime.utcnow(),
        )
        db.add(taxonomy)
        db.flush()
        created = True
    else:
        taxonomy.description = description
        taxonomy.is_system = is_system

    existing_values = {
        value.code: value
        for value in db.query(TaxonomyValue).filter(TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id)
    }

    for sort_order, entry in enumerate(values, start=1):
        code = entry.get("code") or _code_from_label(entry["label"])
        record = existing_values.get(code)
        if record:
            record.label = entry["label"]
            record.description = entry.get("description")
            record.sort_order = sort_order
            record.is_active = True
        else:
            db.add(
                TaxonomyValue(
                    taxonomy_id=taxonomy.taxonomy_id,
                    code=code,
                    label=entry["label"],
                    description=entry.get("description"),
                    sort_order=sort_order,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
            )

    print(f"✓ {'Created' if created else 'Updated'} taxonomy: {name} ({len(values)} values managed)")


def seed_taxonomy_reference_data(db):
    """Ensure the Regulatory Category and Model Type taxonomies exist."""
    _upsert_taxonomy_with_values(
        db,
        name="Regulatory Category",
        description="Regulatory or prudential regimes tied to a model's outputs.",
        values=REGULATORY_CATEGORY_VALUES,
    )
    _upsert_taxonomy_with_values(
        db,
        name="Model Type",
        description="Functional classification describing what the model does.",
        values=MODEL_TYPE_VALUES,
    )


def seed_database():
    """Seed essential data."""
    db = SessionLocal()

    try:
        print("Starting database seeding...")

        # Create admin user
        admin = db.query(User).filter(
            User.email == "admin@example.com").first()
        if not admin:
            admin = User(
                email="admin@example.com",
                full_name="Admin User",
                password_hash=get_password_hash("admin123"),
                role=UserRole.ADMIN
            )
            db.add(admin)
            db.commit()
            print("✓ Created admin user (admin@example.com / admin123)")
        else:
            print("✓ Admin user already exists")

        # Create sample vendors
        sample_vendors = [
            {"name": "Bloomberg", "contact_info": "support@bloomberg.com"},
            {"name": "Moody's Analytics", "contact_info": "analytics@moodys.com"},
            {"name": "MSCI", "contact_info": "clientservice@msci.com"},
            {"name": "S&P Global", "contact_info": "support@spglobal.com"},
            {"name": "FactSet", "contact_info": "support@factset.com"},
        ]

        for vendor_data in sample_vendors:
            existing = db.query(Vendor).filter(
                Vendor.name == vendor_data["name"]).first()
            if not existing:
                vendor = Vendor(**vendor_data)
                db.add(vendor)
                print(f"✓ Created vendor: {vendor_data['name']}")
            else:
                print(f"✓ Vendor already exists: {vendor_data['name']}")

        db.commit()

        # Create mock Microsoft Entra directory users
        entra_users = [
            {
                "entra_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "user_principal_name": "john.smith@contoso.com",
                "display_name": "John Smith",
                "given_name": "John",
                "surname": "Smith",
                "mail": "john.smith@contoso.com",
                "job_title": "Senior Risk Analyst",
                "department": "Model Risk Management",
                "office_location": "New York",
                "mobile_phone": "+1-212-555-0101",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
                "user_principal_name": "sarah.johnson@contoso.com",
                "display_name": "Sarah Johnson",
                "given_name": "Sarah",
                "surname": "Johnson",
                "mail": "sarah.johnson@contoso.com",
                "job_title": "Model Developer",
                "department": "Quantitative Research",
                "office_location": "Chicago",
                "mobile_phone": "+1-312-555-0202",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
                "user_principal_name": "michael.chen@contoso.com",
                "display_name": "Michael Chen",
                "given_name": "Michael",
                "surname": "Chen",
                "mail": "michael.chen@contoso.com",
                "job_title": "Risk Manager",
                "department": "Enterprise Risk",
                "office_location": "San Francisco",
                "mobile_phone": "+1-415-555-0303",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "d4e5f6a7-b8c9-0123-defa-456789012345",
                "user_principal_name": "emily.davis@contoso.com",
                "display_name": "Emily Davis",
                "given_name": "Emily",
                "surname": "Davis",
                "mail": "emily.davis@contoso.com",
                "job_title": "Data Scientist",
                "department": "Analytics",
                "office_location": "Boston",
                "mobile_phone": "+1-617-555-0404",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "e5f6a7b8-c9d0-1234-efab-567890123456",
                "user_principal_name": "robert.wilson@contoso.com",
                "display_name": "Robert Wilson",
                "given_name": "Robert",
                "surname": "Wilson",
                "mail": "robert.wilson@contoso.com",
                "job_title": "Compliance Officer",
                "department": "Compliance",
                "office_location": "New York",
                "mobile_phone": "+1-212-555-0505",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "f6a7b8c9-d0e1-2345-fabc-678901234567",
                "user_principal_name": "jennifer.martinez@contoso.com",
                "display_name": "Jennifer Martinez",
                "given_name": "Jennifer",
                "surname": "Martinez",
                "mail": "jennifer.martinez@contoso.com",
                "job_title": "VP of Model Risk",
                "department": "Model Risk Management",
                "office_location": "New York",
                "mobile_phone": "+1-212-555-0606",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "a7b8c9d0-e1f2-3456-abcd-789012345678",
                "user_principal_name": "david.brown@contoso.com",
                "display_name": "David Brown",
                "given_name": "David",
                "surname": "Brown",
                "mail": "david.brown@contoso.com",
                "job_title": "Junior Analyst",
                "department": "Model Risk Management",
                "office_location": "Chicago",
                "mobile_phone": "+1-312-555-0707",
                "account_enabled": True,
                "created_at": datetime.utcnow()
            },
            {
                "entra_id": "b8c9d0e1-f2a3-4567-bcde-890123456789",
                "user_principal_name": "lisa.anderson@contoso.com",
                "display_name": "Lisa Anderson",
                "given_name": "Lisa",
                "surname": "Anderson",
                "mail": "lisa.anderson@contoso.com",
                "job_title": "IT Security Specialist",
                "department": "Information Technology",
                "office_location": "Austin",
                "mobile_phone": "+1-512-555-0808",
                "account_enabled": False,  # Disabled account
                "created_at": datetime.utcnow()
            },
        ]

        for entra_data in entra_users:
            existing = db.query(EntraUser).filter(
                EntraUser.entra_id == entra_data["entra_id"]
            ).first()
            if not existing:
                entra_user = EntraUser(**entra_data)
                db.add(entra_user)
                print(f"✓ Created Entra user: {entra_data['display_name']}")
            else:
                print(
                    f"✓ Entra user already exists: {entra_data['display_name']}")

        db.commit()

        # Create taxonomies
        taxonomies_data = [
            {
                "name": "Model Risk Tier",
                "description": "Risk classification tiers for model criticality and materiality",
                "is_system": True,
                "values": [
                    {
                        "code": "TIER_1",
                        "label": "Tier 1 - High Risk",
                        "description": "Critical models with significant financial or regulatory impact. Require comprehensive validation and frequent monitoring.",
                        "sort_order": 1
                    },
                    {
                        "code": "TIER_2",
                        "label": "Tier 2 - Medium Risk",
                        "description": "Important models with moderate impact. Require standard validation and periodic monitoring.",
                        "sort_order": 2
                    },
                    {
                        "code": "TIER_3",
                        "label": "Tier 3 - Low Risk",
                        "description": "Non-critical models with limited impact. Require basic validation and less frequent monitoring.",
                        "sort_order": 3
                    },
                ]
            },
            {
                "name": "Validation Type",
                "description": "Types of model validation activities",
                "is_system": True,
                "values": [
                    {
                        "code": "INITIAL",
                        "label": "Initial Validation",
                        "description": "First-time validation of a new model before production deployment",
                        "sort_order": 1
                    },
                    {
                        "code": "ANNUAL",
                        "label": "Annual Review",
                        "description": "Regular annual review to ensure continued model appropriateness",
                        "sort_order": 2
                    },
                    {
                        "code": "COMPREHENSIVE",
                        "label": "Comprehensive Validation",
                        "description": "Full deep-dive validation covering all aspects of model performance",
                        "sort_order": 3
                    },
                    {
                        "code": "TARGETED",
                        "label": "Targeted Review",
                        "description": "Focused review on specific model aspects or identified issues",
                        "sort_order": 4
                    },
                    {
                        "code": "ONGOING",
                        "label": "Ongoing Monitoring",
                        "description": "Continuous monitoring of model performance metrics",
                        "sort_order": 5
                    },
                ]
            },
            {
                "name": "Validation Outcome",
                "description": "Results of model validation activities",
                "is_system": True,
                "values": [
                    {
                        "code": "PASS",
                        "label": "Pass",
                        "description": "Model validation passed with no material findings",
                        "sort_order": 1
                    },
                    {
                        "code": "PASS_WITH_FINDINGS",
                        "label": "Pass with Findings",
                        "description": "Model validation passed but with findings that require remediation",
                        "sort_order": 2
                    },
                    {
                        "code": "FAIL",
                        "label": "Fail",
                        "description": "Model validation failed and requires significant remediation",
                        "sort_order": 3
                    },
                ]
            },
            {
                "name": "Validation Scope",
                "description": "Scope and methodology of model validation",
                "is_system": True,
                "values": [
                    {
                        "code": "FULL_SCOPE",
                        "label": "Full Scope",
                        "description": "Comprehensive validation covering all aspects of the model",
                        "sort_order": 1
                    },
                    {
                        "code": "CONCEPTUAL_SOUNDNESS",
                        "label": "Conceptual Soundness",
                        "description": "Review of model theory, assumptions, and mathematical formulation",
                        "sort_order": 2
                    },
                    {
                        "code": "DATA_QUALITY",
                        "label": "Data Quality",
                        "description": "Assessment of input data quality, completeness, and appropriateness",
                        "sort_order": 3
                    },
                    {
                        "code": "IMPLEMENTATION_TESTING",
                        "label": "Implementation Testing",
                        "description": "Verification of model implementation and code correctness",
                        "sort_order": 4
                    },
                    {
                        "code": "PERFORMANCE_MONITORING",
                        "label": "Performance Monitoring",
                        "description": "Ongoing monitoring of model performance and stability",
                        "sort_order": 5
                    },
                ]
            }
        ]

        for tax_data in taxonomies_data:
            existing_tax = db.query(Taxonomy).filter(
                Taxonomy.name == tax_data["name"]
            ).first()
            if not existing_tax:
                taxonomy = Taxonomy(
                    name=tax_data["name"],
                    description=tax_data["description"],
                    is_system=tax_data["is_system"],
                    created_at=datetime.utcnow()
                )
                db.add(taxonomy)
                db.commit()
                db.refresh(taxonomy)

                # Add values
                for val_data in tax_data["values"]:
                    value = TaxonomyValue(
                        taxonomy_id=taxonomy.taxonomy_id,
                        code=val_data["code"],
                        label=val_data["label"],
                        description=val_data["description"],
                        sort_order=val_data["sort_order"],
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(value)
                print(
                    f"✓ Created taxonomy: {tax_data['name']} with {len(tax_data['values'])} values")
            else:
                print(f"✓ Taxonomy already exists: {tax_data['name']}")

        db.commit()

        # Seed reference taxonomies for Regulatory Category and Model Type
        seed_taxonomy_reference_data(db)
        db.commit()

        print("\nSeeding completed successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
