"""Add attestation tables

Revision ID: ab2c3d4e5f6g
Revises: b9c0d1e2f3a4
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab2c3d4e5f6g'
down_revision: Union[str, None] = 'b9c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================================================
    # Add new columns to existing tables
    # ========================================================================

    # Add can_attest to model_delegates
    op.add_column(
        'model_delegates',
        sa.Column('can_attest', sa.Boolean(), nullable=False, server_default='false',
                  comment='Can submit attestations on behalf of model owner')
    )

    # Add high_fluctuation_flag to users
    op.add_column(
        'users',
        sa.Column('high_fluctuation_flag', sa.Boolean(), nullable=False, server_default='false',
                  comment='Manual toggle by Admin; triggers quarterly attestations')
    )

    # ========================================================================
    # Create attestation_cycles table
    # ========================================================================
    op.create_table(
        'attestation_cycles',
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('cycle_name', sa.String(length=100), nullable=False),
        sa.Column('period_start_date', sa.Date(), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),
        sa.Column('submission_due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('opened_by_user_id', sa.Integer(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('closed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['opened_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('cycle_id')
    )
    op.create_index('ix_attestation_cycles_status', 'attestation_cycles', ['status'])

    # ========================================================================
    # Create attestation_records table
    # ========================================================================
    op.create_table(
        'attestation_records',
        sa.Column('attestation_id', sa.Integer(), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('attesting_user_id', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('attested_at', sa.DateTime(), nullable=True),
        sa.Column('decision', sa.String(length=30), nullable=True),
        sa.Column('decision_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cycle_id'], ['attestation_cycles.cycle_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attesting_user_id'], ['users.user_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('attestation_id'),
        sa.UniqueConstraint('cycle_id', 'model_id', name='uq_attestation_cycle_model')
    )
    op.create_index('ix_attestation_records_cycle_id', 'attestation_records', ['cycle_id'])
    op.create_index('ix_attestation_records_model_id', 'attestation_records', ['model_id'])
    op.create_index('ix_attestation_records_attesting_user_id', 'attestation_records', ['attesting_user_id'])
    op.create_index('ix_attestation_records_status', 'attestation_records', ['status'])
    op.create_index('ix_attestation_records_due_date', 'attestation_records', ['due_date'])

    # ========================================================================
    # Create attestation_question_configs table (extends taxonomy_values)
    # ========================================================================
    op.create_table(
        'attestation_question_configs',
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('question_value_id', sa.Integer(), nullable=False),
        sa.Column('frequency_scope', sa.String(length=20), nullable=False, server_default='BOTH'),
        sa.Column('requires_comment_if_no', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['question_value_id'], ['taxonomy_values.value_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('config_id'),
        sa.UniqueConstraint('question_value_id', name='uq_question_config_value')
    )

    # ========================================================================
    # Create attestation_responses table
    # ========================================================================
    op.create_table(
        'attestation_responses',
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('attestation_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer', sa.Boolean(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['attestation_id'], ['attestation_records.attestation_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['taxonomy_values.value_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('response_id'),
        sa.UniqueConstraint('attestation_id', 'question_id', name='uq_response_attestation_question')
    )
    op.create_index('ix_attestation_responses_attestation_id', 'attestation_responses', ['attestation_id'])

    # ========================================================================
    # Create attestation_evidence table
    # ========================================================================
    op.create_table(
        'attestation_evidence',
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('attestation_id', sa.Integer(), nullable=False),
        sa.Column('evidence_type', sa.String(length=30), nullable=False, server_default='OTHER'),
        sa.Column('url', sa.String(length=2000), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('added_by_user_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['attestation_id'], ['attestation_records.attestation_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by_user_id'], ['users.user_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('evidence_id')
    )
    op.create_index('ix_attestation_evidence_attestation_id', 'attestation_evidence', ['attestation_id'])

    # ========================================================================
    # Create attestation_scheduling_rules table
    # ========================================================================
    op.create_table(
        'attestation_scheduling_rules',
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.String(length=30), nullable=False, server_default='GLOBAL_DEFAULT'),
        sa.Column('frequency', sa.String(length=20), nullable=False, server_default='ANNUAL'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_model_count_min', sa.Integer(), nullable=True,
                  comment='Minimum model count for owner to trigger this rule'),
        sa.Column('owner_high_fluctuation_flag', sa.Boolean(), nullable=True,
                  comment='If true, applies to owners with high_fluctuation_flag set'),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('rule_id')
    )
    op.create_index('ix_attestation_scheduling_rules_is_active', 'attestation_scheduling_rules', ['is_active'])
    op.create_index('ix_attestation_scheduling_rules_priority', 'attestation_scheduling_rules', ['priority'])

    # ========================================================================
    # Create attestation_change_proposals table
    # ========================================================================
    op.create_table(
        'attestation_change_proposals',
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('attestation_id', sa.Integer(), nullable=False),
        sa.Column('pending_edit_id', sa.Integer(), nullable=True),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('proposed_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('admin_comment', sa.Text(), nullable=True),
        sa.Column('decided_by_user_id', sa.Integer(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['attestation_id'], ['attestation_records.attestation_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pending_edit_id'], ['model_pending_edits.pending_edit_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('proposal_id')
    )
    op.create_index('ix_attestation_change_proposals_attestation_id', 'attestation_change_proposals', ['attestation_id'])
    op.create_index('ix_attestation_change_proposals_status', 'attestation_change_proposals', ['status'])

    # ========================================================================
    # Create attestation_coverage_targets table
    # ========================================================================
    op.create_table(
        'attestation_coverage_targets',
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('risk_tier_id', sa.Integer(), nullable=False),
        sa.Column('target_percentage', sa.DECIMAL(5, 2), nullable=False),
        sa.Column('is_blocking', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['risk_tier_id'], ['taxonomy_values.value_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('target_id')
    )
    op.create_index('ix_attestation_coverage_targets_risk_tier_id', 'attestation_coverage_targets', ['risk_tier_id'])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index('ix_attestation_coverage_targets_risk_tier_id', table_name='attestation_coverage_targets')
    op.drop_table('attestation_coverage_targets')

    op.drop_index('ix_attestation_change_proposals_status', table_name='attestation_change_proposals')
    op.drop_index('ix_attestation_change_proposals_attestation_id', table_name='attestation_change_proposals')
    op.drop_table('attestation_change_proposals')

    op.drop_index('ix_attestation_scheduling_rules_priority', table_name='attestation_scheduling_rules')
    op.drop_index('ix_attestation_scheduling_rules_is_active', table_name='attestation_scheduling_rules')
    op.drop_table('attestation_scheduling_rules')

    op.drop_index('ix_attestation_evidence_attestation_id', table_name='attestation_evidence')
    op.drop_table('attestation_evidence')

    op.drop_index('ix_attestation_responses_attestation_id', table_name='attestation_responses')
    op.drop_table('attestation_responses')

    op.drop_table('attestation_question_configs')

    op.drop_index('ix_attestation_records_due_date', table_name='attestation_records')
    op.drop_index('ix_attestation_records_status', table_name='attestation_records')
    op.drop_index('ix_attestation_records_attesting_user_id', table_name='attestation_records')
    op.drop_index('ix_attestation_records_model_id', table_name='attestation_records')
    op.drop_index('ix_attestation_records_cycle_id', table_name='attestation_records')
    op.drop_table('attestation_records')

    op.drop_index('ix_attestation_cycles_status', table_name='attestation_cycles')
    op.drop_table('attestation_cycles')

    # Remove columns from existing tables
    op.drop_column('users', 'high_fluctuation_flag')
    op.drop_column('model_delegates', 'can_attest')
