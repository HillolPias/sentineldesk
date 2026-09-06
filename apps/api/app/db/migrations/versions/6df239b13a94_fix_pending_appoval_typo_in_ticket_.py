"""fix pending_appoval typo in ticket_status enum

Revision ID: 6df239b13a94
Revises: 3d7215b24183
Create Date: 2026-09-06 16:32:57.675763

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6df239b13a94"
down_revision: Union[str, Sequence[str], None] = "3d7215b24183"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE ticket_status RENAME VALUE 'pending_appoval' TO 'pending_approval'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TYPE ticket_status RENAME VALUE 'pending_approval' TO 'pending_appoval'"
    )
