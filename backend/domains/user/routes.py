"""User domain API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user, get_optional_user
from backend.models.user import User
from backend.schemas.user import (
    UserResponse,
    UserUpdate,
    AnnouncementResponse,
    AnnouncementCreate,
    UsageLogResponse
)
from backend.domains.user.service import UserService


router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get user service."""
    return UserService(db)


# User profile endpoints

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_required_user)
):
    """Get the current user's profile."""
    return UserResponse.from_orm(current_user)


@router.get("/me/statistics")
def get_current_user_statistics(
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Get statistics for the current user."""
    return service.get_user_statistics(current_user.id)


@router.get("/me/usage", response_model=List[UsageLogResponse])
def get_current_user_usage(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Get API usage logs for the current user."""
    logs = service.get_user_usage_logs(current_user.id, limit)
    return [UsageLogResponse.from_orm(log) for log in logs]


@router.get("/me/usage-summary")
def get_current_user_usage_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Get usage summary for the current user."""
    return service.get_usage_summary(current_user.id, days)


# Admin user management endpoints

@router.get("/", response_model=List[UserResponse])
async def list_users(
    query: Optional[str] = Query(None, description="Search query"),
    role: Optional[str] = Query(None, description="Filter by role"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """List users (admin only)."""
    if not service.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = service.search_users(query, role, limit)
    return [UserResponse.from_orm(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Get a specific user's profile (admin only or self)."""
    # Users can view their own profile
    if user_id == current_user.id:
        return UserResponse.from_orm(current_user)
    
    # Otherwise must be admin
    if not service.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Update a user's role (admin only)."""
    try:
        user = await service.update_user_role(user_id, new_role, current_user)
        return {
            "message": f"User role updated to {new_role}",
            "user": UserResponse.from_orm(user)
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}/statistics")
def get_user_statistics(
    user_id: int,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Get statistics for a specific user (admin only)."""
    if not service.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return service.get_user_statistics(user_id)


# Announcement endpoints

@router.get("/announcements/active", response_model=List[AnnouncementResponse])
def get_active_announcements(
    service: UserService = Depends(get_user_service)
):
    """Get active announcements (public endpoint)."""
    announcements = service.get_announcements(active_only=True)
    return [AnnouncementResponse.from_orm(a) for a in announcements]


@router.get("/announcements/all", response_model=List[AnnouncementResponse])
def get_all_announcements(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Get all announcements including inactive (admin only)."""
    if not service.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    announcements = service.get_announcements(active_only=False, limit=limit)
    return [AnnouncementResponse.from_orm(a) for a in announcements]


@router.post("/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Create a new announcement (admin only)."""
    try:
        announcement = await service.create_announcement(
            message=announcement_data.message,
            is_active=announcement_data.is_active,
            admin_user=current_user
        )
        return AnnouncementResponse.from_orm(announcement)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    message: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Update an announcement (admin only)."""
    try:
        announcement = await service.update_announcement(
            announcement_id=announcement_id,
            message=message,
            is_active=is_active,
            admin_user=current_user
        )
        return AnnouncementResponse.from_orm(announcement)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service)
):
    """Delete an announcement (admin only)."""
    try:
        await service.delete_announcement(announcement_id, current_user)
        return {"message": "Announcement deleted successfully"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Clerk webhook endpoint

@router.post("/clerk/webhook")
async def handle_clerk_webhook(
    request: Request,
    service: UserService = Depends(get_user_service)
):
    """Handle Clerk webhook events."""
    # Get raw body for signature verification
    body = await request.body()
    headers = dict(request.headers)
    
    # Verify webhook signature
    if not service.verify_webhook_signature(body, headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse webhook data
    try:
        import json
        data = json.loads(body)
        event_type = data.get("type")
        
        # Handle the webhook event
        result = await service.handle_clerk_webhook(event_type, data)
        
        if result:
            return {"message": f"Webhook {event_type} processed successfully"}
        else:
            return {"message": f"Webhook {event_type} ignored"}
            
    except Exception as e:
        # Log error but return success to prevent retries
        print(f"Error processing webhook: {e}")
        return {"message": "Webhook received"}


# Legacy compatibility endpoints (will be deprecated)

@router.get("/api/v1/announcements", response_model=List[AnnouncementResponse])
def get_announcements_legacy(
    service: UserService = Depends(get_user_service)
):
    """Legacy endpoint for getting announcements."""
    announcements = service.get_announcements(active_only=True)
    return [AnnouncementResponse.from_orm(a) for a in announcements]