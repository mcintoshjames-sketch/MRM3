"""Add monitoring plan versioning tables and columns.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2025-11-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'l2m3n4o5p6q7'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create monitoring_plan_versions table
    op.create_table(
        'monitoring_plan_versions',
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('version_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('published_by_user_id', sa.Integer(), nullable=True),
        sa.Column('published_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['monitoring_plans.plan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['published_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('version_id'),
        sa.UniqueConstraint('plan_id', 'version_number', name='uq_monitoring_plan_version')
    )
    op.create_index('idx_mpv_plan_id', 'monitoring_plan_versions', ['plan_id'])
    op.create_index('idx_mpv_is_active', 'monitoring_plan_versions', ['is_active'])

    # 2. Create monitoring_plan_metric_snapshots table
    op.create_table(
        'monitoring_plan_metric_snapshots',
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('original_metric_id', sa.Integer(), nullable=True),
        sa.Column('kpm_id', sa.Integer(), nullable=False),
        # Threshold snapshot
        sa.Column('yellow_min', sa.Float(), nullable=True),
        sa.Column('yellow_max', sa.Float(), nullable=True),
        sa.Column('red_min', sa.Float(), nullable=True),
        sa.Column('red_max', sa.Float(), nullable=True),
        sa.Column('qualitative_guidance', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        # KPM metadata snapshot
        sa.Column('kpm_name', sa.String(200), nullable=False),
        sa.Column('kpm_category_name', sa.String(200), nullable=True),
        sa.Column('evaluation_type', sa.String(50), nullable=False, server_default="'Quantitative'"),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['monitoring_plan_versions.version_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kpm_id'], ['kpms.kpm_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('snapshot_id'),
        sa.UniqueConstraint('version_id', 'kpm_id', name='uq_version_kpm')
    )
    op.create_index('idx_mpms_version_id', 'monitoring_plan_metric_snapshots', ['version_id'])

    # 3. Add version tracking columns to monitoring_cycles
    op.add_column('monitoring_cycles', sa.Column(
        'plan_version_id', sa.Integer(), nullable=True,
        comment='Version of monitoring plan this cycle is bound to (locked at DATA_COLLECTION start)'
    ))
    op.add_column('monitoring_cycles', sa.Column(
        'version_locked_at', sa.DateTime(), nullable=True,
        comment='When the version was locked for this cycle'
    ))
    op.add_column('monitoring_cycles', sa.Column(
        'version_locked_by_user_id', sa.Integer(), nullable=True
    ))
    op.create_foreign_key(
        'fk_monitoring_cycles_plan_version',
        'monitoring_cycles', 'monitoring_plan_versions',
        ['plan_version_id'], ['version_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_monitoring_cycles_version_locked_by',
        'monitoring_cycles', 'users',
        ['version_locked_by_user_id'], ['user_id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_mc_plan_version_id', 'monitoring_cycles', ['plan_version_id'])

    # 4. Add monitoring_plan_review_required to validation_policies
    op.add_column('validation_policies', sa.Column(
        'monitoring_plan_review_required', sa.Boolean(), nullable=False, server_default='false',
        comment='If true, component 9b (Performance Monitoring Plan Review) requires Planned or comment'
    ))
    op.add_column('validation_policies', sa.Column(
        'monitoring_plan_review_description', sa.Text(), nullable=True
    ))

    # 5. Add monitoring version fields to validation_plan_components
    op.add_column('validation_plan_components', sa.Column(
        'monitoring_plan_version_id', sa.Integer(), nullable=True,
        comment='For component 9b: which monitoring plan version was reviewed'
    ))
    op.add_column('validation_plan_components', sa.Column(
        'monitoring_review_notes', sa.Text(), nullable=True,
        comment='For component 9b: notes about the monitoring plan review'
    ))
    op.create_foreign_key(
        'fk_vpc_monitoring_plan_version',
        'validation_plan_components', 'monitoring_plan_versions',
        ['monitoring_plan_version_id'], ['version_id'],
        ondelete='SET NULL'
    )

    # 6. Backfill: Create v1 for all existing plans
    connection = op.get_bind()

    # Get all existing plans
    plans = connection.execute(text("SELECT plan_id FROM monitoring_plans")).fetchall()

    for (plan_id,) in plans:
        # Create v1 for each plan
        connection.execute(text("""
            INSERT INTO monitoring_plan_versions
            (plan_id, version_number, version_name, effective_date, is_active, published_at, created_at)
            VALUES (:plan_id, 1, 'Initial Version (Migrated)', CURRENT_DATE, TRUE, NOW(), NOW())
        """), {"plan_id": plan_id})

        # Get the version_id that was just created
        result = connection.execute(text(
            "SELECT version_id FROM monitoring_plan_versions WHERE plan_id = :plan_id AND version_number = 1"
        ), {"plan_id": plan_id})
        version_id = result.scalar()

        # Snapshot current metrics for this plan
        connection.execute(text("""
            INSERT INTO monitoring_plan_metric_snapshots
            (version_id, original_metric_id, kpm_id, yellow_min, yellow_max,
             red_min, red_max, qualitative_guidance, sort_order, is_active,
             kpm_name, kpm_category_name, evaluation_type, created_at)
            SELECT :version_id, m.metric_id, m.kpm_id, m.yellow_min, m.yellow_max,
                   m.red_min, m.red_max, m.qualitative_guidance, m.sort_order, m.is_active,
                   k.name, c.name, COALESCE(k.evaluation_type, 'Quantitative'), NOW()
            FROM monitoring_plan_metrics m
            JOIN kpms k ON m.kpm_id = k.kpm_id
            LEFT JOIN kpm_categories c ON k.category_id = c.category_id
            WHERE m.plan_id = :plan_id
        """), {"version_id": version_id, "plan_id": plan_id})

    # 7. Backfill: Link existing active cycles to v1
    connection.execute(text("""
        UPDATE monitoring_cycles c
        SET plan_version_id = v.version_id,
            version_locked_at = c.created_at
        FROM monitoring_plan_versions v
        WHERE c.plan_id = v.plan_id
        AND v.version_number = 1
        AND c.status NOT IN ('PENDING', 'CANCELLED')
        AND c.plan_version_id IS NULL
    """))


def downgrade() -> None:
    # Drop foreign key constraints first
    op.drop_constraint('fk_vpc_monitoring_plan_version', 'validation_plan_components', type_='foreignkey')
    op.drop_constraint('fk_monitoring_cycles_version_locked_by', 'monitoring_cycles', type_='foreignkey')
    op.drop_constraint('fk_monitoring_cycles_plan_version', 'monitoring_cycles', type_='foreignkey')

    # Drop columns from validation_plan_components
    op.drop_column('validation_plan_components', 'monitoring_review_notes')
    op.drop_column('validation_plan_components', 'monitoring_plan_version_id')

    # Drop columns from validation_policies
    op.drop_column('validation_policies', 'monitoring_plan_review_description')
    op.drop_column('validation_policies', 'monitoring_plan_review_required')

    # Drop columns from monitoring_cycles
    op.drop_index('idx_mc_plan_version_id', 'monitoring_cycles')
    op.drop_column('monitoring_cycles', 'version_locked_by_user_id')
    op.drop_column('monitoring_cycles', 'version_locked_at')
    op.drop_column('monitoring_cycles', 'plan_version_id')

    # Drop tables
    op.drop_index('idx_mpms_version_id', 'monitoring_plan_metric_snapshots')
    op.drop_table('monitoring_plan_metric_snapshots')

    op.drop_index('idx_mpv_is_active', 'monitoring_plan_versions')
    op.drop_index('idx_mpv_plan_id', 'monitoring_plan_versions')
    op.drop_table('monitoring_plan_versions')
