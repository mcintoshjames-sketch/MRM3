"""add_prior_full_validation_request_id

Revision ID: ae688a56da90
Revises: 77b13b91aa3b
Create Date: 2025-11-26 01:52:30.595360

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae688a56da90'
down_revision: Union[str, None] = '77b13b91aa3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prior_full_validation_request_id column
    op.add_column('validation_requests', sa.Column(
        'prior_full_validation_request_id',
        sa.Integer(),
        nullable=True,
        comment='Link to the most recent INITIAL or COMPREHENSIVE validation'
    ))
    op.create_foreign_key(
        'fk_validation_requests_prior_full_validation',
        'validation_requests',
        'validation_requests',
        ['prior_full_validation_request_id'],
        ['request_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_validation_requests_prior_full_validation', 'validation_requests', type_='foreignkey')
    op.drop_column('validation_requests', 'prior_full_validation_request_id')
