"""
FastAPI application entry point.

This is a clean, modular entry point that sets up the FastAPI application
with middleware, routers, and static files.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load environment variables first
load_dotenv()

# Import routers
from .api.v1 import translation, community, admin, webhooks, announcements, schemas, illustrations

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
    title="Context-Aware Translation API",
    description="AI-powered literary translation service with context awareness",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://catrans.me",
        "https://www.catrans.me",
        "https://context-aware-translation.vercel.app",
        "https://context-aware-translation-git-dev-cat-rans.vercel.app",
        "https://context-aware-translation-git-main-cat-rans.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Mount static files for serving uploaded images
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Include routers
app.include_router(translation.router)
app.include_router(community.router)
app.include_router(admin.router)
app.include_router(webhooks.router)
app.include_router(announcements.router)
app.include_router(schemas.router)
app.include_router(illustrations.router, prefix="/api/v1/illustrations", tags=["illustrations"])

# Root endpoint
@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "Translation Service Backend is running!", "version": "1.0.0"}