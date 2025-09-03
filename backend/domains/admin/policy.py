"""Admin domain RBAC (Role-Based Access Control) policy layer."""

from typing import Optional, List, Protocol, Set
from dataclasses import dataclass
from enum import Enum

from backend.models.user import User


class Permission(Enum):
    """System-wide permissions."""
    
    # User management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ROLE_CHANGE = "user:role:change"
    
    # Translation management
    TRANSLATION_VIEW_ALL = "translation:view:all"
    TRANSLATION_DELETE_ANY = "translation:delete:any"
    TRANSLATION_EXPORT_ALL = "translation:export:all"
    
    # Community management
    POST_DELETE_ANY = "post:delete:any"
    POST_EDIT_ANY = "post:edit:any"
    POST_PIN = "post:pin"
    POST_LOCK = "post:lock"
    COMMENT_DELETE_ANY = "comment:delete:any"
    COMMENT_EDIT_ANY = "comment:edit:any"
    CATEGORY_CREATE = "category:create"
    CATEGORY_EDIT = "category:edit"
    CATEGORY_DELETE = "category:delete"
    
    # Announcement management
    ANNOUNCEMENT_CREATE = "announcement:create"
    ANNOUNCEMENT_EDIT = "announcement:edit"
    ANNOUNCEMENT_DELETE = "announcement:delete"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_BACKUP = "system:backup"
    
    # API management
    API_KEY_CREATE = "api:key:create"
    API_KEY_REVOKE = "api:key:revoke"
    API_RATE_LIMIT_OVERRIDE = "api:ratelimit:override"
    
    # Task management
    TASK_VIEW_ALL = "task:view:all"
    TASK_CANCEL_ANY = "task:cancel:any"
    TASK_RETRY_ANY = "task:retry:any"


class Role(Enum):
    """System roles with their permissions."""
    
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


# Role-Permission mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions
    
    Role.ADMIN: {
        # User management
        Permission.USER_VIEW,
        Permission.USER_UPDATE,
        Permission.USER_ROLE_CHANGE,
        # Translation management
        Permission.TRANSLATION_VIEW_ALL,
        Permission.TRANSLATION_DELETE_ANY,
        Permission.TRANSLATION_EXPORT_ALL,
        # Community management
        Permission.POST_DELETE_ANY,
        Permission.POST_EDIT_ANY,
        Permission.POST_PIN,
        Permission.POST_LOCK,
        Permission.COMMENT_DELETE_ANY,
        Permission.COMMENT_EDIT_ANY,
        Permission.CATEGORY_CREATE,
        Permission.CATEGORY_EDIT,
        # Announcements
        Permission.ANNOUNCEMENT_CREATE,
        Permission.ANNOUNCEMENT_EDIT,
        Permission.ANNOUNCEMENT_DELETE,
        # System
        Permission.SYSTEM_LOGS,
        Permission.SYSTEM_METRICS,
        # Tasks
        Permission.TASK_VIEW_ALL,
        Permission.TASK_CANCEL_ANY,
    },
    
    Role.MODERATOR: {
        # Limited user management
        Permission.USER_VIEW,
        # Community management
        Permission.POST_DELETE_ANY,
        Permission.POST_EDIT_ANY,
        Permission.POST_PIN,
        Permission.COMMENT_DELETE_ANY,
        Permission.COMMENT_EDIT_ANY,
        # View tasks
        Permission.TASK_VIEW_ALL,
    },
    
    Role.USER: set(),  # No special permissions
    
    Role.GUEST: set(),  # No permissions
}


@dataclass
class AdminPolicyContext:
    """Context for admin policy decisions."""
    
    user: Optional[User]
    permission: Permission
    resource: Optional[object] = None
    metadata: dict = None


class AdminPolicyResult:
    """Result of an admin policy check."""
    
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason
    
    def __bool__(self) -> bool:
        return self.allowed
    
    @classmethod
    def allow(cls, reason: str = "") -> "AdminPolicyResult":
        """Create an allowed result."""
        return cls(True, reason)
    
    @classmethod
    def deny(cls, reason: str = "") -> "AdminPolicyResult":
        """Create a denied result."""
        return cls(False, reason)


