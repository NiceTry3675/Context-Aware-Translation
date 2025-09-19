"""Community domain API routes - thin routing layer."""

from typing import List, Optional

from fastapi import Depends, HTTPException, Query, UploadFile, File, Response, status
from sqlalchemy.orm import Session

from backend.config.dependencies import get_db, get_required_user, get_optional_user
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
    CategoryOverview
)
from backend.domains.community.service import CommunityService


def get_community_service(db: Session = Depends(get_db)) -> CommunityService:
    """Dependency to get community service."""
    return CommunityService(db)


async def list_posts(
    response: Response,
    category: Optional[str] = Query(None, description="Category name to filter by"),
    category_id: Optional[int] = Query(None, description="Category ID to filter by"),
    search: Optional[str] = Query(None, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
) -> List[PostList]:
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
        response.headers["X-Total-Count"] = str(total)
        return [PostList.from_orm(post) for post in posts]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def list_categories(
    service: CommunityService = Depends(get_community_service)
) -> List[PostCategorySchema]:
    """Return all community categories."""

    try:
        categories = service.get_categories()
        return [PostCategorySchema.from_orm(category) for category in categories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def list_categories_overview(
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
) -> List[CategoryOverview]:
    """Return categories with aggregated statistics and recent posts."""

    try:
        return service.get_categories_with_stats(user=current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
) -> PostSchema:
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


async def get_post(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
) -> PostSchema:
    """Get a specific post with comments."""
    try:
        post = service.get_post(post_id, current_user)
        return PostSchema.from_orm(post)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


async def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
) -> PostSchema:
    """Update an existing post."""
    try:
        post = await service.update_post(post_id, post_update, current_user)
        return PostSchema.from_orm(post)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def delete_post(
    post_id: int,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
) -> Response:
    """Delete a post."""
    try:
        await service.delete_post(post_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def increment_post_view(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
):
    """Increment the view count for a post."""
    try:
        post = service.increment_view_count(post_id, current_user)
        return {"view_count": post.view_count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def list_post_comments(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    service: CommunityService = Depends(get_community_service)
) -> List[CommentSchema]:
    """Get comments for a specific post."""
    try:
        comments = service.get_comments_for_post(post_id, current_user)
        return [CommentSchema.from_orm(comment) for comment in comments]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
) -> CommentSchema:
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


async def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
) -> CommentSchema:
    """Update an existing comment."""
    try:
        comment = await service.update_comment(comment_id, comment_update, current_user)
        return CommentSchema.from_orm(comment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
) -> Response:
    """Delete a comment."""
    try:
        await service.delete_comment(comment_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_required_user),
    service: CommunityService = Depends(get_community_service)
):
    """Handle community image uploads."""
    try:
        content_type = file.content_type or ""
        file_bytes = await file.read()
        service.validate_image_upload(file_bytes, content_type)
        service.init_upload_directory()
        filename = file.filename or "upload"
        saved = service.save_uploaded_image(file_bytes, filename)
        return saved
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
