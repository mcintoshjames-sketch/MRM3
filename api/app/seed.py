"""Seed minimal reference data."""
import re
from datetime import datetime, date, timedelta
from typing import Dict, List
from app.core.database import SessionLocal
from app.core.time import utc_now
from app.core.security import get_password_hash
from app.models import User, UserRole, Vendor, EntraUser, Taxonomy, TaxonomyValue, ValidationWorkflowSLA, ValidationPolicy, Region, ValidationComponentDefinition, ComponentDefinitionConfiguration, ComponentDefinitionConfigItem, ModelTypeCategory, ModelType, ValidationRequest, ValidationOutcome, ValidationRequestModelVersion, ApproverRole, ConditionalApprovalRule, RuleRequiredApprover, MapApplication
from app.models.recommendation import RecommendationPriorityConfig, RecommendationTimeframeConfig
from app.models.kpm import KpmCategory, Kpm
from app.models.model import Model
from app.models.risk_assessment import QualitativeRiskFactor, QualitativeFactorGuidance
from app.models.scorecard import ScorecardSection, ScorecardCriterion


REGULATORY_CATEGORY_VALUES = [
    {"code": "CCAR_DFAST", "label": "CCAR / DFAST Stress Testing",
        "description": "Models used for Federal Reserve stress tests and internal CCAR projections."},
    {"code": "BASEL_CREDIT", "label": "Basel Regulatory Capital – Credit Risk (RWA)",
     "description": "Calculates Basel risk-weighted assets for credit portfolios (PD/LGD/EAD)."},
    {"code": "MARKET_RISK", "label": "Market Risk Capital (VaR / FRTB / Stressed VaR / RNIV)",
     "description": "Trading book capital models including VaR, stressed VaR, RNIV, and FRTB."},
    {"code": "CCR_CVA", "label": "Counterparty Credit Risk / CVA Capital",
        "description": "Exposure, PFE, and CVA models supporting counterparty credit risk capital."},
    {"code": "ICAAP", "label": "Internal Economic Capital / ICAAP",
        "description": "Economic capital and ICAAP models beyond regulatory minima."},
    {"code": "CECL", "label": "CECL / Allowance for Credit Losses (ACL)",
     "description": "Expected credit loss and allowance models under U.S. GAAP CECL."},
    {"code": "IFRS9_ECL", "label": "IFRS 9 Expected Credit Loss",
        "description": "IFRS 9 staging and expected credit loss models for non-U.S. entities."},
    {"code": "FAIR_VALUE", "label": "Fair Value / Valuation for Financial Reporting",
        "description": "ASC 820 fair value and valuation models for financial reporting."},
    {"code": "LIQUIDITY", "label": "Liquidity Risk & LCR / NSFR",
        "description": "Liquidity coverage, NSFR, and cashflow forecasting models."},
    {"code": "IRRBB", "label": "Interest Rate Risk in the Banking Book (IRRBB)",
     "description": "IRRBB models for EVE/NII metrics and customer behaviour assumptions."},
    {"code": "ALM_FTP", "label": "Asset/Liability Management (ALM) / FTP",
     "description": "Structural balance sheet, FTP, and hedge optimization models."},
    {"code": "AML_SANCTIONS", "label": "AML / Sanctions / Transaction Monitoring",
        "description": "AML/BSA transaction monitoring, sanctions screening, and customer risk scoring."},
    {"code": "FRAUD", "label": "Fraud Detection",
        "description": "Fraud detection across cards, payments, and digital channels."},
    {"code": "CONDUCT_RISK", "label": "Conduct Risk / Fair Lending / UDAAP",
        "description": "Models supporting conduct, fair lending, and UDAAP surveillance."},
    {"code": "OP_RISK", "label": "Operational Risk Capital / Scenario Models",
        "description": "Operational risk capital, LDA, and scenario aggregation models."},
    {"code": "REG_REPORTING", "label": "Regulatory Reporting (FFIEC, FR Y-9C, FR Y-14, Call Reports, etc.)",
     "description": "Models feeding data to regulatory reports and schedules."},
    {"code": "INT_REPORTING", "label": "Internal Risk & Board Reporting",
        "description": "Models that drive internal risk dashboards and board reporting."},
    {"code": "PRICING", "label": "Pricing & Valuation – Internal / Customer",
        "description": "Pricing and valuation models used primarily for business decisioning."},
    {"code": "MARGIN_COLL", "label": "Margin & Collateral Models (IM / VM / Haircuts)",
     "description": "Margin, collateral, and haircut models for IM/VM and eligibility."},
    {"code": "MRM_META", "label": "Model Risk Management / Meta-Models",
        "description": "Models that quantify or aggregate model risk (scores, capital add-ons)."},
    {"code": "NON_REG", "label": "Non-Regulatory / Business Only",
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


# Qualitative Outcome values for qualitative KPM assessments
QUALITATIVE_OUTCOME_VALUES = [
    {"code": "GREEN", "label": "Green",
        "description": "KPM within acceptable parameters; no concerns identified."},
    {"code": "YELLOW", "label": "Yellow",
        "description": "KPM warrants attention; minor concerns or approaching thresholds."},
    {"code": "RED", "label": "Red",
        "description": "KPM breached thresholds or significant concerns identified; action required."},
]


MODEL_TYPE_HIERARCHY = {
    "taxonomy_name": "Model Risk Management (MRM) Model Types",
    "structure": "Hierarchical (L1 Category -> L2 Sub-types)",
    "categories": [
        {
            "l1_name": "Capital",
            "description": "Models primarily used to calculate regulatory capital requirements, including risk-weighted assets (RWA) and minimum capital ratios under frameworks like Basel III and US rules (e.g., 12 CFR 3). These focus on quantifying credit, market, and operational risks for compliance reporting, without incorporating scenario-based stresses.",
            "l2_subtypes": [
                "Credit Risk – Retail (PD, LGD, EAD)",
                "Credit Risk – Wholesale (PD, LGD, EAD)",
                "Credit Risk – Counterparty",
                "Market Risk Capital",
                "Operational Risk Capital",
                "Economic / ICAAP Capital",
                "Consolidated Capital Engine"
            ]
        },
        {
            "l1_name": "Liquidity Risk",
            "description": "Models designed to measure, monitor, and manage liquidity positions, including projections of cash flows, funding needs, and compliance with ratios like the Liquidity Coverage Ratio (LCR) or Net Stable Funding Ratio (NSFR). These emphasize behavioral assumptions about deposits, wholesale funding, and contingent liabilities under normal conditions.",
            "l2_subtypes": [
                "LCR / NSFR Calculation",
                "Cash-Flow and Funding Projections",
                "Collateral and Margin Optimisation",
                "Deposit Behavioural Models",
                "ALM and Banking-Book Interest-Rate Risk"
            ]
        },
        {
            "l1_name": "Stress Testing",
            "description": "Models applied to simulate adverse economic scenarios for assessing institutional resilience, as required by regulations like the Dodd-Frank Act Stress Tests (DFAST) or Comprehensive Capital Analysis and Review (CCAR). These integrate inputs from other model types but focus on scenario generation, loss projection, and post-stress capital/liquidity outcomes.",
            "l2_subtypes": [
                "Enterprise-wide EWST/CCAR/DFAST",
                "Credit Stress Projection",
                "Market and Liquidity Stress",
                "Macroeconomic Scenario Generator"
            ]
        },
        {
            "l1_name": "Market and Pricing",
            "description": "Models for valuing financial instruments, estimating market risks, and supporting trading decisions, focusing on price discovery, volatility, and fair value under current market conditions. These do not include regulatory capital calculations or stress applications.",
            "l2_subtypes": [
                "Instrument Valuation and Fair-Value",
                "Curves, Surfaces and Vol-Cubes",
                "Market Risk Metrics (Non-Capital)",
                "Algorithmic and Quant Trading"
            ]
        },
        {
            "l1_name": "Credit Risk Management",
            "description": "Models for day-to-day credit decisions, portfolio monitoring, and loss estimation outside of regulatory capital or stress contexts, including underwriting, scoring, and allowance calculations (e.g., under CECL standards).",
            "l2_subtypes": [
                "Underwriting / Adjudication",
                "Account and Portfolio Management",
                "Allowance and Loss Provisioning (IFRS 9 and CECL)",
                "Internal PD / LGD / EAD (Non-Capital)",
                "Collections and Recovery",
                "Wealth and Insurance Credit Models"
            ]
        },
        {
            "l1_name": "Operational Risk and Financial Crime",
            "description": "Models to quantify and mitigate non-financial risks from internal processes, people, systems, or external events, including detection of irregularities like fraud or money laundering.",
            "l2_subtypes": [
                "Fraud Detection and Prevention",
                "AML and Sanctions Monitoring",
                "Cybersecurity and Information-Security Risk",
                "Operational Loss Quantification"
            ]
        },
        {
            "l1_name": "Compliance and Other Decision-Support",
            "description": "Models for ensuring adherence to laws, regulations, and internal policies, or supporting non-risk business decisions like forecasting, marketing, or asset management. This catch-all category covers qualitative-quantitative hybrids not fitting elsewhere.",
            "l2_subtypes": [
                "Regulatory Compliance Analytics",
                "Marketing and Customer Analytics",
                "Strategic and Executive Decision Support",
                "Financial Reporting and Accounting",
                "Investment and Advisory (Non-Credit)",
                "Other or Unclassified"
            ]
        }
    ]
}


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
            created_at=utc_now(),
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
                    created_at=utc_now(),
                )
            )

    print(f"✓ {'Created' if created else 'Updated'} taxonomy: {name} ({len(values)} values managed)")


def seed_taxonomy_reference_data(db):
    """Ensure the Regulatory Category, Model Type, and Qualitative Outcome taxonomies exist."""
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
    _upsert_taxonomy_with_values(
        db,
        name="Qualitative Outcome",
        description="Assessment outcomes for qualitative KPMs (Red/Yellow/Green rating scale).",
        values=QUALITATIVE_OUTCOME_VALUES,
    )


