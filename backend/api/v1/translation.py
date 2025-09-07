"""Translation API router aggregator.

This module combines all translation-related routers for better code organization.
"""

from fastapi import APIRouter

# Import sub-routers
from . import analysis, jobs, downloads, validation, post_edit, export

# Create main router
router = APIRouter(prefix="/api/v1")

# Include all sub-routers
router.include_router(analysis.router)
router.include_router(jobs.router)
router.include_router(downloads.router)
router.include_router(validation.router)
router.include_router(post_edit.router)
router.include_router(export.router)