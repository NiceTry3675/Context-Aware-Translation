from pydantic import BaseModel
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
    api_key: Optional[str] = None

class PostEditRequest(BaseModel):
    # Structured validation selection: per-segment boolean array
    # { [segmentIndex]: boolean[] }
    selected_cases: Optional[dict] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None

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