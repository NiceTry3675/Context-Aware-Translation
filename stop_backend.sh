#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Backend Services...${NC}"

# Stop Celery workers
echo -e "${YELLOW}Stopping Celery workers...${NC}"
pkill -f "celery -A backend.celery_app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Celery workers stopped${NC}"
else
    echo -e "${YELLOW}No Celery workers were running${NC}"
fi

# Stop uvicorn
echo -e "${YELLOW}Stopping uvicorn...${NC}"
pkill -f "uvicorn backend.main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Uvicorn stopped${NC}"
else
    echo -e "${YELLOW}No uvicorn processes were running${NC}"
fi

# Stop Redis
echo -e "${YELLOW}Stopping Redis server...${NC}"
redis-cli shutdown 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis server stopped${NC}"
else
    echo -e "${YELLOW}Redis was not running${NC}"
fi

echo -e "${GREEN}All backend services stopped.${NC}"