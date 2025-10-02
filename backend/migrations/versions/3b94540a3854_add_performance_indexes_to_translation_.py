"""Add performance indexes to translation_jobs

Revision ID: 3b94540a3854
Revises: d45c9e8f3b10
Create Date: 2025-09-30 20:54:40.463142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b94540a3854'
down_revision: Union[str, Sequence[str], None] = 'd45c9e8f3b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
