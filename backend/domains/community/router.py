from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import traceback

from backend.config.db import get_db
from backend.config import dependencies
from backend.domains.user.models import User
from backend.domains.community.schemas import (
    Post as PostSchema,
    PostCreate,
    PostUpdate,
    PostList,
    Comment as CommentSchema,
    CommentCreate,
    CommentUpdate,
    PostCategory as PostCategorySchema,
    PostCategoryCreate,
    CategoryOverview
)
from backend.domains.user.schemas import Announcement as AnnouncementSchema, AnnouncementCreate
from backend.domains.community.services import (
    PostService,
    CommentService,
    CategoryService,
    ImageService,
    AnnouncementService,
)
from backend.domains.community.exceptions import (
    PostNotFoundException,
    CommentNotFoundException,
    CategoryNotFoundException,
    PermissionDeniedException,
    CommunityException
)

router = APIRouter()

def get_post_service(db: Session = Depends(get_db)) -> PostService:
    return PostService(db)

def get_comment_service(db: Session = Depends(get_db)) -> CommentService:
    return CommentService(db)

def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(db)

def get_image_service() -> ImageService:
    return ImageService()

def get_announcement_service(db: Session = Depends(get_db)) -> AnnouncementService:
    return AnnouncementService(db)

@router.get("/posts", response_model=List[PostList])
async def list_posts(
    response: Response,
    category: str = Query(..., description="Category name to filter by"),
    search: Optional[str] = Query(None, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(dependencies.get_optional_user),
    post_service: PostService = Depends(get_post_service),
) -> List[PostList]:
    """Get posts with filtering and pagination."""
    try:
        posts, total = post_service.list_posts(
            category_name=category,
            search_query=search,
            user=current_user,
            skip=skip,
            limit=limit
        )
        response.headers["X-Total-Count"] = str(total)
        return [PostList.from_orm(post) for post in posts]
    except CategoryNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/categories", response_model=List[PostCategorySchema])
async def list_categories(
    category_service: CategoryService = Depends(get_category_service)
) -> List[PostCategorySchema]:
    """Return all community categories."""
    categories = category_service.get_categories()
    return [PostCategorySchema.from_orm(category) for category in categories]

@router.get("/categories/overview", response_model=List[CategoryOverview])
async def list_categories_overview(
    current_user: Optional[User] = Depends(dependencies.get_optional_user),
    category_service: CategoryService = Depends(get_category_service)
) -> List[CategoryOverview]:
    """Return categories with aggregated statistics and recent posts."""
    return category_service.get_categories_with_stats(user=current_user)

@router.post("/posts", response_model=PostSchema, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(dependencies.get_required_user),
    post_service: PostService = Depends(get_post_service)
) -> PostSchema:
    """Create a new post."""
    print(f"--- DEBUG: create_post received data: {post_data.dict()}")
    try:
        post = await post_service.create_post(post_data, current_user)
        return PostSchema.from_orm(post)
    except CategoryNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.get("/posts/{post_id}", response_model=PostSchema)
async def get_post(
    post_id: int,
    current_user: Optional[User] = Depends(dependencies.get_optional_user),
    post_service: PostService = Depends(get_post_service)
) -> PostSchema:
    """Get a specific post with comments."""
    try:
        post = post_service.get_post(post_id, current_user)
        return PostSchema.from_orm(post)
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.put("/posts/{post_id}", response_model=PostSchema)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(dependencies.get_required_user),
    post_service: PostService = Depends(get_post_service)
) -> PostSchema:
    """Update an existing post."""
    print(f"--- DEBUG: update_post received data for post {post_id}: {post_update.dict()}")
    try:
        post = await post_service.update_post(post_id, post_update, current_user)
        return PostSchema.from_orm(post)
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(dependencies.get_required_user),
    post_service: PostService = Depends(get_post_service)
):
    """Delete a post."""
    try:
        await post_service.delete_post(post_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.post("/posts/{post_id}/view", status_code=status.HTTP_200_OK)
async def increment_post_view(
    post_id: int,
    current_user: Optional[User] = Depends(dependencies.get_optional_user),
    post_service: PostService = Depends(get_post_service)
):
    """Increment the view count for a post."""
    try:
        view_count = await post_service.increment_view_count(post_id, current_user)
        return {"view_count": view_count}
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.get("/posts/{post_id}/comments", response_model=List[CommentSchema])
async def list_post_comments(
    post_id: int,
    current_user: Optional[User] = Depends(dependencies.get_optional_user),
    comment_service: CommentService = Depends(get_comment_service)
) -> List[CommentSchema]:
    """Get comments for a specific post."""
    try:
        comments = comment_service.get_comments_for_post(post_id, current_user)
        return [CommentSchema.from_orm(comment) for comment in comments]
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)

