"""Community domain service layer with business logic."""

from typing import List, Optional, Tuple, Protocol
from datetime import datetime
import os
import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from backend.domains.user.models import User
from backend.domains.community.models import Post, Comment, PostCategory, Announcement
from backend.domains.community.schemas import (
    PostCreate, PostUpdate, PostList,
    CommentCreate, CommentUpdate,
    PostCategoryCreate,
    CategoryOverview, PostSummary
)
from backend.domains.user.schemas import AnnouncementCreate
from backend.domains.community.repository import (
    PostRepository, SqlAlchemyPostRepository,
    CommentRepository, SqlAlchemyCommentRepository,
    PostCategoryRepository,
    AnnouncementRepository, SqlAlchemyAnnouncementRepository
)
from backend.domains.community.policy import (
    CommunityPolicy, Action, PolicyContext,
    check_policy, enforce_policy
)
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import DomainEvent
from backend.config.settings import get_settings


# Domain Events
class PostCreatedEvent(DomainEvent):
    """Event raised when a post is created."""
    
    def __init__(self, post_id: int, author_id: int, category_id: int):
        super().__init__(event_type="post.created")
        self.post_id = post_id
        self.author_id = author_id
        self.category_id = category_id


class PostUpdatedEvent(DomainEvent):
    """Event raised when a post is updated."""
    
    def __init__(self, post_id: int, author_id: int, changes: dict):
        super().__init__(event_type="post.updated")
        self.post_id = post_id
        self.author_id = author_id
        self.changes = changes


class PostDeletedEvent(DomainEvent):
    """Event raised when a post is deleted."""
    
    def __init__(self, post_id: int, author_id: int):
        super().__init__(event_type="post.deleted")
        self.post_id = post_id
        self.author_id = author_id


class CommentCreatedEvent(DomainEvent):
    """Event raised when a comment is created."""
    
    def __init__(self, comment_id: int, post_id: int, author_id: int):
        super().__init__(event_type="comment.created")
        self.comment_id = comment_id
        self.post_id = post_id
        self.author_id = author_id


