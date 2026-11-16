"""make users.email unique

Revision ID: f8962e7d2d93
Revises: e4c3a61e677b
Create Date: 2026-11-16 18:08:47.216929

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f8962e7d2d93"
down_revision: Union[str, Sequence[str], None] = "e4c3a61e677b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE users SET email = lower(email)")
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_email", "users", type_="unique")
