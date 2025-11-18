"""add_regional_support_to_validation_requests

Revision ID: 93f240c5f60c
Revises: 7b44e960ad31
Create Date: 2025-11-18 00:39:17.651000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93f240c5f60c'
down_revision: Union[str, None] = '7b44e960ad31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add regional_model_implementation_id column to validation_requests table
    op.add_column('validation_requests', sa.Column('regional_model_implementation_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_validation_requests_regional_implementation',
        'validation_requests',
        'regional_model_implementations',
        ['regional_model_implementation_id'],
        ['regional_model_impl_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Remove foreign key and column
    op.drop_constraint('fk_validation_requests_regional_implementation', 'validation_requests', type_='foreignkey')
    op.drop_column('validation_requests', 'regional_model_implementation_id')
