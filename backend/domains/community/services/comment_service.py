
from typing import List, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session, sessionmaker

from backend.domains.user.models import User
from backend.domains.community.models import Comment
from backend.domains.community.schemas import CommentCreate, CommentUpdate
from backend.domains.community.repository import CommentRepository, SqlAlchemyCommentRepository, PostRepository, SqlAlchemyPostRepository
from backend.domains.community.policy import Action, enforce_policy, check_policy
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import CommentAddedEvent, CommentDeletedEvent
from backend.domains.community.exceptions import PostNotFoundException, CommentNotFoundException, PermissionDeniedException

class CommentService:
    def __init__(self, session: Session):
        self.session = session
        self._session_factory = sessionmaker(
            bind=session.bind,
            class_=session.__class__,
            expire_on_commit=False,
        )
        self.comment_repo: CommentRepository = SqlAlchemyCommentRepository(session)
        self.post_repo: PostRepository = SqlAlchemyPostRepository(session)

    def _create_session(self):
        """Create a new session for UoW transactions."""
        return self._session_factory()

    async def create_comment(self, comment_data: CommentCreate, user: User) -> Comment:
        with SqlAlchemyUoW(self._create_session) as uow:
            # Use repositories bound to the UoW session for consistency
            post_repo = SqlAlchemyPostRepository(uow.session)
            comment_repo = SqlAlchemyCommentRepository(uow.session)
            post = post_repo.get(comment_data.post_id)
            if not post:
                raise PostNotFoundException(f"Post {comment_data.post_id} not found")

            try:
                enforce_policy(action=Action.CREATE, parent=post, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            # Merge user object into the current session to avoid session conflicts
            user = uow.session.merge(user)

            comment = Comment(
                content=comment_data.content,
                post_id=comment_data.post_id,
                author=user,
                parent_id=comment_data.parent_id,
                is_private=comment_data.is_private,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            if comment_data.parent_id:
                parent_comment = comment_repo.get(comment_data.parent_id)
                if not parent_comment:
                    raise CommentNotFoundException(f"Parent comment {comment_data.parent_id} not found")
                if parent_comment.post_id != comment_data.post_id:
                    raise CommentNotFoundException("Parent comment must be on the same post")

            uow.session.add(comment)
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
            # Return a fresh copy with all relationships loaded from a repository
            return SqlAlchemyCommentRepository(self.session).get(comment.id)

    async def update_comment(self, comment_id: int, comment_update: CommentUpdate, user: User) -> Comment:
        with SqlAlchemyUoW(self._create_session) as uow:
            # Use repository bound to UoW session
            comment_repo = SqlAlchemyCommentRepository(uow.session)
            comment = comment_repo.get(comment_id)
            if not comment:
                raise CommentNotFoundException(f"Comment {comment_id} not found")

            try:
                enforce_policy(action=Action.EDIT, resource=comment, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            if comment_update.content is not None:
                comment.content = comment_update.content

            if comment_update.is_private is not None:
                if comment.is_private != comment_update.is_private:
                    try:
                        enforce_policy(action=Action.MAKE_PRIVATE, resource=comment, user=user)
                    except PermissionError as e:
                        raise PermissionDeniedException(str(e))
                comment.is_private = comment_update.is_private

            comment.updated_at = datetime.utcnow()

            uow.commit()
            # Return a fresh copy with all relationships loaded from a repository
            return SqlAlchemyCommentRepository(self.session).get(comment.id)

    async def delete_comment(self, comment_id: int, user: User) -> None:
        with SqlAlchemyUoW(self._create_session) as uow:
            # Use repository bound to UoW session
            comment_repo = SqlAlchemyCommentRepository(uow.session)
            comment = comment_repo.get(comment_id)
            if not comment:
                raise CommentNotFoundException(f"Comment {comment_id} not found")

            try:
                enforce_policy(action=Action.DELETE, resource=comment, user=user)
            except PermissionError as e:
                raise PermissionDeniedException(str(e))

            # Replies are deleted by cascade
            uow.session.delete(comment)

            uow.add_event(CommentDeletedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(comment.id),
                comment_id=comment.id,
                post_id=comment.post_id,
                author_id=comment.author_id,
                deleted_by=user.id
            ))

            uow.commit()

    def get_comments_for_post(self, post_id: int, user: Optional[User] = None) -> List[Comment]:
        comments = self.comment_repo.get_by_post(post_id)
        # Filter comments based on view permissions using policy
        visible_comments = [c for c in comments if check_policy(Action.VIEW, resource=c, user=user).allowed]
        return visible_comments
