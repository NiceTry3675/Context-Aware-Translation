"""
User Provider implementation for the Translation domain.

This module provides user information to the translation domain
without creating direct dependencies on the User model.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.domains.shared.interfaces import (
    IUserProvider,
    UserContext,
    UserContextAdapter
)


class TranslationUserProvider(IUserProvider):
    """
    Provides user information to the translation domain.
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


class TranslationOwnershipService:
    """
    Service for managing job ownership without direct User model dependency.
    """
    
    def __init__(self, user_provider: IUserProvider):
        self.user_provider = user_provider
    
    async def can_access_job(
        self, 
        user_id: int, 
        job_owner_id: Optional[int]
    ) -> bool:
        """Check if user can access a translation job."""
        # Admin can access all jobs
        if await self.user_provider.is_admin(user_id):
            return True
        
        # Legacy jobs without owner (accessible by admin only)
        if job_owner_id is None:
            return False
        
        # Owner can access their own jobs
        return user_id == job_owner_id
    
    async def assign_job_owner(
        self,
        job_id: int,
        user_context: UserContext
    ) -> None:
        """Assign ownership of a job to a user."""
        # This would update the job's owner_id field
        # Implementation depends on how you want to handle this
        pass