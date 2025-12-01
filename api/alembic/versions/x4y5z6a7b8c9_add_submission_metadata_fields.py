"""Add submission metadata fields to validation_requests

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2025-12-01

This migration adds fields to capture additional submission metadata when
marking a validation submission as received:
- confirmed_model_version_id: To confirm/correct the model version associated with validation
- model_documentation_version: Version of the model documentation submitted
- model_submission_version: Version of the model code/artifacts submitted
- model_documentation_id: External ID for the documentation (e.g., document management system ID)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'x4y5z6a7b8c9'
down_revision = 'w3x4y5z6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # Add confirmed_model_version_id - FK to model_versions
    op.add_column('validation_requests', sa.Column(
        'confirmed_model_version_id',
        sa.Integer(),
        nullable=True,
        comment='Confirmed model version at time of submission (may differ from originally associated version)'
    ))
    op.create_foreign_key(
        'fk_validation_requests_confirmed_version',
        'validation_requests',
        'model_versions',
        ['confirmed_model_version_id'],
        ['version_id'],
        ondelete='SET NULL'
    )

    # Add model_documentation_version
    op.add_column('validation_requests', sa.Column(
        'model_documentation_version',
        sa.String(100),
        nullable=True,
        comment='Version identifier for the model documentation submitted'
    ))

    # Add model_submission_version
    op.add_column('validation_requests', sa.Column(
        'model_submission_version',
        sa.String(100),
        nullable=True,
        comment='Version identifier for the model code/artifacts submitted'
    ))

    # Add model_documentation_id
    op.add_column('validation_requests', sa.Column(
        'model_documentation_id',
        sa.String(255),
        nullable=True,
        comment='External ID or reference for the model documentation (e.g., document management system ID)'
    ))


def downgrade():
    # Drop the FK constraint first
    op.drop_constraint('fk_validation_requests_confirmed_version', 'validation_requests', type_='foreignkey')

    # Drop columns
    op.drop_column('validation_requests', 'model_documentation_id')
    op.drop_column('validation_requests', 'model_submission_version')
    op.drop_column('validation_requests', 'model_documentation_version')
    op.drop_column('validation_requests', 'confirmed_model_version_id')
