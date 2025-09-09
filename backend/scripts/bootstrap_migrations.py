"""
Bootstrap Alembic versioning for environments where tables exist
but the alembic_version table has not been initialized.

Logic:
- If alembic_version table exists: do nothing.
- If alembic_version missing and known initial tables exist: stamp to initial revision.
- Else: do nothing (fresh DB), regular upgrade will create everything.
"""
from sqlalchemy import inspect
from alembic import command
from alembic.config import Config

from backend.config.database import engine


INITIAL_REVISION = "391a749ff797"  # init


def main() -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())

    # If alembic_version table present, nothing to do
    if "alembic_version" in tables:
        return

    # Detect if DB was created outside Alembic (tables exist already)
    sentinel_tables = {"announcements", "translation_jobs", "users"}
    if tables.intersection(sentinel_tables):
        cfg = Config("backend/alembic.ini")
        # Stamp to initial known revision so subsequent upgrade works
        command.stamp(cfg, INITIAL_REVISION)


if __name__ == "__main__":
    main()

