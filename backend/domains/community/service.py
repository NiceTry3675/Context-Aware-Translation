"""Community domain service layer with business logic."""

from typing import List, Optional, Tuple
from datetime import datetime
import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from backend.domains.user.models import User
from backend.domains.community.models import Post, Comment, PostCategory, Announcement
from backend.domains.community.schemas import (
    PostCreate, PostUpdate,
    CommentCreate, CommentUpdate,
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
    CommunityPolicy, Action,
    check_policy, enforce_policy
)
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import (
    PostCreatedEvent as CommunityPostCreatedEvent,
    PostUpdatedEvent as CommunityPostUpdatedEvent,
    PostDeletedEvent as CommunityPostDeletedEvent,
    CommentAddedEvent,
    CommentDeletedEvent,
)
from backend.config.settings import get_settings


class CommunityService:
    """Service layer for community domain operations."""

    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session
        self.post_repo: PostRepository = SqlAlchemyPostRepository(session)
        self.comment_repo: CommentRepository = SqlAlchemyCommentRepository(session)
        self.category_repo = PostCategoryRepository(session)
        self.announcement_repo: AnnouncementRepository = SqlAlchemyAnnouncementRepository(session)
        self.policy = CommunityPolicy()
        self.settings = get_settings()

    # Post operations

    async def create_post(
        self,
        post_data: PostCreate,
        user: User
    ) -> Post:
        """Create a new post."""
        with SqlAlchemyUoW(self.session) as uow:
            category = self.category_repo.get(post_data.category_id)
            if not category:
                raise ValueError(f"Category {post_data.category_id} not found")

            enforce_policy(
                action=Action.CREATE,
                parent=category,
                user=user
            )

            post = Post(
                title=post_data.title,
                content=post_data.content,
                category_id=post_data.category_id,
                author_id=user.id,
                is_private=post_data.is_private or False,
                is_pinned=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                view_count=0,
                images=post_data.images or []
            )

            self.session.add(post)
            uow.flush()

            uow.add_event(CommunityPostCreatedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(post.id),
                post_id=post.id,
                author_id=user.id,
                category_id=category.id,
                title=post.title,
                is_pinned=post.is_pinned,
                is_private=post.is_private,
                metadata={"images": post.images or []}
            ))

            uow.commit()
            self.session.refresh(post)
            return post

    async def update_post(
        self,
        post_id: int,
        post_update: PostUpdate,
        user: User
    ) -> Post:
        """Update an existing post."""
        with SqlAlchemyUoW(self.session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise ValueError(f"Post {post_id} not found")

            enforce_policy(
                action=Action.EDIT,
                resource=post,
                user=user
            )

            changes = {}

            if post_update.title is not None:
                changes['title'] = (post.title, post_update.title)
                post.title = post_update.title

            if post_update.content is not None:
                changes['content'] = (len(post.content), len(post_update.content))
                post.content = post_update.content

            if post_update.is_private is not None:
                if post.is_private != post_update.is_private:
                    enforce_policy(
                        action=Action.MAKE_PRIVATE,
                        resource=post,
                        user=user
                    )
                changes['is_private'] = (post.is_private, post_update.is_private)
                post.is_private = post_update.is_private

            if post_update.is_pinned is not None:
                if post.is_pinned != post_update.is_pinned:
                    enforce_policy(
                        action=Action.PIN,
                        resource=post,
                        user=user
                    )
                changes['is_pinned'] = (post.is_pinned, post_update.is_pinned)
                post.is_pinned = post_update.is_pinned

            if post_update.images is not None:
                changes['images'] = (post.images or [], post_update.images)
                post.images = post_update.images

            post.updated_at = datetime.utcnow()

            if changes:
                uow.add_event(CommunityPostUpdatedEvent(
                    event_id=str(uuid.uuid4()),
                    aggregate_id=str(post.id),
                    post_id=post.id,
                    author_id=post.author_id,
                    updated_fields=list(changes.keys()),
                    updated_by=user.id,
                    metadata={"changes": changes}
                ))

            uow.commit()
            self.session.refresh(post)
            return post

    async def delete_post(self, post_id: int, user: User) -> None:
        """Delete a post."""
        with SqlAlchemyUoW(self.session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise ValueError(f"Post {post_id} not found")

            enforce_policy(
                action=Action.DELETE,
                resource=post,
                user=user
            )

            comments = self.comment_repo.get_by_post(post_id)
            for comment in comments:
                self.session.delete(comment)

            self.session.delete(post)

            uow.add_event(CommunityPostDeletedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(post.id),
                post_id=post_id,
                author_id=post.author_id,
                deleted_by=user.id
            ))

            uow.commit()

    def get_post(self, post_id: int, user: Optional[User] = None) -> Post:
        """Get a post with permission checking."""
        post = self.post_repo.get_with_details(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        enforce_policy(
            action=Action.VIEW,
            resource=post,
            user=user
        )

        if post.comments:
            visible_comments: List[Comment] = []
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
        """List posts with filtering and permission checking."""
        include_private = bool(user and user.role == "admin")

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
            query = self.session.query(Post).options(
                joinedload(Post.author),
                joinedload(Post.category)
            )
            if not include_private:
                query = query.filter(Post.is_private == False)

            total = query.count()
            posts = query.order_by(
                Post.is_pinned.desc(),
                Post.created_at.desc()
            ).offset(skip).limit(limit).all()

        visible_posts = [post for post in posts if check_policy(Action.VIEW, post, user)]
        return visible_posts, total

    def increment_view_count(self, post_id: int, user: Optional[User] = None) -> Post:
        """Increment post view count if user can view it."""
        post = self.post_repo.get(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        enforce_policy(
            action=Action.VIEW,
            resource=post,
            user=user
        )

        self.post_repo.increment_view_count(post_id)
        self.session.commit()
        self.session.refresh(post)
        return post

    # Comment operations

    async def create_comment(
        self,
        comment_data: CommentCreate,
        user: User
    ) -> Comment:
        """Create a new comment."""
        with SqlAlchemyUoW(self.session) as uow:
            post = self.post_repo.get(comment_data.post_id)
            if not post:
                raise ValueError(f"Post {comment_data.post_id} not found")

            enforce_policy(
                action=Action.CREATE,
                parent=post,
                user=user
            )

            comment = Comment(
                content=comment_data.content,
                post_id=comment_data.post_id,
                author_id=user.id,
                parent_id=comment_data.parent_id,
                is_private=comment_data.is_private or False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            if comment_data.parent_id:
                parent_comment = self.comment_repo.get(comment_data.parent_id)
                if not parent_comment:
                    raise ValueError(f"Parent comment {comment_data.parent_id} not found")
                if parent_comment.post_id != comment_data.post_id:
                    raise ValueError("Parent comment must be on the same post")

            self.session.add(comment)
            uow.flush()

            uow.add_event(CommentAddedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(comment.id),
                comment_id=comment.id,
                post_id=post.id,
                author_id=user.id,
                parent_id=comment_data.parent_id,
                is_private=comment.is_private
            ))

            uow.commit()
            self.session.refresh(comment)
            return comment

    async def update_comment(
        self,
        comment_id: int,
        comment_update: CommentUpdate,
        user: User
    ) -> Comment:
        """Update a comment."""
        with SqlAlchemyUoW(self.session) as uow:
            comment = self.comment_repo.get(comment_id)
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")

            enforce_policy(
                action=Action.EDIT,
                resource=comment,
                user=user
            )

            if comment_update.content is not None:
                comment.content = comment_update.content

            if comment_update.is_private is not None:
                if comment.is_private != comment_update.is_private:
                    enforce_policy(
                        action=Action.MAKE_PRIVATE,
                        resource=comment,
                        user=user
                    )
                comment.is_private = comment_update.is_private

            comment.updated_at = datetime.utcnow()

            uow.commit()
            self.session.refresh(comment)
            return comment

    async def delete_comment(self, comment_id: int, user: User) -> None:
        """Delete a comment."""
        with SqlAlchemyUoW(self.session) as uow:
            comment = self.comment_repo.get(comment_id)
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")

            enforce_policy(
                action=Action.DELETE,
                resource=comment,
                user=user
            )

            if hasattr(comment, 'replies'):
                for reply in comment.replies:
                    self.session.delete(reply)

            self.session.delete(comment)

            uow.add_event(CommentDeletedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(comment.id),
                comment_id=comment.id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                deleted_by=user.id
            ))

            uow.commit()

    def get_comments_for_post(
        self,
        post_id: int,
        user: Optional[User] = None
    ) -> List[Comment]:
        """Get comments for a post with permission checking."""
        comments = self.comment_repo.get_by_post(post_id)

        visible_comments: List[Comment] = []
        for comment in comments:
            if check_policy(Action.VIEW, comment, user):
                if comment.replies:
                    visible_replies = [reply for reply in comment.replies if check_policy(Action.VIEW, reply, user)]
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
        """Create a new announcement."""
        enforce_policy(
            action=Action.CREATE,
            user=user,
            metadata={'resource_type': 'announcement'}
        )

        with SqlAlchemyUoW(self.session) as uow:
            announcement = self.announcement_repo.create(
                message=announcement_data.message,
                is_active=announcement_data.is_active
            )
            uow.commit()
            return announcement

    async def delete_announcement(self, announcement_id: int, user: User) -> None:
        """Delete an announcement."""
        enforce_policy(
            action=Action.DELETE,
            user=user,
            metadata={'resource_type': 'announcement'}
        )

        with SqlAlchemyUoW(self.session) as uow:
            announcement = self.announcement_repo.get(announcement_id)
            if not announcement:
                raise ValueError(f"Announcement {announcement_id} not found")

            self.announcement_repo.delete(announcement_id)
            uow.commit()

    # Image handling

    @staticmethod
    def validate_image_upload(file_content: bytes, content_type: str) -> None:
        """Validate an uploaded image file."""
        settings = get_settings()

        if len(file_content) > settings.max_file_size:
            raise ValueError(f"File size exceeds maximum of {settings.max_file_size} bytes")

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if content_type not in allowed_types:
            raise ValueError(f"Invalid image type: {content_type}")

        signatures = {
            b'\xff\xd8\xff': 'image/jpeg',
            b'\x89\x50\x4e\x47': 'image/png',
            b'\x47\x49\x46\x38': 'image/gif',
            b'RIFF': 'image/webp'
        }

        for sig, expected_type in signatures.items():
            if file_content.startswith(sig) and content_type == expected_type:
                return

        raise ValueError("File signature doesn't match content type")

    @staticmethod
    def save_uploaded_image(file_content: bytes, filename: str) -> dict:
        """Save an uploaded image file."""
        settings = get_settings()

        file_ext = Path(filename).suffix
        file_hash = hashlib.md5(file_content).hexdigest()
        unique_name = f"{uuid.uuid4().hex}_{file_hash}{file_ext}"

        upload_dir = Path(settings.upload_dir) / "community"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / unique_name
        file_path.write_bytes(file_content)

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
