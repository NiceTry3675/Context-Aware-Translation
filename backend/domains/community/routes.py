"""Community domain API routes - thin routing layer."""

from typing import List, Optional

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.config.dependencies import get_db, get_required_user, get_optional_user
from backend.domains.user.models import User
from backend.domains.community.schemas import (
    Post as PostSchema,
    PostCreate,
    PostList,
    Comment as CommentSchema,
    CommentCreate,
    PostCategory as PostCategorySchema,
    CategoryOverview
)
from backend.domains.community.service import CommunityService


def get_community_service(db: Session = Depends(get_db)) -> CommunityService:
    """Dependency to get community service."""
    return CommunityService(db)


async def list_posts(
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