def seed_validation_components(db):
    """Seed validation component definitions (Figure 3 matrix)."""
    # Check if already seeded
    existing_count = db.query(ValidationComponentDefinition).count()
    if existing_count > 0:
        print(
            f"✓ Validation component definitions already seeded ({existing_count} components)")
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
        {"section_number": "9", "section_title": "Model Performance Monitoring Requirements", "component_code": "9b", "component_title": "Performance Monitoring Plan Review", "is_test_or_analysis": False, "sort_order": 29,
         "expectation_high": "Required", "expectation_medium": "Required", "expectation_low": "IfApplicable", "expectation_very_low": "NotExpected"},

        # Section 10 – Reference
        {"section_number": "10", "section_title": "Reference", "component_code": "10", "component_title": "Reference", "is_test_or_analysis": False, "sort_order": 30,
         "expectation_high": "IfApplicable", "expectation_medium": "IfApplicable", "expectation_low": "IfApplicable", "expectation_very_low": "IfApplicable"},

        # Section 11 – Appendix
        {"section_number": "11", "section_title": "Appendix", "component_code": "11", "component_title": "Appendix", "is_test_or_analysis": False, "sort_order": 31,
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
        print(
            f"✓ Component configuration already exists (config_id: {existing_config.config_id})")
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
    components = db.query(ValidationComponentDefinition).filter_by(
        is_active=True).all()

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
    print(
        f"✓ Created initial configuration (config_id: {initial_config.config_id}) with {len(components)} component snapshots")

    return initial_config


def seed_priority_configs(db):
    """
    Seed RecommendationPriorityConfig entries with enforce_timeframes settings.

    Configuration per priority level:
    - HIGH/MEDIUM/LOW: enforce_timeframes=True (strict enforcement)
    - CONSIDERATION: enforce_timeframes=False (no remediation tracking)
    """
    print("\n=== Seeding Recommendation Priority Configurations ===")

    rec_priority_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Recommendation Priority"
    ).first()

    if not rec_priority_taxonomy:
        print("⚠ Recommendation Priority taxonomy not found - skipping priority config seeding")
        return

    # Configuration for each priority level
    priority_configs = {
        "HIGH": {
            "requires_final_approval": True,
            "requires_action_plan": True,
            "enforce_timeframes": True,
            "description": "High priority - full approval workflow, action plan required, strict timeframe enforcement"
        },
        "MEDIUM": {
            "requires_final_approval": True,
            "requires_action_plan": True,
            "enforce_timeframes": True,
            "description": "Medium priority - full approval workflow, action plan required, strict timeframe enforcement"
        },
        "LOW": {
            "requires_final_approval": False,
            "requires_action_plan": True,
            "enforce_timeframes": True,
            "description": "Low priority - validator approval sufficient, action plan required, strict timeframe enforcement"
        },
        "CONSIDERATION": {
            "requires_final_approval": False,
            "requires_action_plan": False,
            "enforce_timeframes": False,
            "description": "Consideration - no action plan required, no timeframe enforcement"
        },
    }

    for priority_code, config_data in priority_configs.items():
        priority_value = db.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == rec_priority_taxonomy.taxonomy_id,
            TaxonomyValue.code == priority_code
        ).first()

        if priority_value:
            existing_config = db.query(RecommendationPriorityConfig).filter(
                RecommendationPriorityConfig.priority_id == priority_value.value_id
            ).first()

            if not existing_config:
                config = RecommendationPriorityConfig(
                    priority_id=priority_value.value_id,
                    requires_final_approval=config_data["requires_final_approval"],
                    requires_action_plan=config_data["requires_action_plan"],
                    enforce_timeframes=config_data["enforce_timeframes"],
                    description=config_data["description"],
                    created_at=utc_now(),
                    updated_at=utc_now()
                )
                db.add(config)
                print(f"✓ Created priority config for {priority_value.label}")
            else:
                # Update existing config if enforce_timeframes not set correctly
                if existing_config.enforce_timeframes != config_data["enforce_timeframes"]:
                    existing_config.enforce_timeframes = config_data["enforce_timeframes"]
                    print(f"✓ Updated enforce_timeframes for {priority_value.label}")
                else:
                    print(f"✓ Priority config already exists for {priority_value.label}")

    db.commit()


