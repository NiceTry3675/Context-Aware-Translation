"""
Shared interfaces for cross-domain communication.
"""

from .user_context import (
    IUserContext,
    UserContext,
    IUserProvider,
    UserContextAdapter,
    UserPermissions,
)

__all__ = [
    "IUserContext",
    "UserContext", 
    "IUserProvider",
    "UserContextAdapter",
    "UserPermissions",
]