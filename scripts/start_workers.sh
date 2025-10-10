#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Celery Workers for Translation Processing...${NC}"

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Reduce glibc arena fragmentation to keep RSS lower on multithreaded workers
export MALLOC_ARENA_MAX=${MALLOC_ARENA_MAX:-2}

# Check if Redis is running
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Redis is not running. Please start Redis first with: ./start_backend.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Start Celery worker
echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A backend.celery_app worker --loglevel=info --pool=threads
