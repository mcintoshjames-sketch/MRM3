"""rename_pending_to_draft_row_approval_status

Revision ID: 671ed8be0fa4
Revises: mrsa001_add_mrsa_irp
Create Date: 2025-12-13 13:04:31.185405

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '671ed8be0fa4'
down_revision: Union[str, None] = 'mrsa001_add_mrsa_irp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update existing 'pending' row_approval_status values to 'Draft'
    op.execute("UPDATE models SET row_approval_status = 'Draft' WHERE row_approval_status = 'pending'")


def downgrade() -> None:
    # Revert 'Draft' row_approval_status values back to 'pending'
    op.execute("UPDATE models SET row_approval_status = 'pending' WHERE row_approval_status = 'Draft'")
