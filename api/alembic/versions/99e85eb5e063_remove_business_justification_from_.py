"""remove_business_justification_from_validation_requests

Revision ID: 99e85eb5e063
Revises: 5692dfd2d5e7
Create Date: 2025-11-18 05:33:37.482801

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99e85eb5e063'
down_revision: Union[str, None] = '5692dfd2d5e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove business_justification column from validation_requests table
    op.drop_column('validation_requests', 'business_justification')


def downgrade() -> None:
    # Add business_justification column back if rolling back
    op.add_column('validation_requests', sa.Column('business_justification', sa.Text(), nullable=False, server_default=''))
