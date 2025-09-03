"""Community domain API routes."""

from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user, get_optional_user
from backend.models.user import User
from backend.schemas.community import (
    Post as PostSchema,
    PostCreate, PostUpdate, PostList,
    Comment as CommentSchema,
    CommentCreate, CommentUpdate,
    PostCategory as CategorySchema,
    Announcement as AnnouncementSchema,
    AnnouncementCreate
)
from backend.domains.community.service import CommunityService


router = APIRouter(prefix="/community", tags=["community"])


def get_community_service(db: Session = Depends(get_db)) -> CommunityService:
    """Dependency to get community service."""
    return CommunityService(db)


# Image upload endpoint

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Upload an image for posts."""
    try:
        file_content = await file.read()
        service.validate_image_upload(file_content, file.content_type)
        result = service.save_uploaded_image(file_content, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {e}")


# Category endpoints

@router.get("/categories", response_model=List[CategorySchema])
def get_categories(
    service: CommunityService = Depends(get_community_service)
):
    """Get all post categories."""
    return service.get_categories()


@router.get("/categories/overview")
def get_categories_with_stats(
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
):
    """Get categories with their recent posts and statistics."""
    return service.get_categories_with_stats(current_user)


# Post endpoints

@router.get("/posts", response_model=List[PostList])
def list_posts(
    category: Optional[str] = Query(None, description="Category name to filter by"),
    category_id: Optional[int] = Query(None, description="Category ID to filter by"),
    search: Optional[str] = Query(None, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
):
    """Get posts with filtering and pagination."""
    # Handle category filtering (support both name and ID for backward compatibility)
    filter_category_id = category_id
    if category and not category_id:
        # Look up category by name
        categories = service.get_categories()
        for cat in categories:
            if cat.name.lower() == category.lower():
                filter_category_id = cat.id
                break
    
    try:
        posts, total = service.list_posts(
            category_id=filter_category_id,
            search_query=search,
            user=current_user,
            skip=skip,
            limit=limit
        )
        
        # Convert to response model
        return [PostList.from_orm(post) for post in posts]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts", response_model=PostSchema)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Create a new post."""
    try:
        post = await service.create_post(post_data, current_user)
        return PostSchema.from_orm(post)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/{post_id}", response_model=PostSchema)
def get_post(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
):
    """Get a specific post with comments."""
    try:
        post = service.get_post(post_id, current_user)
        return PostSchema.from_orm(post)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/posts/{post_id}/view")
def increment_view_count(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
):
    """Increment post view count."""
    try:
        post = service.increment_view_count(post_id, current_user)
        return {"view_count": post.view_count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/posts/{post_id}", response_model=PostSchema)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Update a post."""
    try:
        post = await service.update_post(post_id, post_update, current_user)
        return PostSchema.from_orm(post)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Delete a post."""
    try:
        await service.delete_post(post_id, current_user)
        return {"message": "Post deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# Comment endpoints

@router.get("/posts/{post_id}/comments", response_model=List[CommentSchema])
def get_post_comments(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
):
    """Get comments for a post."""
    try:
        comments = service.get_comments_for_post(post_id, current_user)
        return [CommentSchema.from_orm(c) for c in comments]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/posts/{post_id}/comments", response_model=CommentSchema)
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Create a comment on a post."""
    try:
        # Ensure post_id matches
        comment_data.post_id = post_id
        comment = await service.create_comment(comment_data, current_user)
        return CommentSchema.from_orm(comment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/comments/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Update a comment."""
    try:
        comment = await service.update_comment(comment_id, comment_update, current_user)
        return CommentSchema.from_orm(comment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Delete a comment."""
    try:
        await service.delete_comment(comment_id, current_user)
        return {"message": "Comment deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# Announcement endpoints

@router.get("/announcements", response_model=List[AnnouncementSchema])
def get_announcements(
    service: CommunityService = Depends(get_community_service)
):
    """Get all active announcements."""
    announcements = service.get_active_announcements()
    return [AnnouncementSchema.from_orm(a) for a in announcements]


@router.post("/announcements", response_model=AnnouncementSchema)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Create a new announcement (admin only)."""
    try:
        announcement = await service.create_announcement(announcement_data, current_user)
        return AnnouncementSchema.from_orm(announcement)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Delete an announcement (admin only)."""
    try:
        await service.delete_announcement(announcement_id, current_user)
        return {"message": "Announcement deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))