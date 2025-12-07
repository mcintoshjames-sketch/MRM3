"""add lob hierarchy

Revision ID: lob001
Revises: 5b2648700ba6
Create Date: 2025-12-07 00:00:00.000000

"""
from typing import Sequence, Union, List, Dict, Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'lob001'
down_revision: Union[str, None] = '5b2648700ba6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# LOB hierarchy data based on EXAMPLE_LOBS.json patterns
LOB_DATA = [
    # SBU Level (level=1)
    {"code": "BCM", "name": "BankUSA Capital Markets", "level": 1, "sort_order": 1},
    {"code": "CB", "name": "Consumer Banking", "level": 1, "sort_order": 2},
    {"code": "CIB", "name": "Corporate & Investment Banking", "level": 1, "sort_order": 3},
    {"code": "WM", "name": "Wealth Management", "level": 1, "sort_order": 4},
    {"code": "RISK", "name": "Enterprise Risk", "level": 1, "sort_order": 5},

    # LOB1 Level (level=2) - under BCM
    {"code": "GM", "name": "Global Markets", "level": 2, "parent_code": "BCM", "sort_order": 1},
    {"code": "FICC", "name": "Fixed Income", "level": 2, "parent_code": "BCM", "sort_order": 2},

    # LOB1 Level (level=2) - under CB
    {"code": "RL", "name": "Retail Lending", "level": 2, "parent_code": "CB", "sort_order": 1},
    {"code": "CARDS", "name": "Cards & Payments", "level": 2, "parent_code": "CB", "sort_order": 2},
    {"code": "DEPOSITS", "name": "Deposits & Savings", "level": 2, "parent_code": "CB", "sort_order": 3},

    # LOB1 Level (level=2) - under CIB
    {"code": "LENDING", "name": "Commercial Lending", "level": 2, "parent_code": "CIB", "sort_order": 1},
    {"code": "TREASURY", "name": "Treasury Services", "level": 2, "parent_code": "CIB", "sort_order": 2},

    # LOB1 Level (level=2) - under WM
    {"code": "PB", "name": "Private Banking", "level": 2, "parent_code": "WM", "sort_order": 1},
    {"code": "AM", "name": "Asset Management", "level": 2, "parent_code": "WM", "sort_order": 2},

    # LOB1 Level (level=2) - under RISK
    {"code": "MR", "name": "Market Risk", "level": 2, "parent_code": "RISK", "sort_order": 1},
    {"code": "CR", "name": "Credit Risk", "level": 2, "parent_code": "RISK", "sort_order": 2},
    {"code": "OR", "name": "Operational Risk", "level": 2, "parent_code": "RISK", "sort_order": 3},

    # LOB2 Level (level=3) - under GM
    {"code": "EQ", "name": "Equities", "level": 3, "parent_code": "GM", "sort_order": 1},
    {"code": "FX", "name": "Foreign Exchange", "level": 3, "parent_code": "GM", "sort_order": 2},
    {"code": "COMM", "name": "Commodities", "level": 3, "parent_code": "GM", "sort_order": 3},

    # LOB2 Level (level=3) - under FICC
    {"code": "RATES", "name": "Rates Trading", "level": 3, "parent_code": "FICC", "sort_order": 1},
    {"code": "CREDIT_TR", "name": "Credit Trading", "level": 3, "parent_code": "FICC", "sort_order": 2},

    # LOB2 Level (level=3) - under RL
    {"code": "MTG", "name": "Mortgage", "level": 3, "parent_code": "RL", "sort_order": 1},
    {"code": "AUTO", "name": "Auto Finance", "level": 3, "parent_code": "RL", "sort_order": 2},
    {"code": "STUDENT", "name": "Student Loans", "level": 3, "parent_code": "RL", "sort_order": 3},

    # LOB2 Level (level=3) - under CARDS
    {"code": "CONS_CARDS", "name": "Consumer Cards", "level": 3, "parent_code": "CARDS", "sort_order": 1},
    {"code": "COMM_CARDS", "name": "Commercial Cards", "level": 3, "parent_code": "CARDS", "sort_order": 2},

    # LOB2 Level (level=3) - under LENDING
    {"code": "CRE", "name": "Commercial Real Estate", "level": 3, "parent_code": "LENDING", "sort_order": 1},
    {"code": "C_AND_I", "name": "C&I Lending", "level": 3, "parent_code": "LENDING", "sort_order": 2},

    # LOB3 Level (level=4) - under EQ
    {"code": "DERIV", "name": "Derivatives", "level": 4, "parent_code": "EQ", "sort_order": 1},
    {"code": "CASH_EQ", "name": "Cash Equities", "level": 4, "parent_code": "EQ", "sort_order": 2},

    # LOB3 Level (level=4) - under MTG
    {"code": "MTG_ORIG", "name": "Origination", "level": 4, "parent_code": "MTG", "sort_order": 1},
    {"code": "MTG_SERV", "name": "Servicing", "level": 4, "parent_code": "MTG", "sort_order": 2},

    # LOB4 Level (level=5) - under DERIV
    {"code": "EXOTIC", "name": "Exotic Products", "level": 5, "parent_code": "DERIV", "sort_order": 1},
    {"code": "VANILLA", "name": "Vanilla Options", "level": 5, "parent_code": "DERIV", "sort_order": 2},

    # LOB5 Level (level=6) - under EXOTIC
    {"code": "VOLATARB", "name": "Volatility Arbitrage", "level": 6, "parent_code": "EXOTIC", "sort_order": 1},
    {"code": "CORRELATION", "name": "Correlation Trading", "level": 6, "parent_code": "EXOTIC", "sort_order": 2},

    # LOB4 Level (level=5) - under MTG_ORIG
    {"code": "DIRECT_CH", "name": "Direct Channels", "level": 5, "parent_code": "MTG_ORIG", "sort_order": 1},
    {"code": "BROKER_CH", "name": "Broker Channels", "level": 5, "parent_code": "MTG_ORIG", "sort_order": 2},

    # LOB5 Level (level=6) - under DIRECT_CH
    {"code": "DIGITAL_OPS", "name": "Digital Operations", "level": 6, "parent_code": "DIRECT_CH", "sort_order": 1},
    {"code": "CALL_CENTER", "name": "Call Center", "level": 6, "parent_code": "DIRECT_CH", "sort_order": 2},
]


