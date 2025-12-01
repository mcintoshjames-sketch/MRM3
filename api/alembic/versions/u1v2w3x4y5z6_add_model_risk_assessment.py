"""Add model risk assessment tables

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2025-11-30

This migration adds:
1. qualitative_risk_factors - Admin-customizable risk assessment factors
2. qualitative_factor_guidance - Rating guidance per factor (HIGH/MEDIUM/LOW)
3. model_risk_assessments - Main assessment table for models (global and regional)
4. qualitative_factor_assessments - Individual factor ratings per assessment
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'u1v2w3x4y5z6'
down_revision = 't0u1v2w3x4y5'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create qualitative_risk_factors table (Admin-customizable taxonomy)
    op.create_table(
        'qualitative_risk_factors',
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False,
                  comment='Unique code identifier (e.g., REPUTATION_LEGAL)'),
        sa.Column('name', sa.String(200), nullable=False,
                  comment='Display name for the factor'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Full description of what this factor measures'),
        sa.Column('weight', sa.Numeric(5, 4), nullable=False,
                  comment='Weight for weighted average calculation (e.g., 0.3000 for 30%)'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0',
                  comment='Display order in the assessment form'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true',
                  comment='Active factors appear in new assessments'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('factor_id'),
        sa.UniqueConstraint('code', name='uq_risk_factor_code')
    )

    # 2. Create qualitative_factor_guidance table (Rating guidance per factor)
    op.create_table(
        'qualitative_factor_guidance',
        sa.Column('guidance_id', sa.Integer(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False,
                  comment='FK to qualitative_risk_factors'),
        sa.Column('rating', sa.String(10), nullable=False,
                  comment='Rating level: HIGH, MEDIUM, or LOW'),
        sa.Column('points', sa.Integer(), nullable=False,
                  comment='Points for this rating: 3 (HIGH), 2 (MEDIUM), 1 (LOW)'),
        sa.Column('description', sa.Text(), nullable=False,
                  comment='Guidance text explaining when this rating applies'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0',
                  comment='Display order within the factor'),
        sa.ForeignKeyConstraint(['factor_id'], ['qualitative_risk_factors.factor_id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('guidance_id'),
        sa.UniqueConstraint('factor_id', 'rating', name='uq_factor_rating'),
        sa.CheckConstraint("rating IN ('HIGH', 'MEDIUM', 'LOW')", name='chk_guidance_rating')
    )
    op.create_index('ix_factor_guidance_factor_id', 'qualitative_factor_guidance', ['factor_id'])

    # 3. Create model_risk_assessments table (Main assessment table)
    op.create_table(
        'model_risk_assessments',
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False,
                  comment='FK to models table'),
        sa.Column('region_id', sa.Integer(), nullable=True,
                  comment='FK to regions table. NULL = Global assessment'),

        # Quantitative Assessment
        sa.Column('quantitative_rating', sa.String(10), nullable=True,
                  comment='Direct quantitative rating: HIGH, MEDIUM, LOW'),
        sa.Column('quantitative_comment', sa.Text(), nullable=True,
                  comment='Justification for quantitative rating'),
        sa.Column('quantitative_override', sa.String(10), nullable=True,
                  comment='Override for quantitative: HIGH, MEDIUM, LOW'),
        sa.Column('quantitative_override_comment', sa.Text(), nullable=True,
                  comment='Justification for quantitative override'),

        # Qualitative Assessment (calculated from factors)
        sa.Column('qualitative_calculated_score', sa.Numeric(5, 2), nullable=True,
                  comment='Weighted score from factor assessments (e.g., 2.30)'),
        sa.Column('qualitative_calculated_level', sa.String(10), nullable=True,
                  comment='Level derived from score: HIGH (>=2.1), MEDIUM (>=1.6), LOW (<1.6)'),
        sa.Column('qualitative_override', sa.String(10), nullable=True,
                  comment='Override for qualitative: HIGH, MEDIUM, LOW'),
        sa.Column('qualitative_override_comment', sa.Text(), nullable=True,
                  comment='Justification for qualitative override'),

        # Derived Inherent Risk (from matrix lookup)
        sa.Column('derived_risk_tier', sa.String(10), nullable=True,
                  comment='Matrix lookup result: HIGH, MEDIUM, LOW, VERY_LOW'),
        sa.Column('derived_risk_tier_override', sa.String(10), nullable=True,
                  comment='Override for final tier: HIGH, MEDIUM, LOW, VERY_LOW'),
        sa.Column('derived_risk_tier_override_comment', sa.Text(), nullable=True,
                  comment='Justification for final tier override'),

        # Final tier (mapped to taxonomy)
        sa.Column('final_tier_id', sa.Integer(), nullable=True,
                  comment='FK to taxonomy_values for Model Risk Tier (TIER_1, TIER_2, TIER_3, TIER_4)'),

        # Metadata
        sa.Column('assessed_by_id', sa.Integer(), nullable=True,
                  comment='FK to users who performed the assessment'),
        sa.Column('assessed_at', sa.DateTime(), nullable=True,
                  comment='Timestamp when assessment was finalized'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['final_tier_id'], ['taxonomy_values.value_id']),
        sa.ForeignKeyConstraint(['assessed_by_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('assessment_id'),
        sa.UniqueConstraint('model_id', 'region_id', name='uq_model_region_assessment'),

        # Check constraints for rating values
        sa.CheckConstraint("quantitative_rating IN ('HIGH', 'MEDIUM', 'LOW') OR quantitative_rating IS NULL",
                          name='chk_quantitative_rating'),
        sa.CheckConstraint("quantitative_override IN ('HIGH', 'MEDIUM', 'LOW') OR quantitative_override IS NULL",
                          name='chk_quantitative_override'),
        sa.CheckConstraint("qualitative_calculated_level IN ('HIGH', 'MEDIUM', 'LOW') OR qualitative_calculated_level IS NULL",
                          name='chk_qualitative_level'),
        sa.CheckConstraint("qualitative_override IN ('HIGH', 'MEDIUM', 'LOW') OR qualitative_override IS NULL",
                          name='chk_qualitative_override'),
        sa.CheckConstraint("derived_risk_tier IN ('HIGH', 'MEDIUM', 'LOW', 'VERY_LOW') OR derived_risk_tier IS NULL",
                          name='chk_derived_tier'),
        sa.CheckConstraint("derived_risk_tier_override IN ('HIGH', 'MEDIUM', 'LOW', 'VERY_LOW') OR derived_risk_tier_override IS NULL",
                          name='chk_derived_tier_override'),
    )
    op.create_index('ix_risk_assessments_model_id', 'model_risk_assessments', ['model_id'])
    op.create_index('ix_risk_assessments_region_id', 'model_risk_assessments', ['region_id'])

    # 4. Create qualitative_factor_assessments table (Factor ratings per assessment)
    op.create_table(
        'qualitative_factor_assessments',
        sa.Column('factor_assessment_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False,
                  comment='FK to model_risk_assessments'),
        sa.Column('factor_id', sa.Integer(), nullable=False,
                  comment='FK to qualitative_risk_factors'),
        sa.Column('rating', sa.String(10), nullable=True,
                  comment='Rating for this factor: HIGH, MEDIUM, LOW (nullable for partial saves)'),
        sa.Column('comment', sa.Text(), nullable=True,
                  comment='Optional justification for this factor rating'),
        sa.Column('weight_at_assessment', sa.Numeric(5, 4), nullable=False,
                  comment='Snapshot of factor weight at time of assessment'),
        sa.Column('score', sa.Numeric(5, 2), nullable=True,
                  comment='Calculated score: weight * points (e.g., 0.30 * 3 = 0.90)'),

        sa.ForeignKeyConstraint(['assessment_id'], ['model_risk_assessments.assessment_id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['factor_id'], ['qualitative_risk_factors.factor_id']),
        sa.PrimaryKeyConstraint('factor_assessment_id'),
        sa.UniqueConstraint('assessment_id', 'factor_id', name='uq_assessment_factor'),
        sa.CheckConstraint("rating IN ('HIGH', 'MEDIUM', 'LOW') OR rating IS NULL",
                          name='chk_factor_rating'),
    )
    op.create_index('ix_factor_assessments_assessment_id', 'qualitative_factor_assessments', ['assessment_id'])
    op.create_index('ix_factor_assessments_factor_id', 'qualitative_factor_assessments', ['factor_id'])


def downgrade():
    # Drop tables in reverse order (due to foreign key dependencies)
    op.drop_index('ix_factor_assessments_factor_id', table_name='qualitative_factor_assessments')
    op.drop_index('ix_factor_assessments_assessment_id', table_name='qualitative_factor_assessments')
    op.drop_table('qualitative_factor_assessments')

    op.drop_index('ix_risk_assessments_region_id', table_name='model_risk_assessments')
    op.drop_index('ix_risk_assessments_model_id', table_name='model_risk_assessments')
    op.drop_table('model_risk_assessments')

    op.drop_index('ix_factor_guidance_factor_id', table_name='qualitative_factor_guidance')
    op.drop_table('qualitative_factor_guidance')

    op.drop_table('qualitative_risk_factors')
