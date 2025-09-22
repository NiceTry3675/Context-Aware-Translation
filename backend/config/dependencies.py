"""Common dependencies for FastAPI routes."""

import os
from fastapi import Depends, Header, HTTPException

from .. import auth
from .db import get_db

def verify_admin_secret(x_admin_secret: str = Header(None)):
    """Verify admin secret key for admin endpoints."""
    DEV_SECRET_KEY = os.environ.get("DEV_SECRET_KEY", "dev-secret-key")
    if x_admin_secret is None or x_admin_secret != DEV_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing admin secret key")


# Re-export auth dependencies for convenience
get_required_user = auth.get_required_user
get_optional_user = auth.get_optional_user
is_admin = auth.is_admin
is_admin_sync = auth.is_admin_sync