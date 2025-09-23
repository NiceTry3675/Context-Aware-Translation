"""Change translation_usage_logs.job_id foreign key to ON DELETE SET NULL

Revision ID: c3a7c1b2d4e5
Revises: fix_outbox_occurred_at
Create Date: 2025-09-23 10:00:00.000000

"""
from typing import Sequence, Union, Optional

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a7c1b2d4e5'
down_revision: Union[str, Sequence[str], None] = 'fix_outbox_occurred_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _find_job_fk_name(bind) -> Optional[str]:
    inspector = sa.inspect(bind)
    fks = inspector.get_foreign_keys('translation_usage_logs')
    for fk in fks:
        referred_table = fk.get('referred_table')
        constrained_columns = fk.get('constrained_columns') or []
        if referred_table == 'translation_jobs' and 'job_id' in constrained_columns:
            return fk.get('name')
    # Common default name in Postgres if created without explicit name
    return 'translation_usage_logs_job_id_fkey'


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        # SQLite: altering FK requires table recreation; skip (dev DB keeps app-level safeguard)
        return

    fk_name = _find_job_fk_name(bind)

    with op.batch_alter_table('translation_usage_logs') as batch_op:
        try:
            batch_op.drop_constraint(fk_name, type_='foreignkey')
        except Exception:
            # If drop fails due to name mismatch, attempt best-effort known default
            if fk_name != 'translation_usage_logs_job_id_fkey':
                try:
                    batch_op.drop_constraint('translation_usage_logs_job_id_fkey', type_='foreignkey')
                except Exception:
                    # Give up silently; creation below may still succeed if no FK existed
                    pass
        batch_op.create_foreign_key(
            'fk_translation_usage_logs_job_id',
            'translation_jobs',
            ['job_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        return

    with op.batch_alter_table('translation_usage_logs') as batch_op:
        try:
            batch_op.drop_constraint('fk_translation_usage_logs_job_id', type_='foreignkey')
        except Exception:
            pass
        batch_op.create_foreign_key(
            'translation_usage_logs_job_id_fkey',
            'translation_jobs',
            ['job_id'],
            ['id'],
        )