def seed_timeframe_configs(db):
    """
    Seed RecommendationTimeframeConfig entries for all priority/risk/frequency combinations.

    Creates 48 configs: 3 priorities (HIGH, MEDIUM, LOW) × 4 risk tiers × 4 frequencies
    CONSIDERATION priority is excluded as it has no timeframe enforcement.

    Values are based on REC_TIMES.json specification.
    """
    print("\n=== Seeding Recommendation Timeframe Configurations ===")

    # Get required taxonomies
    rec_priority_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Recommendation Priority"
    ).first()
    risk_tier_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Model Risk Tier"
    ).first()
    usage_freq_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Model Usage Frequency"
    ).first()

    if not rec_priority_taxonomy or not risk_tier_taxonomy or not usage_freq_taxonomy:
        print("⚠ Required taxonomies not found - skipping timeframe config seeding")
        return

    # Get taxonomy values
    priorities = {v.code: v.value_id for v in db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == rec_priority_taxonomy.taxonomy_id,
        TaxonomyValue.code.in_(["HIGH", "MEDIUM", "LOW"])  # Exclude CONSIDERATION
    ).all()}

    risk_tiers = {v.code: v.value_id for v in db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == risk_tier_taxonomy.taxonomy_id
    ).all()}

    frequencies = {v.code: v.value_id for v in db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == usage_freq_taxonomy.taxonomy_id
    ).all()}

    # Timeframe data based on REC_TIMES.json
    # Format: (priority, risk_tier, frequency) -> max_days
    timeframe_data = {
        # HIGH priority - strictest timeframes
        ("HIGH", "TIER_1", "DAILY"): 0,
        ("HIGH", "TIER_1", "MONTHLY"): 0,
        ("HIGH", "TIER_1", "QUARTERLY"): 90,
        ("HIGH", "TIER_1", "ANNUALLY"): 90,
        ("HIGH", "TIER_2", "DAILY"): 0,
        ("HIGH", "TIER_2", "MONTHLY"): 90,
        ("HIGH", "TIER_2", "QUARTERLY"): 90,
        ("HIGH", "TIER_2", "ANNUALLY"): 180,
        ("HIGH", "TIER_3", "DAILY"): 90,
        ("HIGH", "TIER_3", "MONTHLY"): 90,
        ("HIGH", "TIER_3", "QUARTERLY"): 180,
        ("HIGH", "TIER_3", "ANNUALLY"): 180,
        ("HIGH", "TIER_4", "DAILY"): 90,
        ("HIGH", "TIER_4", "MONTHLY"): 90,
        ("HIGH", "TIER_4", "QUARTERLY"): 180,
        ("HIGH", "TIER_4", "ANNUALLY"): 180,

        # MEDIUM priority - moderate timeframes
        ("MEDIUM", "TIER_1", "DAILY"): 180,
        ("MEDIUM", "TIER_1", "MONTHLY"): 180,
        ("MEDIUM", "TIER_1", "QUARTERLY"): 180,
        ("MEDIUM", "TIER_1", "ANNUALLY"): 180,
        ("MEDIUM", "TIER_2", "DAILY"): 180,
        ("MEDIUM", "TIER_2", "MONTHLY"): 180,
        ("MEDIUM", "TIER_2", "QUARTERLY"): 180,
        ("MEDIUM", "TIER_2", "ANNUALLY"): 365,
        ("MEDIUM", "TIER_3", "DAILY"): 180,
        ("MEDIUM", "TIER_3", "MONTHLY"): 180,
        ("MEDIUM", "TIER_3", "QUARTERLY"): 365,
        ("MEDIUM", "TIER_3", "ANNUALLY"): 365,
        ("MEDIUM", "TIER_4", "DAILY"): 180,
        ("MEDIUM", "TIER_4", "MONTHLY"): 180,
        ("MEDIUM", "TIER_4", "QUARTERLY"): 365,
        ("MEDIUM", "TIER_4", "ANNUALLY"): 365,

        # LOW priority - longest timeframes
        ("LOW", "TIER_1", "DAILY"): 365,
        ("LOW", "TIER_1", "MONTHLY"): 365,
        ("LOW", "TIER_1", "QUARTERLY"): 365,
        ("LOW", "TIER_1", "ANNUALLY"): 365,
        ("LOW", "TIER_2", "DAILY"): 365,
        ("LOW", "TIER_2", "MONTHLY"): 365,
        ("LOW", "TIER_2", "QUARTERLY"): 365,
        ("LOW", "TIER_2", "ANNUALLY"): 1095,
        ("LOW", "TIER_3", "DAILY"): 365,
        ("LOW", "TIER_3", "MONTHLY"): 365,
        ("LOW", "TIER_3", "QUARTERLY"): 1095,
        ("LOW", "TIER_3", "ANNUALLY"): 1095,
        ("LOW", "TIER_4", "DAILY"): 365,
        ("LOW", "TIER_4", "MONTHLY"): 365,
        ("LOW", "TIER_4", "QUARTERLY"): 1095,
        ("LOW", "TIER_4", "ANNUALLY"): 1095,
    }

    created_count = 0
    skipped_count = 0

    for (priority_code, risk_code, freq_code), max_days in timeframe_data.items():
        priority_id = priorities.get(priority_code)
        risk_tier_id = risk_tiers.get(risk_code)
        freq_id = frequencies.get(freq_code)

        if not priority_id or not risk_tier_id or not freq_id:
            print(f"⚠ Skipping {priority_code}/{risk_code}/{freq_code} - missing taxonomy values")
            continue

        # Check if config already exists
        existing = db.query(RecommendationTimeframeConfig).filter(
            RecommendationTimeframeConfig.priority_id == priority_id,
            RecommendationTimeframeConfig.risk_tier_id == risk_tier_id,
            RecommendationTimeframeConfig.usage_frequency_id == freq_id
        ).first()

        if not existing:
            config = RecommendationTimeframeConfig(
                priority_id=priority_id,
                risk_tier_id=risk_tier_id,
                usage_frequency_id=freq_id,
                max_days=max_days,
                description=f"{priority_code} priority, {risk_code}, {freq_code} usage - {max_days} days max",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(config)
            created_count += 1
        else:
            skipped_count += 1

    db.commit()
    print(f"✓ Created {created_count} timeframe configs, skipped {skipped_count} existing")


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

        # Create John Smith (UAT User)
        john_smith = db.query(User).filter(
            User.email == "john.smith@contoso.com").first()
        if not john_smith:
            john_smith = User(
                email="john.smith@contoso.com",
                full_name="John Smith",
                password_hash=get_password_hash("john123"),
                role=UserRole.USER
            )
            db.add(john_smith)
            db.commit()
            print("✓ Created John Smith (john.smith@contoso.com / john123)")
        else:
            if john_smith.role != UserRole.USER:
                john_smith.role = UserRole.USER
                db.add(john_smith)
                db.commit()
                print("✓ Updated John Smith role to USER (Model Developer)")
            else:
                print("✓ John Smith already exists")

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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                "created_at": utc_now()
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
                        "code": "COMPREHENSIVE",
                        "label": "Comprehensive Validation",
                        "description": "Full deep-dive validation covering all aspects of model performance. Used for periodic revalidations.",
                        "sort_order": 2
                    },
                    {
                        "code": "TARGETED",
                        "label": "Targeted Review",
                        "description": "Focused review on specific model aspects or identified issues",
                        "sort_order": 3
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
            },
            {
                "name": "Approval Role",
                "description": "Roles eligible to approve validation requests; editable by Admins.",
                "is_system": True,
                "values": [
                    {
                        "code": "GLOBAL_APPROVER",
                        "label": "Global Approver",
                        "description": "Global approver role",
                        "sort_order": 1
                    },
                    {
                        "code": "REGIONAL_APPROVER",
                        "label": "Regional Approver",
                        "description": "Regional approver role (supports region-coded variants)",
                        "sort_order": 2
                    },
                    {
                        "code": "REGIONAL_VALIDATOR",
                        "label": "Regional Validator",
                        "description": "Regional validator role (supports region-coded variants)",
                        "sort_order": 3
                    },
                    {
                        "code": "MODEL_OWNER",
                        "label": "Model Owner",
                        "description": "Model owner approval",
                        "sort_order": 4
                    },
                    {
                        "code": "MODEL_RISK_COMMITTEE",
                        "label": "Model Risk Committee",
                        "description": "Committee-level approver",
                        "sort_order": 5
                    },
                    {
                        "code": "SENIOR_MANAGEMENT",
                        "label": "Senior Management",
                        "description": "Senior management approver",
                        "sort_order": 6
                    },
                    {
                        "code": "COMMITTEE",
                        "label": "Committee",
                        "description": "Generic committee approver",
                        "sort_order": 7
                    },
                ]
            },
            # Model relationship taxonomies
            {
                "name": "Model Hierarchy Type",
                "description": "Types of hierarchical relationships between models",
                "is_system": True,
                "values": [
                    {
                        "code": "SUB_MODEL",
                        "label": "Sub-Model",
                        "description": "Child model that is a component or subset of a parent model",
                        "sort_order": 1
                    },
                ]
            },
            {
                "name": "Model Dependency Type",
                "description": "Types of data dependencies between models (feeder/consumer relationships)",
                "is_system": True,
                "values": [
                    {
                        "code": "INPUT_DATA",
                        "label": "Input Data",
                        "description": "Feeder model provides raw data inputs to consumer model",
                        "sort_order": 1
                    },
                    {
                        "code": "SCORE",
                        "label": "Score/Output",
                        "description": "Feeder model provides calculated scores or predictions to consumer model",
                        "sort_order": 2
                    },
                    {
                        "code": "PARAMETER",
                        "label": "Parameter",
                        "description": "Feeder model provides configuration parameters or coefficients to consumer model",
                        "sort_order": 3
                    },
                    {
                        "code": "GOVERNANCE_SIGNAL",
                        "label": "Governance Signal",
                        "description": "Feeder model provides governance flags or override signals to consumer model",
                        "sort_order": 4
                    },
                    {
                        "code": "OTHER",
                        "label": "Other",
                        "description": "Other types of model dependencies not covered by standard categories",
                        "sort_order": 5
                    },
                ]
            },
            # Model-Application relationship taxonomy
            {
                "name": "Application Relationship Type",
                "description": "Types of relationships between models and supporting applications from MAP",
                "is_system": True,
                "values": [
                    {
                        "code": "DATA_SOURCE",
                        "label": "Data Source",
                        "description": "Application provides input data to the model",
                        "sort_order": 1
                    },
                    {
                        "code": "EXECUTION",
                        "label": "Execution Platform",
                        "description": "Application runs or hosts the model",
                        "sort_order": 2
                    },
                    {
                        "code": "OUTPUT_CONSUMER",
                        "label": "Output Consumer",
                        "description": "Application consumes model outputs or scores",
                        "sort_order": 3
                    },
                    {
                        "code": "MONITORING",
                        "label": "Monitoring/Alerting",
                        "description": "Application monitors model performance",
                        "sort_order": 4
                    },
                    {
                        "code": "REPORTING",
                        "label": "Reporting/Dashboard",
                        "description": "Application displays model results",
                        "sort_order": 5
                    },
                    {
                        "code": "DATA_STORAGE",
                        "label": "Data Storage",
                        "description": "Application stores model data or results",
                        "sort_order": 6
                    },
                    {
                        "code": "ORCHESTRATION",
                        "label": "Workflow/Orchestration",
                        "description": "Application orchestrates model execution",
                        "sort_order": 7
                    },
                    {
                        "code": "VALIDATION",
                        "label": "Validation Support",
                        "description": "Application supports model validation process",
                        "sort_order": 8
                    },
                    {
                        "code": "OTHER",
                        "label": "Other",
                        "description": "Other relationship type",
                        "sort_order": 9
                    },
                ]
            },
            # Recommendation taxonomies
            {
                "name": "Recommendation Priority",
                "description": "Priority levels for recommendations - determines closure approval requirements and workflow",
                "is_system": True,
                "values": [
                    {
                        "code": "HIGH",
                        "label": "High",
                        "description": "High priority - requires prompt action with senior oversight. Full approval workflow required.",
                        "sort_order": 1
                    },
                    {
                        "code": "MEDIUM",
                        "label": "Medium",
                        "description": "Standard priority - requires timely remediation. Full approval workflow required.",
                        "sort_order": 2
                    },
                    {
                        "code": "LOW",
                        "label": "Low",
                        "description": "Low priority - can be scheduled as resources permit. Validator approval sufficient.",
                        "sort_order": 3
                    },
                    {
                        "code": "CONSIDERATION",
                        "label": "Consideration",
                        "description": "Minor suggestion or observation - action plan not required. Developer acknowledges and closes.",
                        "sort_order": 4
                    },
                ]
            },
            {
                "name": "Recommendation Status",
                "description": "Workflow status for recommendations",
                "is_system": True,
                "values": [
                    {
                        "code": "REC_DRAFT",
                        "label": "Draft",
                        "description": "Initial draft - validator is still composing the recommendation",
                        "sort_order": 1
                    },
                    {
                        "code": "REC_PENDING_RESPONSE",
                        "label": "Pending Response",
                        "description": "Finalized and sent to developer - awaiting acknowledgement",
                        "sort_order": 2
                    },
                    {
                        "code": "REC_PENDING_ACKNOWLEDGEMENT",
                        "label": "Pending Acknowledgement",
                        "description": "Developer must acknowledge or submit rebuttal",
                        "sort_order": 3
                    },
                    {
                        "code": "REC_IN_REBUTTAL",
                        "label": "In Rebuttal",
                        "description": "Developer submitted rebuttal - awaiting validator review",
                        "sort_order": 4
                    },
                    {
                        "code": "REC_PENDING_ACTION_PLAN",
                        "label": "Pending Action Plan",
                        "description": "Acknowledged - developer must submit action plan",
                        "sort_order": 5
                    },
                    {
                        "code": "REC_PENDING_VALIDATOR_REVIEW",
                        "label": "Pending Validator Review",
                        "description": "Action plan submitted - awaiting validator approval",
                        "sort_order": 6
                    },
                    {
                        "code": "REC_OPEN",
                        "label": "Open",
                        "description": "Action plan approved - remediation work in progress",
                        "sort_order": 7
                    },
                    {
                        "code": "REC_REWORK_REQUIRED",
                        "label": "Rework Required",
                        "description": "Validator rejected closure evidence - additional work needed",
                        "sort_order": 8
                    },
                    {
                        "code": "REC_PENDING_CLOSURE_REVIEW",
                        "label": "Pending Closure Review",
                        "description": "Closure evidence submitted - awaiting validator review",
                        "sort_order": 9
                    },
                    {
                        "code": "REC_PENDING_APPROVAL",
                        "label": "Pending Final Approval",
                        "description": "Validator approved closure - awaiting stakeholder approvals",
                        "sort_order": 10
                    },
                    {
                        "code": "REC_CLOSED",
                        "label": "Closed",
                        "description": "All approvals received - recommendation successfully closed",
                        "sort_order": 11
                    },
                    {
                        "code": "REC_DROPPED",
                        "label": "Dropped",
                        "description": "Rebuttal accepted - recommendation withdrawn",
                        "sort_order": 12
                    },
                ]
            },
            {
                "name": "Recommendation Category",
                "description": "Categories for classifying recommendations by type of issue",
                "is_system": True,
                "values": [
                    {
                        "code": "DATA_QUALITY",
                        "label": "Data Quality",
                        "description": "Issues related to input data, data sources, or data transformations",
                        "sort_order": 1
                    },
                    {
                        "code": "METHODOLOGY",
                        "label": "Methodology",
                        "description": "Issues with model theory, algorithms, or statistical methods",
                        "sort_order": 2
                    },
                    {
                        "code": "IMPLEMENTATION",
                        "label": "Implementation",
                        "description": "Issues with code, systems, or technical implementation",
                        "sort_order": 3
                    },
                    {
                        "code": "DOCUMENTATION",
                        "label": "Documentation",
                        "description": "Issues with model documentation, specifications, or user guides",
                        "sort_order": 4
                    },
                    {
                        "code": "MONITORING",
                        "label": "Monitoring",
                        "description": "Issues with ongoing performance monitoring or controls",
                        "sort_order": 5
                    },
                    {
                        "code": "GOVERNANCE",
                        "label": "Governance",
                        "description": "Issues with model governance, ownership, or approval processes",
                        "sort_order": 6
                    },
                    {
                        "code": "OTHER",
                        "label": "Other",
                        "description": "Other issues not covered by standard categories",
                        "sort_order": 7
                    },
                ]
            },
            {
                "name": "Action Plan Task Status",
                "description": "Status tracking for individual action plan tasks",
                "is_system": True,
                "values": [
                    {
                        "code": "NOT_STARTED",
                        "label": "Not Started",
                        "description": "Task has not been started yet",
                        "sort_order": 1
                    },
                    {
                        "code": "IN_PROGRESS",
                        "label": "In Progress",
                        "description": "Task is currently being worked on",
                        "sort_order": 2
                    },
                    {
                        "code": "COMPLETED",
                        "label": "Completed",
                        "description": "Task has been completed",
                        "sort_order": 3
                    },
                ]
            },
            {
                "name": "Model Usage Frequency",
                "description": "How frequently a model is typically used in production",
                "is_system": True,
                "values": [
                    {
                        "code": "DAILY",
                        "label": "Daily",
                        "description": "Model runs daily or more frequently",
                        "sort_order": 1
                    },
                    {
                        "code": "MONTHLY",
                        "label": "Monthly",
                        "description": "Model runs monthly",
                        "sort_order": 2
                    },
                    {
                        "code": "QUARTERLY",
                        "label": "Quarterly",
                        "description": "Model runs quarterly",
                        "sort_order": 3
                    },
                    {
                        "code": "ANNUALLY",
                        "label": "Annually",
                        "description": "Model runs annually",
                        "sort_order": 4
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
                    created_at=utc_now()
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
                        created_at=utc_now()
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
                            created_at=utc_now()
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
                created_at=utc_now(),
                updated_at=utc_now()
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
            # Define per-tier policies: frequency, grace period, and lead time
            tier_policies = {
                "TIER_1": {
                    "frequency_months": 12,
                    "grace_period_months": 2,  # Shorter grace for high-risk
                    "model_change_lead_time_days": 120,
                    "description": "High-risk models require comprehensive re-validation every 12 months, 2-month grace period, and 120-day lead time for validation completion"
                },
                "TIER_2": {
                    "frequency_months": 18,
                    "grace_period_months": 3,
                    "model_change_lead_time_days": 90,
                    "description": "Medium-risk models require re-validation every 18 months, 3-month grace period, and 90-day lead time for validation completion"
                },
                "TIER_3": {
                    "frequency_months": 24,
                    "grace_period_months": 3,
                    "model_change_lead_time_days": 60,
                    "description": "Low-risk models require re-validation every 24 months, 3-month grace period, and 60-day lead time for validation completion"
                },
                "TIER_4": {
                    "frequency_months": 36,
                    "grace_period_months": 4,  # Longer grace for low-risk
                    "model_change_lead_time_days": 45,
                    "description": "Very low-risk models require re-validation every 36 months, 4-month grace period, and 45-day lead time for validation completion"
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
                            grace_period_months=policy_config["grace_period_months"],
                            model_change_lead_time_days=policy_config["model_change_lead_time_days"],
                            description=policy_config["description"],
                            created_at=utc_now(),
                            updated_at=utc_now()
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

        # Seed Recommendation Priority Configurations
        print("\n=== Seeding Recommendation Priority Configurations ===")
        rec_priority_taxonomy = db.query(Taxonomy).filter(
            Taxonomy.name == "Recommendation Priority"
        ).first()

        if rec_priority_taxonomy:
            # Configuration for each priority level
            # HIGH/MEDIUM: Full workflow with action plan required
            # LOW: Validator approval sufficient, action plan required
            # CONSIDERATION: Action plan NOT required, simplified workflow
            priority_configs = {
                "HIGH": {
                    "requires_final_approval": True,
                    "requires_action_plan": True,
                    "description": "High priority - full approval workflow and action plan required"
                },
                "MEDIUM": {
                    "requires_final_approval": True,
                    "requires_action_plan": True,
                    "description": "Medium priority - full approval workflow and action plan required"
                },
                "LOW": {
                    "requires_final_approval": False,
                    "requires_action_plan": True,
                    "description": "Low priority - validator approval sufficient, action plan required"
                },
                "CONSIDERATION": {
                    "requires_final_approval": False,
                    "requires_action_plan": False,
                    "description": "Consideration - action plan not required, simplified workflow"
                },
            }

            for priority_code, config_data in priority_configs.items():
                priority_value = db.query(TaxonomyValue).filter(
                    TaxonomyValue.taxonomy_id == rec_priority_taxonomy.taxonomy_id,
                    TaxonomyValue.code == priority_code
                ).first()

                if priority_value:
                    existing_config = db.query(RecommendationPriorityConfig).filter(
                        RecommendationPriorityConfig.priority_id == priority_value.value_id
                    ).first()

                    if not existing_config:
                        config = RecommendationPriorityConfig(
                            priority_id=priority_value.value_id,
                            requires_final_approval=config_data["requires_final_approval"],
                            requires_action_plan=config_data["requires_action_plan"],
                            description=config_data["description"],
                            created_at=utc_now(),
                            updated_at=utc_now()
                        )
                        db.add(config)
                        print(f"✓ Created priority config for {priority_value.label}")
                    else:
                        print(f"✓ Priority config already exists for {priority_value.label}")

            db.commit()
        else:
            print("⚠ Recommendation Priority taxonomy not found - skipping priority config seeding")

        # Seed timeframe configurations
        seed_timeframe_configs(db)

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
        comprehensive_val_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "COMPREHENSIVE"
        ).first()
        pass_outcome = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "PASS"
        ).first()

        # New taxonomy values for ValidationRequest
        medium_priority = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "MEDIUM").first()
        approved_status = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "APPROVED").first()
        fit_for_purpose = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "FIT_FOR_PURPOSE").first()

        # Get usage frequency for demo models
        usage_freq_monthly = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "MONTHLY").first()

        if tier_2 and tier_3 and initial_val_type and comprehensive_val_type and pass_outcome and admin and validator and medium_priority and approved_status and fit_for_purpose and usage_freq_monthly:
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
                    usage_frequency_id=usage_freq_monthly.value_id,
                    created_at=utc_now()
                )
                db.add(model_a)
                db.flush()

                # Add validation from 24 months ago
                val_date = today - timedelta(days=24*30)
                req = ValidationRequest(
                    requestor_id=admin.user_id,
                    validation_type_id=comprehensive_val_type.value_id,
                    priority_id=medium_priority.value_id,
                    target_completion_date=val_date,
                    current_status_id=approved_status.value_id,
                    created_at=val_date - timedelta(days=30),
                    updated_at=val_date,
                    completion_date=datetime.combine(
                        val_date, datetime.min.time())
                )
                db.add(req)
                db.flush()

                db.add(ValidationRequestModelVersion(
                    request_id=req.request_id, model_id=model_a.model_id))

                outcome = ValidationOutcome(
                    request_id=req.request_id,
                    overall_rating_id=fit_for_purpose.value_id,
                    executive_summary="Comprehensive validation completed. Model performing as expected.",
                    recommended_review_frequency=18,
                    effective_date=val_date,
                    created_at=val_date
                )
                db.add(outcome)

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
                    usage_frequency_id=usage_freq_monthly.value_id,
                    created_at=utc_now()
                )
                db.add(model_b)
                db.flush()

                # Add validation from 20 months ago
                val_date = today - timedelta(days=20*30)
                req = ValidationRequest(
                    requestor_id=admin.user_id,
                    validation_type_id=comprehensive_val_type.value_id,
                    priority_id=medium_priority.value_id,
                    target_completion_date=val_date,
                    current_status_id=approved_status.value_id,
                    created_at=val_date - timedelta(days=30),
                    updated_at=val_date,
                    completion_date=datetime.combine(
                        val_date, datetime.min.time())
                )
                db.add(req)
                db.flush()

                db.add(ValidationRequestModelVersion(
                    request_id=req.request_id, model_id=model_b.model_id))

                outcome = ValidationOutcome(
                    request_id=req.request_id,
                    overall_rating_id=fit_for_purpose.value_id,
                    executive_summary="Comprehensive validation completed.",
                    recommended_review_frequency=18,
                    effective_date=val_date,
                    created_at=val_date
                )
                db.add(outcome)

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
                    usage_frequency_id=usage_freq_monthly.value_id,
                    created_at=utc_now()
                )
                db.add(model_c)
                db.flush()

                # Add validation from 17 months ago
                val_date = today - timedelta(days=17*30)
                req = ValidationRequest(
                    requestor_id=admin.user_id,
                    validation_type_id=comprehensive_val_type.value_id,
                    priority_id=medium_priority.value_id,
                    target_completion_date=val_date,
                    current_status_id=approved_status.value_id,
                    created_at=val_date - timedelta(days=30),
                    updated_at=val_date,
                    completion_date=datetime.combine(
                        val_date, datetime.min.time())
                )
                db.add(req)
                db.flush()

                db.add(ValidationRequestModelVersion(
                    request_id=req.request_id, model_id=model_c.model_id))

                outcome = ValidationOutcome(
                    request_id=req.request_id,
                    overall_rating_id=fit_for_purpose.value_id,
                    executive_summary="Comprehensive validation completed.",
                    recommended_review_frequency=18,
                    effective_date=val_date,
                    created_at=val_date
                )
                db.add(outcome)

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
                    usage_frequency_id=usage_freq_monthly.value_id,
                    created_at=utc_now()
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
                    usage_frequency_id=usage_freq_monthly.value_id,
                    created_at=utc_now()
                )
                db.add(model_e)
                db.flush()

                # Add recent validation
                val_date = today - timedelta(days=6*30)
                req = ValidationRequest(
                    requestor_id=admin.user_id,
                    validation_type_id=comprehensive_val_type.value_id,
                    priority_id=medium_priority.value_id,
                    target_completion_date=val_date,
                    current_status_id=approved_status.value_id,
                    created_at=val_date - timedelta(days=30),
                    updated_at=val_date,
                    completion_date=datetime.combine(
                        val_date, datetime.min.time())
                )
                db.add(req)
                db.flush()

                db.add(ValidationRequestModelVersion(
                    request_id=req.request_id, model_id=model_e.model_id))

                outcome = ValidationOutcome(
                    request_id=req.request_id,
                    overall_rating_id=fit_for_purpose.value_id,
                    executive_summary="Comprehensive validation completed. Model is compliant.",
                    recommended_review_frequency=18,
                    effective_date=val_date,
                    created_at=val_date
                )
                db.add(outcome)

                print(
                    "✓ Created 'Demo: Compliant Model' (6 months - well within compliance)")

            db.commit()
            print("✓ Demo data creation completed\n")
        else:
            print(
                "⚠ Missing required taxonomy values or users - skipping demo data creation\n")

        # Seed Model Type Hierarchy
        seed_model_type_taxonomy(db)

        # Seed KPM Library (Key Performance Metrics for ongoing monitoring)
        seed_kpm(db)

        # Seed MAP Applications (Mock Managed Application Portfolio)
        seed_map_applications(db)

        # Seed Conditional Approvals
        seed_conditional_approvals(db)

        # Seed Qualitative Risk Factors (for Model Risk Assessment)
        seed_qualitative_risk_factors(db)

        # Seed Validation Scorecard Configuration
        seed_scorecard_config(db)

        print("Seeding completed successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_map_applications(db):
    """Seed mock Managed Application Portfolio (MAP) applications."""
    print("Seeding MAP applications...")

    # Check if already seeded
    existing_count = db.query(MapApplication).count()
    if existing_count > 0:
        print(
            f"✓ MAP applications already seeded ({existing_count} applications)")
        return

    # Mock applications typical of a financial services organization
    applications = [
        {
            "application_code": "APP-EDW-001",
            "application_name": "Enterprise Data Warehouse",
            "description": "Central repository for enterprise data including market data, positions, and risk metrics",
            "owner_name": "Jane Smith",
            "owner_email": "jane.smith@contoso.com",
            "department": "Data Engineering",
            "technology_stack": "Snowflake/AWS",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-EDW-001"
        },
        {
            "application_code": "APP-RAP-001",
            "application_name": "Risk Analytics Platform",
            "description": "Enterprise platform for risk model execution, scoring, and analytics",
            "owner_name": "Michael Chen",
            "owner_email": "michael.chen@contoso.com",
            "department": "Model Risk",
            "technology_stack": "Python/Kubernetes",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-RAP-001"
        },
        {
            "application_code": "APP-BBG-001",
            "application_name": "Bloomberg Data Feed",
            "description": "Market data integration from Bloomberg terminals and APIs",
            "owner_name": "Sarah Johnson",
            "owner_email": "sarah.johnson@contoso.com",
            "department": "Market Data",
            "technology_stack": "Bloomberg API/Java",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-BBG-001"
        },
        {
            "application_code": "APP-MRD-001",
            "application_name": "Model Results Dashboard",
            "description": "Business intelligence dashboards displaying model outputs and performance metrics",
            "owner_name": "David Wilson",
            "owner_email": "david.wilson@contoso.com",
            "department": "Business Intelligence",
            "technology_stack": "Tableau/React",
            "criticality_tier": "High",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-MRD-001"
        },
        {
            "application_code": "APP-AMS-001",
            "application_name": "Alert Management System",
            "description": "Centralized alerting and incident management for model operations",
            "owner_name": "Lisa Anderson",
            "owner_email": "lisa.anderson@contoso.com",
            "department": "Operations",
            "technology_stack": "ServiceNow/Python",
            "criticality_tier": "High",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-AMS-001"
        },
        {
            "application_code": "APP-PMS-001",
            "application_name": "Portfolio Management System",
            "description": "Enterprise portfolio management and position tracking system",
            "owner_name": "Robert Taylor",
            "owner_email": "robert.taylor@contoso.com",
            "department": "Trading",
            "technology_stack": "Java/Oracle",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-PMS-001"
        },
        {
            "application_code": "APP-TES-001",
            "application_name": "Trade Execution System",
            "description": "Low-latency trade execution and order management platform",
            "owner_name": "James Martinez",
            "owner_email": "james.martinez@contoso.com",
            "department": "Trading",
            "technology_stack": "C++/Low-Latency",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-TES-001"
        },
        {
            "application_code": "APP-RRP-001",
            "application_name": "Regulatory Reporting Platform",
            "description": "Automated regulatory report generation for FR Y-14, CCAR, and other filings",
            "owner_name": "Emily Davis",
            "owner_email": "emily.davis@contoso.com",
            "department": "Compliance",
            "technology_stack": "Python/SQL Server",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-RRP-001"
        },
        {
            "application_code": "APP-DQM-001",
            "application_name": "Data Quality Monitor",
            "description": "Automated data quality monitoring and validation framework",
            "owner_name": "Chris Brown",
            "owner_email": "chris.brown@contoso.com",
            "department": "Data Governance",
            "technology_stack": "Great Expectations/Python",
            "criticality_tier": "Medium",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-DQM-001"
        },
        {
            "application_code": "APP-MSO-001",
            "application_name": "Model Scheduler/Orchestrator",
            "description": "Workflow orchestration for model execution schedules and dependencies",
            "owner_name": "Amanda White",
            "owner_email": "amanda.white@contoso.com",
            "department": "Model Operations",
            "technology_stack": "Airflow/AWS",
            "criticality_tier": "High",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-MSO-001"
        },
        {
            "application_code": "APP-CRM-001",
            "application_name": "Credit Risk Manager",
            "description": "Credit risk assessment and exposure management platform",
            "owner_name": "Thomas Lee",
            "owner_email": "thomas.lee@contoso.com",
            "department": "Credit Risk",
            "technology_stack": "SAS/Oracle",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-CRM-001"
        },
        {
            "application_code": "APP-FVS-001",
            "application_name": "Fair Value System",
            "description": "Fair value calculation and financial reporting system",
            "owner_name": "Jennifer Garcia",
            "owner_email": "jennifer.garcia@contoso.com",
            "department": "Accounting",
            "technology_stack": "Python/PostgreSQL",
            "criticality_tier": "High",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-FVS-001"
        },
        {
            "application_code": "APP-STR-001",
            "application_name": "Stress Testing Runner",
            "description": "Grid computing platform for CCAR/DFAST stress testing scenarios",
            "owner_name": "Kevin Harris",
            "owner_email": "kevin.harris@contoso.com",
            "department": "Risk Management",
            "technology_stack": "Python/Grid Computing",
            "criticality_tier": "Critical",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-STR-001"
        },
        {
            "application_code": "APP-LMS-001",
            "application_name": "Limit Management System",
            "description": "Real-time limit monitoring and breach management",
            "owner_name": "Michelle Clark",
            "owner_email": "michelle.clark@contoso.com",
            "department": "Risk Management",
            "technology_stack": "Java/Oracle",
            "criticality_tier": "High",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-LMS-001"
        },
        {
            "application_code": "APP-RDL-001",
            "application_name": "Reference Data Library",
            "description": "Master data management for securities, counterparties, and entities",
            "owner_name": "Daniel Moore",
            "owner_email": "daniel.moore@contoso.com",
            "department": "Data Management",
            "technology_stack": "MDM/SQL Server",
            "criticality_tier": "High",
            "status": "Active",
            "external_url": "https://map.contoso.com/app/APP-RDL-001"
        },
    ]

    for app_data in applications:
        app = MapApplication(
            application_code=app_data["application_code"],
            application_name=app_data["application_name"],
            description=app_data["description"],
            owner_name=app_data["owner_name"],
            owner_email=app_data["owner_email"],
            department=app_data["department"],
            technology_stack=app_data["technology_stack"],
            criticality_tier=app_data["criticality_tier"],
            status=app_data["status"],
            external_url=app_data["external_url"],
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(app)

    db.commit()
    print(f"✓ Created {len(applications)} MAP applications")


def seed_conditional_approvals(db):
    """Seed sample approver roles and conditional approval rules for UAT."""
    print("Seeding conditional approvals...")

    # Create sample approver roles
    sample_roles = [
        {
            "role_name": "US Model Risk Management Committee",
            "description": "US Model Risk Committee responsible for approving high-risk model use in US wholly-owned regions",
            "is_active": True
        },
        {
            "role_name": "UK Model Risk Management Committee",
            "description": "UK Model Risk Committee responsible for approving high-risk model use in UK regions",
            "is_active": True
        },
        {
            "role_name": "EU Model Risk Management Committee",
            "description": "EU Model Risk Committee responsible for approving high-risk model use in EU regions",
            "is_active": True
        },
        {
            "role_name": "Global Model Risk Officer",
            "description": "Global oversight for critical Tier 1 models across all regions",
            "is_active": True
        },
        {
            "role_name": "Chief Risk Officer",
            "description": "CRO approval required for CCAR/DFAST models and high-risk stress testing models",
            "is_active": True
        }
    ]

    role_id_map = {}
    for role_data in sample_roles:
        existing = db.query(ApproverRole).filter(
            ApproverRole.role_name == role_data["role_name"]
        ).first()

        if not existing:
            role = ApproverRole(**role_data)
            db.add(role)
            db.flush()
            role_id_map[role_data["role_name"]] = role.role_id
            print(f"✓ Created approver role: {role_data['role_name']}")
        else:
            role_id_map[role_data["role_name"]] = existing.role_id
            print(f"✓ Approver role already exists: {role_data['role_name']}")

    db.commit()

    # Get taxonomy values and regions for rule conditions
    validation_type_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Validation Type"
    ).first()

    risk_tier_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Model Risk Tier"
    ).first()

    if not validation_type_taxonomy or not risk_tier_taxonomy:
        print("⚠ Missing required taxonomies for conditional approval rules")
        return

    # Get specific taxonomy values
    initial_validation = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == validation_type_taxonomy.taxonomy_id,
        TaxonomyValue.code == "INITIAL"
    ).first()

    tier1_high = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == risk_tier_taxonomy.taxonomy_id,
        TaxonomyValue.code == "TIER_1"
    ).first()

    # Get regions
    us_region = db.query(Region).filter(Region.code == "US").first()
    uk_region = db.query(Region).filter(Region.code == "UK").first()
    eu_region = db.query(Region).filter(Region.code == "EU").first()

    if not all([initial_validation, tier1_high, us_region, uk_region, eu_region]):
        print(
            "⚠ Missing required taxonomy values or regions for conditional approval rules")
        return

    # Create sample conditional approval rules
    sample_rules = [
        {
            "rule_name": "US High Risk Initial Validation Approval",
            "description": "Requires US MRM Committee approval for initial validation of Tier 1 (High Risk) models in US region",
            "is_active": True,
            "validation_type_ids": str(initial_validation.value_id),
            "risk_tier_ids": str(tier1_high.value_id),
            "governance_region_ids": str(us_region.region_id),
            "deployed_region_ids": str(us_region.region_id),
            "required_approver_roles": ["US Model Risk Management Committee"]
        },
        {
            "rule_name": "UK High Risk Initial Validation Approval",
            "description": "Requires UK MRM Committee approval for initial validation of Tier 1 (High Risk) models in UK region",
            "is_active": True,
            "validation_type_ids": str(initial_validation.value_id),
            "risk_tier_ids": str(tier1_high.value_id),
            "governance_region_ids": str(uk_region.region_id),
            "deployed_region_ids": str(uk_region.region_id),
            "required_approver_roles": ["UK Model Risk Management Committee"]
        },
        {
            "rule_name": "EU High Risk Initial Validation Approval",
            "description": "Requires EU MRM Committee approval for initial validation of Tier 1 (High Risk) models in EU region",
            "is_active": True,
            "validation_type_ids": str(initial_validation.value_id),
            "risk_tier_ids": str(tier1_high.value_id),
            "governance_region_ids": str(eu_region.region_id),
            "deployed_region_ids": str(eu_region.region_id),
            "required_approver_roles": ["EU Model Risk Management Committee"]
        },
        {
            "rule_name": "Global Tier 1 Model Oversight",
            "description": "Requires Global Model Risk Officer approval for all Tier 1 (High Risk) initial validations regardless of region",
            "is_active": True,
            "validation_type_ids": str(initial_validation.value_id),
            "risk_tier_ids": str(tier1_high.value_id),
            "governance_region_ids": None,  # ANY region
            "deployed_region_ids": None,  # ANY region
            "required_approver_roles": ["Global Model Risk Officer"]
        }
    ]

    for rule_data in sample_rules:
        existing = db.query(ConditionalApprovalRule).filter(
            ConditionalApprovalRule.rule_name == rule_data["rule_name"]
        ).first()

        if existing:
            print(
                f"✓ Conditional approval rule already exists: {rule_data['rule_name']}")
            continue

        # Create rule
        rule = ConditionalApprovalRule(
            rule_name=rule_data["rule_name"],
            description=rule_data["description"],
            is_active=rule_data["is_active"],
            validation_type_ids=rule_data["validation_type_ids"],
            risk_tier_ids=rule_data["risk_tier_ids"],
            governance_region_ids=rule_data["governance_region_ids"],
            deployed_region_ids=rule_data["deployed_region_ids"]
        )
        db.add(rule)
        db.flush()

        # Add required approver roles
        for approver_role_name in rule_data["required_approver_roles"]:
            if approver_role_name in role_id_map:
                assoc = RuleRequiredApprover(
                    rule_id=rule.rule_id,
                    approver_role_id=role_id_map[approver_role_name]
                )
                db.add(assoc)

        print(f"✓ Created conditional approval rule: {rule_data['rule_name']}")

    db.commit()
    print("✓ Conditional approvals seeded")


