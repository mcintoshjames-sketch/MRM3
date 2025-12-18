"""add_validation_findings_table

Revision ID: 5809df3fd79c
Revises: c3e779534394
Create Date: 2025-12-17 18:53:30.422944

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5809df3fd79c'
down_revision: Union[str, None] = 'c3e779534394'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add validation_findings table for tracking findings during validations."""
    op.create_table('validation_findings',
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('finding_type', sa.String(length=50), nullable=False,
                  comment='Category of finding: DATA_QUALITY, METHODOLOGY, IMPLEMENTATION, etc.'),
        sa.Column('severity', sa.String(length=20), nullable=False,
                  comment='Severity level: HIGH, MEDIUM, LOW'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False,
                  comment='Finding status: OPEN or RESOLVED'),
        sa.Column('identified_by_id', sa.Integer(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['identified_by_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('finding_id')
    )
    # Add indexes for common queries
    op.create_index('ix_validation_findings_request_id', 'validation_findings', ['request_id'])
    op.create_index('ix_validation_findings_status', 'validation_findings', ['status'])


def downgrade() -> None:
    """Remove validation_findings table."""
    op.drop_index('ix_validation_findings_status', table_name='validation_findings')
    op.drop_index('ix_validation_findings_request_id', table_name='validation_findings')
    op.drop_table('validation_findings')
