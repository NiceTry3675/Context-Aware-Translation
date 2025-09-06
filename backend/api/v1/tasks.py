"""Task API endpoints - thin wrapper for domain routes."""

from fastapi import APIRouter

from ...domains.tasks.routes import router as tasks_domain_router

# Create a new router that will re-mount the domain router with the correct prefix
router = APIRouter(prefix="/api/v1", tags=["tasks"])

# Include all domain task routes
# Note: The domain router has prefix="/tasks", so endpoints will be at /api/v1/tasks/*
router.include_router(tasks_domain_router)