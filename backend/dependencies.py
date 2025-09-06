"""Common dependencies for FastAPI routes."""

import os
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal
from . import auth


def get_db():
    """Dependency to get a database session for a single request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin_secret(x_admin_secret: str = Header(...)):
    """Verify admin secret key for admin endpoints."""
    ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-secret-key")
    if x_admin_secret != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin secret key")


# Re-export auth dependencies for convenience
get_required_user = auth.get_required_user
get_optional_user = auth.get_optional_user
is_admin = auth.is_admin
is_admin_sync = auth.is_admin_sync