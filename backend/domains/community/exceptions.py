
class CommunityException(Exception):
    """Base exception for the community domain."""
    def __init__(self, detail: str):
        self.detail = detail

class PostNotFoundException(CommunityException):
    """Raised when a post is not found."""
    pass

class CommentNotFoundException(CommunityException):
    """Raised when a comment is not found."""
    pass

class CategoryNotFoundException(CommunityException):
    """Raised when a category is not found."""
    pass

class PermissionDeniedException(CommunityException):
    """Raised when a user lacks permission to perform an action."""
    pass
