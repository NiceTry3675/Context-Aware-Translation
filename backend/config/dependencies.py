"""Common dependencies for FastAPI routes."""

import os
from fastapi import Depends, Header, HTTPException

from .. import auth
from .db import get_db

def verify_admin_secret(x_admin_secret: str = Header(None)):
    """Verify admin secret key for admin endpoints."""
    # Try ADMIN_SECRET_KEY first (production), fallback to DEV_SECRET_KEY (local dev)
    ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY")
    DEV_SECRET_KEY = os.environ.get("DEV_SECRET_KEY", "dev-secret-key")

    # Use ADMIN_SECRET_KEY if available, otherwise DEV_SECRET_KEY
    valid_key = ADMIN_SECRET_KEY if ADMIN_SECRET_KEY else DEV_SECRET_KEY

    if x_admin_secret is None or x_admin_secret != valid_key:
        raise HTTPException(status_code=403, detail="Invalid or missing admin secret key")


# Re-export auth dependencies for convenience
get_required_user = auth.get_required_user
get_optional_user = auth.get_optional_user
is_admin = auth.is_admin
is_admin_sync = auth.is_admin_sync