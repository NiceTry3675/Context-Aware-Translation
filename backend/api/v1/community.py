"""Community board API endpoints - thin router layer."""

from fastapi import APIRouter

# Import the domain router directly
from ...domains.community.routes import router as domain_router

# Export the domain router as the API router
# The domain router already has all the endpoints implemented
router = domain_router