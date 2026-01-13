"""Add model tagging tables

Revision ID: c1d2e3f4a5b6
Revises: 8c3c43b05035
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = '8c3c43b05035'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Tag Categories
    op.create_table(
        'tag_categories',
        sa.Column('category_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=False, server_default='#6B7280',
                  comment='Hex color code (e.g., #DC2626)'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false',
                  comment='System categories cannot be deleted'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
    )

    # 2. Tags
    op.create_table(
        'tags',
        sa.Column('tag_id', sa.Integer(), primary_key=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('tag_categories.category_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=True,
                  comment='Optional override color (hex code)'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.UniqueConstraint('category_id', 'name', name='uq_tag_category_name'),
    )
    op.create_index('ix_tags_category_id', 'tags', ['category_id'])
    op.create_index('ix_tags_is_active', 'tags', ['is_active'])

    # 3. Model-Tag Association (hard delete - current state only)
    op.create_table(
        'model_tags',
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tags.tag_id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('added_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.PrimaryKeyConstraint('model_id', 'tag_id'),
    )
    op.create_index('ix_model_tags_tag_id', 'model_tags', ['tag_id'])

    # 4. Model Tag History (full audit trail)
    op.create_table(
        'model_tag_history',
        sa.Column('history_id', sa.Integer(), primary_key=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tags.tag_id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False,
                  comment="Action type: 'ADDED' or 'REMOVED'"),
        sa.Column('performed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('performed_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_model_tag_history_model', 'model_tag_history', ['model_id'])
    op.create_index('ix_model_tag_history_tag', 'model_tag_history', ['tag_id'])
    op.create_index('ix_model_tag_history_performed_at', 'model_tag_history', ['performed_at'])


def downgrade():
    op.drop_table('model_tag_history')
    op.drop_table('model_tags')
    op.drop_table('tags')
    op.drop_table('tag_categories')
