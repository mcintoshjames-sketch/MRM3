"""add_conditional_model_use_approvals

Revision ID: edab17d6ee8f
Revises: 7466212450b8
Create Date: 2025-11-24 05:34:47.315960

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edab17d6ee8f'
down_revision: Union[str, None] = '7466212450b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create approver_roles table
    op.create_table(
        'approver_roles',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('role_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('role_name')
    )
    op.create_index('ix_approver_roles_is_active', 'approver_roles', ['is_active'])

    # Create conditional_approval_rules table
    op.create_table(
        'conditional_approval_rules',
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        # Condition fields - store as comma-separated IDs (empty/null = ANY)
        sa.Column('validation_type_ids', sa.Text(), nullable=True,
                  comment='Comma-separated validation type IDs (empty = any validation type)'),
        sa.Column('risk_tier_ids', sa.Text(), nullable=True,
                  comment='Comma-separated risk tier IDs (empty = any risk tier)'),
        sa.Column('governance_region_ids', sa.Text(), nullable=True,
                  comment='Comma-separated governance region IDs (empty = any governance region)'),
        sa.Column('deployed_region_ids', sa.Text(), nullable=True,
                  comment='Comma-separated deployed region IDs (empty = any deployed region)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('rule_id')
    )
    op.create_index('ix_conditional_rules_is_active', 'conditional_approval_rules', ['is_active'])

    # Create rule_required_approvers join table
    op.create_table(
        'rule_required_approvers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('approver_role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['conditional_approval_rules.rule_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_role_id'], ['approver_roles.role_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rule_required_approvers_rule', 'rule_required_approvers', ['rule_id'])
    op.create_index('ix_rule_required_approvers_role', 'rule_required_approvers', ['approver_role_id'])

    # Add approver_role_id FK to validation_approvals (for conditional approvals)
    op.add_column('validation_approvals',
                  sa.Column('approver_role_id', sa.Integer(), nullable=True,
                            comment='FK to approver_roles (for conditional approvals); NULL for traditional approvals'))
    op.create_foreign_key('fk_validation_approvals_approver_role', 'validation_approvals',
                          'approver_roles', ['approver_role_id'], ['role_id'], ondelete='SET NULL')
    op.create_index('ix_validation_approvals_approver_role', 'validation_approvals', ['approver_role_id'])

    # Add approval evidence field to validation_approvals
    op.add_column('validation_approvals',
                  sa.Column('approval_evidence', sa.Text(), nullable=True,
                            comment='Description of approval evidence (meeting minutes, email, etc.)'))

    # Add voiding fields to validation_approvals (Admin can void requirements)
    op.add_column('validation_approvals',
                  sa.Column('voided_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_validation_approvals_voided_by', 'validation_approvals',
                          'users', ['voided_by_id'], ['user_id'], ondelete='SET NULL')
    op.add_column('validation_approvals',
                  sa.Column('void_reason', sa.Text(), nullable=True,
                            comment='Reason why this approval requirement was voided by Admin'))
    op.add_column('validation_approvals',
                  sa.Column('voided_at', sa.DateTime(), nullable=True))

    # Add use_approval_date to models table
    op.add_column('models',
                  sa.Column('use_approval_date', sa.DateTime(), nullable=True,
                            comment='Timestamp when model was approved for use (last required approval granted)'))


def downgrade() -> None:
    # Remove use_approval_date from models
    op.drop_column('models', 'use_approval_date')

    # Remove voiding fields from validation_approvals
    op.drop_column('validation_approvals', 'voided_at')
    op.drop_column('validation_approvals', 'void_reason')
    op.drop_constraint('fk_validation_approvals_voided_by', 'validation_approvals', type_='foreignkey')
    op.drop_column('validation_approvals', 'voided_by_id')

    # Remove approval_evidence from validation_approvals
    op.drop_column('validation_approvals', 'approval_evidence')

    # Remove approver_role_id from validation_approvals
    op.drop_index('ix_validation_approvals_approver_role', 'validation_approvals')
    op.drop_constraint('fk_validation_approvals_approver_role', 'validation_approvals', type_='foreignkey')
    op.drop_column('validation_approvals', 'approver_role_id')

    # Drop rule_required_approvers join table
    op.drop_index('ix_rule_required_approvers_role', 'rule_required_approvers')
    op.drop_index('ix_rule_required_approvers_rule', 'rule_required_approvers')
    op.drop_table('rule_required_approvers')

    # Drop conditional_approval_rules table
    op.drop_index('ix_conditional_rules_is_active', 'conditional_approval_rules')
    op.drop_table('conditional_approval_rules')

    # Drop approver_roles table
    op.drop_index('ix_approver_roles_is_active', 'approver_roles')
    op.drop_table('approver_roles')
