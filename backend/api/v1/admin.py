"""Admin API endpoints - thin wrapper for domain routes."""

from fastapi import APIRouter

from ...domains.admin.routes import router as admin_domain_router

# Create a new router that will re-mount the domain router with the correct prefix
router = APIRouter(prefix="/api/v1", tags=["admin"])

# Include all domain admin routes
# Note: The domain router has prefix="/admin", so endpoints will be at /api/v1/admin/*
router.include_router(admin_domain_router)

# For backward compatibility, also expose legacy endpoints at their original paths
# These will redirect to the new domain endpoints