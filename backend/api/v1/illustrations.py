"""Illustrations API endpoints - thin wrapper for domain routes."""

from fastapi import APIRouter

from ...domains.illustrations.routes import router as illustrations_domain_router

# Create a new router that will re-mount the domain router with the correct prefix
router = APIRouter(prefix="/api/v1", tags=["illustrations"])

# Include all domain illustration routes
# Note: The domain router has prefix="/illustrations", so endpoints will be at /api/v1/illustrations/*
router.include_router(illustrations_domain_router)