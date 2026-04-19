"""drop next_token from bookmarks

Revision ID: a8793833394f
Revises: 78c2e346713f
Create Date: 2026-04-15 13:38:10.415717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8793833394f'
down_revision: Union[str, Sequence[str], None] = '78c2e346713f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
