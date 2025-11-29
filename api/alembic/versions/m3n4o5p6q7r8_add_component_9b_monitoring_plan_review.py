"""Add component 9b Performance Monitoring Plan Review

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2025-11-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.core.time import utc_now

# revision identifiers, used by Alembic.
revision: str = 'm3n4o5p6q7r8'
down_revision: Union[str, None] = 'l2m3n4o5p6q7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add component 9b for Performance Monitoring Plan Review."""

    # Update sort_order for existing components 10 and 11 to make room for 9b
    op.execute("""
        UPDATE validation_component_definitions
        SET sort_order = sort_order + 1
        WHERE component_code IN ('10', '11')
    """)

    # Insert component 9b
    op.execute(f"""
        INSERT INTO validation_component_definitions (
            section_number, section_title, component_code, component_title,
            is_test_or_analysis, expectation_high, expectation_medium,
            expectation_low, expectation_very_low, sort_order, is_active,
            created_at, updated_at
        ) VALUES (
            '9', 'Model Performance Monitoring Requirements', '9b',
            'Performance Monitoring Plan Review',
            false, 'Required', 'Required', 'IfApplicable', 'NotExpected',
            29, true, '{utc_now().isoformat()}', '{utc_now().isoformat()}'
        )
        ON CONFLICT (component_code) DO NOTHING
    """)

    # Also add to component_definition_config_items if a configuration exists
    # This snapshots the new component for existing configurations
    op.execute("""
        INSERT INTO component_definition_config_items (
            config_id, component_id, section_number, section_title,
            component_code, component_title, is_test_or_analysis,
            expectation_high, expectation_medium, expectation_low,
            expectation_very_low, sort_order, is_active
        )
        SELECT
            c.config_id,
            vcd.component_id,
            vcd.section_number,
            vcd.section_title,
            vcd.component_code,
            vcd.component_title,
            vcd.is_test_or_analysis,
            vcd.expectation_high,
            vcd.expectation_medium,
            vcd.expectation_low,
            vcd.expectation_very_low,
            vcd.sort_order,
            vcd.is_active
        FROM component_definition_configurations c
        CROSS JOIN validation_component_definitions vcd
        WHERE vcd.component_code = '9b'
        AND NOT EXISTS (
            SELECT 1 FROM component_definition_config_items ci
            WHERE ci.config_id = c.config_id AND ci.component_code = '9b'
        )
    """)


def downgrade() -> None:
    """Remove component 9b."""

    # Remove from config items first
    op.execute("""
        DELETE FROM component_definition_config_items
        WHERE component_code = '9b'
    """)

    # Remove component 9b
    op.execute("""
        DELETE FROM validation_component_definitions
        WHERE component_code = '9b'
    """)

    # Restore original sort_order for components 10 and 11
    op.execute("""
        UPDATE validation_component_definitions
        SET sort_order = sort_order - 1
        WHERE component_code IN ('10', '11')
    """)