def seed_model_type_taxonomy(db):
    """Seed the hierarchical model type taxonomy."""
    print("Seeding model type taxonomy...")

    for i, cat_data in enumerate(MODEL_TYPE_HIERARCHY["categories"], 1):
        # Create or update category
        category = db.query(ModelTypeCategory).filter(
            ModelTypeCategory.name == cat_data["l1_name"]
        ).first()

        if not category:
            category = ModelTypeCategory(
                name=cat_data["l1_name"],
                description=cat_data["description"],
                sort_order=i
            )
            db.add(category)
            db.flush()
            print(f"✓ Created category: {category.name}")
        else:
            category.description = cat_data["description"]
            category.sort_order = i
            print(f"✓ Updated category: {category.name}")

        # Create or update types
        for j, type_name in enumerate(cat_data["l2_subtypes"], 1):
            model_type = db.query(ModelType).filter(
                ModelType.name == type_name,
                ModelType.category_id == category.category_id
            ).first()

            if not model_type:
                model_type = ModelType(
                    category_id=category.category_id,
                    name=type_name,
                    sort_order=j,
                    is_active=True
                )
                db.add(model_type)
            else:
                model_type.sort_order = j
                model_type.is_active = True

    db.commit()
    print("✓ Model type taxonomy seeded")


