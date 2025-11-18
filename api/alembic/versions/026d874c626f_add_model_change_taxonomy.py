"""add_model_change_taxonomy

Revision ID: 026d874c626f
Revises: d6989a9d64c9
Create Date: 2025-11-18 02:52:48.165688

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '026d874c626f'
down_revision: Union[str, None] = 'd6989a9d64c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create model_change_categories table (L1)
    op.create_table(
        'model_change_categories',
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('category_id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_model_change_categories_code'), 'model_change_categories', ['code'], unique=False)

    # Create model_change_types table (L2)
    op.create_table(
        'model_change_types',
        sa.Column('change_type_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('mv_activity', sa.String(length=50), nullable=True),
        sa.Column('requires_mv_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['category_id'], ['model_change_categories.category_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('change_type_id'),
        sa.UniqueConstraint('code', name='uq_model_change_type_code')
    )
    op.create_index(op.f('ix_model_change_types_category_id'), 'model_change_types', ['category_id'], unique=False)

    # Seed L1 categories
    op.execute("""
        INSERT INTO model_change_categories (category_id, code, name, sort_order) VALUES
        (1, 'A', 'New Model', 1),
        (2, 'B', 'Change to Model', 2),
        (3, 'C', 'Change to Input Data', 3),
        (4, 'D', 'Change to Output', 4),
        (5, 'E', 'Technical Change', 5),
        (6, 'F', 'Operational Change', 6),
        (7, 'G', 'Governance Change', 7),
        (8, 'H', 'Other Change', 8)
    """)

    # Seed L2 change types
    op.execute("""
        INSERT INTO model_change_types (change_type_id, category_id, code, name, description, mv_activity, requires_mv_approval, sort_order) VALUES
        -- A: New Model
        (1, 1, 1, 'New Model Development', 'Develop new model due to new regulatory requirement, new policy, new product, new modeling approach', 'Approval', true, 1),

        -- B: Change to Model
        (2, 2, 2, 'Change to Model Methodology', 'Change to model theory, model philosophy, or model assumption', 'Approval', true, 2),
        (3, 2, 3, 'Change to Model Input/Parameter', 'Change to model input or input parameter. For AML models: Sanction lists', 'Approval', true, 3),
        (4, 2, 4, 'Change to Model Implementation', 'Change to realization of model theory/design, including implementation change via system migration/upgrade, etc.', 'Approval', true, 4),
        (5, 2, 5, 'Change to Model Output', 'Change to model output measures', 'Approval', true, 5),
        (6, 2, 6, 'Change to Model Usage', 'Change of model use scope, e.g., applying to different underlying/asset class', 'Approval', true, 6),
        (7, 2, 7, 'Bug Fixes', 'Bug fixes to existing model theory/implementation/output that does not affect model theory', 'Approval', true, 7),

        -- C: Change to Input Data
        (8, 3, 8, 'Change to Input Data Type/Source - Type I', 'Change to type/source/flow of input data directly impacts model', 'Approval', true, 8),
        (9, 3, 9, 'Change to Input Data Type/Source - Type II', 'Change to type/source/field in database that does not affect model theory or implementation', 'Not in scope to MV', false, 9),
        (10, 3, 10, 'Change to Input Data Calibration', 'Change to the calibration routine/methodology of input data', 'Approval', true, 10),
        (11, 3, 11, 'Change to Input Data Proxy - Type I', 'Change of proxy rule set selected by the model or default value to the model', 'Approval', true, 11),
        (12, 3, 12, 'Change to Input Data Proxy - Type II', 'Change of proxy (tactical) to support day-to-day model run', 'Not in scope to MV', false, 12),

        -- D: Change to Output
        (13, 4, 13, 'Change to Output Format/Report', 'Change to reporting-related information or communication', 'Not in scope to MV', false, 13),
        (14, 4, 14, 'Change to Output Usage', 'Change of model output usage scope', 'Inform', false, 14),

        -- E: Technical Change
        (15, 5, 15, 'Change to System/Infrastructure - Type I', 'Change to feed mapping or system migration that doesn''t directly impact models.', 'Inform', false, 15),
        (16, 5, 16, 'Change to System/Infrastructure - Type II', 'Change to the technology platform, such as system upgrade that doesn''t directly impact models.', 'Inform', false, 16),
        (17, 5, 17, 'Change to System/Infrastructure - Type III', 'Change to GUI or module that do not affect model theory or implementation.', 'Not in scope to MV', false, 17),

        -- F: Operational Change
        (18, 6, 18, 'Change to Operational Processes - Type I', 'Turn on/off approved model.', 'Inform', false, 18),
        (19, 6, 19, 'Change to Operational Processes - Type II', 'Change to the operating process or workflow.', 'Not in scope to MV', false, 19),

        -- G: Governance Change
        (20, 7, 20, 'Change to related policy or model documentation', 'Change to model documentation, policy or procedure.', 'Inform', false, 20),

        -- H: Other Change
        (21, 8, 21, 'Please specify by Model Owners', '', '', false, 21)
    """)

    # Add change_type_id to model_versions table
    op.add_column('model_versions', sa.Column('change_type_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_model_versions_change_type', 'model_versions', 'model_change_types', ['change_type_id'], ['change_type_id'], ondelete='SET NULL')
    op.create_index(op.f('ix_model_versions_change_type_id'), 'model_versions', ['change_type_id'], unique=False)


def downgrade() -> None:
    # Drop change_type_id from model_versions
    op.drop_index(op.f('ix_model_versions_change_type_id'), table_name='model_versions')
    op.drop_constraint('fk_model_versions_change_type', 'model_versions', type_='foreignkey')
    op.drop_column('model_versions', 'change_type_id')

    # Drop tables in reverse order
    op.drop_index(op.f('ix_model_change_types_category_id'), table_name='model_change_types')
    op.drop_table('model_change_types')
    op.drop_index(op.f('ix_model_change_categories_code'), table_name='model_change_categories')
    op.drop_table('model_change_categories')
