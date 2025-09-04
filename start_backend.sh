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

# Set environment variables from backend/.env
echo -e "${YELLOW}Loading environment variables...${NC}"
export $(cat backend/.env | grep -v '^#' | xargs)

# Start Celery worker from project root with full module path
echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A backend.celery_app worker --loglevel=info --queues=translation,validation,post_edit,default --detach

# Check if Celery started successfully
sleep 2
if pgrep -f "celery.*backend.celery_app" > /dev/null; then
    echo -e "${GREEN}✓ Celery worker started${NC}"
else
    echo -e "${RED}Warning: Celery worker may not have started properly${NC}"
    echo -e "${YELLOW}Trying to start Celery in foreground for debugging...${NC}"
    # Try to show more detailed error
    celery -A backend.celery_app worker --loglevel=debug --queues=translation,validation,post_edit,default &
    sleep 3
    if ! pgrep -f "celery.*backend.celery_app" > /dev/null; then
        echo -e "${RED}Failed to start Celery. Check if backend/.env has all required variables.${NC}"
    fi
fi

# Start uvicorn
echo -e "${YELLOW}Starting FastAPI server on port 8000...${NC}"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000