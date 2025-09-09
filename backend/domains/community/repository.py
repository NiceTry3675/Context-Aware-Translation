from typing import Protocol, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func

from backend.domains.community.models import Post, Comment, PostCategory, Announcement
from backend.domains.user.models import User
from backend.domains.shared.repository import SqlAlchemyRepository


class PostRepository(Protocol):
    """Protocol for Post repository operations."""
    
    def get(self, id: int) -> Optional[Post]:
        """Get a post by ID."""
        ...
    
    def get_with_details(self, id: int) -> Optional[Post]:
        """Get a post with author and category eagerly loaded."""
        ...
    
    def list_by_category(
        self,
        category_id: int,
        skip: int = 0,
        limit: int = 20,
        include_private: bool = False
    ) -> Tuple[List[Post], int]:
        """List posts by category with pagination."""
        ...
    
    def list_by_author(
        self,
        author_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Post]:
        """List posts by author."""
        ...
    
    def search(
        self,
        query: str,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Post], int]:
        """Search posts by title or content."""
        ...
    
    def increment_view_count(self, id: int) -> None:
        """Increment the view count for a post."""
        ...
    
    def get_pinned_posts(self, category_id: Optional[int] = None) -> List[Post]:
        """Get all pinned posts, optionally filtered by category."""
        ...
    
    def can_user_view(self, post_id: int, user: Optional[User]) -> bool:
        """Check if a user can view a specific post."""
        ...
    
    def can_user_edit(self, post_id: int, user: Optional[User]) -> bool:
        """Check if a user can edit a specific post."""
        ...


class SqlAlchemyPostRepository(SqlAlchemyRepository[Post]):
    """SQLAlchemy implementation of PostRepository."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, Post)
    
    def get_with_details(self, id: int) -> Optional[Post]:
        """Get a post with author and category eagerly loaded."""
        return self.session.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.category),
            joinedload(Post.comments)
        ).filter(Post.id == id).first()
    
    def list_by_category(
        self,
        category_id: int,
        skip: int = 0,
        limit: int = 20,
        include_private: bool = False
    ) -> Tuple[List[Post], int]:
        """
        List posts by category with pagination.
        
        Returns:
            Tuple of (posts, total_count)
        """
        query = self.session.query(Post).filter(Post.category_id == category_id)
        
        if not include_private:
            query = query.filter(Post.is_private == False)
        
        # Pinned posts first, then by created_at
        query = query.order_by(
            desc(Post.is_pinned),
            desc(Post.created_at)
        )
        
        total = query.count()
        posts = query.options(
            joinedload(Post.author),
            joinedload(Post.category)
        ).offset(skip).limit(limit).all()
        
        return posts, total
    
    def list_by_author(
        self,
        author_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Post]:
        """List posts by author."""
        return self.session.query(Post).filter(
            Post.author_id == author_id
        ).options(
            joinedload(Post.category)
        ).order_by(
            desc(Post.created_at)
        ).offset(skip).limit(limit).all()
    
    def search(
        self,
        query: str,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Post], int]:
        """
        Search posts by title or content.
        
        Returns:
            Tuple of (posts, total_count)
        """
        search_pattern = f"%{query}%"
        db_query = self.session.query(Post).filter(
            or_(
                Post.title.ilike(search_pattern),
                Post.content.ilike(search_pattern)
            )
        )
        
        if category_id:
            db_query = db_query.filter(Post.category_id == category_id)
        
        # Exclude private posts from search
        db_query = db_query.filter(Post.is_private == False)
        
        db_query = db_query.order_by(desc(Post.created_at))
        
        total = db_query.count()
        posts = db_query.options(
            joinedload(Post.author),
            joinedload(Post.category)
        ).offset(skip).limit(limit).all()
        
        return posts, total
    
    def increment_view_count(self, id: int) -> None:
        """Increment the view count for a post."""
        self.session.query(Post).filter(Post.id == id).update(
            {Post.view_count: Post.view_count + 1}
        )
        self.session.flush()
    
    def get_pinned_posts(self, category_id: Optional[int] = None) -> List[Post]:
        """Get all pinned posts, optionally filtered by category."""
        query = self.session.query(Post).filter(
            Post.is_pinned == True,
            Post.is_private == False
        )
        
        if category_id:
            query = query.filter(Post.category_id == category_id)
        
        return query.options(
            joinedload(Post.author),
            joinedload(Post.category)
        ).order_by(desc(Post.created_at)).all()
    
    def can_user_view(self, post_id: int, user: Optional[User]) -> bool:
        """Check if a user can view a specific post."""
        post = self.get(post_id)
        if not post:
            return False
        
        # Public posts can be viewed by anyone
        if not post.is_private:
            return True
        
        # Private posts require authentication
        if not user:
            return False
        
        # Author can view their own posts
        if post.author_id == user.id:
            return True
        
        # Admins can view all posts
        if user.role == "admin":
            return True
        
        return False
    
    def can_user_edit(self, post_id: int, user: Optional[User]) -> bool:
        """Check if a user can edit a specific post."""
        if not user:
            return False
        
        post = self.get(post_id)
        if not post:
            return False
        
        # Author can edit their own posts
        if post.author_id == user.id:
            return True
        
        # Admins can edit all posts
        if user.role == "admin":
            return True
        
        return False
    
    def get_popular_posts(self, days: int = 7, limit: int = 10) -> List[Post]:
        """Get popular posts based on view count within the last N days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return self.session.query(Post).filter(
            Post.created_at >= cutoff_date,
            Post.is_private == False
        ).order_by(
            desc(Post.view_count)
        ).limit(limit).all()


