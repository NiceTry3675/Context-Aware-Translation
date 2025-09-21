
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.domains.user.models import User
from backend.domains.community.models import PostCategory
from backend.domains.community.schemas import CategoryOverview, PostSummary
from backend.domains.community.repository import SqlAlchemyPostRepository, SqlAlchemyPostCategoryRepository
from backend.domains.community.policy import Action, check_policy

class CategoryService:
    def __init__(self, session: Session):
        self.session = session
        self.category_repo: SqlAlchemyPostCategoryRepository = SqlAlchemyPostCategoryRepository(session)
        self.post_repo: PostRepository = SqlAlchemyPostRepository(session)

    def get_categories(self) -> List[PostCategory]:
        return self.category_repo.list_ordered()

    def get_categories_with_stats(self, user: Optional[User] = None) -> List[CategoryOverview]:
        categories = self.get_categories()
        overview: List[CategoryOverview] = []

        for category in categories:
            # If a user is authenticated, include private posts in the initial query.
            # They will be filtered by `can_user_view` later.
            include_private_in_query = user is not None

            posts, total = self.post_repo.list_by_category(
                category_id=category.id,
                skip=0,
                limit=5,  # Hardcoded limit for recent posts
                include_private=include_private_in_query
            )

            recent_posts: List[PostSummary] = []
            for post in posts:
                if not self.post_repo.can_user_view(post.id, user):
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
