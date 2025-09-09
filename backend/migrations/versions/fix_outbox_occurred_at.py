"""Add occurred_at column to outbox_events

Revision ID: fix_outbox_occurred_at
Revises: 31c08441cdc2
Create Date: 2025-09-07 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_outbox_occurred_at'
down_revision: Union[str, Sequence[str], None] = '31c08441cdc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add occurred_at column without default (SQLite limitation)
    op.add_column('outbox_events', sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True))
    
    # Update existing rows with current timestamp
    op.execute("UPDATE outbox_events SET occurred_at = CURRENT_TIMESTAMP WHERE occurred_at IS NULL")
    
    # Create index for status column if it doesn't exist
    try:
        op.create_index(op.f('ix_outbox_events_status'), 'outbox_events', ['status'], unique=False)
    except:
        pass
    
    # Note: We can't easily change aggregate_id from INTEGER to String in SQLite
    # This would require recreating the table. For now, we'll leave it as INTEGER.


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_index(op.f('ix_outbox_events_status'), table_name='outbox_events')
    except:
        pass
    op.drop_column('outbox_events', 'occurred_at')