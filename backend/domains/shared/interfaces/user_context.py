"""
User Context Interface for Cross-Domain Communication

This module defines interfaces that expose only necessary user information
to each domain, avoiding direct coupling to the User model.
"""

from typing import Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from pydantic import BaseModel


@runtime_checkable
class IUserContext(Protocol):
    """
    Protocol defining the minimal user context needed by domains.
    This is a structural typing interface that any object can satisfy.
    """
    
    @property
    def id(self) -> int:
        """User's database ID."""
        ...
    
    @property
    def clerk_id(self) -> str:
        """User's Clerk authentication ID."""
        ...
    
    @property
    def email(self) -> Optional[str]:
        """User's email address."""
        ...
    
    @property
    def name(self) -> Optional[str]:
        """User's display name."""
        ...
    
    @property
    def role(self) -> str:
        """User's role (e.g., 'user', 'admin')."""
        ...


class UserContext(BaseModel):
    """
    Value object representing user context for cross-domain communication.
    This is a concrete implementation that can be passed between domains.
    """
    
    id: int
    clerk_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str = "user"
    
    class Config:
        frozen = True  # Make immutable
        
    @classmethod
    def from_user_model(cls, user: any) -> "UserContext":
        """Create UserContext from a User model instance."""
        return cls(
            id=user.id,
            clerk_id=user.clerk_user_id,
            email=user.email,
            name=user.name,
            role=user.role
        )


class IUserProvider(ABC):
    """
    Abstract interface for providing user information to domains.
    Each domain can implement this to fetch user data without knowing
    about the User model structure.
    """
    
    @abstractmethod
    async def get_user_context(self, user_id: int) -> Optional[UserContext]:
        """Get user context by user ID."""
        pass
    
    @abstractmethod
    async def get_user_context_by_clerk_id(self, clerk_id: str) -> Optional[UserContext]:
        """Get user context by Clerk ID."""
        pass
    
    @abstractmethod
    async def is_admin(self, user_id: int) -> bool:
        """Check if user has admin role."""
        pass
    
    @abstractmethod
    async def user_exists(self, user_id: int) -> bool:
        """Check if user exists."""
        pass


class UserContextAdapter:
    """
    Adapter to convert between User model and UserContext.
    This helps in gradual migration from direct User model usage.
    """
    
    @staticmethod
    def to_context(user: any) -> UserContext:
        """Convert User model to UserContext."""
        if user is None:
            return None
        
        return UserContext(
            id=user.id,
            clerk_id=user.clerk_user_id,
            email=user.email,
            name=user.name,
            role=user.role
        )
    
    @staticmethod
    def to_dict(context: UserContext) -> dict:
        """Convert UserContext to dictionary."""
        return {
            "id": context.id,
            "clerk_id": context.clerk_id,
            "email": context.email,
            "name": context.name,
            "role": context.role
        }


class UserPermissions:
    """
    Encapsulates user permission checks without exposing User model.
    """
    
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.user_context.role == "admin"
    
    def can_edit_post(self, post_author_id: int) -> bool:
        """Check if user can edit a post."""
        return self.is_admin() or self.user_context.id == post_author_id
    
    def can_delete_post(self, post_author_id: int) -> bool:
        """Check if user can delete a post."""
        return self.is_admin() or self.user_context.id == post_author_id
    
    def can_edit_comment(self, comment_author_id: int) -> bool:
        """Check if user can edit a comment."""
        return self.is_admin() or self.user_context.id == comment_author_id
    
    def can_delete_comment(self, comment_author_id: int) -> bool:
        """Check if user can delete a comment."""
        return self.is_admin() or self.user_context.id == comment_author_id
    
    def can_create_announcement(self) -> bool:
        """Check if user can create announcements."""
        return self.is_admin()
    
    def can_access_job(self, job_owner_id: Optional[int]) -> bool:
        """Check if user can access a translation job."""
        if job_owner_id is None:
            # Legacy jobs without owner
            return self.is_admin()
        return self.is_admin() or self.user_context.id == job_owner_id