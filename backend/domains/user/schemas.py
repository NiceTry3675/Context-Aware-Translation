"""User domain schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

# Import shared base schemas from the shared domain
from backend.domains.shared.schemas import KSTTimezoneBase

# --- User Schemas ---
class UserBase(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None

class UserCreate(UserBase):
    clerk_user_id: str

class UserUpdate(UserBase):
    pass

class User(UserBase, KSTTimezoneBase):
    id: int
    clerk_user_id: str
    role: str = "user"
    api_provider: Optional[str] = None
    gemini_model: Optional[str] = None
    vertex_model: Optional[str] = None
    openrouter_model: Optional[str] = None

# --- API Configuration Schemas ---
class ApiConfigurationBase(BaseModel):
    api_provider: Optional[str] = None  # "gemini", "vertex", "openrouter"
    api_key: Optional[str] = None  # For gemini/openrouter
    provider_config: Optional[str] = None  # Vertex JSON config
    gemini_model: Optional[str] = None
    vertex_model: Optional[str] = None
    openrouter_model: Optional[str] = None

class ApiConfigurationUpdate(ApiConfigurationBase):
    pass

class ApiConfiguration(BaseModel):
    api_provider: Optional[str] = None
    api_key: Optional[str] = None  # Will be decrypted from storage
    provider_config: Optional[str] = None  # Will be decrypted from storage
    gemini_model: Optional[str] = None
    vertex_model: Optional[str] = None
    openrouter_model: Optional[str] = None

# --- TranslationUsageLog Schemas ---
class TranslationUsageLogBase(BaseModel):
    job_id: int
    user_id: Optional[int] = None
    original_length: int
    translated_length: int
    translation_duration_seconds: int
    model_used: str
    error_type: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class TranslationUsageLogCreate(TranslationUsageLogBase):
    pass

class TranslationUsageLog(TranslationUsageLogBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class TokenUsageTotals(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ModelTokenUsage(TokenUsageTotals):
    model: str


class IllustrationUsageTotals(TokenUsageTotals):
    image_count: int
    per_model: List[ModelTokenUsage] = Field(default_factory=list)


class TokenUsageDashboard(BaseModel):
    total: TokenUsageTotals
    per_model: List[ModelTokenUsage]
    illustrations: IllustrationUsageTotals
    last_updated: Optional[datetime.datetime] = None

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