@router.post("/posts/{post_id}/comments", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(dependencies.get_required_user),
    comment_service: CommentService = Depends(get_comment_service)
) -> CommentSchema:
    """Create a comment on a post."""
    try:
        comment_data.post_id = post_id
        comment = await comment_service.create_comment(comment_data, current_user)
        return CommentSchema.from_orm(comment)
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)
    except Exception as e:
        print(f"--- UNHANDLED EXCEPTION IN CREATE_COMMENT ---")
        traceback.print_exc()
        print(f"-------------------------------------------")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.put("/comments/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: User = Depends(dependencies.get_required_user),
    comment_service: CommentService = Depends(get_comment_service)
) -> CommentSchema:
    """Update an existing comment."""
    try:
        comment = await comment_service.update_comment(comment_id, comment_update, current_user)
        return CommentSchema.from_orm(comment)
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(dependencies.get_required_user),
    comment_service: CommentService = Depends(get_comment_service)
):
    """Delete a comment."""
    try:
        await comment_service.delete_comment(comment_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(dependencies.get_required_user),
    image_service: ImageService = Depends(get_image_service)
):
    """Handle community image uploads."""
    try:
        content_type = file.content_type or ""
        file_bytes = await file.read()
        image_service.validate_image_upload(file_bytes, content_type)
        image_service.init_upload_directory()
        filename = file.filename or "upload"
        saved = image_service.save_uploaded_image(file_bytes, filename)
        return saved
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Category management endpoints
@router.post("/categories", response_model=PostCategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: PostCategoryCreate,
    current_user: User = Depends(dependencies.get_required_user),
    category_service: CategoryService = Depends(get_category_service)
) -> PostCategorySchema:
    """Create a new category (admin only)."""
    try:
        db_category = await category_service.create_category(category, current_user)
        return PostCategorySchema.from_orm(db_category)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.get("/categories/{category_id}", response_model=PostCategorySchema)
async def get_category(
    category_id: int,
    category_service: CategoryService = Depends(get_category_service)
) -> PostCategorySchema:
    """Get a specific category."""
    category = category_service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return PostCategorySchema.from_orm(category)

@router.put("/categories/{category_id}", response_model=PostCategorySchema)
async def update_category(
    category_id: int,
    category: PostCategoryCreate,
    current_user: User = Depends(dependencies.get_required_user),
    category_service: CategoryService = Depends(get_category_service)
) -> PostCategorySchema:
    """Update a category (admin only)."""
    try:
        db_category = await category_service.update_category(category_id, category, current_user)
        return PostCategorySchema.from_orm(db_category)
    except CategoryNotFoundException:
        raise HTTPException(status_code=404, detail="Category not found")
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(dependencies.get_required_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Delete a category (admin only)."""
    try:
        await category_service.delete_category(category_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except CategoryNotFoundException:
        raise HTTPException(status_code=404, detail="Category not found")
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

# Announcement endpoints
@router.get("/announcements", response_model=List[AnnouncementSchema])
async def list_announcements(
    active_only: bool = Query(True, description="Only return active announcements"),
    limit: int = Query(10, ge=1, le=100, description="Maximum announcements to return"),
    announcement_service: AnnouncementService = Depends(get_announcement_service)
) -> List[AnnouncementSchema]:
    """Get announcements with optional filtering."""
    announcements = announcement_service.get_announcements(active_only=active_only, limit=limit)
    return [AnnouncementSchema.from_orm(a) for a in announcements]

@router.get("/announcements/stream")
async def stream_announcements(
    announcement_service: AnnouncementService = Depends(get_announcement_service)
):
    """Stream announcements via Server-Sent Events (SSE)."""
    import asyncio
    import json

    async def event_generator():
        while True:
            try:
                # Get active announcements
                announcements = announcement_service.get_announcements(active_only=True)
                announcements_data = [announcement_service.format_announcement_for_json(a) for a in announcements]

                # Send the announcement data
                yield f"data: {json.dumps(announcements_data)}\n\n"

                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                print(f"Error in announcement stream: {e}")
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/announcements", response_model=AnnouncementSchema, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    announcement: AnnouncementCreate,
    _: str = Depends(dependencies.verify_admin_secret),
    announcement_service: AnnouncementService = Depends(get_announcement_service)
) -> AnnouncementSchema:
    """Create a new announcement (admin only)."""
    try:
        # Deactivate all other announcements first
        announcement_service.deactivate_all_announcements()

        # Create the new announcement
        db_announcement = await announcement_service.create_announcement(announcement)
        return AnnouncementSchema.from_orm(db_announcement)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)

@router.put("/announcements/{announcement_id}", response_model=AnnouncementSchema)
async def update_announcement(
    announcement_id: int,
    announcement: AnnouncementCreate,
    _: str = Depends(dependencies.verify_admin_secret),
    announcement_service: AnnouncementService = Depends(get_announcement_service)
) -> AnnouncementSchema:
    """Update an existing announcement (admin only)."""
    try:
        db_announcement = await announcement_service.update_announcement(
            announcement_id=announcement_id,
            message=announcement.message,
            is_active=announcement.is_active
        )
        return AnnouncementSchema.from_orm(db_announcement)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)
    except CommunityException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: int,
    _: str = Depends(dependencies.verify_admin_secret),
    announcement_service: AnnouncementService = Depends(get_announcement_service)
):
    """Delete an announcement (admin only)."""
    try:
        await announcement_service.delete_announcement(announcement_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=e.detail)
    except CommunityException as e:
        raise HTTPException(status_code=404, detail=str(e))