"""Change scorecard FK from outcome_id to request_id

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2025-12-01

This migration changes the scorecard tables to link to validation_requests
instead of validation_outcomes. This allows validators to complete the
scorecard BEFORE determining the final outcome (proper workflow sequence).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'w3x4y5z6a7b8'
down_revision = 'v2w3x4y5z6a7'
branch_labels = None
depends_on = None


def upgrade():
    # === validation_scorecard_ratings table ===

    # 1. Drop existing constraints and indexes
    op.drop_constraint('uq_outcome_criterion', 'validation_scorecard_ratings', type_='unique')
    op.drop_index('ix_scorecard_ratings_outcome_id', table_name='validation_scorecard_ratings')
    op.drop_constraint('validation_scorecard_ratings_outcome_id_fkey', 'validation_scorecard_ratings', type_='foreignkey')

    # 2. Rename column from outcome_id to request_id
    op.alter_column('validation_scorecard_ratings', 'outcome_id', new_column_name='request_id')

    # 3. Update the FK comment
    op.alter_column('validation_scorecard_ratings', 'request_id',
                    comment='FK to validation request')

    # 4. Add new FK constraint to validation_requests
    op.create_foreign_key(
        'validation_scorecard_ratings_request_id_fkey',
        'validation_scorecard_ratings',
        'validation_requests',
        ['request_id'],
        ['request_id'],
        ondelete='CASCADE'
    )

    # 5. Create new index and unique constraint
    op.create_index('ix_scorecard_ratings_request_id', 'validation_scorecard_ratings', ['request_id'])
    op.create_unique_constraint('uq_request_criterion', 'validation_scorecard_ratings', ['request_id', 'criterion_code'])

    # === validation_scorecard_results table ===

    # 1. Drop existing constraint
    op.drop_constraint('uq_scorecard_result_outcome', 'validation_scorecard_results', type_='unique')
    op.drop_constraint('validation_scorecard_results_outcome_id_fkey', 'validation_scorecard_results', type_='foreignkey')

    # 2. Rename column from outcome_id to request_id
    op.alter_column('validation_scorecard_results', 'outcome_id', new_column_name='request_id')

    # 3. Update the FK comment
    op.alter_column('validation_scorecard_results', 'request_id',
                    comment='FK to validation request (ONE result per request)')

    # 4. Add new FK constraint to validation_requests
    op.create_foreign_key(
        'validation_scorecard_results_request_id_fkey',
        'validation_scorecard_results',
        'validation_requests',
        ['request_id'],
        ['request_id'],
        ondelete='CASCADE'
    )

    # 5. Create new unique constraint
    op.create_unique_constraint('uq_scorecard_result_request', 'validation_scorecard_results', ['request_id'])


def downgrade():
    # === validation_scorecard_results table ===

    # 1. Drop new constraints
    op.drop_constraint('uq_scorecard_result_request', 'validation_scorecard_results', type_='unique')
    op.drop_constraint('validation_scorecard_results_request_id_fkey', 'validation_scorecard_results', type_='foreignkey')

    # 2. Rename column back to outcome_id
    op.alter_column('validation_scorecard_results', 'request_id', new_column_name='outcome_id')

    # 3. Update the FK comment
    op.alter_column('validation_scorecard_results', 'outcome_id',
                    comment='FK to validation outcome (ONE result per outcome)')

    # 4. Add FK constraint back to validation_outcomes
    op.create_foreign_key(
        'validation_scorecard_results_outcome_id_fkey',
        'validation_scorecard_results',
        'validation_outcomes',
        ['outcome_id'],
        ['outcome_id'],
        ondelete='CASCADE'
    )

    # 5. Create original unique constraint
    op.create_unique_constraint('uq_scorecard_result_outcome', 'validation_scorecard_results', ['outcome_id'])

    # === validation_scorecard_ratings table ===

    # 1. Drop new constraints and indexes
    op.drop_constraint('uq_request_criterion', 'validation_scorecard_ratings', type_='unique')
    op.drop_index('ix_scorecard_ratings_request_id', table_name='validation_scorecard_ratings')
    op.drop_constraint('validation_scorecard_ratings_request_id_fkey', 'validation_scorecard_ratings', type_='foreignkey')

    # 2. Rename column back to outcome_id
    op.alter_column('validation_scorecard_ratings', 'request_id', new_column_name='outcome_id')

    # 3. Update the FK comment
    op.alter_column('validation_scorecard_ratings', 'outcome_id',
                    comment='FK to validation outcome')

    # 4. Add FK constraint back to validation_outcomes
    op.create_foreign_key(
        'validation_scorecard_ratings_outcome_id_fkey',
        'validation_scorecard_ratings',
        'validation_outcomes',
        ['outcome_id'],
        ['outcome_id'],
        ondelete='CASCADE'
    )

    # 5. Create original index and unique constraint
    op.create_index('ix_scorecard_ratings_outcome_id', 'validation_scorecard_ratings', ['outcome_id'])
    op.create_unique_constraint('uq_outcome_criterion', 'validation_scorecard_ratings', ['outcome_id', 'criterion_code'])
