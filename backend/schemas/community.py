from __future__ import annotations
from pydantic import BaseModel, field_serializer
from typing import Optional, List
import datetime
from .base import KSTTimezoneBase, UTC_ZONE, KST_ZONE

# Forward declaration to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User

# --- PostCategory Schemas ---
class PostCategoryBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    is_admin_only: bool = False
    order: int = 0

class PostCategoryCreate(PostCategoryBase):
    pass

class PostCategory(PostCategoryBase):
    id: int
    created_at: datetime.datetime

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)

    class Config:
        from_attributes = True

# --- Post Schemas ---
class PostBase(BaseModel):
    title: str
    content: str
    category_id: int
    is_pinned: bool = False
    is_private: bool = False
    images: list[str] = []  # List of image URLs

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None
    images: Optional[list[str]] = None

# --- Comment Schemas ---
class CommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None
    is_private: bool = False

class CommentCreate(CommentBase):
    post_id: int

class CommentUpdate(BaseModel):
    content: str

# Forward references will be updated after all imports in __init__.py
class PostList(KSTTimezoneBase):
    id: int
    title: str
    author: User
    category: PostCategory
    is_pinned: bool
    is_private: bool
    view_count: int
    images: list[str] = []
    comment_count: int = 0

class Post(PostBase, KSTTimezoneBase):
    id: int
    author: User
    category: PostCategory
    view_count: int
    comments: List[Comment] = []

class Comment(CommentBase, KSTTimezoneBase):
    id: int
    author: User
    post_id: int
    replies: List[Comment] = []