"""Translation domain schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import datetime

# Import core schemas directly
from core.schemas import (
    ExtractedTerms,
    TranslatedTerms,
    TranslatedTerm,
    CharacterInteraction,
    DialogueAnalysisResult,
    NarrativeStyleDefinition,
    StyleDeviation,
)

# --- TranslationJob Schemas ---
class TranslationJobBase(BaseModel):
    filename: str

class TranslationJobCreate(TranslationJobBase):
    owner_id: int
    segment_size: int

class TranslationJobListItem(TranslationJobBase):
    """Lightweight schema for listing jobs - excludes large JSON fields"""
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
    validation_completed_at: Optional[datetime.datetime] = None
    post_edit_enabled: Optional[bool] = None
    post_edit_status: Optional[str] = None
    post_edit_progress: Optional[int] = None
    post_edit_completed_at: Optional[datetime.datetime] = None

    # Illustration fields - lightweight (exclude data)
    illustrations_enabled: Optional[bool] = None
    illustrations_status: Optional[str] = None
    illustrations_progress: Optional[int] = None
    illustrations_count: Optional[int] = None

    class Config:
        from_attributes = True

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
    validation_report_path: Optional[str] = None
    post_edit_enabled: Optional[bool] = None
    post_edit_status: Optional[str] = None
    post_edit_progress: Optional[int] = None
    post_edit_completed_at: Optional[datetime.datetime] = None
    post_edit_log_path: Optional[str] = None
    
    # Illustration fields
    illustrations_enabled: Optional[bool] = None
    illustrations_status: Optional[str] = None
    illustrations_progress: Optional[int] = None
    illustrations_count: Optional[int] = None
    illustrations_data: Optional[List[Dict[str, Any]]] = None
    
    # Character base workflow
    character_profile: Optional[Dict[str, Any]] = None
    character_base_images: Optional[List[Dict[str, Any]]] = None
    character_base_selected_index: Optional[int] = None
    character_base_directory: Optional[str] = None
    
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

# --- Translation-related Schemas ---
# Use core GlossaryTerm (TranslatedTerm) directly
GlossaryTerm = TranslatedTerm  # Alias for backward compatibility


# --- Requests ---
class ResumeRequest(BaseModel):
    """Request payload for resuming a failed translation job."""
    api_key: Optional[str] = None
    model_name: Optional[str] = "gemini-flash-lite-latest"
    translation_model_name: Optional[str] = None
    style_model_name: Optional[str] = None
    glossary_model_name: Optional[str] = None
    api_provider: Optional[str] = "gemini"
    provider_config: Optional[str] = None
    turbo_mode: Optional[bool] = False