# KPM (Key Performance Metrics) data for ongoing monitoring
KPM_DATA = {
    "categories": [
        {
            "code": "model_calibration",
            "name": "Model calibration",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Brier Score", "description": "Mean squared error between predicted probabilities and actual binary outcomes; reflects both calibration and overall probabilistic accuracy.",
                    "calculation": "Average over all observations of (predicted_probability - actual_outcome)^2, where actual_outcome is 0 or 1.", "interpretation": "Lower is better; 0 indicates perfect calibration. As a rule of thumb, a model that is materially better than a naive constant-probability model (event_rate * (1 - event_rate)) is acceptable. Rising Brier score over time suggests worsening calibration."},
                {"name": "Hosmer-Lemeshow Test", "description": "Goodness-of-fit test for binary probability models; checks whether observed event rates agree with predicted probabilities across risk bands.",
                    "calculation": "Sort observations by predicted probability, split into K groups (often 10), then compute a chi-square statistic comparing observed versus expected events in each group to obtain a p-value.", "interpretation": "High p-value (for example > 0.05) indicates no evidence of miscalibration; very low p-value (for example < 0.01) suggests systematic mismatch between predicted and observed event rates and may trigger recalibration."},
                {"name": "Calibration Intercept", "description": "Measures overall bias of predicted probabilities relative to actual outcomes (calibration in the large).", "calculation": "Fit a logistic regression of outcomes on the log-odds of predicted probabilities with slope fixed at 1; the constant term is the calibration intercept.",
                 "interpretation": "Ideal value is 0. A positive intercept means the model underestimates risk on average (events happen more often than predicted); a negative intercept means the model overestimates risk. In practice, values within about +/-0.1 are usually considered acceptable, with larger deviations suggesting recalibration."},
                {"name": "Calibration Slope", "description": "Assesses whether predicted probabilities are too extreme or too moderate compared to actual outcomes.",
                    "calculation": "Fit a logistic regression of outcomes on the log-odds of predicted probabilities (with intercept); the coefficient on the log-odds term is the calibration slope.", "interpretation": "Ideal value is 1. A slope below 1 indicates over-confident predictions (high risks too high, low risks too low); a slope above 1 indicates under-confident predictions. Slopes between about 0.8 and 1.2 are commonly viewed as reasonable; values much outside this range indicate substantial miscalibration."},
                {"name": "Expected Calibration Error (ECE)", "description": "Summarises, in a single value, the average absolute difference between predicted probabilities and observed event rates across bins of prediction confidence.", "calculation": "Bin predictions into intervals (for example deciles of predicted probability). For each bin, compute the absolute difference between the mean predicted probability and the observed event rate. ECE is the weighted average of these differences, weighted by bin size.",
                 "interpretation": "Ranges from 0 upward; lower is better. Values of a few percentage points (for example ECE < 0.02) usually indicate very good calibration. Increasing ECE over time is a sign of calibration drift and may trigger recalibration or model refresh."},
            ]
        },
        {
            "code": "model_performance",
            "name": "Model performance",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Accuracy", "description": "Overall proportion of correctly classified observations.", "calculation": "Accuracy = (true_positives + true_negatives) / (true_positives + false_positives + true_negatives + false_negatives).",
                 "interpretation": "Ranges from 0 to 1; higher is better. Useful when classes are roughly balanced. In imbalanced problems (for example fraud detection), accuracy can be misleading and should be interpreted together with precision, recall and other metrics."},
                {"name": "Precision", "description": "Share of predicted positives that are actually positive; measures how often alerts are correct.",
                    "calculation": "Precision = true_positives / (true_positives + false_positives).", "interpretation": "Ranges from 0 to 1; higher is better. High precision means few false alarms (for example, most flagged fraud cases are truly fraud). Operationally, institutions may target precision above 0.8 or 0.9 for certain high-cost review processes."},
                {"name": "Recall", "description": "Share of actual positives that the model correctly identifies; also called sensitivity or true positive rate.",
                    "calculation": "Recall = true_positives / (true_positives + false_negatives).", "interpretation": "Ranges from 0 to 1; higher is better. High recall means the model misses few bad cases (for example few defaulters slip through). For risk models, recall above 0.9 on key segments is often desirable, subject to cost trade-offs."},
                {"name": "F1 Score", "description": "Harmonic mean of precision and recall; balances the trade-off between missing positives and generating false alarms.",
                    "calculation": "F1 = 2 * precision * recall / (precision + recall).", "interpretation": "Ranges from 0 to 1; higher is better. An F1 score near 1 indicates both high precision and high recall. In imbalanced settings, F1 is often used as a primary optimisation metric; values above about 0.7 are usually regarded as good, depending on the use case."},
                {"name": "ROC AUC", "description": "Area under the receiver operating characteristic curve; measures the model's ability to rank positive cases above negative cases across all thresholds.", "calculation": "Compute true positive rate and false positive rate for many score thresholds, plot the ROC curve and calculate the area under the curve.",
                    "interpretation": "Ranges from 0.5 (no discrimination) to 1.0 (perfect discrimination). In credit risk, ROC AUC around 0.7 to 0.8 is common; above 0.8 is strong. Declines in ROC AUC over time indicate reduced discriminatory power."},
                {"name": "PR AUC", "description": "Area under the precision-recall curve; focuses on performance on the positive (often rare) class.", "calculation": "Compute precision and recall for many thresholds, plot the curve and calculate the area under it.",
                 "interpretation": "Ranges from 0 to 1; higher is better. The baseline PR AUC equals the prevalence of the positive class. For very rare events (for example 1% fraud), a PR AUC far above 0.01 (for example 0.2 or greater) indicates a highly effective model."},
                {"name": "Kolmogorov-Smirnov (KS)", "description": "Maximum separation between the cumulative score distributions of positive and negative classes; widely used in credit scoring.", "calculation": "Sort records by predicted score; at each score threshold compute cumulative shares of positives and negatives. KS is the maximum difference between these two cumulative curves.",
                 "interpretation": "Ranges from 0 to 1 (often reported as 0 to 100%). Higher is better. In many credit models, KS above 0.3 (30%) is acceptable, around 0.4 to 0.5 is considered strong. A declining KS over time indicates weakening rank-order stability."},
                {"name": "Log Loss (Cross-Entropy)", "description": "Penalty-based measure of how well predicted probabilities match actual outcomes; strongly penalises confident wrong predictions.", "calculation": "For binary classification, log_loss = -(1/N) * sum( y * log(p) + (1 - y) * log(1 - p) ) over all observations, where p is predicted probability and y is 0 or 1.",
                 "interpretation": "Lower is better; 0 is perfect. A log loss close to the entropy of the class distribution corresponds to a weak or uninformative model. Rising log loss over time, with similar class mix, suggests deterioration in either calibration or discrimination."},
                {"name": "Mean Squared Error (MSE)", "description": "Standard regression metric measuring average squared difference between predicted values and actual values.", "calculation": "MSE = (1/N) * sum( (prediction - actual)^2 ) across all observations; root mean squared error (RMSE) is the square root of MSE.",
                 "interpretation": "Lower is better; 0 indicates perfect prediction. Because MSE is in squared units, RMSE is often used for interpretability. Acceptable values depend on the scale of the target; for example, for monetary predictions, RMSE should be small relative to typical transaction sizes."},
            ]
        },
        {
            "code": "model_input_data_monitoring",
            "name": "Model input data monitoring",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Missing Data Rate", "description": "Proportion of missing or null values in model input features.", "calculation": "For each feature, missing_rate = number_of_missing_values / total_number_of_records; can also aggregate across features.",
                    "interpretation": "Ideally low and stable over time. Sudden increases often indicate upstream data issues. Many institutions flag if any key feature's missing rate exceeds a threshold (for example 5%) compared with training."},
                {"name": "New Category Rate", "description": "Frequency with which categorical features take values that were not seen during model training.", "calculation": "For each categorical variable, new_category_rate = records_with_unseen_value / total_records in the monitoring window.",
                    "interpretation": "Should be close to 0; any persistent non-zero values for important features indicate population change or data quality problems and may require model updates or revised encodings."},
                {"name": "Feature Distribution Drift (PSI)", "description": "Population Stability Index computed on individual input features to quantify distribution shift between a baseline period and current data.", "calculation": "Bin each feature using bins defined on baseline data. For each bin, compute baseline and current proportions, then sum over bins: (current - baseline) * ln(current / baseline).",
                 "interpretation": "Common rules of thumb: PSI < 0.1 indicates little change; 0.1 to 0.2 suggests moderate drift; > 0.2 indicates significant drift that may affect model performance. High PSI on key features is a trigger for investigation."},
            ]
        },
        {
            "code": "model_stability",
            "name": "Model stability",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Score Distribution PSI", "description": "Population Stability Index computed on the model score or predicted probability to track shifts in the overall risk mix.",
                    "calculation": "Bin the model scores using bins defined on a reference period (for example training or prior year), then compute PSI between reference and current score distributions.", "interpretation": "The same rule of thumb as for feature PSI applies: < 0.1 stable, 0.1 to 0.2 moderate shift, > 0.2 large shift. Persistent high score PSI often indicates a change in portfolio composition or macroeconomic conditions, and may precede performance degradation."},
                {"name": "Performance Drift (Metric Change)", "description": "Change in a chosen performance metric (for example ROC AUC, KS, F1) between a baseline period and the current monitoring period.", "calculation": "Compute the performance metric on recent data and subtract the baseline value, or express the difference as a percentage of the baseline.",
                 "interpretation": "Negative changes indicate deterioration. Tolerances depend on the metric and use case; for example, an AUC drop of more than 0.03 or a relative drop in KS greater than about 10% may warrant investigation or model recalibration."},
            ]
        },
        {
            "code": "global_interpretability",
            "name": "Global interpretability",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Feature Importance", "description": "Relative contribution of each feature to the model's predictions when considered over the entire portfolio.", "calculation": "Model-specific or model-agnostic methods, such as tree-based impurity reduction, permutation importance, or mean absolute SHAP values aggregated across all observations.",
                    "interpretation": "Features with larger importance scores are the main drivers of model behaviour. Important features should be conceptually sensible and stable over time; sudden shifts in importance profiles may indicate changes in data or model specification that need explanation."},
                {"name": "Surrogate Model Fidelity", "description": "How closely a simpler, interpretable surrogate model can reproduce the predictions of the complex model.", "calculation": "Train a simple model (for example shallow tree, linear model, or scorecard) to predict the complex model's outputs instead of the true labels; compute R-squared, accuracy, or another similarity metric between surrogate predictions and complex model predictions.",
                 "interpretation": "Higher fidelity (for example R-squared or agreement above 0.8) indicates that the complex model's logic can be well-approximated and explained globally. Low fidelity suggests that simple global explanations may be misleading, and that local or more complex explanation techniques are required."},
                {"name": "Model Complexity", "description": "Structural complexity of the model, used as a proxy for ease of understanding and ability to validate.", "calculation": "Depends on model type: number of features with non-zero coefficients, number and depth of trees, number of rules, parameters, or layers, etc.",
                    "interpretation": "There is no universal numeric threshold, but lower complexity generally aids interpretability and governance. Many institutions set explicit limits (for example maximum number of features or tree depth) and flag models that exceed those limits for additional review."},
            ]
        },
        {
            "code": "local_interpretability",
            "name": "Local interpretability",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Local Explanation Fidelity", "description": "How accurately a local explanation (for example LIME, local SHAP) reproduces the complex model's predictions in a small neighbourhood around an individual case.", "calculation": "For a given observation, generate perturbed samples around it, fit a simple local surrogate model, and compute R-squared or classification accuracy between surrogate predictions and the complex model's predictions on those samples.",
                 "interpretation": "Higher values indicate more trustworthy explanations. As a guideline, local fidelity above about 0.8 is generally considered good; low-fidelity explanations should not be used for sensitive decisions without further analysis."},
                {"name": "Local Explanation Stability", "description": "Degree to which explanations for similar inputs remain consistent.", "calculation": "Compare explanations (for example top contributing features or attribution vectors) for the same case under small perturbations or repeated runs, or for very similar cases; quantify similarity using overlap or correlation measures.",
                 "interpretation": "High stability means small changes in input or random seeds do not materially alter the explanation, supporting trust. Large instability suggests that explanations may be fragile and should be treated with caution in customer or regulator-facing contexts."},
                {"name": "Explanation Sparsity", "description": "Number of features required to explain an individual prediction to a reasonable degree.",
                    "calculation": "Count the number of features whose local importance or attribution exceeds a chosen threshold, or fix the explanation length (for example top 3 to 5 features) and measure how much of the prediction is captured.", "interpretation": "Lower sparsity (fewer features) typically improves interpretability. Many financial institutions prefer explanations that rely on a small set of intuitive drivers (for example 3 to 7 variables) for any one decision."},
            ]
        },
        {
            "code": "llm_monitoring",
            "name": "LLM monitoring",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Perplexity", "description": "Measures how well a language model predicts text; lower perplexity means better next-token prediction on a reference corpus.", "calculation": "Perplexity is the exponential of the average negative log-likelihood of the correct token over a set of sequences.",
                    "interpretation": "Lower is better, but absolute values depend on the task and dataset. For monitoring, the main signal is change over time: rising perplexity on a fixed evaluation set suggests degradation in language modelling quality."},
                {"name": "Factual Accuracy", "description": "Proportion of model responses that are factually correct and sufficiently supported by trusted sources.", "calculation": "On a set of prompts with known answers or verifiable ground truth, measure the fraction of responses assessed as fully correct; may be evaluated by human review or automated fact-checking.",
                    "interpretation": "Higher is better; in financial customer-facing use cases, targets may be above 95% or higher, with zero tolerance for errors on critical regulatory or product information."},
                {"name": "Toxicity Score", "description": "Extent to which model outputs contain abusive, hateful, or otherwise inappropriate language.", "calculation": "Run outputs through a toxicity classifier or rule-based detector and record either the average toxicity score or the proportion of outputs whose score exceeds a defined threshold.",
                    "interpretation": "Should be extremely low in production. Many institutions require that virtually no outputs exceed the toxicity threshold; any spike triggers investigation into prompts, guardrails, or model configuration."},
                {"name": "Response Latency", "description": "End-to-end time taken for the model to produce a response to a user query.",
                    "calculation": "Measure wall-clock time between receipt of input and completion of output, and summarise using averages and high percentiles (for example p90, p95).", "interpretation": "Lower is better for user experience. Typical targets for interactive systems are in the range of sub-second to a few seconds; sustained breaches of service-level targets indicate the need for optimisation or scaling."},
            ]
        },
        {
            "code": "fairness_and_governance",
            "name": "Fairness and governance",
            "category_type": "Quantitative",
            "kpis": [
                {"name": "Disparate Impact Ratio", "description": "Ratio of positive outcome rates between a protected group and a reference group; used to assess potential adverse impact.", "calculation": "Compute the proportion of approved or positive decisions in the protected group and in the reference group, then take protected_rate / reference_rate.",
                    "interpretation": "Values close to 1 indicate parity. In many jurisdictions, a ratio below about 0.8 (the 80 percent rule) is treated as a potential red flag for adverse impact and requires further analysis and justification."},
                {"name": "Equal Opportunity Difference", "description": "Difference in true positive rates between a protected group and a reference group for a favourable outcome.",
                    "calculation": "Compute recall (true positive rate) separately for the protected and reference groups, then subtract reference_group_recall from protected_group_recall.", "interpretation": "The ideal value is 0, meaning equal ability to correctly identify positives across groups. Differences of only a few percentage points may be acceptable; larger gaps can indicate fairness concerns that need mitigation or policy review."},
            ]
        },
        # Qualitative KPM categories (from QUALCAT.json)
        {
            "code": "attestation_based",
            "name": "Attestation-based",
            "category_type": "Qualitative",
            "kpis": [
                {"name": "Model Owner Attestation", "description": "Formal certification by the model owner that the model is functioning as intended and assumptions remain appropriate.", "evaluation_type": "Outcome Only",
                    "interpretation": "Green: Owner confirms model performs as expected with no material concerns. Yellow: Owner notes minor deviations or emerging issues requiring monitoring. Red: Owner identifies significant concerns or confirms model is not performing as intended."},
                {"name": "Developer Attestation", "description": "Technical certification by the model developer that model implementation matches design specification.", "evaluation_type": "Outcome Only",
                    "interpretation": "Green: Developer confirms implementation is correct and complete. Yellow: Minor discrepancies identified but not material to model outputs. Red: Implementation deviates materially from specification."},
                {"name": "Data Provider Attestation", "description": "Certification that input data quality and availability meet model requirements.", "evaluation_type": "Outcome Only",
                    "interpretation": "Green: Data meets all quality requirements. Yellow: Minor data quality issues present but managed. Red: Significant data quality issues affecting model reliability."},
            ]
        },
        {
            "code": "governance_usage_alignment",
            "name": "Governance and usage alignment (qualitative triggers)",
            "category_type": "Qualitative",
            "kpis": [
                {"name": "Business Strategy Alignment", "description": "Assessment of whether model usage remains aligned with current business strategy and environment.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: Model fully aligned with business strategy. Yellow: Minor misalignment or strategy evolution may require adjustments. Red: Significant misalignment; model may need redesign or replacement."},
                {"name": "User Feedback Assessment", "description": "Synthesis of feedback from model users regarding fitness for purpose and usability.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: Users report model meets needs effectively. Yellow: Users report some limitations or usability concerns. Red: Users report significant issues affecting business decisions."},
                {"name": "Scope Compliance Review", "description": "Verification that model use cases remain within approved scope and intended applications.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: All uses within approved scope. Yellow: Borderline use cases identified requiring clarification. Red: Model being used outside approved scope."},
                {"name": "Environmental Change Impact", "description": "Assessment of external environmental changes (market, regulatory, economic) affecting model relevance.", "evaluation_type": "Qualitative",
                 "interpretation": "Green: No material environmental changes affecting model. Yellow: Changes identified that may require model adjustments. Red: Significant environmental shifts that may invalidate model assumptions."},
            ]
        },
        {
            "code": "expert_judgment_assessments",
            "name": "Expert-judgment assessments vs policy frameworks",
            "category_type": "Qualitative",
            "kpis": [
                {"name": "Risk Appetite Alignment", "description": "Expert assessment of whether model outputs remain consistent with institutional risk appetite.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: Outputs fully consistent with risk appetite. Yellow: Some outputs approaching risk appetite boundaries. Red: Outputs inconsistent with or exceeding risk appetite."},
                {"name": "Policy Limit Compliance", "description": "Committee or SME assessment of model outputs against policy limits and internal guidelines.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: All outputs within policy limits. Yellow: Outputs approaching policy limits; enhanced monitoring advised. Red: Policy limits breached; escalation required."},
                {"name": "Methodology Reasonableness", "description": "Expert judgment on whether model methodology remains appropriate and defensible.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: Methodology fully appropriate and well-documented. Yellow: Methodology adequate but could benefit from enhancement. Red: Methodology concerns that may affect reliability."},
            ]
        },
        {
            "code": "model_conditions_exceptions",
            "name": "Model conditions and exception compliance",
            "category_type": "Qualitative",
            "kpis": [
                {"name": "Validation Condition Compliance", "description": "Assessment of compliance with conditions and recommendations from prior validations.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: All conditions met or on track. Yellow: Some conditions delayed but remediation in progress. Red: Material conditions overdue or not being addressed."},
                {"name": "Exception Tracking Status", "description": "Review of outstanding exceptions and their remediation progress.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: No material exceptions or all remediated. Yellow: Exceptions exist with active remediation plans. Red: Significant exceptions without adequate remediation progress."},
                {"name": "Approved Use Scope Conformance", "description": "Verification that live model usage conforms to validation scope and approved applications.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: All usage within approved scope. Yellow: Minor deviations identified and documented. Red: Significant use outside approved scope requiring immediate attention."},
            ]
        },
        {
            "code": "algorithmic_qualitative_classification",
            "name": "Algorithmic multi-step qualitative classification",
            "category_type": "Qualitative",
            "kpis": [
                {"name": "Decision Tree Outcome Assessment", "description": "Rule-based multi-step classification producing color outcomes without simple scalar thresholds.",
                    "evaluation_type": "Qualitative", "interpretation": "Green: All decision criteria pass. Yellow: Some criteria at warning levels. Red: Critical criteria fail or multiple warnings present."},
                {"name": "Composite Qualitative Score", "description": "Weighted combination of multiple qualitative factors into an overall assessment.", "evaluation_type": "Qualitative",
                    "interpretation": "Green: Composite assessment indicates acceptable status. Yellow: Composite indicates monitoring required. Red: Composite indicates material concerns requiring action."},
                {"name": "Expert Panel Rating", "description": "Consensus rating from expert panel applying structured evaluation framework.", "evaluation_type": "Outcome Only",
                    "interpretation": "Green: Panel consensus is favorable. Yellow: Panel notes concerns requiring attention. Red: Panel identifies significant issues."},
            ]
        },
    ]
}


