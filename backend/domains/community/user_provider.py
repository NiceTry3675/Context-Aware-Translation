"""
User Provider implementation for the Community domain.

This module provides user information to the community domain
without creating direct dependencies on the User model.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.domains.shared.interfaces import (
    IUserProvider,
    UserContext,
    UserContextAdapter,
    UserPermissions
)


class CommunityUserProvider(IUserProvider):
    """
    Provides user information to the community domain.
    This implementation uses the database session to fetch user data
    without importing the User model directly in domain services.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_context(self, user_id: int) -> Optional[UserContext]:
        """Get user context by user ID."""
        # Import here to avoid circular dependency at module level
        from backend.domains.user.models import User
        
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return UserContextAdapter.to_context(user)
        return None
    
    async def get_user_context_by_clerk_id(self, clerk_id: str) -> Optional[UserContext]:
        """Get user context by Clerk ID."""
        from backend.domains.user.models import User
        
        result = await self.session.execute(
            select(User).where(User.clerk_user_id == clerk_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return UserContextAdapter.to_context(user)
        return None
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user has admin role."""
        context = await self.get_user_context(user_id)
        return context and context.role == "admin"
    
    async def user_exists(self, user_id: int) -> bool:
        """Check if user exists."""
        from backend.domains.user.models import User
        
        result = await self.session.execute(
            select(User.id).where(User.id == user_id)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_users_by_ids(self, user_ids: List[int]) -> List[UserContext]:
        """Get multiple user contexts by IDs (useful for batch operations)."""
        from backend.domains.user.models import User
        
        result = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = result.scalars().all()
        
        return [UserContextAdapter.to_context(user) for user in users]


class CommunityPermissionService:
    """
    Service for managing community permissions without direct User model dependency.
    """
    
    def __init__(self, user_provider: IUserProvider):
        self.user_provider = user_provider
    
    async def can_create_post(
        self, 
        user_context: UserContext,
        category_is_admin_only: bool
    ) -> bool:
        """Check if user can create a post in a category."""
        if category_is_admin_only:
            return user_context.role == "admin"
        return True
    
    async def can_edit_post(
        self,
        user_context: UserContext,
        post_author_id: int
    ) -> bool:
        """Check if user can edit a post."""
        permissions = UserPermissions(user_context)
        return permissions.can_edit_post(post_author_id)
    
    async def can_delete_post(
        self,
        user_context: UserContext,
        post_author_id: int
    ) -> bool:
        """Check if user can delete a post."""
        permissions = UserPermissions(user_context)
        return permissions.can_delete_post(post_author_id)
    
    async def can_edit_comment(
        self,
        user_context: UserContext,
        comment_author_id: int
    ) -> bool:
        """Check if user can edit a comment."""
        permissions = UserPermissions(user_context)
        return permissions.can_edit_comment(comment_author_id)
    
    async def can_delete_comment(
        self,
        user_context: UserContext,
        comment_author_id: int
    ) -> bool:
        """Check if user can delete a comment."""
        permissions = UserPermissions(user_context)
        return permissions.can_delete_comment(comment_author_id)
    
    async def can_view_private_post(
        self,
        user_context: UserContext,
        post_author_id: int
    ) -> bool:
        """Check if user can view a private post."""
        permissions = UserPermissions(user_context)
        return permissions.is_admin() or user_context.id == post_author_id
    
    async def can_create_announcement(
        self,
        user_context: UserContext
    ) -> bool:
        """Check if user can create announcements."""
        permissions = UserPermissions(user_context)
        return permissions.can_create_announcement()