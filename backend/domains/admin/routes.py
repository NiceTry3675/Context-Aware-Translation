"""Admin domain API routes with RBAC."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.community.models import Post, Comment, PostCategory
from backend.domains.translation.models import TranslationJob
from backend.domains.user.schemas import User as UserSchema, AnnouncementCreate
from backend.domains.community.schemas import PostList, Comment as CommentSchema, PostUpdate
from backend.domains.translation.schemas import TranslationJob as TranslationJobSchema
from backend.domains.admin.policy import (
    Permission,
    enforce_permission,
    require_admin,
    admin_policy
)
from backend.domains.user.service import UserService
from backend.domains.community.service import CommunityService
from backend.domains.community.repository import PostCategoryRepository
from backend.config.settings import get_settings
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/admin", tags=["admin"])


# Dependency to verify admin secret key (legacy support)
async def verify_admin_secret(
    admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret")
):
    """Verify admin secret key from header (deprecated, use RBAC instead)."""
    settings = get_settings()
    if settings.admin_secret_key and admin_secret == settings.admin_secret_key:
        return True
    return False


# User management endpoints

@router.get("/users", response_model=List[UserSchema])
def list_all_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """List all users (requires USER_VIEW permission)."""
    try:
        enforce_permission(current_user, Permission.USER_VIEW)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = UserService(db)
    users = service.search_users(search, role, limit)
    return [UserSchema.from_orm(u) for u in users]


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Change a user's role (requires USER_ROLE_CHANGE permission)."""
    try:
        enforce_permission(current_user, Permission.USER_ROLE_CHANGE)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = UserService(db)
    try:
        user = await service.update_user_role(user_id, new_role, current_user)
        return {
            "message": f"User role changed to {new_role}",
            "user": UserSchema.from_orm(user)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Delete a user (requires USER_DELETE permission)."""
    try:
        enforce_permission(current_user, Permission.USER_DELETE)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    # Implementation would go here
    raise HTTPException(status_code=501, detail="User deletion not implemented")


# Community moderation endpoints

@router.delete("/posts/{post_id}")
async def delete_any_post(
    post_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Delete any post (requires POST_DELETE_ANY permission)."""
    try:
        enforce_permission(current_user, Permission.POST_DELETE_ANY)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = CommunityService(db)
    try:
        await service.delete_post(post_id, current_user)
        return {"message": f"Post {post_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/posts/{post_id}/pin")
async def pin_post(
    post_id: int,
    is_pinned: bool = True,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Pin or unpin a post (requires POST_PIN permission)."""
    try:
        enforce_permission(current_user, Permission.POST_PIN)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = CommunityService(db)
    
    try:
        post = await service.update_post(
            post_id,
            PostUpdate(is_pinned=is_pinned),
            current_user
        )
        action = "pinned" if is_pinned else "unpinned"
        return {"message": f"Post {action}", "post_id": post.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/posts/{post_id}/lock")
async def lock_post(
    post_id: int,
    is_locked: bool = True,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Lock or unlock a post for comments (requires POST_LOCK permission)."""
    try:
        enforce_permission(current_user, Permission.POST_LOCK)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    # Implementation would need to add is_locked field to Post model
    raise HTTPException(status_code=501, detail="Post locking not implemented")


@router.delete("/comments/{comment_id}")
async def delete_any_comment(
    comment_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Delete any comment (requires COMMENT_DELETE_ANY permission)."""
    try:
        enforce_permission(current_user, Permission.COMMENT_DELETE_ANY)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = CommunityService(db)
    try:
        await service.delete_comment(comment_id, current_user)
        return {"message": f"Comment {comment_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Translation management endpoints

@router.get("/translations", response_model=List[TranslationJobSchema])
def list_all_translations(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """List all translation jobs (requires TRANSLATION_VIEW_ALL permission)."""
    try:
        enforce_permission(current_user, Permission.TRANSLATION_VIEW_ALL)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    query = db.query(TranslationJob)
    
    if user_id:
        query = query.filter(TranslationJob.user_id == user_id)
    if status:
        query = query.filter(TranslationJob.status == status)
    
    jobs = query.order_by(TranslationJob.created_at.desc()).limit(limit).all()
    return [TranslationJobSchema.from_orm(job) for job in jobs]


@router.delete("/translations/{job_id}")
async def delete_translation_job(
    job_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Delete any translation job (requires TRANSLATION_DELETE_ANY permission)."""
    try:
        enforce_permission(current_user, Permission.TRANSLATION_DELETE_ANY)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    
    return {"message": f"Translation job {job_id} deleted"}


# Announcement management endpoints

@router.post("/announcements")
async def create_announcement(
    announcement: AnnouncementCreate,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Create a new announcement (requires ANNOUNCEMENT_CREATE permission)."""
    try:
        enforce_permission(current_user, Permission.ANNOUNCEMENT_CREATE)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = UserService(db)
    # Deactivate all other announcements first
    service.deactivate_all_announcements()
    
    # Create the new announcement
    from backend.domains.community.models import Announcement
    db_announcement = Announcement(**announcement.dict())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    
    return JSONResponse(
        content=UserService.format_announcement_for_json(db_announcement),
        media_type="application/json; charset=utf-8"
    )


@router.put("/announcements/{announcement_id}/deactivate")
async def deactivate_announcement(
    announcement_id: int,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Deactivate a specific announcement (requires ANNOUNCEMENT_DELETE permission)."""
    try:
        enforce_permission(current_user, Permission.ANNOUNCEMENT_DELETE)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    try:
        service = UserService(db)
        db_announcement = service.deactivate_announcement(announcement_id)
        return JSONResponse(
            content=UserService.format_announcement_for_json(db_announcement),
            media_type="application/json; charset=utf-8"
        )
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e)},
            media_type="application/json; charset=utf-8"
        )


@router.put("/announcements/deactivate-all")
async def deactivate_all_announcements(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Deactivate all active announcements (requires ANNOUNCEMENT_DELETE permission)."""
    try:
        enforce_permission(current_user, Permission.ANNOUNCEMENT_DELETE)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    service = UserService(db)
    updated_count = service.deactivate_all_announcements()
    
    return JSONResponse(
        content={
            "message": f"모든 공지가 비활성화되었습니다.",
            "deactivated_count": updated_count,
            "success": True
        },
        media_type="application/json; charset=utf-8"
    )


@router.post("/community/init-categories")
async def initialize_categories(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Initialize default post categories (requires SYSTEM_CONFIG permission)."""
    try:
        enforce_permission(current_user, Permission.SYSTEM_CONFIG)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    default_categories = [
        {"name": "notice", "display_name": "공지사항", "description": "중요한 공지사항", "is_admin_only": True, "order": 1},
        {"name": "suggestion", "display_name": "건의사항", "description": "서비스 개선을 위한 제안", "is_admin_only": False, "order": 2},
        {"name": "qna", "display_name": "Q&A", "description": "질문과 답변", "is_admin_only": False, "order": 3},
        {"name": "free", "display_name": "자유게시판", "description": "자유로운 소통 공간", "is_admin_only": False, "order": 4}
    ]
    
    created_categories = []
    category_repo = PostCategoryRepository(db)
    for cat_data in default_categories:
        existing = category_repo.get_by_name(cat_data["name"])
        if not existing:
            category = PostCategory(**cat_data)
            db.add(category)
            db.commit()
            db.refresh(category)
            created_categories.append(category)
    
    return {
        "message": f"Created {len(created_categories)} categories",
        "categories": created_categories
    }


# Legacy announcement endpoints (for backward compatibility)

@router.post("/legacy/announcements")
async def create_announcement_legacy(
    announcement: AnnouncementCreate,
    admin_secret: str = Depends(verify_admin_secret),
    db: Session = Depends(get_db)
):
    """Legacy endpoint to create announcement using admin secret."""
    if not admin_secret:
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    
    service = UserService(db)
    service.deactivate_all_announcements()
    
    from backend.domains.community.models import Announcement
    db_announcement = Announcement(**announcement.dict())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    
    return JSONResponse(
        content=UserService.format_announcement_for_json(db_announcement),
        media_type="application/json; charset=utf-8"
    )


@router.put("/legacy/announcements/{announcement_id}/deactivate")
async def deactivate_announcement_legacy(
    announcement_id: int,
    admin_secret: str = Depends(verify_admin_secret),
    db: Session = Depends(get_db)
):
    """Legacy endpoint to deactivate announcement using admin secret."""
    if not admin_secret:
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    
    try:
        service = UserService(db)
        db_announcement = service.deactivate_announcement(announcement_id)
        return JSONResponse(
            content=UserService.format_announcement_for_json(db_announcement),
            media_type="application/json; charset=utf-8"
        )
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e)},
            media_type="application/json; charset=utf-8"
        )