class CommentRepository(Protocol):
    """Protocol for Comment repository operations."""
    
    def get(self, id: int) -> Optional[Comment]:
        """Get a comment by ID."""
        ...
    
    def get_by_post(self, post_id: int) -> List[Comment]:
        """Get all comments for a post."""
        ...
    
    def get_thread(self, comment_id: int) -> List[Comment]:
        """Get a comment and all its replies."""
        ...
    
    def add_reply(self, parent_id: int, comment: Comment) -> Comment:
        """Add a reply to an existing comment."""
        ...
    
    def can_user_view(self, comment_id: int, user: Optional[User]) -> bool:
        """Check if a user can view a specific comment."""
        ...
    
    def can_user_edit(self, comment_id: int, user: Optional[User]) -> bool:
        """Check if a user can edit a specific comment."""
        ...


class SqlAlchemyCommentRepository(SqlAlchemyRepository[Comment]):
    """SQLAlchemy implementation of CommentRepository."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, Comment)
    
    def get_by_post(self, post_id: int) -> List[Comment]:
        """Get all comments for a post, organized hierarchically."""
        return self.session.query(Comment).filter(
            Comment.post_id == post_id,
            Comment.parent_id == None  # Top-level comments only
        ).options(
            joinedload(Comment.author),
            joinedload(Comment.replies).joinedload(Comment.author)
        ).order_by(Comment.created_at).all()
    
    def get_thread(self, comment_id: int) -> List[Comment]:
        """Get a comment and all its replies recursively."""
        comment = self.session.query(Comment).options(
            joinedload(Comment.author),
            joinedload(Comment.replies).joinedload(Comment.author)
        ).filter(Comment.id == comment_id).first()
        
        if not comment:
            return []
        
        # Recursively collect all replies
        result = [comment]
        for reply in comment.replies:
            result.extend(self.get_thread(reply.id))
        
        return result
    
    def add_reply(self, parent_id: int, comment: Comment) -> Comment:
        """Add a reply to an existing comment."""
        parent = self.get(parent_id)
        if not parent:
            raise ValueError(f"Parent comment {parent_id} not found")
        
        comment.parent_id = parent_id
        comment.post_id = parent.post_id  # Ensure same post
        
        self.session.add(comment)
        self.session.flush()
        return comment
    
    def can_user_view(self, comment_id: int, user: Optional[User]) -> bool:
        """Check if a user can view a specific comment."""
        comment = self.session.query(Comment).options(
            joinedload(Comment.post)
        ).filter(Comment.id == comment_id).first()
        
        if not comment:
            return False
        
        # Public comments can be viewed by anyone
        if not comment.is_private:
            return True
        
        # Private comments require authentication
        if not user:
            return False
        
        # Comment author can view their own comments
        if comment.author_id == user.id:
            return True
        
        # Post author can view all comments on their post
        if comment.post and comment.post.author_id == user.id:
            return True
        
        # Admins can view all comments
        if user.role == "admin":
            return True
        
        return False
    
    def can_user_edit(self, comment_id: int, user: Optional[User]) -> bool:
        """Check if a user can edit a specific comment."""
        if not user:
            return False
        
        comment = self.get(comment_id)
        if not comment:
            return False
        
        # Author can edit their own comments
        if comment.author_id == user.id:
            return True
        
        # Admins can edit all comments
        if user.role == "admin":
            return True
        
        return False
    
    def count_by_author(self, author_id: int) -> int:
        """Count total comments by an author."""
        return self.session.query(Comment).filter(
            Comment.author_id == author_id
        ).count()
    
    def get_recent_by_author(self, author_id: int, limit: int = 10) -> List[Comment]:
        """Get recent comments by an author."""
        return self.session.query(Comment).filter(
            Comment.author_id == author_id
        ).options(
            joinedload(Comment.post)
        ).order_by(
            desc(Comment.created_at)
        ).limit(limit).all()


class PostCategoryRepository(SqlAlchemyRepository[PostCategory]):
    """Repository for PostCategory operations."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, PostCategory)
    
    def get_by_name(self, name: str) -> Optional[PostCategory]:
        """Get a category by its name."""
        return self.session.query(PostCategory).filter(
            PostCategory.name == name
        ).first()
    
    def list_ordered(self) -> List[PostCategory]:
        """Get all categories ordered by their display order."""
        return self.session.query(PostCategory).order_by(
            PostCategory.order,
            PostCategory.id
        ).all()
    
    def can_user_post(self, category_id: int, user: Optional[User]) -> bool:
        """Check if a user can post in a specific category."""
        if not user:
            return False
        
        category = self.get(category_id)
        if not category:
            return False
        
        # Admin-only categories require admin role
        if category.is_admin_only and user.role != "admin":
            return False
        
        return True


