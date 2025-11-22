"""Seed minimal reference data."""
import re
from datetime import datetime, date, timedelta
from typing import Dict, List
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import User, UserRole, Vendor, EntraUser, Taxonomy, TaxonomyValue, ValidationWorkflowSLA, ValidationPolicy, Region, ValidationComponentDefinition, ComponentDefinitionConfiguration, ComponentDefinitionConfigItem
from app.models.model import Model


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
    {"code": "RETAIL_PD", "label": "Retail PD Model",
        "description": "Predicts probability of default for retail exposures."},
    {"code": "WHOLESALE_PD", "label": "Wholesale PD Model",
        "description": "Predicts probability of default for wholesale obligors."},
    {"code": "LGD", "label": "LGD Model (Loss Given Default)",
     "description": "Estimates loss severity conditional on default."},
    {"code": "EAD_CCF", "label": "EAD / CCF Model (Exposure at Default / Credit Conversion Factor)",
     "description": "Estimates exposure or credit conversion factors at default."},
    {"code": "APP_SCORECARD", "label": "Application Scorecard",
        "description": "Origination scorecard for approve/decline, limits, and pricing."},
    {"code": "BEHAV_SCORECARD", "label": "Behavioural Scorecard",
        "description": "Scores existing accounts based on recent behaviour."},
    {"code": "COLL_SCORECARD", "label": "Collections Scorecard",
        "description": "Prioritizes delinquent accounts for collections strategies."},
    {"code": "INTERNAL_RATING", "label": "Internal Rating Model – Obligor / Facility",
        "description": "Assigns internal ratings mapped to PD/LGD bands."},
    {"code": "TRANSITION_MATRIX", "label": "Transition / Migration / Roll-Rate Model",
        "description": "Projects migrations between delinquency or rating states."},
    {"code": "PREPAYMENT", "label": "Prepayment / Early Termination Model",
        "description": "Predicts early payoff, refinance, or attrition."},
    {"code": "CURE_RECOVERY", "label": "Cure / Recovery Process Model",
        "description": "Models probability, timing, and magnitude of cure or recovery."},
    {"code": "PRICING_LINEAR", "label": "Pricing Model – Linear Instruments",
        "description": "Values bonds, swaps, forwards, and other linear instruments."},
    {"code": "PRICING_EXOTIC", "label": "Pricing Model – Options & Exotics",
        "description": "Values options and structured products using advanced methods."},
    {"code": "CURVE_CONSTRUCT", "label": "Curve / Surface Construction Model",
        "description": "Builds discount curves, credit curves, vol surfaces, and correlations."},
    {"code": "VAR_ES", "label": "VaR / Expected Shortfall (ES) Model",
     "description": "Computes market risk via VaR or ES methodologies."},
    {"code": "SENSITIVITY_AGG", "label": "Sensitivity / Greeks Aggregation Model",
        "description": "Aggregates position sensitivities for hedging or limits."},
    {"code": "XVA", "label": "XVA Model (CVA / DVA / FVA / MVA)",
     "description": "Calculates derivative valuation adjustments."},
    {"code": "RISK_SIMULATION", "label": "Risk Factor Simulation / Scenario Generator",
        "description": "Simulates joint paths of market risk factors."},
    {"code": "NMD", "label": "Non-Maturity Deposit (NMD) Model",
     "description": "Models NMD balances, stability, and rate sensitivity."},
    {"code": "LIQUIDITY_RUNOFF", "label": "Liquidity Runoff / Survival Horizon Model",
        "description": "Projects stressed inflows/outflows and survival horizons."},
    {"code": "BAL_SHEET_DYN", "label": "Balance Sheet Evolution / Dynamic Balance Sheet Model",
        "description": "Simulates balance sheet composition under scenarios."},
    {"code": "IRRBB", "label": "IRRBB Model (EVE / NII Simulation)",
     "description": "Projects EVE/NII impacts under rate scenarios."},
    {"code": "FTP", "label": "Funds Transfer Pricing (FTP) Model",
     "description": "Allocates funding and liquidity costs across products."},
    {"code": "ECL_ENGINE", "label": "Lifetime Loss / Expected Credit Loss (ECL) Engine",
     "description": "Combines components to produce lifetime expected losses."},
    {"code": "RESERVE_ALLOC", "label": "Provision / Reserve Allocation Model",
        "description": "Allocates allowance or reserves across portfolios."},
    {"code": "ECON_CAPITAL", "label": "Economic Capital / Unexpected Loss Model",
        "description": "Computes economic capital via loss distributions and correlations."},
    {"code": "STRESS_TEST_PROJ", "label": "Stress Testing Projection Model (Top-Down / Bottom-Up)",
     "description": "Generates stressed projections of PPNR, losses, and capital."},
    {"code": "REG_METRIC_CALC", "label": "Regulatory Metric Calculation Engine",
        "description": "Calculates regulatory ratios such as capital, leverage, or liquidity."},
    {"code": "AML_TXN_MON", "label": "Transaction Monitoring / Alert Generation Model (AML)",
     "description": "Scores transactions or accounts and issues AML alerts."},
    {"code": "AML_CUST_RISK", "label": "Customer Risk Rating (CRR) Model – AML/KYC",
     "description": "Assigns inherent AML risk scores to customers."},
    {"code": "SANCTIONS", "label": "Sanctions Screening Matching Model",
        "description": "Performs sanctions list matching and similarity scoring."},
    {"code": "FRAUD", "label": "Fraud Detection Model",
        "description": "Detects fraudulent transactions or accounts across channels."},
    {"code": "FAIR_LENDING", "label": "Fair Lending / Fairness Assessment Model",
        "description": "Quantifies disparate impact or bias in credit processes."},
    {"code": "OP_RISK_CAP", "label": "Operational Risk Capital Model (Loss Distribution Approach)",
     "description": "Fits severity/frequency and computes op-risk capital."},
    {"code": "OP_RISK_SCEN", "label": "Operational Risk Scenario Model",
        "description": "Aggregates scenario-based operational risk losses."},
    {"code": "CONDUCT_RISK", "label": "Conduct Risk / Complaints Scoring Model",
        "description": "Scores complaints or events for conduct risk severity."},
    {"code": "VENDOR_RISK", "label": "Vendor / Third-Party Risk Scoring Model",
        "description": "Scores third parties based on inherent risk and controls."},
    {"code": "PROPENSITY", "label": "Propensity / Next-Best-Offer Model",
        "description": "Predicts acceptance likelihood for offers or products."},
    {"code": "CHURN", "label": "Churn / Attrition Model",
        "description": "Predicts likelihood a customer will leave or reduce activity."},
    {"code": "PRICING_ELAST", "label": "Pricing & Elasticity Model",
        "description": "Estimates demand or margin sensitivity to pricing changes."},
    {"code": "SEGMENTATION", "label": "Segmentation / Clustering Model",
        "description": "Groups customers or exposures into segments."},
    {"code": "FORECAST_KPI", "label": "Forecasting Model – Volumes / Revenues / KPIs",
        "description": "Forecasts balances, volumes, revenues, or KPIs."},
    {"code": "AGGREGATION", "label": "Aggregation / Composite Index Model",
        "description": "Combines multiple inputs into composite indices."},
    {"code": "ALLOCATION", "label": "Mapping / Allocation Model",
        "description": "Allocates metrics between dimensions or entities."},
    {"code": "MRM_SCORING", "label": "Model Risk Scoring / Model Tiering Model",
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


def seed_validation_components(db):
    """Seed validation component definitions (Figure 3 matrix)."""
    # Check if already seeded
    existing_count = db.query(ValidationComponentDefinition).count()
    if existing_count > 0:
        print(f"✓ Validation component definitions already seeded ({existing_count} components)")
        return

    print("Seeding validation component definitions...")

    # Figure 3: Minimum Requirements for Validation Approach
    # Risk tiers: High (Comprehensive), Medium (Standard), Low (Conceptual), Very Low (Executive Summary)
    # Expectations: Required, IfApplicable, NotExpected

    components = [
        # Section 1 – Executive Summary
        {"section_number": "1", "section_title": "Executive Summary", "component_code": "1.1", "component_title": "Summary", "is_test_or_analysis": False, "sort_order": 1,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},
        {"section_number": "1", "section_title": "Executive Summary", "component_code": "1.2", "component_title": "Model Risk and Model Limitation", "is_test_or_analysis": False, "sort_order": 2,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},
        {"section_number": "1", "section_title": "Executive Summary", "component_code": "1.3", "component_title": "Recent Updates and Outstanding Issues", "is_test_or_analysis": False, "sort_order": 3,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "IfApplicable", "expectation_very_low": "IfApplicable"},
        {"section_number": "1", "section_title": "Executive Summary", "component_code": "1.4", "component_title": "Scorecard", "is_test_or_analysis": False, "sort_order": 4,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},
        {"section_number": "1", "section_title": "Executive Summary", "component_code": "1.5", "component_title": "Model Risk Ranking Template", "is_test_or_analysis": False, "sort_order": 5,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},

        # Section 2 – Introduction
        {"section_number": "2", "section_title": "Introduction", "component_code": "2.1", "component_title": "Purpose and Rationale for Modelling", "is_test_or_analysis": False, "sort_order": 6,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},
        {"section_number": "2", "section_title": "Introduction", "component_code": "2.2", "component_title": "Product Description", "is_test_or_analysis": False, "sort_order": 7,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "IfApplicable"},
        {"section_number": "2", "section_title": "Introduction", "component_code": "2.3", "component_title": "Regulatory Requirements", "is_test_or_analysis": False, "sort_order": 8,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "IfApplicable", "expectation_very_low": "IfApplicable"},
        {"section_number": "2", "section_title": "Introduction", "component_code": "2.4", "component_title": "Validation Scope", "is_test_or_analysis": False, "sort_order": 9,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},

        # Section 3 – Evaluation of Conceptual Soundness
        {"section_number": "3", "section_title": "Evaluation of Conceptual Soundness", "component_code": "3.1", "component_title": "Model Methodology", "is_test_or_analysis": False, "sort_order": 10,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},
        {"section_number": "3", "section_title": "Evaluation of Conceptual Soundness", "component_code": "3.2", "component_title": "Model Development Data", "is_test_or_analysis": False, "sort_order": 11,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},
        {"section_number": "3", "section_title": "Evaluation of Conceptual Soundness", "component_code": "3.3", "component_title": "Model Assumptions and Simplifications", "is_test_or_analysis": False, "sort_order": 12,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "IfApplicable"},
        {"section_number": "3", "section_title": "Evaluation of Conceptual Soundness", "component_code": "3.4", "component_title": "Model Inputs and Model Outputs", "is_test_or_analysis": False, "sort_order": 13,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "IfApplicable"},
        {"section_number": "3", "section_title": "Evaluation of Conceptual Soundness", "component_code": "3.5", "component_title": "Alternative Modelling", "is_test_or_analysis": True, "sort_order": 14,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "NotExpected", "expectation_very_low": "NotExpected"},
        {"section_number": "3", "section_title": "Evaluation of Conceptual Soundness", "component_code": "3.6", "component_title": "Vendor Models", "is_test_or_analysis": False, "sort_order": 15,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "IfApplicable"},

        # Section 4 – Ongoing Monitoring / Benchmarking
        {"section_number": "4", "section_title": "Ongoing Monitoring / Benchmarking", "component_code": "4.1", "component_title": "Benchmarking", "is_test_or_analysis": True, "sort_order": 16,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "NotExpected", "expectation_very_low": "NotExpected"},
        {"section_number": "4", "section_title": "Ongoing Monitoring / Benchmarking", "component_code": "4.2", "component_title": "Process Verification / Replication Testing", "is_test_or_analysis": True, "sort_order": 17,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},
        {"section_number": "4", "section_title": "Ongoing Monitoring / Benchmarking", "component_code": "4.3", "component_title": "Sensitivity Analysis", "is_test_or_analysis": True, "sort_order": 18,
         "expectation_high": "Required", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},

        # Section 5 – Outcome Analysis / Model Assessment and Testing
        {"section_number": "5", "section_title": "Outcome Analysis / Model Assessment and Testing", "component_code": "5.1", "component_title": "Back-testing", "is_test_or_analysis": True, "sort_order": 19,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "NotExpected", "expectation_very_low": "NotExpected"},
        {"section_number": "5", "section_title": "Outcome Analysis / Model Assessment and Testing", "component_code": "5.2", "component_title": "Stress Testing", "is_test_or_analysis": True, "sort_order": 20,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "NotExpected", "expectation_very_low": "NotExpected"},
        {"section_number": "5", "section_title": "Outcome Analysis / Model Assessment and Testing", "component_code": "5.3", "component_title": "Boundary Testing", "is_test_or_analysis": True, "sort_order": 21,
         "expectation_high": "Required", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},
        {"section_number": "5", "section_title": "Outcome Analysis / Model Assessment and Testing", "component_code": "5.4", "component_title": "Accuracy Testing / Convergence Analysis", "is_test_or_analysis": True, "sort_order": 22,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},
        {"section_number": "5", "section_title": "Outcome Analysis / Model Assessment and Testing", "component_code": "5.5", "component_title": "Impact Analysis", "is_test_or_analysis": True, "sort_order": 23,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},
        {"section_number": "5", "section_title": "Outcome Analysis / Model Assessment and Testing", "component_code": "5.6", "component_title": "Other Quantitative / Qualitative Testing", "is_test_or_analysis": True, "sort_order": 24,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},

        # Section 6 – Model Risk: Limitations and Weakness
        {"section_number": "6", "section_title": "Model Risk: Limitations and Weakness", "component_code": "6", "component_title": "Model Risk: Limitations and Weakness", "is_test_or_analysis": False, "sort_order": 25,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "IfApplicable"},

        # Section 7 – Conclusion
        {"section_number": "7", "section_title": "Conclusion", "component_code": "7", "component_title": "Conclusion", "is_test_or_analysis": False, "sort_order": 26,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "Required"},

        # Section 8 – Model Deployment
        {"section_number": "8", "section_title": "Model Deployment", "component_code": "8", "component_title": "Model Deployment", "is_test_or_analysis": False, "sort_order": 27,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},

        # Section 9 – Model Performance Monitoring Requirements
        {"section_number": "9", "section_title": "Model Performance Monitoring Requirements", "component_code": "9", "component_title": "Model Performance Monitoring Requirements", "is_test_or_analysis": False, "sort_order": 28,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "Required", "expectation_very_low": "IfApplicable"},

        # Section 10 – Reference
        {"section_number": "10", "section_title": "Reference", "component_code": "10", "component_title": "Reference", "is_test_or_analysis": False, "sort_order": 29,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "IfApplicable"},

        # Section 11 – Appendix
        {"section_number": "11", "section_title": "Appendix", "component_code": "11", "component_title": "Appendix", "is_test_or_analysis": False, "sort_order": 30,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "IfApplicable"},
    ]

    for comp_data in components:
        component = ValidationComponentDefinition(**comp_data)
        db.add(component)

    db.commit()
    print(f"✓ Seeded {len(components)} validation component definitions")


def seed_initial_component_configuration(db, admin_user):
    """
    Create initial configuration version by snapshotting current component definitions.
    This is required for validation plan versioning and grandfathering.
    """
    # Check if configuration already exists
    existing_config = db.query(ComponentDefinitionConfiguration).first()
    if existing_config:
        print(f"✓ Component configuration already exists (config_id: {existing_config.config_id})")
        return existing_config

    print("Creating initial component definition configuration...")

    # Create initial configuration
    initial_config = ComponentDefinitionConfiguration(
        config_name="Initial SR 11-7 Configuration",
        description="Baseline validation standards per SR 11-7. Created during system initialization.",
        effective_date=date.today(),
        created_by_user_id=admin_user.user_id if admin_user else None,
        is_active=True
    )
    db.add(initial_config)
    db.flush()  # Get config_id

    # Snapshot all component definitions
    components = db.query(ValidationComponentDefinition).filter_by(is_active=True).all()

    for component in components:
        config_item = ComponentDefinitionConfigItem(
            config_id=initial_config.config_id,
            component_id=component.component_id,
            expectation_high=component.expectation_high,
            expectation_medium=component.expectation_medium,
            expectation_low=component.expectation_low,
            expectation_very_low=component.expectation_very_low,
            section_number=component.section_number,
            section_title=component.section_title,
            component_code=component.component_code,
            component_title=component.component_title,
            is_test_or_analysis=component.is_test_or_analysis,
            sort_order=component.sort_order,
            is_active=component.is_active
        )
        db.add(config_item)

    db.commit()
    print(f"✓ Created initial configuration (config_id: {initial_config.config_id}) with {len(components)} component snapshots")

    return initial_config


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

        # Create validator user for UAT
        validator = db.query(User).filter(
            User.email == "validator@example.com").first()
        if not validator:
            validator = User(
                email="validator@example.com",
                full_name="Sarah Chen",
                password_hash=get_password_hash("validator123"),
                role=UserRole.VALIDATOR
            )
            db.add(validator)
            db.commit()
            print("✓ Created validator user (validator@example.com / validator123)")
        else:
            print("✓ Validator user already exists")

        # Create regular user for testing
        regular_user = db.query(User).filter(
            User.email == "user@example.com").first()
        if not regular_user:
            regular_user = User(
                email="user@example.com",
                full_name="Model Owner User",
                password_hash=get_password_hash("user123"),
                role=UserRole.USER
            )
            db.add(regular_user)
            db.commit()
            print("✓ Created regular user (user@example.com / user123)")
        else:
            print("✓ Regular user already exists")

        # Create global approver user
        global_approver = db.query(User).filter(
            User.email == "globalapprover@example.com").first()
        if not global_approver:
            global_approver = User(
                email="globalapprover@example.com",
                full_name="Global Approver",
                password_hash=get_password_hash("approver123"),
                role=UserRole.GLOBAL_APPROVER
            )
            db.add(global_approver)
            db.commit()
            print("✓ Created global approver (globalapprover@example.com / approver123)")
        else:
            print("✓ Global approver already exists")

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

        # Create regions
        default_regions = [
            {"code": "US", "name": "United States",
                "requires_regional_approval": True},
            {"code": "UK", "name": "United Kingdom",
                "requires_regional_approval": True},
            {"code": "EU", "name": "European Union",
                "requires_regional_approval": True},
            {"code": "APAC", "name": "Asia Pacific",
                "requires_regional_approval": True},
        ]

        for region_data in default_regions:
            existing = db.query(Region).filter(
                Region.code == region_data["code"]).first()
            if not existing:
                region = Region(**region_data)
                db.add(region)
                print(
                    f"✓ Created region: {region_data['name']} ({region_data['code']})")
            else:
                print(f"✓ Region already exists: {region_data['name']}")

        db.commit()

        # Create regional approver users with region associations
        # US Regional Approver
        us_approver = db.query(User).filter(
            User.email == "usapprover@example.com").first()
        if not us_approver:
            us_approver = User(
                email="usapprover@example.com",
                full_name="US Regional Approver",
                password_hash=get_password_hash("approver123"),
                role=UserRole.REGIONAL_APPROVER
            )
            # Associate with US region
            us_region = db.query(Region).filter(Region.code == "US").first()
            if us_region:
                us_approver.regions.append(us_region)
            db.add(us_approver)
            db.commit()
            print("✓ Created US regional approver (usapprover@example.com / approver123)")
        else:
            print("✓ US regional approver already exists")

        # EU/UK Regional Approver
        eu_approver = db.query(User).filter(
            User.email == "euapprover@example.com").first()
        if not eu_approver:
            eu_approver = User(
                email="euapprover@example.com",
                full_name="EU Regional Approver",
                password_hash=get_password_hash("approver123"),
                role=UserRole.REGIONAL_APPROVER
            )
            # Associate with EU and UK regions
            eu_region = db.query(Region).filter(Region.code == "EU").first()
            uk_region = db.query(Region).filter(Region.code == "UK").first()
            if eu_region:
                eu_approver.regions.append(eu_region)
            if uk_region:
                eu_approver.regions.append(uk_region)
            db.add(eu_approver)
            db.commit()
            print("✓ Created EU regional approver (euapprover@example.com / approver123)")
        else:
            print("✓ EU regional approver already exists")

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
                    {
                        "code": "TIER_4",
                        "label": "Tier 4 - Very Low Risk",
                        "description": "Minimal-impact models with very limited scope. Require lightweight validation and minimal monitoring.",
                        "sort_order": 4
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
                    {
                        "code": "INTERIM",
                        "label": "Interim Model Change Review",
                        "description": "Auto-generated validation for model changes with imminent implementation dates. Expedited review to validate changes before production deployment.",
                        "sort_order": 6
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
            # New validation workflow taxonomies
            {
                "name": "Validation Priority",
                "description": "Priority levels for validation requests",
                "is_system": True,
                "values": [
                    {
                        "code": "CRITICAL",
                        "label": "Critical",
                        "description": "Highest priority - requires immediate attention and resources",
                        "sort_order": 1
                    },
                    {
                        "code": "HIGH",
                        "label": "High",
                        "description": "High priority - should be addressed promptly",
                        "sort_order": 2
                    },
                    {
                        "code": "MEDIUM",
                        "label": "Medium",
                        "description": "Normal priority - standard processing timeline",
                        "sort_order": 3
                    },
                    {
                        "code": "LOW",
                        "label": "Low",
                        "description": "Low priority - can be scheduled as resources permit",
                        "sort_order": 4
                    },
                ]
            },
            {
                "name": "Validation Request Status",
                "description": "Workflow status for validation requests",
                "is_system": True,
                "values": [
                    {
                        "code": "INTAKE",
                        "label": "Intake",
                        "description": "Initial validation request submission - awaiting assignment and planning",
                        "sort_order": 1
                    },
                    {
                        "code": "PLANNING",
                        "label": "Planning",
                        "description": "Scoping and resource allocation phase",
                        "sort_order": 2
                    },
                    {
                        "code": "IN_PROGRESS",
                        "label": "In Progress",
                        "description": "Active validation work being performed",
                        "sort_order": 3
                    },
                    {
                        "code": "REVIEW",
                        "label": "Review",
                        "description": "Internal QA and compilation of findings",
                        "sort_order": 4
                    },
                    {
                        "code": "PENDING_APPROVAL",
                        "label": "Pending Approval",
                        "description": "Awaiting stakeholder sign-offs",
                        "sort_order": 5
                    },
                    {
                        "code": "APPROVED",
                        "label": "Approved",
                        "description": "Validation complete with all approvals",
                        "sort_order": 6
                    },
                    {
                        "code": "ON_HOLD",
                        "label": "On Hold",
                        "description": "Temporarily paused - requires reason tracking",
                        "sort_order": 7
                    },
                    {
                        "code": "CANCELLED",
                        "label": "Cancelled",
                        "description": "Terminated before completion - requires justification",
                        "sort_order": 8
                    },
                ]
            },
            {
                "name": "Overall Rating",
                "description": "Final validation outcome rating",
                "is_system": True,
                "values": [
                    {
                        "code": "FIT_FOR_PURPOSE",
                        "label": "Fit for Purpose",
                        "description": "Model is suitable for its intended use without material concerns",
                        "sort_order": 1
                    },
                    {
                        "code": "FIT_WITH_CONDITIONS",
                        "label": "Fit with Conditions",
                        "description": "Model is suitable for use but with specific conditions or limitations",
                        "sort_order": 2
                    },
                    {
                        "code": "NOT_FIT_FOR_PURPOSE",
                        "label": "Not Fit for Purpose",
                        "description": "Model is not suitable for its intended use and requires significant remediation",
                        "sort_order": 3
                    },
                ]
            },
            {
                "name": "Model Ownership Type",
                "description": "Classification of model ownership and regional scope",
                "is_system": True,
                "values": [
                    {
                        "code": "GLOBAL",
                        "label": "Global",
                        "description": "Single global implementation with no regional specificity",
                        "sort_order": 1
                    },
                    {
                        "code": "REGIONALLY_OWNED",
                        "label": "Regionally Owned",
                        "description": "Models owned and maintained by a specific region",
                        "sort_order": 2
                    },
                    {
                        "code": "GLOBAL_WITH_REGIONAL_IMPACT",
                        "label": "Global with Regional Impact",
                        "description": "Global models with region-specific implementations or adaptations",
                        "sort_order": 3
                    },
                ]
            }
        ]

        for tax_data in taxonomies_data:
            existing_tax = db.query(Taxonomy).filter(
                Taxonomy.name == tax_data["name"]
            ).first()

            if not existing_tax:
                # Create new taxonomy with all values
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
                # Taxonomy exists - check for missing values and add them
                existing_codes = {v.code for v in db.query(TaxonomyValue).filter(
                    TaxonomyValue.taxonomy_id == existing_tax.taxonomy_id
                ).all()}

                added_count = 0
                for val_data in tax_data["values"]:
                    if val_data["code"] not in existing_codes:
                        value = TaxonomyValue(
                            taxonomy_id=existing_tax.taxonomy_id,
                            code=val_data["code"],
                            label=val_data["label"],
                            description=val_data["description"],
                            sort_order=val_data["sort_order"],
                            is_active=True,
                            created_at=datetime.utcnow()
                        )
                        db.add(value)
                        added_count += 1

                if added_count > 0:
                    print(
                        f"✓ Updated taxonomy: {tax_data['name']} (added {added_count} new values)")
                else:
                    print(f"✓ Taxonomy already exists: {tax_data['name']}")

        db.commit()

        # Seed reference taxonomies for Regulatory Category and Model Type
        seed_taxonomy_reference_data(db)
        db.commit()

        # Seed validation component definitions (Figure 3 matrix)
        seed_validation_components(db)
        db.commit()

        # Create initial component configuration version (for grandfathering)
        seed_initial_component_configuration(db, admin)
        db.commit()

        # Create validation workflow SLA configuration
        existing_sla = db.query(ValidationWorkflowSLA).filter(
            ValidationWorkflowSLA.workflow_type == "Validation"
        ).first()
        if not existing_sla:
            sla_config = ValidationWorkflowSLA(
                workflow_type="Validation",
                assignment_days=10,
                begin_work_days=5,
                complete_work_days=80,
                approval_days=10,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(sla_config)
            db.commit()
            print("✓ Created validation workflow SLA configuration")
        else:
            print("✓ Validation workflow SLA configuration already exists")

        # Create validation policies for each risk tier (Phase 6)
        risk_tier_taxonomy = db.query(Taxonomy).filter(
            Taxonomy.name == "Model Risk Tier"
        ).first()

        if risk_tier_taxonomy:
            # Define per-tier policies: lead time days and re-validation frequency
            tier_policies = {
                "TIER_1": {
                    "frequency_months": 12,
                    "model_change_lead_time_days": 120,
                    "description": "High-risk models require annual re-validation and 120-day lead time for model changes"
                },
                "TIER_2": {
                    "frequency_months": 18,
                    "model_change_lead_time_days": 90,
                    "description": "Medium-risk models require re-validation every 18 months and 90-day lead time for model changes"
                },
                "TIER_3": {
                    "frequency_months": 24,
                    "model_change_lead_time_days": 60,
                    "description": "Low-risk models require re-validation every 24 months and 60-day lead time for model changes"
                },
                "TIER_4": {
                    "frequency_months": 36,
                    "model_change_lead_time_days": 45,
                    "description": "Very low-risk models require re-validation every 36 months and 45-day lead time for model changes"
                },
            }

            for tier_code, policy_config in tier_policies.items():
                tier_value = db.query(TaxonomyValue).filter(
                    TaxonomyValue.taxonomy_id == risk_tier_taxonomy.taxonomy_id,
                    TaxonomyValue.code == tier_code
                ).first()

                if tier_value:
                    existing_policy = db.query(ValidationPolicy).filter(
                        ValidationPolicy.risk_tier_id == tier_value.value_id
                    ).first()

                    if not existing_policy:
                        policy = ValidationPolicy(
                            risk_tier_id=tier_value.value_id,
                            frequency_months=policy_config["frequency_months"],
                            model_change_lead_time_days=policy_config["model_change_lead_time_days"],
                            description=policy_config["description"],
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        db.add(policy)
                        print(
                            f"✓ Created validation policy for {tier_value.label}")
                    else:
                        print(
                            f"✓ Validation policy already exists for {tier_value.label} (skipping update to preserve user changes)")

            db.commit()
        else:
            print(
                "⚠ Model Risk Tier taxonomy not found - skipping validation policy seeding")

        # Create demo models with validations to demonstrate overdue logic
        print("\n=== Creating Demo Data for Overdue Validation Dashboard ===")

        # Get required taxonomy values
        tier_2 = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "TIER_2"
        ).first()
        tier_3 = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "TIER_3"
        ).first()
        initial_val_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "INITIAL"
        ).first()
        annual_val_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "ANNUAL"
        ).first()
        pass_outcome = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "PASS"
        ).first()

        if tier_2 and tier_3 and initial_val_type and annual_val_type and pass_outcome and admin and validator:
            # Calculate strategic dates for Tier 2 (18 month frequency, 90 day lead time)
            # Total overdue threshold: 18 months + 3 months grace + 90 days = ~21.5 months
            today = date.today()

            # Model A: Completely overdue (last validated 24 months ago)
            model_a_exists = db.query(Model).filter(
                Model.model_name == "Demo: Overdue Model").first()
            if not model_a_exists:
                model_a = Model(
                    model_name="Demo: Overdue Model",
                    description="Tier 2 model - validation overdue (last validated 24 months ago)",
                    development_type="In-House",
                    status="Active",
                    owner_id=admin.user_id,
                    risk_tier_id=tier_2.value_id,
                    created_at=datetime.utcnow()
                )
                db.add(model_a)
                db.flush()

                # Add validation from 24 months ago
                validation_a = Validation(
                    model_id=model_a.model_id,
                    validator_id=validator.user_id,
                    validation_type_id=annual_val_type.value_id,
                    outcome_id=pass_outcome.value_id,
                    validation_date=today -
                    timedelta(days=24*30),  # 24 months ago
                    findings_summary="Annual validation completed. Model performing as expected.",
                    created_at=datetime.utcnow()
                )
                db.add(validation_a)
                print(
                    "✓ Created 'Demo: Overdue Model' (24 months since last validation - OVERDUE)")

            # Model B: Submission overdue but validation not yet due (last validated 20 months ago)
            model_b_exists = db.query(Model).filter(
                Model.model_name == "Demo: Submission Overdue").first()
            if not model_b_exists:
                model_b = Model(
                    model_name="Demo: Submission Overdue",
                    description="Tier 2 model - past submission grace period (last validated 20 months ago)",
                    development_type="In-House",
                    status="Active",
                    owner_id=admin.user_id,
                    risk_tier_id=tier_2.value_id,
                    created_at=datetime.utcnow()
                )
                db.add(model_b)
                db.flush()

                # Add validation from 20 months ago
                validation_b = Validation(
                    model_id=model_b.model_id,
                    validator_id=validator.user_id,
                    validation_type_id=annual_val_type.value_id,
                    outcome_id=pass_outcome.value_id,
                    validation_date=today -
                    timedelta(days=20*30),  # 20 months ago
                    findings_summary="Annual validation completed.",
                    created_at=datetime.utcnow()
                )
                db.add(validation_b)
                print(
                    "✓ Created 'Demo: Submission Overdue' (20 months - submission grace passed)")

            # Model C: Due soon but not overdue (last validated 17 months ago)
            model_c_exists = db.query(Model).filter(
                Model.model_name == "Demo: Due Soon").first()
            if not model_c_exists:
                model_c = Model(
                    model_name="Demo: Due Soon",
                    description="Tier 2 model - approaching submission deadline (last validated 17 months ago)",
                    development_type="In-House",
                    status="Active",
                    owner_id=admin.user_id,
                    risk_tier_id=tier_2.value_id,
                    created_at=datetime.utcnow()
                )
                db.add(model_c)
                db.flush()

                # Add validation from 17 months ago
                validation_c = Validation(
                    model_id=model_c.model_id,
                    validator_id=validator.user_id,
                    validation_type_id=annual_val_type.value_id,
                    outcome_id=pass_outcome.value_id,
                    validation_date=today -
                    timedelta(days=17*30),  # 17 months ago
                    findings_summary="Annual validation completed.",
                    created_at=datetime.utcnow()
                )
                db.add(validation_c)
                print(
                    "✓ Created 'Demo: Due Soon' (17 months - submission due within 1 month)")

            # Model D: Never validated (Tier 3)
            model_d_exists = db.query(Model).filter(
                Model.model_name == "Demo: Never Validated").first()
            if not model_d_exists:
                model_d = Model(
                    model_name="Demo: Never Validated",
                    description="Tier 3 model - never validated since deployment",
                    development_type="In-House",
                    status="Active",
                    owner_id=admin.user_id,
                    risk_tier_id=tier_3.value_id,
                    created_at=datetime.utcnow()
                )
                db.add(model_d)
                print("✓ Created 'Demo: Never Validated' (no validation history)")

            # Model E: Recently validated (compliant)
            model_e_exists = db.query(Model).filter(
                Model.model_name == "Demo: Compliant Model").first()
            if not model_e_exists:
                model_e = Model(
                    model_name="Demo: Compliant Model",
                    description="Tier 2 model - recently validated and compliant (6 months ago)",
                    development_type="In-House",
                    status="Active",
                    owner_id=admin.user_id,
                    risk_tier_id=tier_2.value_id,
                    created_at=datetime.utcnow()
                )
                db.add(model_e)
                db.flush()

                # Add recent validation
                validation_e = Validation(
                    model_id=model_e.model_id,
                    validator_id=validator.user_id,
                    validation_type_id=annual_val_type.value_id,
                    outcome_id=pass_outcome.value_id,
                    validation_date=today -
                    timedelta(days=6*30),  # 6 months ago
                    findings_summary="Annual validation completed. Model is compliant.",
                    created_at=datetime.utcnow()
                )
                db.add(validation_e)
                print(
                    "✓ Created 'Demo: Compliant Model' (6 months - well within compliance)")

            db.commit()
            print("✓ Demo data creation completed\n")
        else:
            print(
                "⚠ Missing required taxonomy values or users - skipping demo data creation\n")

        print("Seeding completed successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
