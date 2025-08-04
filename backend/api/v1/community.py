"""Community board API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user, get_optional_user, is_admin
from ...services.community_service import CommunityService
from ... import crud, models, schemas


router = APIRouter(prefix="/api/v1/community", tags=["community"])


# Initialize upload directory on module load
CommunityService.init_upload_directory()


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_required_user)
):
    """Upload an image for posts."""
    try:
        file_content = await file.read()
        CommunityService.validate_image_upload(file_content, file.content_type)
        result = CommunityService.save_uploaded_image(file_content, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {e}")


@router.get("/categories", response_model=list[schemas.PostCategory])
def get_categories(db: Session = Depends(get_db)):
    """Get all post categories."""
    return crud.get_post_categories(db)


@router.get("/categories/overview")
def get_categories_with_recent_posts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_optional_user)
):
    """Get categories with their recent posts for community overview."""
    return CommunityService.get_categories_overview(db, current_user)


@router.get("/posts", response_model=list[schemas.PostList])
def get_posts(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_optional_user)
):
    """Get posts, masking private ones based on user permissions."""
    return CommunityService.get_posts_list(
        db, current_user, category, skip, limit, search
    )


@router.post("/posts", response_model=schemas.Post)
async def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Create a new post."""
    try:
        # Validate category permissions
        user_is_admin = await is_admin(current_user)
        CommunityService.validate_category_permissions(
            db, post.category_id, user_is_admin
        )
        return crud.create_post(db, post, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/posts/{post_id}", response_model=schemas.Post)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_optional_user)
):
    """Get a specific post, masking private comments based on user permissions."""
    try:
        return CommunityService.get_post_with_comments(db, post_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/posts/{post_id}/view")
def increment_post_view(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_optional_user)
):
    """Increment post view count (separate endpoint)."""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user can view private post
    if not crud.can_view_private_post(post, current_user):
        raise HTTPException(status_code=403, detail="Access denied to private post")
    
    updated_post = crud.increment_post_view_count(db, post_id)
    return {"view_count": updated_post.view_count}


@router.put("/posts/{post_id}", response_model=schemas.Post)
async def update_post(
    post_id: int,
    post_update: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Update a post."""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check permission (author or admin)
    user_is_admin = await is_admin(current_user)
    if post.author_id != current_user.id and not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    return crud.update_post(db, post_id, post_update)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Delete a post."""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check permission (author or admin)
    user_is_admin = await is_admin(current_user)
    if post.author_id != current_user.id and not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    crud.delete_post(db, post_id)
    return {"message": "Post deleted successfully"}


@router.get("/posts/{post_id}/comments", response_model=list[schemas.Comment])
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_optional_user)
):
    """Get comments for a post, masking private ones based on user permissions."""
    try:
        return CommunityService.get_comments_for_post(db, post_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/posts/{post_id}/comments", response_model=schemas.Comment)
def create_comment(
    post_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Create a comment on a post."""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Ensure post_id matches
    comment.post_id = post_id
    
    return crud.create_comment(db, comment, current_user.id)


@router.put("/comments/{comment_id}", response_model=schemas.Comment)
async def update_comment(
    comment_id: int,
    comment_update: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Update a comment."""
    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permission (author or admin)
    user_is_admin = await is_admin(current_user)
    if comment.author_id != current_user.id and not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    return crud.update_comment(db, comment_id, comment_update)


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_required_user)
):
    """Delete a comment."""
    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permission (author or admin)
    user_is_admin = await is_admin(current_user)
    if comment.author_id != current_user.id and not user_is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    crud.delete_comment(db, comment_id)
    return {"message": "Comment deleted successfully"}