def seed_kpm(db):
    """Seed the KPM (Key Performance Metrics) library."""
    print("Seeding KPM library...")

    for i, cat_data in enumerate(KPM_DATA["categories"], 1):
        # Create or update category
        category = db.query(KpmCategory).filter(
            KpmCategory.code == cat_data["code"]
        ).first()

        if not category:
            category = KpmCategory(
                code=cat_data["code"],
                name=cat_data["name"],
                sort_order=i,
                category_type=cat_data.get("category_type", "Quantitative")
            )
            db.add(category)
            db.flush()
            print(
                f"✓ Created KPM category: {category.name} ({cat_data.get('category_type', 'Quantitative')})")
        else:
            category.name = cat_data["name"]
            category.sort_order = i
            category.category_type = cat_data.get(
                "category_type", "Quantitative")
            print(
                f"✓ Updated KPM category: {category.name} ({category.category_type})")

        # Create or update KPMs
        for j, kpi_data in enumerate(cat_data["kpis"], 1):
            kpm = db.query(Kpm).filter(
                Kpm.name == kpi_data["name"],
                Kpm.category_id == category.category_id
            ).first()

            # Determine evaluation type (default to Quantitative for existing metrics)
            eval_type = kpi_data.get("evaluation_type", "Quantitative")

            if not kpm:
                kpm = Kpm(
                    category_id=category.category_id,
                    name=kpi_data["name"],
                    description=kpi_data.get("description"),
                    calculation=kpi_data.get("calculation"),
                    interpretation=kpi_data.get("interpretation"),
                    sort_order=j,
                    is_active=True,
                    evaluation_type=eval_type
                )
                db.add(kpm)
            else:
                kpm.description = kpi_data.get("description")
                kpm.calculation = kpi_data.get("calculation")
                kpm.interpretation = kpi_data.get("interpretation")
                kpm.sort_order = j
                kpm.is_active = True
                kpm.evaluation_type = eval_type

    db.commit()
    print("✓ KPM library seeded")


