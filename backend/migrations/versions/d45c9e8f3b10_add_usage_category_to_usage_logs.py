"""Add usage_category to translation usage logs

Revision ID: d45c9e8f3b10
Revises: 1b2d3f4a1c7b, c3a7c1b2d4e5
Create Date: 2025-09-10 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d45c9e8f3b10"
down_revision: Union[str, Sequence[str], None] = ("1b2d3f4a1c7b", "c3a7c1b2d4e5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding usage_category column."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        existing_columns = {
            row[1] for row in bind.execute(sa.text("PRAGMA table_info('translation_usage_logs')"))
        }
        if "usage_category" not in existing_columns:
            op.execute(
                sa.text(
                    "ALTER TABLE translation_usage_logs ADD COLUMN usage_category VARCHAR DEFAULT 'translation'"
                )
            )
    else:
        with op.batch_alter_table("translation_usage_logs") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "usage_category",
                    sa.String(),
                    nullable=False,
                    server_default="translation",
                )
            )
        op.execute(
            sa.text(
                "UPDATE translation_usage_logs SET usage_category = 'translation' WHERE usage_category IS NULL"
            )
        )
        with op.batch_alter_table("translation_usage_logs") as batch_op:
            batch_op.alter_column("usage_category", server_default=None)

    op.create_index(
        "ix_translation_usage_logs_usage_category",
        "translation_usage_logs",
        ["usage_category"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema by dropping usage_category column."""
    op.drop_index(
        "ix_translation_usage_logs_usage_category",
        table_name="translation_usage_logs",
    )

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite cannot drop columns without complex workarounds; skip.
        return

    with op.batch_alter_table("translation_usage_logs") as batch_op:
        batch_op.drop_column("usage_category")
