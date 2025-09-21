"""Community domain authorization policy layer."""

from typing import Optional, Protocol
from dataclasses import dataclass
from enum import Enum

from backend.domains.user.models import User
from backend.domains.community.models import Post, Comment, PostCategory


class Action(Enum):
    """Enumeration of possible actions on community resources."""
    
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    PIN = "pin"
    LOCK = "lock"
    MAKE_PRIVATE = "make_private"
    MODERATE = "moderate"


@dataclass
class PolicyContext:
    """Context for policy decisions."""
    
    user: Optional[User]
    action: Action
    resource: Optional[object] = None
    parent_resource: Optional[object] = None
    metadata: dict = None


class PolicyResult:
    """Result of a policy check with reason."""
    
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason
    
    def __bool__(self) -> bool:
        return self.allowed
    
    @classmethod
    def allow(cls, reason: str = "") -> "PolicyResult":
        """Create an allowed result."""
        return cls(True, reason)
    
    @classmethod
    def deny(cls, reason: str = "") -> "PolicyResult":
        """Create a denied result."""
        return cls(False, reason)


class Policy(Protocol):
    """Base policy protocol."""
    
    def can(self, context: PolicyContext) -> PolicyResult:
        """Check if action is allowed in given context."""
        ...


class PostPolicy:
    """Authorization policy for posts."""
    
    def can_view(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can view a post."""
        # Public posts can be viewed by anyone
        if not post.is_private:
            return PolicyResult.allow("Post is public")
        
        # Private posts require authentication
        if not user:
            return PolicyResult.deny("Authentication required for private posts")
        
        # Author can view their own posts
        if post.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can view all posts
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to view private post")
    
    def can_create(self, category: PostCategory, user: Optional[User]) -> PolicyResult:
        """Check if user can create a post in a category."""
        if not user:
            return PolicyResult.deny("Authentication required to create posts")
        
        # Admin-only categories require admin role
        if category.is_admin_only and user.role != "admin":
            return PolicyResult.deny(f"Category '{category.name}' is admin-only")
        
        return PolicyResult.allow("User can create posts in this category")
    
    def can_edit(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can edit a post."""
        if not user:
            return PolicyResult.deny("Authentication required to edit posts")
        
        # Author can edit their own posts
        if post.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can edit all posts
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to edit this post")
    
    def can_delete(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can delete a post."""
        if not user:
            return PolicyResult.deny("Authentication required to delete posts")
        
        # Author can delete their own posts
        if post.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can delete all posts
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to delete this post")
    
    def can_pin(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can pin/unpin a post."""
        if not user:
            return PolicyResult.deny("Authentication required to pin posts")
        
        # Only admins can pin posts
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can pin posts")
    
    def can_lock(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can lock/unlock a post for comments."""
        if not user:
            return PolicyResult.deny("Authentication required to lock posts")
        
        # Post author can lock their own posts
        if post.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can lock any post
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to lock this post")
    
    def can_make_private(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can change post visibility."""
        if not user:
            return PolicyResult.deny("Authentication required to change post visibility")
        
        # Post author can change their own post visibility
        if post.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can change any post visibility
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to change post visibility")


class CommentPolicy:
    """Authorization policy for comments."""
    
    def can_view(self, comment: Comment, user: Optional[User]) -> PolicyResult:
        """Check if user can view a comment."""
        # Public comments can be viewed by anyone
        if not comment.is_private:
            return PolicyResult.allow("Comment is public")
        
        # Private comments require authentication
        if not user:
            return PolicyResult.deny("Authentication required for private comments")
        
        # Comment author can view their own comments
        if comment.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Post author can view all comments on their post
        if hasattr(comment, 'post') and comment.post and comment.post.author_id == user.id:
            return PolicyResult.allow("User is the post author")
        
        # Admins can view all comments
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to view private comment")
    
    def can_create(self, post: Post, user: Optional[User]) -> PolicyResult:
        """Check if user can create a comment on a post."""
        if not user:
            return PolicyResult.deny("Authentication required to comment")
        
        # Check if post is locked
        if hasattr(post, 'is_locked') and post.is_locked:
            # Only post author and admins can comment on locked posts
            if post.author_id != user.id and user.role != "admin":
                return PolicyResult.deny("Post is locked for comments")
        
        # Check if post is private
        if post.is_private:
            # Must be able to view the post to comment on it
            post_policy = PostPolicy()
            view_result = post_policy.can_view(post, user)
            if not view_result:
                return PolicyResult.deny("Cannot comment on posts you cannot view")
        
        return PolicyResult.allow("User can comment on this post")
    
    def can_edit(self, comment: Comment, user: Optional[User]) -> PolicyResult:
        """Check if user can edit a comment."""
        if not user:
            return PolicyResult.deny("Authentication required to edit comments")
        
        # Author can edit their own comments
        if comment.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can edit all comments
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to edit this comment")
    
    def can_delete(self, comment: Comment, user: Optional[User]) -> PolicyResult:
        """Check if user can delete a comment."""
        if not user:
            return PolicyResult.deny("Authentication required to delete comments")
        
        # Author can delete their own comments
        if comment.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Post author can delete comments on their posts
        if hasattr(comment, 'post') and comment.post and comment.post.author_id == user.id:
            return PolicyResult.allow("User is the post author")
        
        # Admins can delete all comments
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to delete this comment")
    
    def can_make_private(self, comment: Comment, user: Optional[User]) -> PolicyResult:
        """Check if user can change comment visibility."""
        if not user:
            return PolicyResult.deny("Authentication required to change comment visibility")
        
        # Comment author can change their own comment visibility
        if comment.author_id == user.id:
            return PolicyResult.allow("User is the author")
        
        # Admins can change any comment visibility
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("User lacks permission to change comment visibility")


class CategoryPolicy:
    """Authorization policy for categories."""
    
    def can_view(self, category: PostCategory, user: Optional[User]) -> PolicyResult:
        """Check if user can view a category."""
        # All categories are viewable (but posting may be restricted)
        return PolicyResult.allow("Categories are public")
    
    def can_create(self, user: Optional[User]) -> PolicyResult:
        """Check if user can create a category."""
        if not user:
            return PolicyResult.deny("Authentication required to create categories")
        
        # Only admins can create categories
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can create categories")
    
    def can_edit(self, category: PostCategory, user: Optional[User]) -> PolicyResult:
        """Check if user can edit a category."""
        if not user:
            return PolicyResult.deny("Authentication required to edit categories")
        
        # Only admins can edit categories
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can edit categories")
    
    def can_delete(self, category: PostCategory, user: Optional[User]) -> PolicyResult:
        """Check if user can delete a category."""
        if not user:
            return PolicyResult.deny("Authentication required to delete categories")
        
        # Only admins can delete categories
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can delete categories")
    
    def can_post_in(self, category: PostCategory, user: Optional[User]) -> PolicyResult:
        """Check if user can post in a category."""
        if not user:
            return PolicyResult.deny("Authentication required to post")
        
        # Admin-only categories require admin role
        if category.is_admin_only and user.role != "admin":
            return PolicyResult.deny(f"Category '{category.name}' is admin-only")
        
        return PolicyResult.allow("User can post in this category")


class AnnouncementPolicy:
    """Authorization policy for announcements."""
    
    def can_view(self, user: Optional[User]) -> PolicyResult:
        """Check if user can view announcements."""
        # All users can view active announcements
        return PolicyResult.allow("Announcements are public")
    
    def can_create(self, user: Optional[User]) -> PolicyResult:
        """Check if user can create announcements."""
        if not user:
            return PolicyResult.deny("Authentication required to create announcements")
        
        # Only admins can create announcements
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can create announcements")
    
    def can_edit(self, user: Optional[User]) -> PolicyResult:
        """Check if user can edit announcements."""
        if not user:
            return PolicyResult.deny("Authentication required to edit announcements")
        
        # Only admins can edit announcements
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can edit announcements")
    
    def can_delete(self, user: Optional[User]) -> PolicyResult:
        """Check if user can delete announcements."""
        if not user:
            return PolicyResult.deny("Authentication required to delete announcements")
        
        # Only admins can delete announcements
        if user.role == "admin":
            return PolicyResult.allow("User is an admin")
        
        return PolicyResult.deny("Only admins can delete announcements")


class CommunityPolicy:
    """Composite policy for all community resources."""
    
    def __init__(self):
        self.post = PostPolicy()
        self.comment = CommentPolicy()
        self.category = CategoryPolicy()
        self.announcement = AnnouncementPolicy()
    
    def can(self, context: PolicyContext) -> PolicyResult:
        """
        Generic policy check dispatcher.
        
        Routes to the appropriate policy based on resource type.
        """
        resource = context.resource
        action = context.action
        user = context.user
        
        if isinstance(resource, Post):
            if action == Action.VIEW:
                return self.post.can_view(resource, user)
            elif action == Action.CREATE:
                # For post creation, parent_resource should be the category
                if context.parent_resource and isinstance(context.parent_resource, PostCategory):
                    return self.post.can_create(context.parent_resource, user)
                return PolicyResult.deny("Category required for post creation")
            elif action == Action.EDIT:
                return self.post.can_edit(resource, user)
            elif action == Action.DELETE:
                return self.post.can_delete(resource, user)
            elif action == Action.PIN:
                return self.post.can_pin(resource, user)
            elif action == Action.LOCK:
                return self.post.can_lock(resource, user)
            elif action == Action.MAKE_PRIVATE:
                return self.post.can_make_private(resource, user)
        
        elif isinstance(resource, Comment):
            if action == Action.VIEW:
                return self.comment.can_view(resource, user)
            elif action == Action.CREATE:
                # For comment creation, parent_resource should be the post
                if context.parent_resource and isinstance(context.parent_resource, Post):
                    return self.comment.can_create(context.parent_resource, user)
                return PolicyResult.deny("Post required for comment creation")
            elif action == Action.EDIT:
                return self.comment.can_edit(resource, user)
            elif action == Action.DELETE:
                return self.comment.can_delete(resource, user)
            elif action == Action.MAKE_PRIVATE:
                return self.comment.can_make_private(resource, user)
        
        elif isinstance(resource, PostCategory):
            if action == Action.VIEW:
                return self.category.can_view(resource, user)
            elif action == Action.CREATE:
                return self.category.can_create(user)
            elif action == Action.EDIT:
                return self.category.can_edit(resource, user)
            elif action == Action.DELETE:
                return self.category.can_delete(resource, user)
        
        elif resource is None and action == Action.CREATE:
            # Handle creation without a specific resource
            if context.parent_resource and isinstance(context.parent_resource, PostCategory):
                # Creating a post in a category
                return self.post.can_create(context.parent_resource, user)
            elif context.parent_resource and isinstance(context.parent_resource, Post):
                # Creating a comment on a post
                return self.comment.can_create(context.parent_resource, user)
            elif context.metadata and context.metadata.get('resource_type') == 'announcement':
                return self.announcement.can_create(user)
            elif context.metadata and context.metadata.get('resource_type') == 'category':
                return self.category.can_create(user)
        
        return PolicyResult.deny("Unknown resource or action")
    
    def enforce(self, context: PolicyContext) -> None:
        """
        Enforce a policy, raising PermissionError if denied.
        
        Args:
            context: The policy context to check
            
        Raises:
            PermissionError: If the action is not allowed
        """
        result = self.can(context)
        if not result:
            raise PermissionError(result.reason or "Permission denied")


def check_policy(
    action: Action,
    resource: Optional[object] = None,
    user: Optional[User] = None,
    parent: Optional[object] = None,
    metadata: dict = None
) -> PolicyResult:
    """
    Convenience function to check a policy.
    
    Args:
        action: The action to check
        resource: The resource being acted upon
        user: The user performing the action
        parent: Parent resource (e.g., category for post creation)
        metadata: Additional context information
    
    Returns:
        PolicyResult indicating if action is allowed
    """
    policy = CommunityPolicy()
    context = PolicyContext(
        user=user,
        action=action,
        resource=resource,
        parent_resource=parent,
        metadata=metadata
    )
    return policy.can(context)


def enforce_policy(
    action: Action,
    resource: Optional[object] = None,
    user: Optional[User] = None,
    parent: Optional[object] = None,
    metadata: dict = None
) -> None:
    """
    Convenience function to enforce a policy.
    
    Args:
        action: The action to check
        resource: The resource being acted upon
        user: The user performing the action
        parent: Parent resource (e.g., category for post creation)
        metadata: Additional context information
    
    Raises:
        PermissionError: If the action is not allowed
    """
    policy = CommunityPolicy()
    context = PolicyContext(
        user=user,
        action=action,
        resource=resource,
        parent_resource=parent,
        metadata=metadata
    )
    policy.enforce(context)