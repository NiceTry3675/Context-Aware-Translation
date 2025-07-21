from pydantic import BaseModel, field_serializer
import datetime
from typing import Optional, List
try:
    from zoneinfo import ZoneInfo
    # Windows 환경 호환을 위한 UTC 처리
    try:
        UTC_ZONE = ZoneInfo('UTC')
    except:
        UTC_ZONE = datetime.timezone.utc
    
    try:
        KST_ZONE = ZoneInfo('Asia/Seoul')
    except:
        # 백업: UTC+9 시간대 직접 생성
        KST_ZONE = datetime.timezone(datetime.timedelta(hours=9))
except ImportError:
    # Python < 3.9 또는 zoneinfo 없는 경우
    UTC_ZONE = datetime.timezone.utc
    KST_ZONE = datetime.timezone(datetime.timedelta(hours=9))

# --- User Schemas ---
class UserBase(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None

class UserCreate(UserBase):
    clerk_user_id: str

class UserUpdate(UserBase):
    pass

class User(UserBase):
    id: int
    clerk_user_id: str
    role: str = "user"
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            # UTC로 가정하고 한국 시간으로 변환
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)

    class Config:
        from_attributes = True

# --- TranslationJob Schemas ---
class TranslationJobBase(BaseModel):
    filename: str

class TranslationJobCreate(TranslationJobBase):
    owner_id: int

class TranslationJob(TranslationJobBase):
    id: int
    status: str
    progress: int
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- TranslationUsageLog Schemas ---
class TranslationUsageLogBase(BaseModel):
    job_id: int
    original_length: int
    translated_length: int
    translation_duration_seconds: int
    model_used: str
    error_type: Optional[str] = None

class TranslationUsageLogCreate(TranslationUsageLogBase):
    pass

class TranslationUsageLog(TranslationUsageLogBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Announcement Schemas ---
class AnnouncementBase(BaseModel):
    message: str
    is_active: bool = True

class AnnouncementCreate(AnnouncementBase):
    pass

class Announcement(AnnouncementBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

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

class PostList(BaseModel):
    id: int
    title: str
    author: User
    category: PostCategory
    is_pinned: bool
    is_private: bool
    view_count: int
    images: list[str] = []
    comment_count: int = 0
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)

    class Config:
        from_attributes = True

class Post(PostBase):
    id: int
    author: User
    category: PostCategory
    view_count: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)

    class Config:
        from_attributes = True

# --- Comment Schemas ---
class CommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None
    is_private: bool = False

class CommentCreate(CommentBase):
    post_id: int

class CommentUpdate(BaseModel):
    content: str

class Comment(CommentBase):
    id: int
    author: User
    post_id: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    replies: List['Comment'] = []

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)

    class Config:
        from_attributes = True

# Update forward references
Comment.model_rebuild()
