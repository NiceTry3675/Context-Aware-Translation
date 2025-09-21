from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response, status
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
    CategoryOverview
)
from backend.domains.community.services import (
    PostService,
    CommentService,
    CategoryService,
    ImageService,
)
from backend.domains.community.exceptions import (
    PostNotFoundException,
    CommentNotFoundException,
    CategoryNotFoundException,
    PermissionDeniedException
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
        post = await post_service.increment_view_count(post_id, current_user)
        return {"view_count": post.view_count}
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