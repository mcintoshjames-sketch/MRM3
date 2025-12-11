"""add_mrsa_and_irp_tables

Revision ID: mrsa001_add_mrsa_irp
Revises: mas001_approval_status
Create Date: 2025-12-11 10:00:00.000000

This migration adds MRSA (Model Risk-Sensitive Application) classification and
IRP (Independent Review Process) management features:
- Adds requires_irp column to taxonomy_values for MRSA risk level enforcement
- Adds MRSA fields to models table (is_mrsa, mrsa_risk_level_id, mrsa_risk_rationale)
- Creates irps table for Independent Review Processes
- Creates mrsa_irp association table for many-to-many IRP-MRSA relationships
- Creates irp_reviews table for periodic IRP assessments
- Creates irp_certifications table for MRM sign-off on IRP design
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'mrsa001_add_mrsa_irp'
down_revision: Union[str, None] = 'mas001_approval_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add requires_irp column to taxonomy_values table
    op.add_column(
        'taxonomy_values',
        sa.Column(
            'requires_irp',
            sa.Boolean(),
            nullable=True,
            comment='For MRSA Risk Level taxonomy: True if this risk level requires IRP coverage'
        )
    )

    # 2. Add MRSA fields to models table
    op.add_column(
        'models',
        sa.Column(
            'is_mrsa',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True for Model Risk-Sensitive Applications (non-models requiring oversight)'
        )
    )
    op.add_column(
        'models',
        sa.Column(
            'mrsa_risk_level_id',
            sa.Integer(),
            sa.ForeignKey('taxonomy_values.value_id', ondelete='SET NULL'),
            nullable=True,
            comment='MRSA risk classification (High-Risk or Low-Risk)'
        )
    )
    op.add_column(
        'models',
        sa.Column(
            'mrsa_risk_rationale',
            sa.Text(),
            nullable=True,
            comment='Narrative explaining the MRSA risk level assignment'
        )
    )

    # 3. Create irps table
    op.create_table(
        'irps',
        sa.Column('irp_id', sa.Integer(), primary_key=True),
        sa.Column('process_name', sa.String(255), nullable=False,
                  comment='Name of the Independent Review Process'),
        sa.Column('contact_user_id', sa.Integer(),
                  sa.ForeignKey('users.user_id'), nullable=False,
                  comment='Primary contact person responsible for this IRP'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Description of the IRP scope and purpose'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true',
                  comment='Whether this IRP is currently active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 4. Create mrsa_irp association table (many-to-many)
    op.create_table(
        'mrsa_irp',
        sa.Column('model_id', sa.Integer(),
                  sa.ForeignKey('models.model_id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('irp_id', sa.Integer(),
                  sa.ForeignKey('irps.irp_id', ondelete='CASCADE'),
                  primary_key=True),
    )

    # 5. Create irp_reviews table
    op.create_table(
        'irp_reviews',
        sa.Column('review_id', sa.Integer(), primary_key=True),
        sa.Column('irp_id', sa.Integer(),
                  sa.ForeignKey('irps.irp_id', ondelete='CASCADE'),
                  nullable=False, index=True,
                  comment='IRP being reviewed'),
        sa.Column('review_date', sa.Date(), nullable=False,
                  comment='Date the review was completed'),
        sa.Column('outcome_id', sa.Integer(),
                  sa.ForeignKey('taxonomy_values.value_id'),
                  nullable=False,
                  comment='IRP Review Outcome taxonomy value (Satisfactory, etc.)'),
        sa.Column('notes', sa.Text(), nullable=True,
                  comment='Notes and observations from the review'),
        sa.Column('reviewed_by_user_id', sa.Integer(),
                  sa.ForeignKey('users.user_id'),
                  nullable=False,
                  comment='User who performed the review'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 6. Create irp_certifications table
    op.create_table(
        'irp_certifications',
        sa.Column('certification_id', sa.Integer(), primary_key=True),
        sa.Column('irp_id', sa.Integer(),
                  sa.ForeignKey('irps.irp_id', ondelete='CASCADE'),
                  nullable=False, index=True,
                  comment='IRP being certified'),
        sa.Column('certification_date', sa.Date(), nullable=False,
                  comment='Date the certification was completed'),
        sa.Column('certified_by_user_id', sa.Integer(),
                  sa.ForeignKey('users.user_id'),
                  nullable=False,
                  comment='MRM person who performed the certification'),
        sa.Column('conclusion_summary', sa.Text(), nullable=False,
                  comment='Narrative summary of the certification conclusion'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for common query patterns
    op.create_index('ix_irps_is_active', 'irps', ['is_active'])
    op.create_index('ix_irp_reviews_review_date', 'irp_reviews', ['review_date'])
    op.create_index('ix_irp_certifications_certification_date', 'irp_certifications', ['certification_date'])
    op.create_index('ix_models_is_mrsa', 'models', ['is_mrsa'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_models_is_mrsa', table_name='models')
    op.drop_index('ix_irp_certifications_certification_date', table_name='irp_certifications')
    op.drop_index('ix_irp_reviews_review_date', table_name='irp_reviews')
    op.drop_index('ix_irps_is_active', table_name='irps')

    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table('irp_certifications')
    op.drop_table('irp_reviews')
    op.drop_table('mrsa_irp')
    op.drop_table('irps')

    # Remove MRSA columns from models
    op.drop_column('models', 'mrsa_risk_rationale')
    op.drop_column('models', 'mrsa_risk_level_id')
    op.drop_column('models', 'is_mrsa')

    # Remove requires_irp from taxonomy_values
    op.drop_column('taxonomy_values', 'requires_irp')
