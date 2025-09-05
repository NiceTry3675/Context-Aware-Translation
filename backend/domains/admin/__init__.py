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
]