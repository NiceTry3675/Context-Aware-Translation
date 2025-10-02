"""Analysis domain schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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

# --- Analysis Response Schemas ---

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


class CharacterAnalysisResponse(BaseModel):
    """Response for character analysis"""
    characters: List[Dict[str, Any]]
    interactions: Optional[List[CharacterInteraction]] = None
    dialogue_analysis: Optional[List[DialogueAnalysisResult]] = None


# Backward compatibility aliases
GlossaryTerm = TranslatedTerm