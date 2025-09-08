"""Add status and last_error columns to outbox_events

Revision ID: 8fadd0f0d9a2
Revises: fix_outbox_occurred_at
Create Date: 2025-09-08 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fadd0f0d9a2'
down_revision: Union[str, Sequence[str], None] = 'fix_outbox_occurred_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to match OutboxEvent model."""
    # Add status column if not exists
    try:
        op.add_column('outbox_events', sa.Column('status', sa.String(), nullable=True))
    except Exception:
        # Column may already exist
        pass

    # Backfill status with 'pending' where NULL
    try:
        op.execute("UPDATE outbox_events SET status = 'pending' WHERE status IS NULL")
    except Exception:
        pass

    # Add last_error column if not exists
    try:
        op.add_column('outbox_events', sa.Column('last_error', sa.Text(), nullable=True))
    except Exception:
        pass

    # Create index on status for faster queries
    try:
        op.create_index(op.f('ix_outbox_events_status'), 'outbox_events', ['status'], unique=False)
    except Exception:
        # Index may already exist
        pass


def downgrade() -> None:
    """Revert schema changes."""
    # Drop index if exists
    try:
        op.drop_index(op.f('ix_outbox_events_status'), table_name='outbox_events')
    except Exception:
        pass

    # Drop columns (SQLite supports drop column in recent versions; ignore if not supported)
    try:
        op.drop_column('outbox_events', 'last_error')
    except Exception:
        pass
    try:
        op.drop_column('outbox_events', 'status')
    except Exception:
        pass

