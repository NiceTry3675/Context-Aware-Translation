"""Admin domain module with RBAC."""

from .policy import (
    Permission,
    Role,
    AdminPolicy,
    AdminPolicyContext,
    AdminPolicyResult,
    admin_policy,
    check_permission,
    enforce_permission,
    require_admin,
    require_super_admin,
)
from .routes import router as admin_router

__all__ = [
    # Policy
    "Permission",
    "Role",
    "AdminPolicy",
    "AdminPolicyContext",
    "AdminPolicyResult",
    "admin_policy",
    "check_permission",
    "enforce_permission",
    "require_admin",
    "require_super_admin",
    # Router
    "admin_router",
]