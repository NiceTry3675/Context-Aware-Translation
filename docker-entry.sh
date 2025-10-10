#!/bin/sh
set -e

echo "[entry] Starting backend container"

# Defaults
: "${START_CELERY_WORKER:=true}"
: "${START_CELERY_BEAT:=false}"
: "${ENABLE_LOCAL_REDIS:=auto}"  # auto|true|false
: "${REDIS_URL:=}"
: "${CELERY_AUTOSCALE:=}"
# Keep glibc thread arenas small to reduce RSS on multithreaded workers
export MALLOC_ARENA_MAX=${MALLOC_ARENA_MAX:-2}

# Default Celery worker sizing: prefer autoscale if provided, otherwise
# choose a sensible concurrency per environment (more aggressive in prod).
if [ -z "${CELERY_CONCURRENCY}" ]; then
  if [ "${APP_ENV:-development}" = "production" ]; then
    CELERY_CONCURRENCY=20
  else
    CELERY_CONCURRENCY=1
  fi
fi

# Start local Redis if requested or if REDIS_URL is empty/localhost
start_local_redis=false
if [ "$ENABLE_LOCAL_REDIS" = "true" ]; then
  start_local_redis=true
elif [ "$ENABLE_LOCAL_REDIS" = "auto" ]; then
  if [ -z "$REDIS_URL" ]; then
    start_local_redis=true
    REDIS_URL="redis://127.0.0.1:6379/0"
    export REDIS_URL
  else
    # Parse host from REDIS_URL
    host="$(python - <<'PY'
import os
from urllib.parse import urlparse
u=os.environ.get('REDIS_URL','')
print(urlparse(u).hostname or '')
PY
)"
    if [ "$host" = "localhost" ] || [ "$host" = "127.0.0.1" ]; then
      start_local_redis=true
    fi
  fi
fi

if [ "$start_local_redis" = true ]; then
  echo "[entry] Starting local Redis server"
  redis-server --daemonize yes --bind 127.0.0.1 --port 6379 || true
  # Wait for Redis
  ATTEMPTS=0; MAX=10
  until redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; do
    ATTEMPTS=$((ATTEMPTS+1))
    if [ $ATTEMPTS -ge $MAX ]; then
      echo "[entry] Redis did not become ready in time; continuing"
      break
    fi
    echo "[entry] Waiting for Redis ($ATTEMPTS/$MAX)"
    sleep 1
  done
fi

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

# Run migrations once (best effort)
echo "[entry] Running Alembic upgrade head"
alembic -c backend/alembic.ini upgrade head || echo "[entry] Alembic upgrade failed (continuing)"

# Start Celery processes if enabled
if [ "$START_CELERY_WORKER" = "true" ]; then
  if [ -n "$CELERY_AUTOSCALE" ]; then
    echo "[entry] Celery autoscale is not supported with the threads pool; ignoring CELERY_AUTOSCALE=${CELERY_AUTOSCALE}"
    unset CELERY_AUTOSCALE
  fi
  echo "[entry] Starting Celery worker (threads pool, concurrency=${CELERY_CONCURRENCY})"
  C_FORCE_ROOT=true celery -A backend.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY}" \
    --queues=translation,validation,post_edit,illustrations,events,maintenance,default \
    --pool=threads &
fi

if [ "$START_CELERY_BEAT" = "true" ]; then
  echo "[entry] Starting Celery beat"
  celery -A backend.celery_app beat --loglevel=info &
fi

echo "[entry] Starting Uvicorn"
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
