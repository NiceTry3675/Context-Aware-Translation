"""add_performance_indexes_to_translation_jobs

Revision ID: 292087d8217d
Revises: 3b94540a3854
Create Date: 2025-09-30 20:56:46.721144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '292087d8217d'
down_revision: Union[str, Sequence[str], None] = '3b94540a3854'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance-critical indexes to translation_jobs table."""
    # Composite index for status + created_at (common filter pattern)
    op.create_index(
        'ix_translation_jobs_status_created_at',
        'translation_jobs',
        ['status', 'created_at'],
        unique=False
    )
    
    # Index on owner_id for user-specific queries
    op.create_index(
        'ix_translation_jobs_owner_id',
        'translation_jobs',
        ['owner_id'],
        unique=False
    )
    
    # Index on created_at for time-based queries
    op.create_index(
        'ix_translation_jobs_created_at',
        'translation_jobs',
        ['created_at'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('ix_translation_jobs_created_at', table_name='translation_jobs')
    op.drop_index('ix_translation_jobs_owner_id', table_name='translation_jobs')
    op.drop_index('ix_translation_jobs_status_created_at', table_name='translation_jobs')
