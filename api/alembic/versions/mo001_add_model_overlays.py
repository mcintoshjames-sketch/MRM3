"""add_model_overlays_table

Revision ID: mo001_add_model_overlays
Revises: 7f3a1c2d4e5f
Create Date: 2026-01-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'mo001_add_model_overlays'
down_revision: Union[str, None] = '7f3a1c2d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_overlays',
        sa.Column('overlay_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False, comment='The model this overlay applies to'),
        sa.Column('overlay_kind', sa.String(30), nullable=False, comment='OVERLAY or MANAGEMENT_JUDGEMENT'),
        sa.Column('is_underperformance_related', sa.Boolean(), nullable=False, default=True,
                  comment='Explicitly mark as underperformance-related for regulatory reporting'),
        sa.Column('description', sa.Text(), nullable=False, comment='What overlay or judgement is applied'),
        sa.Column('rationale', sa.Text(), nullable=False, comment='Why this overlay/judgement is applied'),
        sa.Column('effective_from', sa.Date(), nullable=False, comment='Start date for the overlay effectiveness window'),
        sa.Column('effective_to', sa.Date(), nullable=True, comment='Optional end date for the overlay effectiveness window'),
        sa.Column('region_id', sa.Integer(), nullable=True, comment='Optional region scope (NULL = global)'),
        sa.Column('trigger_monitoring_result_id', sa.Integer(), nullable=True,
                  comment='Monitoring result that triggered the overlay (optional)'),
        sa.Column('trigger_monitoring_cycle_id', sa.Integer(), nullable=True,
                  comment='Monitoring cycle that triggered the overlay (optional)'),
        sa.Column('related_recommendation_id', sa.Integer(), nullable=True,
                  comment='Related recommendation (optional)'),
        sa.Column('related_limitation_id', sa.Integer(), nullable=True,
                  comment='Related limitation (optional)'),
        sa.Column('evidence_description', sa.Text(), nullable=True,
                  comment='Evidence description supporting the overlay (optional)'),
        sa.Column('is_retired', sa.Boolean(), nullable=False, default=False),
        sa.Column('retirement_date', sa.DateTime(), nullable=True),
        sa.Column('retirement_reason', sa.Text(), nullable=True),
        sa.Column('retired_by_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('overlay_id'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trigger_monitoring_result_id'], ['monitoring_results.result_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trigger_monitoring_cycle_id'], ['monitoring_cycles.cycle_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_recommendation_id'], ['recommendations.recommendation_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_limitation_id'], ['model_limitations.limitation_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['retired_by_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.CheckConstraint("overlay_kind IN ('OVERLAY', 'MANAGEMENT_JUDGEMENT')", name='chk_overlay_kind'),
        sa.CheckConstraint("(effective_to IS NULL OR effective_to >= effective_from)", name='chk_overlay_effective_window'),
        sa.CheckConstraint(
            "(is_retired = FALSE AND retirement_date IS NULL AND retirement_reason IS NULL AND retired_by_id IS NULL) OR "
            "(is_retired = TRUE AND retirement_date IS NOT NULL AND retirement_reason IS NOT NULL AND retired_by_id IS NOT NULL)",
            name='chk_overlay_retirement_fields_consistency'
        ),
    )

    op.create_index('idx_overlay_model', 'model_overlays', ['model_id'])
    op.create_index('idx_overlay_kind', 'model_overlays', ['overlay_kind'])
    op.create_index('idx_overlay_underperformance', 'model_overlays', ['is_underperformance_related'])
    op.create_index('idx_overlay_region', 'model_overlays', ['region_id'])
    op.create_index('idx_overlay_retired', 'model_overlays', ['is_retired'])
    op.create_index('idx_overlay_monitoring_result', 'model_overlays', ['trigger_monitoring_result_id'])
    op.create_index('idx_overlay_monitoring_cycle', 'model_overlays', ['trigger_monitoring_cycle_id'])
    op.create_index('idx_overlay_recommendation', 'model_overlays', ['related_recommendation_id'])
    op.create_index('idx_overlay_limitation', 'model_overlays', ['related_limitation_id'])


def downgrade() -> None:
    op.drop_index('idx_overlay_limitation', table_name='model_overlays')
    op.drop_index('idx_overlay_recommendation', table_name='model_overlays')
    op.drop_index('idx_overlay_monitoring_cycle', table_name='model_overlays')
    op.drop_index('idx_overlay_monitoring_result', table_name='model_overlays')
    op.drop_index('idx_overlay_retired', table_name='model_overlays')
    op.drop_index('idx_overlay_region', table_name='model_overlays')
    op.drop_index('idx_overlay_underperformance', table_name='model_overlays')
    op.drop_index('idx_overlay_kind', table_name='model_overlays')
    op.drop_index('idx_overlay_model', table_name='model_overlays')
    op.drop_table('model_overlays')
