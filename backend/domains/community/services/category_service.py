
from typing import List, Optional

from sqlalchemy.orm import Session, sessionmaker

from backend.domains.user.models import User
from backend.domains.community.models import PostCategory
from backend.domains.community.schemas import CategoryOverview, PostSummary, PostCategoryCreate
from backend.domains.community.repository import PostRepository, SqlAlchemyPostRepository, PostCategoryRepository
from backend.domains.community.policy import Action, check_policy, enforce_policy
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.community.exceptions import CategoryNotFoundException, PermissionDeniedException

class CategoryService:
    def __init__(self, session: Session):
        self.session = session
        self._session_factory = sessionmaker(
            bind=session.bind,
            class_=session.__class__,
            expire_on_commit=False,
        )
        self.category_repo = PostCategoryRepository(session)
        self.post_repo: PostRepository = SqlAlchemyPostRepository(session)

    def _create_session(self):
        """Create a new session for UoW transactions."""
        return self._session_factory()

    def get_categories(self) -> List[PostCategory]:
        return self.category_repo.list_ordered()

    def get_categories_with_stats(self, user: Optional[User] = None) -> List[CategoryOverview]:
        categories = self.get_categories()
        overview: List[CategoryOverview] = []

        for category in categories:
            # Use repository-level filtering instead of post-processing
            posts, total = self.post_repo.list_by_category(
                category_id=category.id,
                skip=0,
                limit=5,  # Hardcoded limit for recent posts
                user=user
            )

            recent_posts: List[PostSummary] = []
            for post in posts:
                # No need to check policy - repository already filtered

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

    async def create_category(self, category_data: PostCategoryCreate, user: User) -> PostCategory:
        """Create a new category (admin only)."""
        try:
            enforce_policy(action=Action.CREATE, user=user, metadata={'resource_type': 'category'})
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(self._create_session) as uow:
            category = PostCategory(
                name=category_data.name,
                display_name=category_data.display_name,
                description=category_data.description,
                is_admin_only=category_data.is_admin_only,
                order=category_data.order
            )
            uow.session.add(category)
            uow.commit()
            return self.category_repo.get(category.id)

    async def update_category(
        self,
        category_id: int,
        category_data: PostCategoryCreate,
        user: User
    ) -> PostCategory:
        """Update an existing category (admin only)."""
        category = self.category_repo.get(category_id)
        if not category:
            raise CategoryNotFoundException(f"Category {category_id} not found")

        try:
            enforce_policy(action=Action.EDIT, resource=category, user=user)
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(self._create_session) as uow:
            category_repo = PostCategoryRepository(uow.session)
            category = category_repo.get(category_id)

            category.name = category_data.name
            category.display_name = category_data.display_name
            category.description = category_data.description
            category.is_admin_only = category_data.is_admin_only
            category.order = category_data.order

            uow.commit()
            return category

    async def delete_category(self, category_id: int, user: User) -> None:
        """Delete a category (admin only)."""
        category = self.category_repo.get(category_id)
        if not category:
            raise CategoryNotFoundException(f"Category {category_id} not found")

        try:
            enforce_policy(action=Action.DELETE, resource=category, user=user)
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(self._create_session) as uow:
            uow.session.delete(category)
            uow.commit()

    def get_category(self, category_id: int) -> Optional[PostCategory]:
        """Get a category by ID."""
        return self.category_repo.get(category_id)
