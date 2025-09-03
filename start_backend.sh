#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Context-Aware Translation Backend Services...${NC}"

# Start Redis
echo -e "${YELLOW}Starting Redis server...${NC}"
redis-server --daemonize yes

# Check if Redis started successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis server started${NC}"
else
    echo -e "${YELLOW}Failed to start Redis. Please check if Redis is installed.${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Start uvicorn
echo -e "${YELLOW}Starting FastAPI server on port 8000...${NC}"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000