# Initial qualitative risk factors for Model Risk Assessment
QUALITATIVE_RISK_FACTORS = [
    {
        "code": "REPUTATION_LEGAL",
        "name": "Reputation, Regulatory Compliance and/or Financial Reporting Risk",
        "description": "Reputation Risk is defined as the risk of negative publicity regarding business conduct or practices which, whether true or not, could significantly harm the institution's reputation as a leading financial institution, or could materially and adversely affect business, operations or financial condition.",
        "weight": "0.3000",
        "sort_order": 1,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "Failure of the model could significantly impact the institution's reputation, regulatory compliance and/or financial reporting.",
                "sort_order": 1
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "Misuse or errors in the model could impact the institution's reputation, regulatory compliance, and/or financial reporting with moderate to low impact.",
                "sort_order": 2
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "Misuse or errors in the model would have limited impact on the institution's reputation, regulatory compliance, and/or financial reporting.",
                "sort_order": 3
            }
        ]
    },
    {
        "code": "COMPLEXITY",
        "name": "Complexity of the Model",
        "description": "The complexity of the model refers to the mathematical sophistication of the model including the number of model inputs, data sources, transformations, and assumptions.",
        "weight": "0.3000",
        "sort_order": 2,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "Multiple inputs or data sources or complex transformation of input data/parameters or non-standard methodologies and assumptions. Mathematical sophistication: Complex mathematical calculation, analysis, or assumptions or simplifications (e.g. regression, calculus, etc.)",
                "sort_order": 1
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "A few inputs or data sources or simple transformation of input data/parameters. Mathematical sophistication: Moderate mathematics or calculations, few assumptions or simplifications, etc.",
                "sort_order": 2
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "Limited inputs or data sources. Mathematical sophistication: Basic mathematics and limited calculations.",
                "sort_order": 3
            }
        ]
    },
    {
        "code": "USAGE_DEPENDENCY",
        "name": "Model Usage and Model Dependency",
        "description": "The model usage and model dependency assesses the strategic importance of the model usage, any model interdependence and potential impact across the organization.",
        "weight": "0.2000",
        "sort_order": 3,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "If error occurs, it would impact institutions reporting to third parties (e.g., rating agencies, shareholders, etc.). Business decisions are taken based on the individual model. The model is a key input to other models. If error occurs, it would impact several LOBs (departments) at the bank.",
                "sort_order": 1
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "Business decisions are taken using the model results, however, other inputs are also taken into account. The model is fed to other models. If a model error occurs, it would impact several LOBs (departments).",
                "sort_order": 2
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "If a model error occurs, it would impact one department. Business decisions are taken using different inputs, the model is only one factor.",
                "sort_order": 3
            }
        ]
    },
    {
        "code": "STABILITY",
        "name": "Stability of the Model",
        "description": "The stability of the model refers to the likelihood of model error, the uncertainty of the model outcomes (unobservable factors), and the ability to monitor the model.",
        "weight": "0.2000",
        "sort_order": 4,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "The likelihood of error is high, and/or the magnitude of the impact of an error is high. The output of the model is not predictable. Third party models where the Bank does not have access to proprietary elements and performance monitoring is not conducted.",
                "sort_order": 1
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "If there is a model error, the magnitude of the impact may be low to moderate. The output of the model is predictable and an occurrence of error is moderate. Third party models with little or no information, regular performance monitoring is conducted, or models whose information is known, but proper regular monitoring process has not been developed.",
                "sort_order": 2
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "The likelihood of error is low, and/or the magnitude of the impact of an error is immaterial. The outputs or factors predictable enough, and therefore the likelihood that an error occurs is low. Third party models with detailed information and can be monitored regularly.",
                "sort_order": 3
            }
        ]
    }
]


