"""add_scorecard_config_versioning

Revision ID: 451cbddc8250
Revises: y5z6a7b8c9d0
Create Date: 2025-12-02 04:44:10.069712

This migration adds configuration versioning for validation scorecards,
similar to how MonitoringPlanVersion works. This ensures historical
scorecards preserve the configuration (sections, criteria, weights)
that was active when they were created.

Tables created:
- scorecard_config_versions: Version metadata
- scorecard_section_snapshots: Section configuration at version time
- scorecard_criterion_snapshots: Criterion configuration at version time

Also adds:
- config_version_id FK to validation_scorecard_results
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '451cbddc8250'
down_revision: Union[str, None] = 'y5z6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create scorecard config versions table
    op.create_table('scorecard_config_versions',
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, comment='Sequential version number (1, 2, 3...)'),
        sa.Column('version_name', sa.String(length=200), nullable=True, comment="Optional display name (e.g., 'Q4 2025 Updates')"),
        sa.Column('description', sa.Text(), nullable=True, comment='Changelog or notes for this version'),
        sa.Column('effective_date', sa.Date(), nullable=False, comment='Date this version becomes effective'),
        sa.Column('published_by_user_id', sa.Integer(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Only one version should be active at a time'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['published_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('version_id'),
        sa.UniqueConstraint('version_number', name='uq_scorecard_config_version_number')
    )

    # Create section snapshots table
    op.create_table('scorecard_section_snapshots',
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('original_section_id', sa.Integer(), nullable=True, comment='Reference to original section (may be deleted)'),
        sa.Column('code', sa.String(length=20), nullable=False, comment='Section code at time of snapshot'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['scorecard_config_versions.version_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('snapshot_id'),
        sa.UniqueConstraint('version_id', 'code', name='uq_section_snapshot_version_code')
    )
    op.create_index(op.f('ix_scorecard_section_snapshots_version_id'), 'scorecard_section_snapshots', ['version_id'], unique=False)

    # Create criterion snapshots table
    op.create_table('scorecard_criterion_snapshots',
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('original_criterion_id', sa.Integer(), nullable=True, comment='Reference to original criterion (may be deleted)'),
        sa.Column('section_code', sa.String(length=20), nullable=False, comment='Parent section code (not FK - for resilience)'),
        sa.Column('code', sa.String(length=20), nullable=False, comment='Criterion code at time of snapshot'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description_prompt', sa.Text(), nullable=True),
        sa.Column('comments_prompt', sa.Text(), nullable=True),
        sa.Column('include_in_summary', sa.Boolean(), nullable=False),
        sa.Column('allow_zero', sa.Boolean(), nullable=False),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=False, comment='Weight as configured at snapshot time'),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['scorecard_config_versions.version_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('snapshot_id'),
        sa.UniqueConstraint('version_id', 'code', name='uq_criterion_snapshot_version_code')
    )
    op.create_index(op.f('ix_scorecard_criterion_snapshots_version_id'), 'scorecard_criterion_snapshots', ['version_id'], unique=False)

    # Add config_version_id column to validation_scorecard_results
    op.add_column('validation_scorecard_results', sa.Column('config_version_id', sa.Integer(), nullable=True, comment='FK to scorecard config version used for this scorecard'))
    op.create_foreign_key('fk_scorecard_results_config_version', 'validation_scorecard_results', 'scorecard_config_versions', ['config_version_id'], ['version_id'], ondelete='SET NULL')

    # =========================================================================
    # Backfill: Create version 1 from existing scorecard configuration
    # =========================================================================
    connection = op.get_bind()

    # Check if there are existing sections
    sections_exist = connection.execute(text(
        "SELECT COUNT(*) FROM scorecard_sections"
    )).scalar()

    if sections_exist and sections_exist > 0:
        # Create version 1
        connection.execute(text("""
            INSERT INTO scorecard_config_versions
            (version_number, version_name, description, effective_date, published_at, is_active, created_at)
            VALUES (1, 'Initial Configuration (Migrated)', 'Auto-created during migration from existing scorecard configuration',
                    CURRENT_DATE, NOW(), TRUE, NOW())
        """))

        # Get the version_id we just created
        version_id = connection.execute(text(
            "SELECT version_id FROM scorecard_config_versions WHERE version_number = 1"
        )).scalar()

        # Snapshot all existing sections
        connection.execute(text("""
            INSERT INTO scorecard_section_snapshots
            (version_id, original_section_id, code, name, description, sort_order, is_active, created_at)
            SELECT :version_id, section_id, code, name, description, sort_order, is_active, NOW()
            FROM scorecard_sections
        """), {"version_id": version_id})

        # Snapshot all existing criteria with their section codes
        connection.execute(text("""
            INSERT INTO scorecard_criterion_snapshots
            (version_id, original_criterion_id, section_code, code, name,
             description_prompt, comments_prompt, include_in_summary, allow_zero,
             weight, sort_order, is_active, created_at)
            SELECT :version_id, c.criterion_id, s.code, c.code, c.name,
                   c.description_prompt, c.comments_prompt, c.include_in_summary, c.allow_zero,
                   c.weight, c.sort_order, c.is_active, NOW()
            FROM scorecard_criteria c
            JOIN scorecard_sections s ON c.section_id = s.section_id
        """), {"version_id": version_id})

        # Link existing scorecard results to version 1
        connection.execute(text("""
            UPDATE validation_scorecard_results
            SET config_version_id = :version_id
            WHERE config_version_id IS NULL
        """), {"version_id": version_id})


def downgrade() -> None:
    # Drop the foreign key first
    op.drop_constraint('fk_scorecard_results_config_version', 'validation_scorecard_results', type_='foreignkey')
    op.drop_column('validation_scorecard_results', 'config_version_id')

    # Drop snapshot tables
    op.drop_index(op.f('ix_scorecard_criterion_snapshots_version_id'), table_name='scorecard_criterion_snapshots')
    op.drop_table('scorecard_criterion_snapshots')
    op.drop_index(op.f('ix_scorecard_section_snapshots_version_id'), table_name='scorecard_section_snapshots')
    op.drop_table('scorecard_section_snapshots')
    op.drop_table('scorecard_config_versions')
