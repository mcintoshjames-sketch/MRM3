"""add_map_applications_tables

Revision ID: a1b2c3d4e5f6
Revises: cc7c2819a59c
Create Date: 2025-11-25 05:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'cc7c2819a59c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create map_applications table (mock Managed Application Portfolio)
    op.create_table(
        'map_applications',
        sa.Column('application_id', sa.Integer(), primary_key=True),
        sa.Column('application_code', sa.String(50), unique=True, nullable=False,
                  comment='Unique identifier from MAP system (e.g., APP-12345)'),
        sa.Column('application_name', sa.String(255), nullable=False,
                  comment='Display name of the application'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Description of the application purpose'),
        sa.Column('owner_name', sa.String(255), nullable=True,
                  comment='Application owner/steward name'),
        sa.Column('owner_email', sa.String(255), nullable=True,
                  comment='Application owner email'),
        sa.Column('department', sa.String(100), nullable=True,
                  comment='Department responsible for the application'),
        sa.Column('technology_stack', sa.String(255), nullable=True,
                  comment='Technology stack (e.g., Python/AWS Lambda)'),
        sa.Column('criticality_tier', sa.String(20), nullable=True,
                  comment='Application criticality: Critical, High, Medium, Low'),
        sa.Column('status', sa.String(50), nullable=False, server_default='Active',
                  comment='Application status: Active, Decommissioned, In Development'),
        sa.Column('external_url', sa.String(500), nullable=True,
                  comment='Link to MAP system record'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  onupdate=sa.func.now())
    )

    # Create model_applications junction table
    op.create_table(
        'model_applications',
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('application_id', sa.Integer(),
                  sa.ForeignKey('map_applications.application_id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('relationship_type_id', sa.Integer(),
                  sa.ForeignKey('taxonomy_values.value_id'), nullable=False,
                  comment='Type of relationship (Data Source, Execution Platform, etc.)'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Notes about this specific relationship'),
        sa.Column('effective_date', sa.Date(), nullable=True,
                  comment='When this relationship became effective'),
        sa.Column('end_date', sa.Date(), nullable=True,
                  comment='When this relationship ended (soft delete)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_user_id', sa.Integer(),
                  sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  onupdate=sa.func.now())
    )

    # Create index for efficient queries
    op.create_index('ix_model_applications_application_id', 'model_applications', ['application_id'])
    op.create_index('ix_map_applications_status', 'map_applications', ['status'])
    op.create_index('ix_map_applications_department', 'map_applications', ['department'])


def downgrade() -> None:
    op.drop_index('ix_map_applications_department', table_name='map_applications')
    op.drop_index('ix_map_applications_status', table_name='map_applications')
    op.drop_index('ix_model_applications_application_id', table_name='model_applications')
    op.drop_table('model_applications')
    op.drop_table('map_applications')