class CommunityService:
    """Service layer for community domain operations."""
    
    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session
        self.post_repo = SqlAlchemyPostRepository(session)
        self.comment_repo = SqlAlchemyCommentRepository(session)
        self.category_repo = PostCategoryRepository(session)
        self.announcement_repo = SqlAlchemyAnnouncementRepository(session)
        self.policy = CommunityPolicy()
        self.settings = get_settings()
    
    # Post operations
    
    async def create_post(
        self,
        post_data: PostCreate,
        user: User
    ) -> Post:
        """
        Create a new post.
        
        Args:
            post_data: Post creation data
            user: User creating the post
            
        Returns:
            Created post
            
        Raises:
            PermissionError: If user cannot post in the category
            ValueError: If category doesn't exist
        """
        async with SqlAlchemyUoW(self.session) as uow:
            # Get category
            category = self.category_repo.get(post_data.category_id)
            if not category:
                raise ValueError(f"Category {post_data.category_id} not found")
            
            # Check permissions
            enforce_policy(
                action=Action.CREATE,
                parent=category,
                user=user
            )
            
            # Create post
            post = Post(
                title=post_data.title,
                content=post_data.content,
                category_id=post_data.category_id,
                author_id=user.id,
                is_private=post_data.is_private or False,
                is_pinned=False,  # Only admins can pin later
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                view_count=0
            )
            
            # Handle image upload if provided
            if post_data.image_url:
                post.image_url = post_data.image_url
            
            self.session.add(post)
            await uow.flush()
            
            # Raise domain event
            uow.add_event(PostCreatedEvent(
                post_id=post.id,
                author_id=user.id,
                category_id=category.id
            ))
            
            await uow.commit()
            return post
    
    async def update_post(
        self,
        post_id: int,
        post_update: PostUpdate,
        user: User
    ) -> Post:
        """
        Update an existing post.
        
        Args:
            post_id: ID of post to update
            post_update: Update data
            user: User performing the update
            
        Returns:
            Updated post
            
        Raises:
            PermissionError: If user cannot edit the post
            ValueError: If post doesn't exist
        """
        async with SqlAlchemyUoW(self.session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise ValueError(f"Post {post_id} not found")
            
            # Check permissions
            enforce_policy(
                action=Action.EDIT,
                resource=post,
                user=user
            )
            
            # Track changes for event
            changes = {}
            
            # Update fields
            if post_update.title is not None:
                changes['title'] = (post.title, post_update.title)
                post.title = post_update.title
            
            if post_update.content is not None:
                changes['content'] = (len(post.content), len(post_update.content))
                post.content = post_update.content
            
            if post_update.is_private is not None:
                # Check permission to change visibility
                if post.is_private != post_update.is_private:
                    enforce_policy(
                        action=Action.MAKE_PRIVATE,
                        resource=post,
                        user=user
                    )
                changes['is_private'] = (post.is_private, post_update.is_private)
                post.is_private = post_update.is_private
            
            if post_update.is_pinned is not None:
                # Check permission to pin/unpin
                if post.is_pinned != post_update.is_pinned:
                    enforce_policy(
                        action=Action.PIN,
                        resource=post,
                        user=user
                    )
                changes['is_pinned'] = (post.is_pinned, post_update.is_pinned)
                post.is_pinned = post_update.is_pinned
            
            if post_update.image_url is not None:
                changes['image_url'] = (post.image_url, post_update.image_url)
                post.image_url = post_update.image_url
            
            post.updated_at = datetime.utcnow()
            
            # Raise domain event
            if changes:
                uow.add_event(PostUpdatedEvent(
                    post_id=post.id,
                    author_id=user.id,
                    changes=changes
                ))
            
            await uow.commit()
            return post
    
    async def delete_post(self, post_id: int, user: User) -> None:
        """
        Delete a post.
        
        Args:
            post_id: ID of post to delete
            user: User performing the deletion
            
        Raises:
            PermissionError: If user cannot delete the post
            ValueError: If post doesn't exist
        """
        async with SqlAlchemyUoW(self.session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise ValueError(f"Post {post_id} not found")
            
            # Check permissions
            enforce_policy(
                action=Action.DELETE,
                resource=post,
                user=user
            )
            
            # Delete associated comments first (cascade should handle this)
            # But we'll be explicit for clarity
            comments = self.comment_repo.get_by_post(post_id)
            for comment in comments:
                self.session.delete(comment)
            
            # Delete the post
            self.session.delete(post)
            
            # Raise domain event
            uow.add_event(PostDeletedEvent(
                post_id=post_id,
                author_id=post.author_id
            ))
            
            await uow.commit()
    
    def get_post(self, post_id: int, user: Optional[User] = None) -> Post:
        """
        Get a post with permission checking.
        
        Args:
            post_id: ID of the post
            user: User requesting the post
            
        Returns:
            Post if user has permission
            
        Raises:
            ValueError: If post doesn't exist
            PermissionError: If user cannot view the post
        """
        post = self.post_repo.get_with_details(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        # Check view permissions
        enforce_policy(
            action=Action.VIEW,
            resource=post,
            user=user
        )
        
        # Mask private comments if user doesn't have permission
        if post.comments:
            visible_comments = []
            for comment in post.comments:
                if check_policy(Action.VIEW, comment, user):
                    visible_comments.append(comment)
            post.comments = visible_comments
        
        return post
    
    def list_posts(
        self,
        category_id: Optional[int] = None,
        search_query: Optional[str] = None,
        user: Optional[User] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Post], int]:
        """
        List posts with filtering and permission checking.
        
        Args:
            category_id: Optional category filter
            search_query: Optional search query
            user: User requesting the posts
            skip: Pagination offset
            limit: Maximum posts to return
            
        Returns:
            Tuple of (posts, total_count)
        """
        include_private = user and user.role == "admin"
        
        if search_query:
            posts, total = self.post_repo.search(
                query=search_query,
                category_id=category_id,
                skip=skip,
                limit=limit
            )
        elif category_id:
            posts, total = self.post_repo.list_by_category(
                category_id=category_id,
                skip=skip,
                limit=limit,
                include_private=include_private
            )
        else:
            # List all posts
            query = self.session.query(Post)
            if not include_private:
                query = query.filter(Post.is_private == False)
            
            total = query.count()
            posts = query.order_by(
                Post.is_pinned.desc(),
                Post.created_at.desc()
            ).offset(skip).limit(limit).all()
        
        # Filter posts based on permissions
        visible_posts = []
        for post in posts:
            if check_policy(Action.VIEW, post, user):
                # Mask sensitive data for private posts
                if post.is_private and user and user.id != post.author_id and user.role != "admin":
                    # Create a masked version
                    masked_post = PostList.from_orm(post)
                    masked_post.content = "[Private Post - Content Hidden]"
                    visible_posts.append(post)
                else:
                    visible_posts.append(post)
        
        return visible_posts, total
    
    def increment_view_count(self, post_id: int, user: Optional[User] = None) -> Post:
        """
        Increment post view count if user can view it.
        
        Args:
            post_id: ID of the post
            user: User viewing the post
            
        Returns:
            Post with updated view count
            
        Raises:
            ValueError: If post doesn't exist
            PermissionError: If user cannot view the post
        """
        post = self.post_repo.get(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        # Check view permissions
        enforce_policy(
            action=Action.VIEW,
            resource=post,
            user=user
        )
        
        # Increment view count
        self.post_repo.increment_view_count(post_id)
        self.session.commit()
        
        # Refresh to get updated count
        self.session.refresh(post)
        return post
    
    # Comment operations
    
    async def create_comment(
        self,
        comment_data: CommentCreate,
        user: User
    ) -> Comment:
        """
        Create a new comment.
        
        Args:
            comment_data: Comment creation data
            user: User creating the comment
            
        Returns:
            Created comment
            
        Raises:
            PermissionError: If user cannot comment on the post
            ValueError: If post doesn't exist
        """
        async with SqlAlchemyUoW(self.session) as uow:
            # Get the post
            post = self.post_repo.get(comment_data.post_id)
            if not post:
                raise ValueError(f"Post {comment_data.post_id} not found")
            
            # Check permissions
            enforce_policy(
                action=Action.CREATE,
                parent=post,
                user=user
            )
            
            # Create comment
            comment = Comment(
                content=comment_data.content,
                post_id=comment_data.post_id,
                author_id=user.id,
                parent_id=comment_data.parent_id,
                is_private=comment_data.is_private or False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # If this is a reply, verify parent exists
            if comment_data.parent_id:
                parent_comment = self.comment_repo.get(comment_data.parent_id)
                if not parent_comment:
                    raise ValueError(f"Parent comment {comment_data.parent_id} not found")
                if parent_comment.post_id != comment_data.post_id:
                    raise ValueError("Parent comment must be on the same post")
            
            self.session.add(comment)
            await uow.flush()
            
            # Raise domain event
            uow.add_event(CommentCreatedEvent(
                comment_id=comment.id,
                post_id=post.id,
                author_id=user.id
            ))
            
            await uow.commit()
            return comment
    
    async def update_comment(
        self,
        comment_id: int,
        comment_update: CommentUpdate,
        user: User
    ) -> Comment:
        """
        Update a comment.
        
        Args:
            comment_id: ID of comment to update
            comment_update: Update data
            user: User performing the update
            
        Returns:
            Updated comment
            
        Raises:
            PermissionError: If user cannot edit the comment
            ValueError: If comment doesn't exist
        """
        async with SqlAlchemyUoW(self.session) as uow:
            comment = self.comment_repo.get(comment_id)
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")
            
            # Check permissions
            enforce_policy(
                action=Action.EDIT,
                resource=comment,
                user=user
            )
            
            # Update fields
            if comment_update.content is not None:
                comment.content = comment_update.content
            
            if comment_update.is_private is not None:
                # Check permission to change visibility
                if comment.is_private != comment_update.is_private:
                    enforce_policy(
                        action=Action.MAKE_PRIVATE,
                        resource=comment,
                        user=user
                    )
                comment.is_private = comment_update.is_private
            
            comment.updated_at = datetime.utcnow()
            
            await uow.commit()
            return comment
    
    async def delete_comment(self, comment_id: int, user: User) -> None:
        """
        Delete a comment.
        
        Args:
            comment_id: ID of comment to delete
            user: User performing the deletion
            
        Raises:
            PermissionError: If user cannot delete the comment
            ValueError: If comment doesn't exist
        """
        async with SqlAlchemyUoW(self.session) as uow:
            comment = self.comment_repo.get(comment_id)
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")
            
            # Check permissions
            enforce_policy(
                action=Action.DELETE,
                resource=comment,
                user=user
            )
            
            # Delete replies first (if any)
            if hasattr(comment, 'replies'):
                for reply in comment.replies:
                    self.session.delete(reply)
            
            # Delete the comment
            self.session.delete(comment)
            
            await uow.commit()
    
    def get_comments_for_post(
        self,
        post_id: int,
        user: Optional[User] = None
    ) -> List[Comment]:
        """
        Get comments for a post with permission checking.
        
        Args:
            post_id: ID of the post
            user: User requesting comments
            
        Returns:
            List of visible comments
        """
        comments = self.comment_repo.get_by_post(post_id)
        
        # Filter based on permissions
        visible_comments = []
        for comment in comments:
            if check_policy(Action.VIEW, comment, user):
                # Recursively filter replies
                if comment.replies:
                    visible_replies = []
                    for reply in comment.replies:
                        if check_policy(Action.VIEW, reply, user):
                            visible_replies.append(reply)
                    comment.replies = visible_replies
                visible_comments.append(comment)
        
        return visible_comments
    
    # Category operations
    
    def get_categories(self) -> List[PostCategory]:
        """Get all categories ordered for display."""
        return self.category_repo.list_ordered()
    
    def get_categories_with_stats(
        self,
        user: Optional[User] = None
    ) -> List[CategoryOverview]:
        """Return categories enriched with post counts and recent posts."""

        categories = self.category_repo.list_ordered()
        overview: List[CategoryOverview] = []

        for category in categories:
            posts, total = self.post_repo.list_by_category(
                category_id=category.id,
                limit=5,
                include_private=bool(user and user.role == "admin")
            )

            recent_posts: List[PostSummary] = []
            for post in posts:
                if not check_policy(Action.VIEW, post, user):
                    continue

                recent_posts.append(
                    PostSummary(
                        id=post.id,
                        title=post.title,
                        author=post.author,
                        is_pinned=post.is_pinned,
                        is_private=post.is_private,
                        view_count=post.view_count,
                        comment_count=len(post.comments) if post.comments else 0,
                        images=post.images or [],
                        created_at=post.created_at,
                        updated_at=post.updated_at
                    )
                )

            overview.append(
                CategoryOverview(
                    id=category.id,
                    name=category.name,
                    display_name=category.display_name,
                    description=category.description,
                    is_admin_only=category.is_admin_only,
                    order=category.order,
                    created_at=category.created_at,
                    total_posts=total,
                    can_post=check_policy(
                        Action.CREATE,
                        parent=category,
                        user=user
                    ).allowed,
                    recent_posts=recent_posts[:3]
                )
            )

        return overview
    
    # Announcement operations
    
    def get_active_announcements(self) -> List[Announcement]:
        """Get all active announcements."""
        return self.announcement_repo.get_active()
    
    async def create_announcement(
        self,
        announcement_data: AnnouncementCreate,
        user: User
    ) -> Announcement:
        """
        Create a new announcement.
        
        Args:
            announcement_data: Announcement creation data
            user: User creating the announcement (must be admin)
            
        Returns:
            Created announcement
            
        Raises:
            PermissionError: If user is not an admin
        """
        # Check permissions
        enforce_policy(
            action=Action.CREATE,
            user=user,
            metadata={'resource_type': 'announcement'}
        )
        
        async with SqlAlchemyUoW(self.session) as uow:
            announcement = self.announcement_repo.create(
                message=announcement_data.message,
                is_active=announcement_data.is_active
            )
            await uow.commit()
            return announcement
    
    async def delete_announcement(self, announcement_id: int, user: User) -> None:
        """
        Delete an announcement.
        
        Args:
            announcement_id: ID of announcement to delete
            user: User performing the deletion (must be admin)
            
        Raises:
            PermissionError: If user is not an admin
            ValueError: If announcement doesn't exist
        """
        # Check permissions
        enforce_policy(
            action=Action.DELETE,
            user=user,
            metadata={'resource_type': 'announcement'}
        )
        
        async with SqlAlchemyUoW(self.session) as uow:
            announcement = self.announcement_repo.get(announcement_id)
            if not announcement:
                raise ValueError(f"Announcement {announcement_id} not found")
            
            self.announcement_repo.delete(announcement_id)
            await uow.commit()
    
    # Image handling
    
    @staticmethod
    def validate_image_upload(file_content: bytes, content_type: str) -> None:
        """
        Validate an uploaded image file.
        
        Args:
            file_content: File content bytes
            content_type: MIME type of the file
            
        Raises:
            ValueError: If file is invalid
        """
        settings = get_settings()
        
        # Check file size
        if len(file_content) > settings.max_file_size:
            raise ValueError(f"File size exceeds maximum of {settings.max_file_size} bytes")
        
        # Check content type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if content_type not in allowed_types:
            raise ValueError(f"Invalid image type: {content_type}")
        
        # Verify file signature (magic bytes)
        signatures = {
            b'\xff\xd8\xff': 'image/jpeg',
            b'\x89\x50\x4e\x47': 'image/png',
            b'\x47\x49\x46\x38': 'image/gif',
            b'RIFF': 'image/webp'  # Simplified check
        }
        
        for sig, expected_type in signatures.items():
            if file_content.startswith(sig) and content_type == expected_type:
                return
        
        raise ValueError("File signature doesn't match content type")
    
    @staticmethod
    def save_uploaded_image(file_content: bytes, filename: str) -> dict:
        """
        Save an uploaded image file.
        
        Args:
            file_content: File content bytes
            filename: Original filename
            
        Returns:
            Dict with file URL and metadata
        """
        settings = get_settings()
        
        # Generate unique filename
        file_ext = Path(filename).suffix
        file_hash = hashlib.md5(file_content).hexdigest()
        unique_name = f"{uuid.uuid4().hex}_{file_hash}{file_ext}"
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.upload_dir) / "community"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / unique_name
        file_path.write_bytes(file_content)
        
        # Return URL path
        return {
            'url': f"/uploads/community/{unique_name}",
            'filename': unique_name,
            'size': len(file_content),
            'hash': file_hash
        }
    
    @staticmethod
    def init_upload_directory() -> None:
        """Initialize the upload directory structure."""
        settings = get_settings()
        upload_dir = Path(settings.upload_dir) / "community"
        upload_dir.mkdir(parents=True, exist_ok=True)
