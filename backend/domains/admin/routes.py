"""Admin domain API routes - thin routing layer."""

from typing import List, Optional

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.community.models import Announcement
from backend.domains.user.schemas import AnnouncementCreate
from backend.domains.admin.policy import Permission, enforce_permission
from backend.domains.user.service import UserService
from backend.domains.community.service import CommunityService
from backend.config.settings import get_settings


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get user service."""
    return UserService(db)


def get_community_service(db: Session = Depends(get_db)) -> CommunityService:
    """Dependency to get community service."""
    return CommunityService(db)


# Dependency to verify admin secret key (legacy support)
async def verify_admin_secret(
    admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret")
) -> bool:
    """Verify admin secret key from header (deprecated, use RBAC instead)."""
    settings = get_settings()
    if settings.admin_secret_key and admin_secret == settings.admin_secret_key:
        return True
    return False


async def delete_any_post(
    post_id: int,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Delete any post (requires POST_DELETE_ANY permission)."""
    try:
        enforce_permission(current_user, Permission.POST_DELETE_ANY)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    try:
        await service.delete_post(post_id, current_user)
        return {"message": f"Post {post_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def create_announcement(
    announcement: AnnouncementCreate,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service),
    db: Session = Depends(get_db)
):
    """Create a new announcement (requires ANNOUNCEMENT_CREATE permission)."""
    try:
        enforce_permission(current_user, Permission.ANNOUNCEMENT_CREATE)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    # Deactivate all other announcements first
    service.deactivate_all_announcements()
    
    # Create the new announcement
    db_announcement = Announcement(**announcement.dict())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    
    return UserService.format_announcement_for_json(db_announcement)