# Backend Service Scripts

## Quick Start

```bash
# Start backend services (Redis + FastAPI)
./start_backend.sh

# In another terminal, start Celery workers (for translation jobs)
./start_workers.sh

# Stop all backend services
./stop_backend.sh
```

## Scripts

### `start_backend.sh`
Starts the core backend services:
- Redis server (in background)
- FastAPI/uvicorn server (port 8000)

### `start_workers.sh`
Starts Celery worker for background task processing:
- Required for translation jobs
- Run in separate terminal after starting backend

### `stop_backend.sh`
Cleanly stops all backend services:
- Celery workers
- Uvicorn server
- Redis server

## Notes

- Frontend (Next.js) should be started separately with `npm run dev` in the `frontend/` directory
- For production, consider using systemd services or Docker containers instead