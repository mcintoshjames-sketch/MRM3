"""Add CHECK constraint enforcing closure requirements on model_exceptions.

Revision ID: exc002
Revises: rec001
Create Date: 2025-01-15

This migration adds a CHECK constraint to enforce that when an exception
is CLOSED, both closure_reason_id and closure_narrative must be non-null.
This prevents out-of-band writes from violating the closure requirements
that are already enforced at the application level.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'exc002'
down_revision = 'rec001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add CHECK constraint: when status='CLOSED', closure fields must be non-null
    # This enforces at DB level what the app already enforces in _close_exception()
    op.create_check_constraint(
        'ck_model_exceptions_closure_requirements',
        'model_exceptions',
        """
        status != 'CLOSED' OR (
            closure_reason_id IS NOT NULL AND
            closure_narrative IS NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.drop_constraint('ck_model_exceptions_closure_requirements', 'model_exceptions', type_='check')
