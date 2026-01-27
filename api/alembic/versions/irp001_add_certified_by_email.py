"""add certified_by_email to irp_certifications

Revision ID: irp001_certified_by_email
Revises: f608fb026dd8
Create Date: 2026-01-21

This migration adds a certified_by_email column to the irp_certifications table
to capture the email address of the individual who performed the certification.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'irp001_certified_by_email'
down_revision: Union[str, None] = 'f608fb026dd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add certified_by_email column to irp_certifications table
    # First add as nullable to allow backfilling existing records
    op.add_column(
        'irp_certifications',
        sa.Column(
            'certified_by_email',
            sa.String(255),
            nullable=True,
            comment='Email address of the individual who performed the certification'
        )
    )

    # Backfill existing records with the email from the certified_by_user
    op.execute("""
        UPDATE irp_certifications ic
        SET certified_by_email = u.email
        FROM users u
        WHERE ic.certified_by_user_id = u.user_id
        AND ic.certified_by_email IS NULL
    """)

    # Now make the column non-nullable
    op.alter_column(
        'irp_certifications',
        'certified_by_email',
        nullable=False
    )


def downgrade() -> None:
    op.drop_column('irp_certifications', 'certified_by_email')
