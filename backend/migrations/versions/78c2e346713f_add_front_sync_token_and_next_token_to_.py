"""add_front_sync_token_and_next_token_to_users

Revision ID: 78c2e346713f
Revises: 4b9649897d8c
Create Date: 2026-04-14 23:45:29.788687

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "78c2e346713f"
down_revision: Union[str, Sequence[str], None] = "4b9649897d8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("front_sync_token", sa.String(), nullable=True))
    op.add_column("users", sa.Column("next_token", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    pass
