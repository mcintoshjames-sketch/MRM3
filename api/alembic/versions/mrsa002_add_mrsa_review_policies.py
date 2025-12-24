"""add_mrsa_review_policies

Revision ID: mrsa002_review_policies
Revises: chg001
Create Date: 2025-12-24 10:00:00.000000

This migration adds MRSA review policy configuration and exceptions tracking:
- Creates mrsa_review_policies table for risk-based review scheduling policies
- Creates mrsa_review_exceptions table for managing due date overrides
- Adds indexes for common query patterns
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'mrsa002_review_policies'
down_revision: Union[str, None] = 'chg001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create mrsa_review_policies table
    op.create_table(
        'mrsa_review_policies',
        sa.Column('policy_id', sa.Integer(), primary_key=True),
        sa.Column(
            'mrsa_risk_level_id',
            sa.Integer(),
            sa.ForeignKey('taxonomy_values.value_id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
            comment='MRSA Risk Level this policy applies to (High-Risk or Low-Risk)'
        ),
        sa.Column(
            'frequency_months',
            sa.Integer(),
            nullable=False,
            server_default='24',
            comment='How often MRSA reviews are required (in months)'
        ),
        sa.Column(
            'initial_review_months',
            sa.Integer(),
            nullable=False,
            server_default='3',
            comment='Time after MRSA creation when first review is due (in months)'
        ),
        sa.Column(
            'warning_days',
            sa.Integer(),
            nullable=False,
            server_default='90',
            comment='Days before due date to trigger warnings'
        ),
        sa.Column(
            'grace_period_days',
            sa.Integer(),
            nullable=False,
            server_default='30',
            comment='Days after due date before escalation (overdue threshold)'
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='Whether this policy is currently active'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),
    )

    # 2. Create mrsa_review_exceptions table
    op.create_table(
        'mrsa_review_exceptions',
        sa.Column('exception_id', sa.Integer(), primary_key=True),
        sa.Column(
            'mrsa_id',
            sa.Integer(),
            sa.ForeignKey('models.model_id', ondelete='CASCADE'),
            nullable=False,
            comment='MRSA (model) receiving the exception'
        ),
        sa.Column(
            'override_due_date',
            sa.Date(),
            nullable=False,
            comment='New due date for this MRSA review'
        ),
        sa.Column(
            'reason',
            sa.Text(),
            nullable=False,
            comment='Justification for the exception'
        ),
        sa.Column(
            'approved_by_id',
            sa.Integer(),
            sa.ForeignKey('users.user_id', ondelete='SET NULL'),
            nullable=True,
            comment='User who approved this exception'
        ),
        sa.Column(
            'approved_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            comment='When the exception was approved'
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='Whether this exception is currently active'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now()
        ),
    )

    # 3. Create indexes for common query patterns
    op.create_index(
        'ix_mrsa_review_policies_is_active',
        'mrsa_review_policies',
        ['is_active']
    )
    op.create_index(
        'ix_mrsa_review_exceptions_mrsa_id',
        'mrsa_review_exceptions',
        ['mrsa_id']
    )
    op.create_index(
        'ix_mrsa_review_exceptions_is_active',
        'mrsa_review_exceptions',
        ['is_active']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_mrsa_review_exceptions_is_active', table_name='mrsa_review_exceptions')
    op.drop_index('ix_mrsa_review_exceptions_mrsa_id', table_name='mrsa_review_exceptions')
    op.drop_index('ix_mrsa_review_policies_is_active', table_name='mrsa_review_policies')

    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table('mrsa_review_exceptions')
    op.drop_table('mrsa_review_policies')
