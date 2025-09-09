#!/bin/sh
set -e

echo "[entry] Starting backend container"

# Wait for DB to be reachable (few quick retries)
MAX_ATTEMPTS=3
SLEEP_SECONDS=3
ATTEMPT=1
echo "[entry] Waiting for database connectivity"
until python - <<'PY'
from sqlalchemy import text
from backend.config.database import engine
with engine.connect() as c:
    c.execute(text('SELECT 1'))
PY
do
  if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
    echo "[entry] Database not reachable after $ATTEMPT attempts. Proceeding; migrations may fail."
    break
  fi
  echo "[entry] DB not ready (attempt $ATTEMPT). Retrying in ${SLEEP_SECONDS}s..."
  ATTEMPT=$((ATTEMPT+1))
  sleep $SLEEP_SECONDS
done

# Bootstrap alembic if schema exists without alembic_version
echo "[entry] Bootstrapping Alembic version table if needed"
python -m backend.scripts.bootstrap_migrations || true

# Run migrations once
echo "[entry] Running Alembic upgrade head"
if ! alembic -c backend/alembic.ini upgrade head; then
  echo "[entry] Alembic upgrade failed. Starting app anyway (schema may be outdated)."
fi

echo "[entry] Starting Uvicorn"
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