class AdminPolicy:
    """RBAC policy for administrative actions."""
    
    def __init__(self):
        """Initialize the admin policy."""
        self.role_permissions = ROLE_PERMISSIONS.copy()
    
    def get_user_role(self, user: Optional[User]) -> Role:
        """
        Get the role for a user.
        
        Args:
            user: User to check
            
        Returns:
            User's role enum
        """
        if not user:
            return Role.GUEST
        
        # Map database role to enum
        if user.role == "admin":
            # Check for super admin (could be based on specific user ID or flag)
            if hasattr(user, 'is_super_admin') and user.is_super_admin:
                return Role.SUPER_ADMIN
            return Role.ADMIN
        elif user.role == "moderator":
            return Role.MODERATOR
        else:
            return Role.USER
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """
        Get permissions for a role.
        
        Args:
            role: Role to check
            
        Returns:
            Set of permissions for the role
        """
        return self.role_permissions.get(role, set())
    
    def get_user_permissions(self, user: Optional[User]) -> Set[Permission]:
        """
        Get all permissions for a user.
        
        Args:
            user: User to check
            
        Returns:
            Set of permissions for the user
        """
        role = self.get_user_role(user)
        permissions = self.get_role_permissions(role)
        
        # Add any user-specific permissions (if implemented)
        if user and hasattr(user, 'additional_permissions'):
            permissions = permissions.union(user.additional_permissions)
        
        return permissions
    
    def has_permission(
        self,
        user: Optional[User],
        permission: Permission
    ) -> AdminPolicyResult:
        """
        Check if a user has a specific permission.
        
        Args:
            user: User to check
            permission: Permission to check for
            
        Returns:
            PolicyResult indicating if permission is granted
        """
        if not user:
            return AdminPolicyResult.deny("Authentication required")
        
        user_permissions = self.get_user_permissions(user)
        
        if permission in user_permissions:
            role = self.get_user_role(user)
            return AdminPolicyResult.allow(f"Permission granted via {role.value} role")
        
        return AdminPolicyResult.deny(f"User lacks {permission.value} permission")
    
    def can(self, context: AdminPolicyContext) -> AdminPolicyResult:
        """
        Generic permission check.
        
        Args:
            context: Context containing user and permission
            
        Returns:
            PolicyResult indicating if action is allowed
        """
        return self.has_permission(context.user, context.permission)
    
    def enforce(
        self,
        user: Optional[User],
        permission: Permission
    ) -> None:
        """
        Enforce a permission, raising PermissionError if denied.
        
        Args:
            user: User to check
            permission: Permission to enforce
            
        Raises:
            PermissionError: If permission is denied
        """
        result = self.has_permission(user, permission)
        if not result:
            raise PermissionError(result.reason or f"Permission {permission.value} denied")
    
    def require_any_permission(
        self,
        user: Optional[User],
        permissions: List[Permission]
    ) -> AdminPolicyResult:
        """
        Check if user has any of the specified permissions.
        
        Args:
            user: User to check
            permissions: List of permissions (need at least one)
            
        Returns:
            PolicyResult indicating if any permission is granted
        """
        if not user:
            return AdminPolicyResult.deny("Authentication required")
        
        user_permissions = self.get_user_permissions(user)
        
        for permission in permissions:
            if permission in user_permissions:
                return AdminPolicyResult.allow(f"Has {permission.value}")
        
        permission_names = [p.value for p in permissions]
        return AdminPolicyResult.deny(f"Requires any of: {', '.join(permission_names)}")
    
    def require_all_permissions(
        self,
        user: Optional[User],
        permissions: List[Permission]
    ) -> AdminPolicyResult:
        """
        Check if user has all of the specified permissions.
        
        Args:
            user: User to check
            permissions: List of permissions (need all)
            
        Returns:
            PolicyResult indicating if all permissions are granted
        """
        if not user:
            return AdminPolicyResult.deny("Authentication required")
        
        user_permissions = self.get_user_permissions(user)
        
        missing = []
        for permission in permissions:
            if permission not in user_permissions:
                missing.append(permission.value)
        
        if missing:
            return AdminPolicyResult.deny(f"Missing permissions: {', '.join(missing)}")
        
        return AdminPolicyResult.allow("Has all required permissions")
    
    def is_admin(self, user: Optional[User]) -> bool:
        """
        Quick check if user has admin role.
        
        Args:
            user: User to check
            
        Returns:
            True if user is admin or super admin
        """
        if not user:
            return False
        
        role = self.get_user_role(user)
        return role in {Role.ADMIN, Role.SUPER_ADMIN}
    
    def is_super_admin(self, user: Optional[User]) -> bool:
        """
        Quick check if user has super admin role.
        
        Args:
            user: User to check
            
        Returns:
            True if user is super admin
        """
        if not user:
            return False
        
        return self.get_user_role(user) == Role.SUPER_ADMIN
    
    def is_moderator_or_above(self, user: Optional[User]) -> bool:
        """
        Check if user is moderator or higher role.
        
        Args:
            user: User to check
            
        Returns:
            True if user is moderator, admin, or super admin
        """
        if not user:
            return False
        
        role = self.get_user_role(user)
        return role in {Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN}


# Global policy instance
admin_policy = AdminPolicy()


def check_permission(
    user: Optional[User],
    permission: Permission
) -> AdminPolicyResult:
    """
    Convenience function to check a permission.
    
    Args:
        user: User to check
        permission: Permission to check
        
    Returns:
        PolicyResult indicating if permission is granted
    """
    return admin_policy.has_permission(user, permission)


def enforce_permission(
    user: Optional[User],
    permission: Permission
) -> None:
    """
    Convenience function to enforce a permission.
    
    Args:
        user: User to check
        permission: Permission to enforce
        
    Raises:
        PermissionError: If permission is denied
    """
    admin_policy.enforce(user, permission)


def require_admin(user: Optional[User]) -> None:
    """
    Convenience function to require admin role.
    
    Args:
        user: User to check
        
    Raises:
        PermissionError: If user is not admin
    """
    if not admin_policy.is_admin(user):
        raise PermissionError("Admin access required")


def require_super_admin(user: Optional[User]) -> None:
    """
    Convenience function to require super admin role.
    
    Args:
        user: User to check
        
    Raises:
        PermissionError: If user is not super admin
    """
    if not admin_policy.is_super_admin(user):
        raise PermissionError("Super admin access required")