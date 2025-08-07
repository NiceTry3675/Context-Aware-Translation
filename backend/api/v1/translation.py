"""Translation API router aggregator.

This module combines all translation-related routers for better code organization.
"""

from fastapi import APIRouter

# Import sub-routers
from . import analysis, jobs, downloads, validation_routes, post_edit_routes

# Create main router
router = APIRouter(prefix="/api/v1")

# Include all sub-routers
router.include_router(analysis.router)
router.include_router(jobs.router)
router.include_router(downloads.router)
router.include_router(validation_routes.router)
router.include_router(post_edit_routes.router)