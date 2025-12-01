"""Add validation scorecard tables

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2025-12-01

This migration adds:
1. scorecard_sections - User-configurable sections for validation scorecard
2. scorecard_criteria - User-configurable criteria within sections
3. validation_scorecard_ratings - Per-criterion ratings entered by validators
4. validation_scorecard_results - Computed scorecard results with config snapshot
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'v2w3x4y5z6a7'
down_revision = 'u1v2w3x4y5z6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create scorecard_sections table
    op.create_table(
        'scorecard_sections',
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(20), nullable=False,
                  comment='Section code (e.g., "1", "2", "3")'),
        sa.Column('name', sa.String(255), nullable=False,
                  comment='Display name (e.g., "Evaluation of Conceptual Soundness")'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Optional description of this section'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0',
                  comment='Display order in UI'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true',
                  comment='Inactive sections are hidden from new scorecards'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('section_id'),
        sa.UniqueConstraint('code', name='uq_scorecard_section_code')
    )

    # 2. Create scorecard_criteria table
    op.create_table(
        'scorecard_criteria',
        sa.Column('criterion_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(20), nullable=False,
                  comment='Criterion code (e.g., "1.1", "2.3", "3.5")'),
        sa.Column('section_id', sa.Integer(), nullable=False,
                  comment='FK to parent section'),
        sa.Column('name', sa.String(255), nullable=False,
                  comment='Display name (e.g., "Model Development Documentation")'),
        sa.Column('description_prompt', sa.Text(), nullable=True,
                  comment='Prompt guiding validator description entry'),
        sa.Column('comments_prompt', sa.Text(), nullable=True,
                  comment='Prompt guiding validator comments entry'),
        sa.Column('include_in_summary', sa.Boolean(), nullable=False, server_default='true',
                  comment='Whether to include in section summary calculation'),
        sa.Column('allow_zero', sa.Boolean(), nullable=False, server_default='true',
                  comment='Whether N/A rating is allowed for this criterion'),
        sa.Column('weight', sa.Numeric(5, 2), nullable=False, server_default='1.0',
                  comment='Weight for weighted average calculation'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0',
                  comment='Display order within section'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true',
                  comment='Inactive criteria are hidden from new scorecards'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['section_id'], ['scorecard_sections.section_id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('criterion_id'),
        sa.UniqueConstraint('code', name='uq_scorecard_criterion_code')
    )
    op.create_index('ix_scorecard_criteria_section_id', 'scorecard_criteria', ['section_id'])

    # 3. Create validation_scorecard_ratings table
    op.create_table(
        'validation_scorecard_ratings',
        sa.Column('rating_id', sa.Integer(), nullable=False),
        sa.Column('outcome_id', sa.Integer(), nullable=False,
                  comment='FK to validation outcome'),
        sa.Column('criterion_code', sa.String(20), nullable=False,
                  comment='Criterion code - keyed by code for resilience'),
        sa.Column('rating', sa.String(20), nullable=True,
                  comment='Rating: Green, Green-, Yellow+, Yellow, Yellow-, Red, N/A, or NULL'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Validator description response'),
        sa.Column('comments', sa.Text(), nullable=True,
                  comment='Validator comments'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['outcome_id'], ['validation_outcomes.outcome_id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('rating_id'),
        sa.UniqueConstraint('outcome_id', 'criterion_code', name='uq_outcome_criterion'),
        sa.CheckConstraint(
            "rating IS NULL OR rating IN ('Green', 'Green-', 'Yellow+', 'Yellow', 'Yellow-', 'Red', 'N/A')",
            name='chk_valid_rating'
        )
    )
    op.create_index('ix_scorecard_ratings_outcome_id', 'validation_scorecard_ratings', ['outcome_id'])

    # 4. Create validation_scorecard_results table
    op.create_table(
        'validation_scorecard_results',
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('outcome_id', sa.Integer(), nullable=False,
                  comment='FK to validation outcome (ONE result per outcome)'),
        sa.Column('overall_numeric_score', sa.Integer(), nullable=True,
                  comment='Overall numeric score (0-6)'),
        sa.Column('overall_rating', sa.String(20), nullable=True,
                  comment='Overall rating string (Green, Green-, etc.)'),
        sa.Column('section_summaries', sa.JSON(), nullable=True,
                  comment='JSON object with per-section summaries'),
        sa.Column('config_snapshot', sa.JSON(), nullable=True,
                  comment='Snapshot of scorecard configuration at computation time'),
        sa.Column('computed_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  comment='When the scorecard was computed'),
        sa.ForeignKeyConstraint(['outcome_id'], ['validation_outcomes.outcome_id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('result_id'),
        sa.UniqueConstraint('outcome_id', name='uq_scorecard_result_outcome')
    )


def downgrade():
    # Drop tables in reverse order (due to foreign key dependencies)
    op.drop_table('validation_scorecard_results')

    op.drop_index('ix_scorecard_ratings_outcome_id', table_name='validation_scorecard_ratings')
    op.drop_table('validation_scorecard_ratings')

    op.drop_index('ix_scorecard_criteria_section_id', table_name='scorecard_criteria')
    op.drop_table('scorecard_criteria')

    op.drop_table('scorecard_sections')