class AnnouncementRepository(Protocol):
    """Protocol for Announcement repository operations."""
    
    def get(self, id: int) -> Optional[Announcement]:
        """Get an announcement by ID."""
        ...
    
    def get_active(self) -> List[Announcement]:
        """Get all active announcements."""
        ...
    
    def create(self, message: str, is_active: bool = True) -> Announcement:
        """Create a new announcement."""
        ...
    
    def toggle_active(self, id: int) -> bool:
        """Toggle the active status of an announcement."""
        ...
    
    def update_message(self, id: int, message: str) -> bool:
        """Update the message of an announcement."""
        ...


class SqlAlchemyAnnouncementRepository(SqlAlchemyRepository[Announcement]):
    """SQLAlchemy implementation of AnnouncementRepository."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, Announcement)
    
    def get_active(self) -> List[Announcement]:
        """Get all active announcements ordered by creation date."""
        return self.session.query(Announcement).filter(
            Announcement.is_active == True
        ).order_by(
            desc(Announcement.created_at)
        ).all()
    
    def create(self, message: str, is_active: bool = True) -> Announcement:
        """Create a new announcement."""
        announcement = Announcement(
            message=message,
            is_active=is_active,
            created_at=datetime.utcnow()
        )
        self.session.add(announcement)
        self.session.flush()
        return announcement
    
    def toggle_active(self, id: int) -> bool:
        """
        Toggle the active status of an announcement.
        
        Returns:
            True if successful, False if announcement not found
        """
        announcement = self.get(id)
        if announcement:
            announcement.is_active = not announcement.is_active
            self.session.flush()
            return True
        return False
    
    def update_message(self, id: int, message: str) -> bool:
        """
        Update the message of an announcement.
        
        Returns:
            True if successful, False if announcement not found
        """
        announcement = self.get(id)
        if announcement:
            announcement.message = message
            self.session.flush()
            return True
        return False
    
    def get_recent(self, limit: int = 5, include_inactive: bool = False) -> List[Announcement]:
        """Get recent announcements."""
        query = self.session.query(Announcement)
        
        if not include_inactive:
            query = query.filter(Announcement.is_active == True)
        
        return query.order_by(
            desc(Announcement.created_at)
        ).limit(limit).all()
    
    def deactivate_old(self, days: int = 30) -> int:
        """
        Deactivate announcements older than N days.
        
        Returns:
            Number of announcements deactivated
        """
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = self.session.query(Announcement).filter(
            and_(
                Announcement.created_at < cutoff_date,
                Announcement.is_active == True
            )
        ).update({Announcement.is_active: False})
        
        self.session.flush()
        return result
    
    def bulk_create(self, messages: List[str]) -> List[Announcement]:
        """Create multiple announcements at once."""
        announcements = [
            Announcement(
                message=message,
                is_active=True,
                created_at=datetime.utcnow()
            )
            for message in messages
        ]
        
        self.session.bulk_save_objects(announcements, return_defaults=True)
        self.session.flush()
        return announcements