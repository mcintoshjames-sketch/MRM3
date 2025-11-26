"""add_grace_period_months_to_validation_policy

Revision ID: 0a7a0b86ae95
Revises: ae688a56da90
Create Date: 2025-11-26 02:15:21.475136

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a7a0b86ae95'
down_revision: Union[str, None] = 'ae688a56da90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add grace_period_months column with server default for existing rows
    op.add_column('validation_policies', sa.Column(
        'grace_period_months',
        sa.Integer(),
        nullable=False,
        server_default='3',
        comment='Grace period in months after submission due date before item is considered overdue'
    ))


def downgrade() -> None:
    op.drop_column('validation_policies', 'grace_period_months')
