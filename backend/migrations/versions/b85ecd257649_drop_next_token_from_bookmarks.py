"""drop next_token from bookmarks

Revision ID: b85ecd257649
Revises: a8793833394f
Create Date: 2026-04-15 13:39:00.614511

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b85ecd257649"
down_revision: Union[str, Sequence[str], None] = "a8793833394f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("bookmarks", "next_token")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "bookmarks",
        sa.Column("next_token", sa.String(), nullable=False, server_default=""),
    )
