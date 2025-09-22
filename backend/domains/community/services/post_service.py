
from typing import List, Optional, Tuple
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from backend.domains.user.models import User
from backend.domains.community.models import Post
from backend.domains.community.schemas import PostCreate, PostUpdate
from backend.domains.community.repository import PostRepository, SqlAlchemyPostRepository, PostCategoryRepository
from backend.domains.community.policy import Action, enforce_policy, check_policy
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.config.database import SessionLocal
from backend.domains.shared.events import (
    PostCreatedEvent as CommunityPostCreatedEvent,
    PostUpdatedEvent as CommunityPostUpdatedEvent,
    PostDeletedEvent as CommunityPostDeletedEvent,
)
from backend.domains.community.exceptions import PostNotFoundException, CategoryNotFoundException, PermissionDeniedException

class PostService:
    def __init__(self, session: Session):
        self.session = session
        self.post_repo: PostRepository = SqlAlchemyPostRepository(session)
        self.category_repo = PostCategoryRepository(session)

    def _create_session(self):
        """Create a new session for UoW transactions."""
        return SessionLocal()


    async def create_post(self, post_data: PostCreate, user: User) -> Post:
        with SqlAlchemyUoW(self._create_session) as uow:
            # For operations within UoW, use service repos which should be fine for queries
            # and use uow.session for writes
            category = self.category_repo.get(post_data.category_id)
            if not category:
                raise CategoryNotFoundException(f"Category {post_data.category_id} not found")

            try:
                enforce_policy(action=Action.CREATE, parent=category, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            # Merge user object into the current session to avoid session conflicts
            user = uow.session.merge(user)

            post = Post(
                title=post_data.title,
                content=post_data.content,
                category_id=post_data.category_id,
                author=user,
                is_private=post_data.is_private,
                is_pinned=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                view_count=0,
                images=post_data.images or []
            )

            uow.session.add(post)
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
            return self.post_repo.get_with_details(post.id)

    async def update_post(self, post_id: int, post_update: PostUpdate, user: User) -> Post:
        with SqlAlchemyUoW(self._create_session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise PostNotFoundException(f"Post {post_id} not found")

            try:
                enforce_policy(action=Action.EDIT, resource=post, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            changes = {}

            if post_update.title is not None:
                changes['title'] = (post.title, post_update.title)
                post.title = post_update.title

            if post_update.content is not None:
                changes['content'] = (len(post.content), len(post_update.content))
                post.content = post_update.content

            if post_update.is_private is not None:
                if post.is_private != post_update.is_private:
                    try:
                        enforce_policy(action=Action.MAKE_PRIVATE, resource=post, user=user)
                    except PermissionError as e:
                        raise PermissionDeniedException(str(e))
                changes['is_private'] = (post.is_private, post_update.is_private)
                post.is_private = post_update.is_private

            if post_update.is_pinned is not None:
                if post.is_pinned != post_update.is_pinned:
                    try:
                        enforce_policy(action=Action.PIN, resource=post, user=user)
                    except PermissionError as e:
                        raise PermissionDeniedException(str(e))
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
            uow.session.refresh(post)
            return post

    async def delete_post(self, post_id: int, user: User) -> None:
        with SqlAlchemyUoW(self._create_session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise PostNotFoundException(f"Post {post_id} not found")

            try:
                enforce_policy(action=Action.DELETE, resource=post, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            # comments are deleted by cascade
            uow.session.delete(post)

            uow.add_event(CommunityPostDeletedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(post.id),
                post_id=post_id,
                author_id=post.author_id,
                deleted_by=user.id
            ))

            uow.commit()

    def get_post(self, post_id: int, user: Optional[User] = None) -> Post:
        post = self.post_repo.get_with_details(post_id)
        if not post:
            raise PostNotFoundException(f"Post {post_id} not found")

        try:
            enforce_policy(action=Action.VIEW, resource=post, user=user)
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        return post

    def list_posts(
        self,
        category_name: str,
        search_query: Optional[str] = None,
        user: Optional[User] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Post], int]:
        category = self.category_repo.get_by_name(category_name)
        if not category:
            raise CategoryNotFoundException(f"Category '{category_name}' not found.")

        # Use repository-level filtering instead of post-processing
        if search_query:
            posts, total = self.post_repo.search(
                query=search_query,
                category_id=category.id,
                skip=skip,
                limit=limit,
                user=user
            )
        else:
            posts, total = self.post_repo.list_by_category(
                category_id=category.id,
                skip=skip,
                limit=limit,
                user=user
            )

        # No need for post-processing filtering - repository handles it at SQL level
        return posts, total

    async def increment_view_count(self, post_id: int, user: Optional[User] = None) -> Post:
        with SqlAlchemyUoW(self._create_session) as uow:
            post = self.post_repo.get(post_id)
            if not post:
                raise PostNotFoundException(f"Post {post_id} not found")

            try:
                enforce_policy(action=Action.VIEW, resource=post, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            self.post_repo.increment_view_count(post_id)
            uow.commit()
            uow.session.refresh(post)
            return post
