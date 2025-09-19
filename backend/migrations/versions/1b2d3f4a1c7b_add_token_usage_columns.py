"""Add token usage columns to translation usage logs"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1b2d3f4a1c7b'
down_revision = '8fadd0f0d9a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        existing_columns = {
            row[1] for row in bind.execute(sa.text("PRAGMA table_info('translation_usage_logs')"))
        }
        if 'user_id' not in existing_columns:
            op.execute(sa.text('ALTER TABLE translation_usage_logs ADD COLUMN user_id INTEGER'))
        if 'prompt_tokens' not in existing_columns:
            op.execute(sa.text('ALTER TABLE translation_usage_logs ADD COLUMN prompt_tokens INTEGER'))
        if 'completion_tokens' not in existing_columns:
            op.execute(sa.text('ALTER TABLE translation_usage_logs ADD COLUMN completion_tokens INTEGER'))
        if 'total_tokens' not in existing_columns:
            op.execute(sa.text('ALTER TABLE translation_usage_logs ADD COLUMN total_tokens INTEGER'))
        # SQLite doesn't support adding foreign keys after table creation easily; skip FK in dev.
    else:
        with op.batch_alter_table('translation_usage_logs') as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('prompt_tokens', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('completion_tokens', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('total_tokens', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_translation_usage_logs_user_id',
                'users',
                ['user_id'],
                ['id'],
                ondelete='SET NULL',
            )

    existing_indexes = {
        row[1] for row in bind.execute(sa.text("PRAGMA index_list('translation_usage_logs')"))
    }
    if 'ix_translation_usage_logs_user_id' not in existing_indexes:
        op.create_index(
            'ix_translation_usage_logs_user_id',
            'translation_usage_logs',
            ['user_id'],
            unique=False,
        )
    if 'ix_translation_usage_logs_model_used' not in existing_indexes:
        op.create_index(
            'ix_translation_usage_logs_model_used',
            'translation_usage_logs',
            ['model_used'],
            unique=False,
        )
    if 'ix_translation_usage_logs_created_at' not in existing_indexes:
        op.create_index(
            'ix_translation_usage_logs_created_at',
            'translation_usage_logs',
            ['created_at'],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index('ix_translation_usage_logs_created_at', table_name='translation_usage_logs')
    op.drop_index('ix_translation_usage_logs_model_used', table_name='translation_usage_logs')
    op.drop_index('ix_translation_usage_logs_user_id', table_name='translation_usage_logs')

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite cannot drop columns without complex workarounds; leave as-is.
        pass
    else:
        with op.batch_alter_table('translation_usage_logs') as batch_op:
            batch_op.drop_constraint('fk_translation_usage_logs_user_id', type_='foreignkey')
            batch_op.drop_column('total_tokens')
            batch_op.drop_column('completion_tokens')
            batch_op.drop_column('prompt_tokens')
            batch_op.drop_column('user_id')
