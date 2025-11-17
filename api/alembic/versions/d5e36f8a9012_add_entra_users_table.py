"""Add entra_users table for mock directory

Revision ID: d5e36f8a9012
Revises: c4d25e6f7891
Create Date: 2024-01-15 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e36f8a9012'
down_revision = 'c4d25e6f7891'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'entra_users',
        sa.Column('entra_id', sa.String(36), primary_key=True),
        sa.Column('user_principal_name', sa.String(255), unique=True, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('given_name', sa.String(100), nullable=True),
        sa.Column('surname', sa.String(100), nullable=True),
        sa.Column('mail', sa.String(255), nullable=False),
        sa.Column('job_title', sa.String(255), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('office_location', sa.String(255), nullable=True),
        sa.Column('mobile_phone', sa.String(50), nullable=True),
        sa.Column('account_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('entra_users')
