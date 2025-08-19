from pydantic import BaseModel, field_serializer
import datetime
from typing import Optional, List, Dict, Any

# Import core schemas directly
from core.schemas import (
    ValidationCase,
    ValidationResponse,
    ExtractedTerms,
    TranslatedTerms,
    TranslatedTerm,
    CharacterInteraction,
    DialogueAnalysisResult,
    NarrativeStyleDefinition,
    StyleDeviation,
)
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

# --- Base Schemas for Reusability ---
class KSTTimezoneBase(BaseModel):
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

# --- TranslationJob Schemas ---
class TranslationJobBase(BaseModel):
    filename: str

class TranslationJobCreate(TranslationJobBase):
    owner_id: int
    segment_size: int

class TranslationJob(TranslationJobBase):
    id: int
    status: str
    progress: int
    segment_size: int
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    owner_id: Optional[int] = None
    validation_enabled: Optional[bool] = None
    validation_status: Optional[str] = None
    validation_progress: Optional[int] = None
    validation_sample_rate: Optional[int] = None
    quick_validation: Optional[bool] = None
    validation_completed_at: Optional[datetime.datetime] = None
    post_edit_enabled: Optional[bool] = None
    post_edit_status: Optional[str] = None
    post_edit_progress: Optional[int] = None
    post_edit_completed_at: Optional[datetime.datetime] = None
    
    # Structured glossary data (stored as JSON in DB, parsed as Pydantic model)
    final_glossary: Optional[Dict[str, Any]] = None
    structured_glossary: Optional[TranslatedTerms] = None

    class Config:
        from_attributes = True
        
    def model_post_init(self, __context):
        """Parse JSON glossary into structured format if available"""
        if self.final_glossary and not self.structured_glossary:
            try:
                # Try to parse as TranslatedTerms format
                if 'translations' in self.final_glossary:
                    self.structured_glossary = TranslatedTerms(**self.final_glossary)
                # Or convert from dict format
                elif isinstance(self.final_glossary, dict):
                    translations = [
                        TranslatedTerm(source=k, korean=v) 
                        for k, v in self.final_glossary.items()
                    ]
                    self.structured_glossary = TranslatedTerms(translations=translations)
            except Exception:
                pass  # Keep original format if parsing fails

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
    comments: List['Comment'] = []

# --- Comment Schemas ---
class CommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None
    is_private: bool = False

class CommentCreate(CommentBase):
    post_id: int

class CommentUpdate(BaseModel):
    content: str

class Comment(CommentBase, KSTTimezoneBase):
    id: int
    author: User
    post_id: int
    replies: List['Comment'] = []

# --- Translation-related Schemas ---
# Use core GlossaryTerm (TranslatedTerm) directly
GlossaryTerm = TranslatedTerm  # Alias for backward compatibility

class StyleAnalysisResponse(BaseModel):
    """Response for style analysis - extends core NarrativeStyleDefinition"""
    protagonist_name: str
    narration_style_endings: str
    tone_keywords: str
    stylistic_rule: str
    
    # Optional structured data from core
    narrative_style: Optional[NarrativeStyleDefinition] = None
    character_styles: Optional[List[DialogueAnalysisResult]] = None

class GlossaryAnalysisResponse(BaseModel):
    """Response for glossary analysis using core schemas"""
    glossary: List[Dict[str, str]]  # Changed to List[Dict] for flexibility
    
    # Optional structured data
    extracted_terms: Optional[ExtractedTerms] = None
    translated_terms: Optional[TranslatedTerms] = None
    
    @classmethod
    def from_core_schemas(cls, extracted: ExtractedTerms, translated: TranslatedTerms):
        """Create response from core schemas"""
        # Map TranslatedTerm to frontend-compatible format
        glossary_list = [
            {"term": t.source, "translation": t.korean}
            for t in translated.translations
        ]
        return cls(
            glossary=glossary_list,
            extracted_terms=extracted,
            translated_terms=translated
        )

class ValidationRequest(BaseModel):
    quick_validation: bool = False
    validation_sample_rate: float = 1.0  # 0.0 to 1.0
    model_name: Optional[str] = None

class PostEditRequest(BaseModel):
    # Structured validation selection: per-segment boolean array
    # { [segmentIndex]: boolean[] }
    selected_cases: Optional[dict] = None
    model_name: Optional[str] = None

# Structured Post-Edit Response using core schemas  
class PostEditSegment(BaseModel):
    """Individual segment in post-edit log"""
    segment_index: int
    was_edited: bool
    source_text: str
    original_translation: str
    edited_translation: str
    validation_status: str
    structured_cases: Optional[List[ValidationCase]] = None
    changes_made: Optional[Dict[str, Any]] = None
    
class StructuredPostEditLog(BaseModel):
    """Post-edit log with structured data from core"""
    summary: Dict[str, Any]
    segments: List[PostEditSegment]
    validation_cases_fixed: Optional[List[ValidationCase]] = None  # Cases that were fixed
    
    @classmethod
    def from_json_log(cls, log_data: Dict[str, Any]):
        """Create structured log from JSON file"""
        segments = [PostEditSegment(**seg) for seg in log_data.get('segments', [])]
        
        # Extract fixed validation cases
        fixed_cases = []
        for seg in segments:
            if seg.was_edited and seg.structured_cases:
                fixed_cases.extend(seg.structured_cases)
        
        return cls(
            summary=log_data.get('summary', {}),
            segments=segments,
            validation_cases_fixed=fixed_cases if fixed_cases else None
        )

# Structured Validation Response using core schemas
class StructuredValidationReport(BaseModel):
    """Validation report with structured data from core"""
    summary: Dict[str, Any]
    detailed_results: List[Dict[str, Any]]
    validation_response: Optional[ValidationResponse] = None  # Core schema
    
    @classmethod
    def from_validation_response(cls, response: ValidationResponse, summary: Dict, results: List):
        """Create report from core ValidationResponse"""
        return cls(
            summary=summary,
            detailed_results=results,
            validation_response=response
        )

# Update forward references
Comment.model_rebuild()
Post.model_rebuild()
