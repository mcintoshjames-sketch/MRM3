"""shorten_model_type_codes

Revision ID: 69f9c73f2d63
Revises: a12f25297950
Create Date: 2025-11-22 07:41:44.804680

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69f9c73f2d63'
down_revision: Union[str, None] = 'a12f25297950'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get the taxonomy_id for 'Model Type'
    connection = op.get_bind()

    # We need to find the taxonomy_id first
    taxonomy_id_result = connection.execute(
        sa.text("SELECT taxonomy_id FROM taxonomies WHERE name = 'Model Type'")
    ).first()

    if not taxonomy_id_result:
        return  # Model Type taxonomy doesn't exist, nothing to do

    taxonomy_id = taxonomy_id_result[0]

    # Mapping of Label -> New Code
    updates = [
        ("Retail PD Model", "RETAIL_PD"),
        ("Wholesale PD Model", "WHOLESALE_PD"),
        ("LGD Model (Loss Given Default)", "LGD"),
        ("EAD / CCF Model (Exposure at Default / Credit Conversion Factor)", "EAD_CCF"),
        ("Application Scorecard", "APP_SCORECARD"),
        ("Behavioural Scorecard", "BEHAV_SCORECARD"),
        ("Collections Scorecard", "COLL_SCORECARD"),
        ("Internal Rating Model – Obligor / Facility", "INTERNAL_RATING"),
        ("Transition / Migration / Roll-Rate Model", "TRANSITION_MATRIX"),
        ("Prepayment / Early Termination Model", "PREPAYMENT"),
        ("Cure / Recovery Process Model", "CURE_RECOVERY"),
        ("Pricing Model – Linear Instruments", "PRICING_LINEAR"),
        ("Pricing Model – Options & Exotics", "PRICING_EXOTIC"),
        ("Curve / Surface Construction Model", "CURVE_CONSTRUCT"),
        ("VaR / Expected Shortfall (ES) Model", "VAR_ES"),
        ("Sensitivity / Greeks Aggregation Model", "SENSITIVITY_AGG"),
        ("XVA Model (CVA / DVA / FVA / MVA)", "XVA"),
        ("Risk Factor Simulation / Scenario Generator", "RISK_SIMULATION"),
        ("Non-Maturity Deposit (NMD) Model", "NMD"),
        ("Liquidity Runoff / Survival Horizon Model", "LIQUIDITY_RUNOFF"),
        ("Balance Sheet Evolution / Dynamic Balance Sheet Model", "BAL_SHEET_DYN"),
        ("IRRBB Model (EVE / NII Simulation)", "IRRBB"),
        ("Funds Transfer Pricing (FTP) Model", "FTP"),
        ("Lifetime Loss / Expected Credit Loss (ECL) Engine", "ECL_ENGINE"),
        ("Provision / Reserve Allocation Model", "RESERVE_ALLOC"),
        ("Economic Capital / Unexpected Loss Model", "ECON_CAPITAL"),
        ("Stress Testing Projection Model (Top-Down / Bottom-Up)", "STRESS_TEST_PROJ"),
        ("Regulatory Metric Calculation Engine", "REG_METRIC_CALC"),
        ("Transaction Monitoring / Alert Generation Model (AML)", "AML_TXN_MON"),
        ("Customer Risk Rating (CRR) Model – AML/KYC", "AML_CUST_RISK"),
        ("Sanctions Screening Matching Model", "SANCTIONS"),
        ("Fraud Detection Model", "FRAUD"),
        ("Fair Lending / Fairness Assessment Model", "FAIR_LENDING"),
        ("Operational Risk Capital Model (Loss Distribution Approach)", "OP_RISK_CAP"),
        ("Operational Risk Scenario Model", "OP_RISK_SCEN"),
        ("Conduct Risk / Complaints Scoring Model", "CONDUCT_RISK"),
        ("Vendor / Third-Party Risk Scoring Model", "VENDOR_RISK"),
        ("Propensity / Next-Best-Offer Model", "PROPENSITY"),
        ("Churn / Attrition Model", "CHURN"),
        ("Pricing & Elasticity Model", "PRICING_ELAST"),
        ("Segmentation / Clustering Model", "SEGMENTATION"),
        ("Forecasting Model – Volumes / Revenues / KPIs", "FORECAST_KPI"),
        ("Aggregation / Composite Index Model", "AGGREGATION"),
        ("Mapping / Allocation Model", "ALLOCATION"),
        ("Model Risk Scoring / Model Tiering Model", "MRM_SCORING"),
    ]

    for label, new_code in updates:
        connection.execute(
            sa.text("""
                UPDATE taxonomy_values 
                SET code = :new_code 
                WHERE taxonomy_id = :taxonomy_id AND label = :label
            """),
            {"new_code": new_code, "taxonomy_id": taxonomy_id, "label": label}
        )


def downgrade() -> None:
    pass
