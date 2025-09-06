"""API v1 main router aggregation.

This module aggregates all v1 API routers for clean imports in main.py.
"""

from fastapi import APIRouter

# Import all sub-routers
from . import (
    admin,
    announcements, 
    community,
    illustrations,
    tasks,
    translation,
    webhooks
)

# Create main v1 router
router = APIRouter()

# Include all sub-routers
# Note: Most of these already have their own prefixes
router.include_router(admin.router)
router.include_router(announcements.router)
router.include_router(community.router)
router.include_router(illustrations.router)
router.include_router(tasks.router)
router.include_router(translation.router)
router.include_router(webhooks.router)

__all__ = ["router"]