def upgrade() -> None:
    # 1. Create lob_units table
    op.create_table(
        'lob_units',
        sa.Column('lob_id', sa.Integer(), primary_key=True),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('lob_units.lob_id', ondelete='RESTRICT'), nullable=True),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, comment='Hierarchy depth: 1=SBU, 2=LOB1, 3=LOB2, etc.'),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_lob_units_parent_id', 'lob_units', ['parent_id'])
    op.create_index('ix_lob_units_is_active', 'lob_units', ['is_active'])

    # Create unique constraint on (parent_id, code)
    op.create_unique_constraint('uq_lob_parent_code', 'lob_units', ['parent_id', 'code'])

    # 2. Seed LOB hierarchy data
    conn = op.get_bind()

    # First pass: Insert all nodes without parent references (level 1 first)
    # Build a mapping of code -> lob_id for setting parent_id later
    code_to_id: Dict[str, int] = {}

    # Insert level by level to ensure parents exist before children
    for level in range(1, 7):  # levels 1-6
        level_data = [d for d in LOB_DATA if d['level'] == level]
        for item in level_data:
            parent_id = None
            if 'parent_code' in item:
                parent_id = code_to_id.get(item['parent_code'])

            result = conn.execute(
                text("""
                    INSERT INTO lob_units (code, name, level, sort_order, is_active, parent_id, created_at, updated_at)
                    VALUES (:code, :name, :level, :sort_order, true, :parent_id, NOW(), NOW())
                    RETURNING lob_id
                """),
                {
                    'code': item['code'],
                    'name': item['name'],
                    'level': item['level'],
                    'sort_order': item['sort_order'],
                    'parent_id': parent_id
                }
            )
            lob_id = result.scalar()
            code_to_id[item['code']] = lob_id

    # 3. Add lob_id column to users table (nullable initially)
    op.add_column('users', sa.Column('lob_id', sa.Integer(), sa.ForeignKey('lob_units.lob_id', ondelete='RESTRICT'), nullable=True))
    op.create_index('ix_users_lob_id', 'users', ['lob_id'])

    # 4. Distribute existing users to leaf-level LOB nodes (nodes with no children)
    # Get all leaf nodes (nodes that are not parents of any other node)
    leaf_nodes_result = conn.execute(
        text("""
            SELECT lob_id FROM lob_units
            WHERE lob_id NOT IN (SELECT DISTINCT parent_id FROM lob_units WHERE parent_id IS NOT NULL)
            ORDER BY lob_id
        """)
    )
    leaf_node_ids = [row[0] for row in leaf_nodes_result.fetchall()]

    if leaf_node_ids:
        # Get all user IDs
        users_result = conn.execute(text("SELECT user_id FROM users ORDER BY user_id"))
        user_ids = [row[0] for row in users_result.fetchall()]

        # Assign users round-robin to leaf nodes
        for i, user_id in enumerate(user_ids):
            lob_id = leaf_node_ids[i % len(leaf_node_ids)]
            conn.execute(
                text("UPDATE users SET lob_id = :lob_id WHERE user_id = :user_id"),
                {'lob_id': lob_id, 'user_id': user_id}
            )


def downgrade() -> None:
    # Remove lob_id from users first (due to FK constraint)
    op.drop_index('ix_users_lob_id', table_name='users')
    op.drop_column('users', 'lob_id')

    # Drop lob_units table
    op.drop_constraint('uq_lob_parent_code', 'lob_units', type_='unique')
    op.drop_index('ix_lob_units_is_active', table_name='lob_units')
    op.drop_index('ix_lob_units_parent_id', table_name='lob_units')
    op.drop_table('lob_units')
