"""shorten regulatory category codes

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-11-25 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mapping of old codes to new shortened codes
CODE_MAPPING = [
    ("CCAR_DFAST_STRESS_TESTING", "CCAR_DFAST"),
    ("BASEL_REGULATORY_CAPITAL_CREDIT_RISK_RWA", "BASEL_CREDIT"),
    ("MARKET_RISK_CAPITAL_VAR_FRTB_STRESSED_VAR_RNIV", "MARKET_RISK"),
    ("COUNTERPARTY_CREDIT_RISK_CVA_CAPITAL", "CCR_CVA"),
    ("INTERNAL_ECONOMIC_CAPITAL_ICAAP", "ICAAP"),
    ("CECL_ALLOWANCE_FOR_CREDIT_LOSSES_ACL", "CECL"),
    ("IFRS_9_EXPECTED_CREDIT_LOSS", "IFRS9_ECL"),
    ("FAIR_VALUE_VALUATION_FOR_FINANCIAL_REPORTING", "FAIR_VALUE"),
    ("LIQUIDITY_RISK_LCR_NSFR", "LIQUIDITY"),
    ("INTEREST_RATE_RISK_IN_THE_BANKING_BOOK_IRRBB", "IRRBB"),
    ("ASSET_LIABILITY_MANAGEMENT_ALM_FTP", "ALM_FTP"),
    ("AML_SANCTIONS_TRANSACTION_MONITORING", "AML_SANCTIONS"),
    ("FRAUD_DETECTION", "FRAUD"),
    ("CONDUCT_RISK_FAIR_LENDING_UDAAP", "CONDUCT_RISK"),
    ("OPERATIONAL_RISK_CAPITAL_SCENARIO_MODELS", "OP_RISK"),
    ("REGULATORY_REPORTING_FFIEC_FR_Y_9C_FR_Y_14_CALL_RE", "REG_REPORTING"),
    ("INTERNAL_RISK_BOARD_REPORTING", "INT_REPORTING"),
    ("PRICING_VALUATION_INTERNAL_CUSTOMER", "PRICING"),
    ("MARGIN_COLLATERAL_MODELS_IM_VM_HAIRCUTS", "MARGIN_COLL"),
    ("MODEL_RISK_MANAGEMENT_META_MODELS", "MRM_META"),
    ("NON_REGULATORY_BUSINESS_ONLY", "NON_REG"),
]


def upgrade() -> None:
    # Update codes from long auto-generated names to shorter explicit codes
    for old_code, new_code in CODE_MAPPING:
        op.execute(
            f"UPDATE taxonomy_values SET code = '{new_code}' WHERE code = '{old_code}'"
        )


def downgrade() -> None:
    # Revert to original long codes
    for old_code, new_code in CODE_MAPPING:
        op.execute(
            f"UPDATE taxonomy_values SET code = '{old_code}' WHERE code = '{new_code}'"
        )