def seed_qualitative_risk_factors(db):
    """Seed the qualitative risk factors for Model Risk Assessment."""
    from decimal import Decimal
    print("Seeding qualitative risk factors...")

    for factor_data in QUALITATIVE_RISK_FACTORS:
        # Check if factor already exists
        factor = db.query(QualitativeRiskFactor).filter(
            QualitativeRiskFactor.code == factor_data["code"]
        ).first()

        if not factor:
            factor = QualitativeRiskFactor(
                code=factor_data["code"],
                name=factor_data["name"],
                description=factor_data["description"],
                weight=Decimal(factor_data["weight"]),
                sort_order=factor_data["sort_order"],
                is_active=True
            )
            db.add(factor)
            db.flush()
            print(f"✓ Created risk factor: {factor.name}")
        else:
            # Update existing factor
            factor.name = factor_data["name"]
            factor.description = factor_data["description"]
            factor.weight = Decimal(factor_data["weight"])
            factor.sort_order = factor_data["sort_order"]
            print(f"✓ Updated risk factor: {factor.name}")

        # Create or update guidance for each rating level
        for guidance_data in factor_data["guidance"]:
            guidance = db.query(QualitativeFactorGuidance).filter(
                QualitativeFactorGuidance.factor_id == factor.factor_id,
                QualitativeFactorGuidance.rating == guidance_data["rating"]
            ).first()

            if not guidance:
                guidance = QualitativeFactorGuidance(
                    factor_id=factor.factor_id,
                    rating=guidance_data["rating"],
                    points=guidance_data["points"],
                    description=guidance_data["description"],
                    sort_order=guidance_data["sort_order"]
                )
                db.add(guidance)
            else:
                guidance.points = guidance_data["points"]
                guidance.description = guidance_data["description"]
                guidance.sort_order = guidance_data["sort_order"]

    db.commit()
    print("✓ Qualitative risk factors seeded")


def seed_scorecard_config(db):
    """Seed scorecard sections and criteria from SCORE_CRITERIA.json."""
    import json
    from pathlib import Path
    from decimal import Decimal

    print("Seeding scorecard configuration...")

    # Check if already seeded
    existing_sections = db.query(ScorecardSection).count()
    if existing_sections > 0:
        print(f"✓ Scorecard configuration already seeded ({existing_sections} sections)")
        return

    # Load configuration from SCORE_CRITERIA.json
    # In Docker, it's mounted at /app/SCORE_CRITERIA.json
    # Locally (for tests), it's at the repo root
    config_path = Path("/app/SCORE_CRITERIA.json")
    if not config_path.exists():
        # Fallback for local development/testing
        repo_root = Path(__file__).parent.parent.parent
        config_path = repo_root / "SCORE_CRITERIA.json"

    with open(config_path, "r") as f:
        config = json.load(f)

    # Create sections
    section_map = {}  # code -> ScorecardSection for linking criteria
    for i, section_data in enumerate(config.get("sections", [])):
        section = ScorecardSection(
            code=section_data["code"],
            name=section_data["name"],
            sort_order=i + 1,
            is_active=True
        )
        db.add(section)
        db.flush()
        section_map[section_data["code"]] = section
        print(f"✓ Created scorecard section: {section.name}")

    # Create criteria
    for i, criterion_data in enumerate(config.get("criteria", [])):
        section_code = criterion_data.get("section")
        section = section_map.get(section_code)
        if not section:
            print(f"⚠ Unknown section '{section_code}' for criterion {criterion_data['code']}")
            continue

        criterion = ScorecardCriterion(
            code=criterion_data["code"],
            section_id=section.section_id,
            name=criterion_data["name"],
            description_prompt=criterion_data.get("description_prompt"),
            comments_prompt=criterion_data.get("comments_prompt"),
            include_in_summary=criterion_data.get("include_in_summary", True),
            allow_zero=criterion_data.get("allow_zero", True),
            weight=Decimal(str(criterion_data.get("weight", 1.0))),
            sort_order=i + 1,
            is_active=True
        )
        db.add(criterion)
        print(f"✓ Created scorecard criterion: {criterion.code} - {criterion.name}")

    db.commit()
    print("✓ Scorecard configuration seeded successfully")


if __name__ == "__main__":
    seed_database()
