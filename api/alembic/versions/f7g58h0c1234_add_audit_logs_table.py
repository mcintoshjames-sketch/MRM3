"""Add audit_logs table

Revision ID: f7g58h0c1234
Revises: e6f47g9b0123
Create Date: 2024-01-17 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f7g58h0c1234'
down_revision = 'e6f47g9b0123'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('log_id', sa.Integer(), primary_key=True, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
    )
    # Index for faster queries on entity
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_entity', 'audit_logs')
    op.drop_table('audit_logs')
