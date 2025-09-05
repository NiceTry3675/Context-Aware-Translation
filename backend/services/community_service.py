import os
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..domains.community.repository import (
    SqlAlchemyPostRepository,
    SqlAlchemyCommentRepository,
    PostCategoryRepository,
    SqlAlchemyAnnouncementRepository
)
from ..domains.user.repository import SqlAlchemyUserRepository


class CommunityService:
    """Service layer for community board operations."""
    
    UPLOAD_DIR = "uploads/images"
    ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def init_upload_directory():
        """Initialize the upload directory for images."""
        os.makedirs(CommunityService.UPLOAD_DIR, exist_ok=True)
    
    @staticmethod
    def validate_image_upload(file_content: bytes, content_type: str) -> None:
        """Validate an uploaded image file."""
        if content_type not in CommunityService.ALLOWED_IMAGE_TYPES:
            raise ValueError("Only image files (JPEG, PNG, GIF, WebP) are allowed")
        
        if len(file_content) > CommunityService.MAX_FILE_SIZE:
            raise ValueError("File size must be less than 10MB")
    
    @staticmethod
    def save_uploaded_image(file_content: bytes, filename: str) -> dict:
        """Save an uploaded image and return its metadata."""
        # Generate unique filename
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(CommunityService.UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Return metadata
        image_url = f"/static/images/{unique_filename}"
        
        return {
            "url": image_url,
            "filename": unique_filename,
            "original_name": filename,
            "size": len(file_content)
        }
    
    @staticmethod
    def get_categories_overview(db: Session, current_user: Optional[models.User]) -> list:
        """Get categories with their recent posts for community overview."""
        category_repo = PostCategoryRepository(db)
        categories = category_repo.list_ordered()
        categories_overview = []
        
        # Get all recent posts (3 per category)
        all_recent_posts = []
        for category in categories:
            post_repo = SqlAlchemyPostRepository(db)
            recent_posts, _ = post_repo.list_by_category(category.id, skip=0, limit=3)
            all_recent_posts.extend(recent_posts)
        
        # Get comment counts for all posts
        post_ids = [post.id for post in all_recent_posts]
        # Get comment counts manually
        from sqlalchemy import func
        result = db.query(
            models.Comment.post_id,
            func.count(models.Comment.id).label('comment_count')
        ).filter(
            models.Comment.post_id.in_(post_ids)
        ).group_by(
            models.Comment.post_id
        ).all()
        comment_counts = {post_id: count for post_id, count in result}
        
        for category in categories:
            # Filter posts for this category
            recent_posts = [post for post in all_recent_posts if post.category_id == category.id]
            
            # Convert posts to sanitized format
            posts_data = []
            for post in recent_posts:
                posts_data.append(CommunityService._sanitize_post_for_list(post, current_user, comment_counts))
            
            category_overview = {
                'id': category.id,
                'name': category.name,
                'display_name': category.display_name,
                'description': category.description,
                'is_admin_only': category.is_admin_only,
                'order': category.order,
                'created_at': category.created_at,
                'recent_posts': posts_data,
                'total_posts': db.query(models.Post).filter(models.Post.category_id == category.id).count()
            }
            categories_overview.append(category_overview)
        
        return categories_overview
    
    @staticmethod
    def get_posts_list(
        db: Session,
        current_user: Optional[models.User],
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None
    ) -> List[schemas.PostList]:
        """Get a list of posts with privacy filtering."""
        category_id = None
        if category:
            category_repo = PostCategoryRepository(db)
            db_category = category_repo.get_by_name(category)
            if db_category:
                category_id = db_category.id
        
        post_repo = SqlAlchemyPostRepository(db)
        if search:
            posts, _ = post_repo.search(search, category_id=category_id, skip=skip, limit=limit)
        elif category_id:
            posts, _ = post_repo.list_by_category(category_id, skip=skip, limit=limit)
        else:
            # Get all posts
            from sqlalchemy.orm import joinedload
            query = db.query(models.Post).options(
                joinedload(models.Post.author),
                joinedload(models.Post.category)
            )
            query = query.order_by(
                models.Post.is_pinned.desc(),
                models.Post.created_at.desc()
            )
            posts = query.offset(skip).limit(limit).all()
        
        post_ids = [post.id for post in posts]
        # Get comment counts manually
        from sqlalchemy import func
        result = db.query(
            models.Comment.post_id,
            func.count(models.Comment.id).label('comment_count')
        ).filter(
            models.Comment.post_id.in_(post_ids)
        ).group_by(
            models.Comment.post_id
        ).all()
        comment_counts = {post_id: count for post_id, count in result}
        
        sanitized_posts = []
        for post in posts:
            # Check if user can view the private post
            can_view = not post.is_private or (current_user and (
                post.author_id == current_user.id or 
                auth.is_admin_sync(current_user)
            ))
            if can_view:
                post_data = schemas.PostList.model_validate(post)
                post_data.comment_count = comment_counts.get(post.id, 0)
                sanitized_posts.append(post_data)
            else:
                # Mask the private post
                masked_post = schemas.PostList(
                    id=post.id,
                    title="🔒 비밀글입니다.",
                    author=schemas.User(
                        id=0,
                        clerk_user_id="",
                        name="익명",
                        role="user",
                        email="",
                        created_at=post.created_at
                    ),
                    category=post.category,
                    is_pinned=post.is_pinned,
                    is_private=True,
                    view_count=post.view_count,
                    images=[],
                    comment_count=comment_counts.get(post.id, 0),
                    created_at=post.created_at,
                    updated_at=post.updated_at
                )
                sanitized_posts.append(masked_post)
        
        return sanitized_posts
    
    @staticmethod
    def get_post_with_comments(
        db: Session,
        post_id: int,
        current_user: Optional[models.User]
    ) -> models.Post:
        """Get a specific post with sanitized comments."""
        post_repo = SqlAlchemyPostRepository(db)
        post = post_repo.get_with_details(post_id)
        if not post:
            raise ValueError("Post not found")
        
        # Check if user can view the private post
        can_view = not post.is_private or (current_user and (
            post.author_id == current_user.id or 
            auth.is_admin_sync(current_user)
        ))
        if not can_view:
            raise PermissionError("Access denied to this private post")
        
        # Sanitize comments within the post
        sanitized_comments = []
        if post.comments:
            for comment in post.comments:
                sanitized_comments.append(
                    CommunityService._sanitize_comment(comment, current_user)
                )
        
        post.comments = sanitized_comments
        return post
    
    @staticmethod
    def get_comments_for_post(
        db: Session,
        post_id: int,
        current_user: Optional[models.User]
    ) -> List[schemas.Comment]:
        """Get comments for a post with privacy filtering."""
        post_repo = SqlAlchemyPostRepository(db)
        post = post_repo.get_with_details(post_id)
        if not post:
            raise ValueError("Post not found")
        
        # Check if user can view the post
        can_view = not post.is_private or (current_user and (
            post.author_id == current_user.id or 
            auth.is_admin_sync(current_user)
        ))
        if not can_view:
            raise PermissionError("Access denied to this post and its comments")
        
        comment_repo = SqlAlchemyCommentRepository(db)
        comments = comment_repo.get_by_post(post_id)
        
        # Sanitize comments based on permissions
        sanitized_comments = []
        for comment in comments:
            sanitized_comments.append(
                CommunityService._sanitize_comment(comment, current_user)
            )
        
        return sanitized_comments
    
    @staticmethod
    def validate_category_permissions(
        db: Session,
        category_id: int,
        is_admin: bool
    ) -> models.PostCategory:
        """Validate that a user can post in a specific category."""
        category = db.query(models.PostCategory).filter(
            models.PostCategory.id == category_id
        ).first()
        
        if not category:
            raise ValueError("Category not found")
        
        if category.is_admin_only and not is_admin:
            raise PermissionError("Only admins can post in this category")
        
        return category
    
    @staticmethod
    def initialize_default_categories(db: Session) -> dict:
        """Initialize default post categories."""
        default_categories = [
            {"name": "notice", "display_name": "공지사항", "description": "중요한 공지사항", "is_admin_only": True, "order": 1},
            {"name": "suggestion", "display_name": "건의사항", "description": "서비스 개선을 위한 제안", "is_admin_only": False, "order": 2},
            {"name": "qna", "display_name": "Q&A", "description": "질문과 답변", "is_admin_only": False, "order": 3},
            {"name": "free", "display_name": "자유게시판", "description": "자유로운 소통 공간", "is_admin_only": False, "order": 4}
        ]
        
        created_categories = []
        for cat_data in default_categories:
            category_repo = PostCategoryRepository(db)
            existing = category_repo.get_by_name(cat_data["name"])
            if not existing:
                category = models.PostCategory(**cat_data)
                db.add(category)
                db.commit()
                db.refresh(category)
                created_categories.append(category)
        
        return {
            "message": f"Created {len(created_categories)} categories",
            "categories": created_categories
        }
    
    @staticmethod
    def _sanitize_post_for_list(
        post: models.Post,
        current_user: Optional[models.User],
        comment_counts: dict
    ) -> dict:
        """Sanitize a post for list view based on user permissions."""
        # Check if user can view the post
        can_view = not post.is_private or (current_user and (
            post.author_id == current_user.id or 
            auth.is_admin_sync(current_user)
        ))
        
        if can_view:
            return {
                'id': post.id,
                'title': post.title,
                'author': post.author,
                'category': post.category,
                'is_pinned': post.is_pinned,
                'is_private': post.is_private,
                'view_count': post.view_count,
                'images': post.images or [],
                'created_at': post.created_at,
                'updated_at': post.updated_at,
                'comment_count': comment_counts.get(post.id, 0)
            }
        else:
            return {
                'id': post.id,
                'title': '🔒 비밀글입니다',
                'author': schemas.User(
                    id=0,
                    clerk_user_id="",
                    name="익명",
                    role="user",
                    email="",
                    created_at=post.created_at
                ),
                'category': post.category,
                'is_pinned': post.is_pinned,
                'is_private': True,
                'view_count': post.view_count,
                'images': [],
                'created_at': post.created_at,
                'updated_at': post.updated_at,
                'comment_count': comment_counts.get(post.id, 0)
            }
    
    @staticmethod
    def _sanitize_comment(
        comment: models.Comment,
        current_user: Optional[models.User]
    ) -> schemas.Comment:
        """Sanitize a comment based on user permissions."""
        # Check if user can view the comment
        can_view = not comment.is_private or (current_user and (
            comment.author_id == current_user.id or 
            (comment.post and comment.post.author_id == current_user.id) or
            auth.is_admin_sync(current_user)
        ))
        if can_view:
            return comment
        elif comment.is_private:
            return schemas.Comment(
                id=comment.id,
                content="🔒 비밀 댓글입니다.",
                author=schemas.User(
                    id=0,
                    clerk_user_id="",
                    name="익명",
                    role="user",
                    email="",
                    created_at=comment.created_at
                ),
                post_id=comment.post_id,
                parent_id=comment.parent_id,
                is_private=True,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                replies=[]
            )
        else:
            return comment