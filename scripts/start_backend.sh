#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Context-Aware Translation Backend Services...${NC}"

# Start Redis
echo -e "${YELLOW}Starting Redis server...${NC}"
redis-server --daemonize yes

# Check if Redis started successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis server started${NC}"
else
    echo -e "${RED}Failed to start Redis. Please check if Redis is installed.${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Kill any existing Celery workers
echo -e "${YELLOW}Stopping any existing Celery workers...${NC}"
pkill -f "celery.*backend.celery_app" 2>/dev/null

# Load environment variables
echo -e "${YELLOW}Loading environment variables...${NC}"
if [ -f backend/.env ]; then
  set -a
  . backend/.env
  set +a
  echo -e "${GREEN}✓ Loaded backend/.env${NC}"
elif [ -f .env ]; then
  set -a
  . .env
  set +a
  echo -e "${GREEN}✓ Loaded .env${NC}"
else
  echo -e "${YELLOW}No .env file found. Using environment defaults.${NC}"
fi

# Start Celery worker (background, stream logs to this terminal like Railway)
echo -e "${YELLOW}Starting Celery worker (logs will stream here)...${NC}"
CELERY_LOGLEVEL=${CELERY_LOGLEVEL:-info}
CELERY_QUEUES=${CELERY_QUEUES:-translation,validation,post_edit,illustrations,events,maintenance,default}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-1}
celery -A backend.celery_app worker \
  --loglevel="${CELERY_LOGLEVEL}" \
  --concurrency="${CELERY_CONCURRENCY}" \
  --queues="${CELERY_QUEUES}" &
CELERY_PID=$!

# Check if Celery started successfully
sleep 2
if pgrep -f "celery.*backend.celery_app" > /dev/null; then
    echo -e "${GREEN}✓ Celery worker started (PID: ${CELERY_PID})${NC}"
else
    echo -e "${RED}Failed to start Celery worker. See output above for details.${NC}"
    exit 1
fi

# Ensure background Celery/Redis are stopped when this script exits
cleanup() {
  echo -e "${YELLOW}Stopping Celery worker and Redis...${NC}"
  if [ -n "${CELERY_PID}" ] && ps -p ${CELERY_PID} > /dev/null 2>&1; then
    kill ${CELERY_PID} 2>/dev/null || true
  fi
  pkill -f "celery.*backend.celery_app" 2>/dev/null || true
  redis-cli shutdown 2>/dev/null || true
}
trap cleanup EXIT

## Start uvicorn (foreground so both logs appear in this terminal)
echo -e "${YELLOW}Starting FastAPI server on port 8000...${NC}"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
