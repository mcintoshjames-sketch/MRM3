"""Add timeframe enforcement fields and table.

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2025-11-30

This migration adds:
1. recommendation_timeframe_configs table for storing max_days per priority/risk/frequency
2. enforce_timeframes column to recommendation_priority_configs (default True)
3. enforce_timeframes column to recommendation_priority_regional_overrides (nullable)
4. target_date_change_reason column to recommendations (nullable text)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 't0u1v2w3x4y5'
down_revision = 's9t0u1v2w3x4'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create recommendation_timeframe_configs table
    op.create_table(
        'recommendation_timeframe_configs',
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('priority_id', sa.Integer(), nullable=False,
                  comment='FK to priority taxonomy value (High/Medium/Low)'),
        sa.Column('risk_tier_id', sa.Integer(), nullable=False,
                  comment='FK to model risk tier taxonomy value (Tier 1/2/3/4)'),
        sa.Column('usage_frequency_id', sa.Integer(), nullable=False,
                  comment='FK to model usage frequency taxonomy value (Daily/Monthly/Quarterly/Annually)'),
        sa.Column('max_days', sa.Integer(), nullable=False,
                  comment='Maximum days allowed from creation to target date (0 = immediate)'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Admin notes explaining this timeframe configuration'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['priority_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['risk_tier_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['usage_frequency_id'], ['taxonomy_values.value_id'], ),
        sa.PrimaryKeyConstraint('config_id'),
        sa.UniqueConstraint('priority_id', 'risk_tier_id', 'usage_frequency_id',
                           name='uq_timeframe_priority_risk_freq')
    )

    # 2. Add enforce_timeframes to recommendation_priority_configs (default True)
    op.add_column(
        'recommendation_priority_configs',
        sa.Column('enforce_timeframes', sa.Boolean(), nullable=False, server_default='true',
                  comment='If true, target dates must be within max allowed timeframe; if false, timeframe is advisory only')
    )

    # 3. Add enforce_timeframes to recommendation_priority_regional_overrides (nullable)
    op.add_column(
        'recommendation_priority_regional_overrides',
        sa.Column('enforce_timeframes', sa.Boolean(), nullable=True,
                  comment='Override for timeframe enforcement. NULL = inherit from base config')
    )

    # 4. Add target_date_change_reason to recommendations (nullable text)
    op.add_column(
        'recommendations',
        sa.Column('target_date_change_reason', sa.Text(), nullable=True,
                  comment='Explanation for why target date differs from calculated max or has been changed')
    )


def downgrade():
    # 4. Remove target_date_change_reason from recommendations
    op.drop_column('recommendations', 'target_date_change_reason')

    # 3. Remove enforce_timeframes from recommendation_priority_regional_overrides
    op.drop_column('recommendation_priority_regional_overrides', 'enforce_timeframes')

    # 2. Remove enforce_timeframes from recommendation_priority_configs
    op.drop_column('recommendation_priority_configs', 'enforce_timeframes')

    # 1. Drop recommendation_timeframe_configs table
    op.drop_table('recommendation_timeframe_configs')
