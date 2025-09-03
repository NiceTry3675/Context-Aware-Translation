"""Add task execution table for Celery

Revision ID: 31c08441cdc2
Revises: 5e0cb3120dcb
Create Date: 2025-09-03 14:36:07.425695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '31c08441cdc2'
down_revision: Union[str, Sequence[str], None] = '5e0cb3120dcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create TaskStatus enum
    task_status_enum = postgresql.ENUM(
        'pending', 'started', 'retry', 'success', 'failure', 'revoked',
        name='taskstatus'
    )
    task_status_enum.create(op.get_bind())
    
    # Create TaskKind enum
    task_kind_enum = postgresql.ENUM(
        'translation', 'validation', 'post_edit', 'illustration', 
        'event_processing', 'maintenance', 'other',
        name='taskkind'
    )
    task_kind_enum.create(op.get_bind())
    
    # Create task_executions table
    op.create_table('task_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('kind', task_kind_enum, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('status', task_status_enum, nullable=False),
        sa.Column('args', sa.JSON(), nullable=True),
        sa.Column('kwargs', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=True, default=3),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('queue_time', sa.DateTime(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['translation_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_task_executions_job_id', 'task_executions', ['job_id'])
    op.create_index('idx_task_executions_status', 'task_executions', ['status'])
    op.create_index('idx_task_executions_kind', 'task_executions', ['kind'])
    op.create_index('idx_task_executions_created_at', 'task_executions', ['created_at'])
    op.create_index('idx_task_executions_user_id', 'task_executions', ['user_id'])
    op.create_index('idx_task_executions_status_kind', 'task_executions', ['status', 'kind'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_task_executions_status_kind', table_name='task_executions')
    op.drop_index('idx_task_executions_user_id', table_name='task_executions')
    op.drop_index('idx_task_executions_created_at', table_name='task_executions')
    op.drop_index('idx_task_executions_kind', table_name='task_executions')
    op.drop_index('idx_task_executions_status', table_name='task_executions')
    op.drop_index('idx_task_executions_job_id', table_name='task_executions')
    
    # Drop table
    op.drop_table('task_executions')
    
    # Drop enums
    task_status_enum = postgresql.ENUM('pending', 'started', 'retry', 'success', 'failure', 'revoked', name='taskstatus')
    task_status_enum.drop(op.get_bind())
    
    task_kind_enum = postgresql.ENUM('translation', 'validation', 'post_edit', 'illustration', 'event_processing', 'maintenance', 'other', name='taskkind')
    task_kind_enum.drop(op.get_bind())
