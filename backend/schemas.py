from pydantic import BaseModel
import datetime
from typing import Optional

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
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

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
