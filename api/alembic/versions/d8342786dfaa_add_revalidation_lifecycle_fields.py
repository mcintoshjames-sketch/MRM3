"""add_revalidation_lifecycle_fields

Revision ID: d8342786dfaa
Revises: e37fadd1bf67
Create Date: 2025-11-20 14:47:44.433721

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8342786dfaa'
down_revision: Union[str, None] = 'e37fadd1bf67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prior_validation_request_id column (FK to self)
    op.add_column('validation_requests', sa.Column('prior_validation_request_id', sa.Integer(), nullable=True))

    # Add submission_received_date column
    op.add_column('validation_requests', sa.Column('submission_received_date', sa.Date(), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_validation_requests_prior',
        'validation_requests', 'validation_requests',
        ['prior_validation_request_id'], ['request_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_validation_requests_prior', 'validation_requests', type_='foreignkey')

    # Drop columns
    op.drop_column('validation_requests', 'submission_received_date')
    op.drop_column('validation_requests', 'prior_validation_request_id')
