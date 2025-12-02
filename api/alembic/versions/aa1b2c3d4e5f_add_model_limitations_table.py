"""Add model_limitations table

Revision ID: aa1b2c3d4e5f
Revises: a7b8c9d0e1f2
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa1b2c3d4e5f'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create model_limitations table
    op.create_table(
        'model_limitations',
        sa.Column('limitation_id', sa.Integer(), nullable=False),
        # Core relationships
        sa.Column('model_id', sa.Integer(), nullable=False, comment='The model this limitation applies to'),
        sa.Column('validation_request_id', sa.Integer(), nullable=True, comment='Validation request that originally identified this limitation'),
        sa.Column('model_version_id', sa.Integer(), nullable=True, comment='Model version under review when limitation was discovered'),
        sa.Column('recommendation_id', sa.Integer(), nullable=True, comment='Linked recommendation for mitigation (optional)'),
        # Classification
        sa.Column('significance', sa.String(20), nullable=False, comment='Critical or Non-Critical'),
        sa.Column('category_id', sa.Integer(), nullable=False, comment='Limitation category from taxonomy'),
        # Narrative content
        sa.Column('description', sa.Text(), nullable=False, comment='Narrative description of the nature of the limitation'),
        sa.Column('impact_assessment', sa.Text(), nullable=False, comment='Narrative assessment of the limitation impact'),
        sa.Column('conclusion', sa.String(20), nullable=False, comment='Mitigate or Accept'),
        sa.Column('conclusion_rationale', sa.Text(), nullable=False, comment='Explanation for the mitigate/accept decision'),
        sa.Column('user_awareness_description', sa.Text(), nullable=True, comment='How users are made aware (required if Critical)'),
        # Retirement
        sa.Column('is_retired', sa.Boolean(), nullable=False, default=False),
        sa.Column('retirement_date', sa.DateTime(), nullable=True),
        sa.Column('retirement_reason', sa.Text(), nullable=True),
        sa.Column('retired_by_id', sa.Integer(), nullable=True),
        # Audit
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        # Primary key
        sa.PrimaryKeyConstraint('limitation_id'),
        # Foreign keys
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['validation_request_id'], ['validation_requests.request_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.version_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.recommendation_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['taxonomy_values.value_id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['retired_by_id'], ['users.user_id'], ondelete='SET NULL'),
        # Check constraints
        sa.CheckConstraint("significance IN ('Critical', 'Non-Critical')", name='chk_limitation_significance'),
        sa.CheckConstraint("conclusion IN ('Mitigate', 'Accept')", name='chk_limitation_conclusion'),
        sa.CheckConstraint("significance != 'Critical' OR user_awareness_description IS NOT NULL", name='chk_critical_requires_awareness'),
        sa.CheckConstraint(
            "(is_retired = FALSE AND retirement_date IS NULL AND retirement_reason IS NULL AND retired_by_id IS NULL) OR "
            "(is_retired = TRUE AND retirement_date IS NOT NULL AND retirement_reason IS NOT NULL AND retired_by_id IS NOT NULL)",
            name='chk_retirement_fields_consistency'
        ),
    )

    # Create indexes
    op.create_index('idx_limitation_model', 'model_limitations', ['model_id'])
    op.create_index('idx_limitation_validation', 'model_limitations', ['validation_request_id'])
    op.create_index('idx_limitation_version', 'model_limitations', ['model_version_id'])
    op.create_index('idx_limitation_recommendation', 'model_limitations', ['recommendation_id'])
    op.create_index('idx_limitation_category', 'model_limitations', ['category_id'])
    op.create_index('idx_limitation_significance', 'model_limitations', ['significance'])
    op.create_index('idx_limitation_retired', 'model_limitations', ['is_retired'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_limitation_retired', table_name='model_limitations')
    op.drop_index('idx_limitation_significance', table_name='model_limitations')
    op.drop_index('idx_limitation_category', table_name='model_limitations')
    op.drop_index('idx_limitation_recommendation', table_name='model_limitations')
    op.drop_index('idx_limitation_version', table_name='model_limitations')
    op.drop_index('idx_limitation_validation', table_name='model_limitations')
    op.drop_index('idx_limitation_model', table_name='model_limitations')

    # Drop table
    op.drop_table('model_limitations')
