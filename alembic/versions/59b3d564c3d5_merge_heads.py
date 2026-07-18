"""Merge heads

Revision ID: 59b3d564c3d5
Revises: 2ca9432c7e18, 2f88a38e6db2
Create Date: 2026-07-18 23:56:49.909447

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59b3d564c3d5'
down_revision: Union[str, Sequence[str], None] = ('2ca9432c7e18', '2f88a38e6db2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
