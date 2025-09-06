"""
FastAPI application entry point.

This is a clean, modular entry point that sets up the FastAPI application
with middleware, routers, and static files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load environment variables first
load_dotenv()

# Import configuration
from .config import get_settings

# Import main API router
from .api.v1 import router as api_v1_router
from .api.v1 import schemas  # Keep schemas separate for special handling

# Get settings instance
settings = get_settings()

# Note: Database migrations are now handled by Alembic
# Run `cd backend && alembic upgrade head` to apply migrations

# Auto initialization (categories, etc.)
try:
    from . import auto_init
    auto_init.run_auto_init()
except Exception as e:
    print(f"❌ Auto initialization error: {e}")
    # Continue running even if initialization fails

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered literary translation service with context awareness",
    version=settings.app_version,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Create uploads directory if it doesn't exist (handled by settings validator)
# The upload directory is already created by the settings validator

# Mount static files for serving uploaded images
upload_path = Path(settings.upload_directory)
if upload_path.exists():
    app.mount("/static", StaticFiles(directory=str(upload_path)), name="static")

# Include routers
app.include_router(api_v1_router)  # All v1 API routes
app.include_router(schemas.router)  # Schema endpoint (for OpenAPI schema export)

# Root endpoint
@app.get("/")
def read_root():
    """Health check endpoint."""
    return {
        "message": "Translation Service Backend is running!",
        "version": settings.app_version,
        "environment": settings.environment
    }