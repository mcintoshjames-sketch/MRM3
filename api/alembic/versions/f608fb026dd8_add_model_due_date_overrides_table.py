"""add model_due_date_overrides table

Revision ID: f608fb026dd8
Revises: ent001
Create Date: 2026-01-18 18:40:06.491459

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f608fb026dd8'
down_revision: Union[str, None] = 'ent001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the model_due_date_overrides table
    op.create_table('model_due_date_overrides',
        sa.Column('override_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('validation_request_id', sa.Integer(), nullable=True,
                  comment='Linked validation request (only for CURRENT_REQUEST scope)'),
        sa.Column('override_type', sa.String(length=20), nullable=False,
                  comment='ONE_TIME or PERMANENT'),
        sa.Column('target_scope', sa.String(length=20), nullable=False,
                  comment='CURRENT_REQUEST or NEXT_CYCLE'),
        sa.Column('override_date', sa.Date(), nullable=False,
                  comment='New due date - must be earlier than calculated date'),
        sa.Column('original_calculated_date', sa.Date(), nullable=False,
                  comment='Policy-calculated date at time of override creation'),
        sa.Column('reason', sa.Text(), nullable=False,
                  comment='Admin justification for override (min 10 chars)'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('cleared_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When this override was cleared/superseded'),
        sa.Column('cleared_by_user_id', sa.Integer(), nullable=True),
        sa.Column('cleared_reason', sa.Text(), nullable=True,
                  comment='Reason for clearing (manual or auto-cleared)'),
        sa.Column('cleared_type', sa.String(length=30), nullable=True,
                  comment='MANUAL, AUTO_VALIDATION_COMPLETE, AUTO_ROLL_FORWARD, AUTO_REQUEST_CANCELLED, or SUPERSEDED'),
        sa.Column('superseded_by_override_id', sa.Integer(), nullable=True),
        sa.Column('rolled_from_override_id', sa.Integer(), nullable=True,
                  comment="For auto-rolled overrides: points to the previous cycle's override"),
        sa.CheckConstraint(
            "cleared_type IS NULL OR cleared_type IN ('MANUAL', 'AUTO_VALIDATION_COMPLETE', 'AUTO_ROLL_FORWARD', 'AUTO_REQUEST_CANCELLED', 'SUPERSEDED')",
            name='check_cleared_type_valid'),
        sa.CheckConstraint("override_type IN ('ONE_TIME', 'PERMANENT')",
                          name='check_override_type_valid'),
        sa.CheckConstraint("target_scope IN ('CURRENT_REQUEST', 'NEXT_CYCLE')",
                          name='check_target_scope_valid'),
        sa.CheckConstraint('override_date < original_calculated_date',
                          name='check_override_earlier_than_calculated'),
        sa.ForeignKeyConstraint(['cleared_by_user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rolled_from_override_id'], ['model_due_date_overrides.override_id']),
        sa.ForeignKeyConstraint(['superseded_by_override_id'], ['model_due_date_overrides.override_id']),
        sa.ForeignKeyConstraint(['validation_request_id'], ['validation_requests.request_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('override_id')
    )
    op.create_index(op.f('ix_model_due_date_overrides_is_active'), 'model_due_date_overrides', ['is_active'], unique=False)
    op.create_index(op.f('ix_model_due_date_overrides_model_id'), 'model_due_date_overrides', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_due_date_overrides_validation_request_id'), 'model_due_date_overrides', ['validation_request_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_due_date_overrides_validation_request_id'), table_name='model_due_date_overrides')
    op.drop_index(op.f('ix_model_due_date_overrides_model_id'), table_name='model_due_date_overrides')
    op.drop_index(op.f('ix_model_due_date_overrides_is_active'), table_name='model_due_date_overrides')
    op.drop_table('model_due_date_overrides')