# System administration endpoints

@router.get("/system/metrics")
def get_system_metrics(
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Get system metrics (requires SYSTEM_METRICS permission)."""
    try:
        enforce_permission(current_user, Permission.SYSTEM_METRICS)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    # Get various system metrics
    from backend.domains.tasks.models import TaskExecution, TaskStatus
    from sqlalchemy import func
    
    metrics = {
        "users": {
            "total": db.query(User).count(),
            "admins": db.query(User).filter(User.role == "admin").count(),
        },
        "translations": {
            "total": db.query(TranslationJob).count(),
            "completed": db.query(TranslationJob).filter(
                TranslationJob.status == "completed"
            ).count(),
            "failed": db.query(TranslationJob).filter(
                TranslationJob.status == "failed"
            ).count(),
        },
        "community": {
            "posts": db.query(Post).count(),
            "comments": db.query(Comment).count(),
        },
        "tasks": {
            "total": db.query(TaskExecution).count(),
            "running": db.query(TaskExecution).filter(
                TaskExecution.status == TaskStatus.RUNNING
            ).count(),
            "failed_last_24h": db.query(TaskExecution).filter(
                TaskExecution.status == TaskStatus.FAILED,
                TaskExecution.created_at >= func.now() - func.interval('1 day')
            ).count(),
        }
    }
    
    return metrics


@router.get("/system/config")
def get_system_config(
    current_user: User = Depends(get_required_user)
):
    """Get system configuration (requires SYSTEM_CONFIG permission)."""
    try:
        enforce_permission(current_user, Permission.SYSTEM_CONFIG)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    settings = get_settings()
    
    # Return safe configuration (no secrets)
    return {
        "app_env": settings.app_env,
        "debug": settings.debug,
        "cors_origins": settings.cors_origins,
        "max_file_size": settings.max_file_size,
        "storage_backend": settings.storage_backend,
        "redis_url": settings.redis_url is not None,
        "celery_enabled": True,
        "features": {
            "clerk_auth": settings.clerk_publishable_key is not None,
            "openrouter": settings.openrouter_api_key is not None,
            "gemini": settings.gemini_api_key is not None,
        }
    }


# Permission check endpoint

@router.get("/permissions/check")
def check_user_permissions(
    current_user: User = Depends(get_required_user)
):
    """Check current user's permissions."""
    permissions = admin_policy.get_user_permissions(current_user)
    role = admin_policy.get_user_role(current_user)
    
    return {
        "user_id": current_user.id,
        "role": role.value,
        "permissions": [p.value for p in permissions],
        "is_admin": admin_policy.is_admin(current_user),
        "is_super_admin": admin_policy.is_super_admin(current_user),
        "is_moderator_or_above": admin_policy.is_moderator_or_above(current_user),
    }


# Legacy admin endpoints (for backward compatibility)

@router.delete("/legacy/posts/{post_id}")
async def delete_post_legacy(
    post_id: int,
    admin_secret: str = Depends(verify_admin_secret),
    db: Session = Depends(get_db)
):
    """Legacy endpoint to delete a post using admin secret."""
    if not admin_secret:
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    
    return {"message": f"Post {post_id} deleted (legacy)"}


@router.delete("/legacy/comments/{comment_id}")
async def delete_comment_legacy(
    comment_id: int,
    admin_secret: str = Depends(verify_admin_secret),
    db: Session = Depends(get_db)
):
    """Legacy endpoint to delete a comment using admin secret."""
    if not admin_secret:
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    db.delete(comment)
    db.commit()
    
    return {"message": f"Comment {comment_id} deleted (legacy)"}