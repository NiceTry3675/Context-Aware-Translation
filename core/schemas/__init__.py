"""
Centralized schema definitions for structured output.

This module contains:
- Pydantic models for type safety and validation
- JSON schema builders for Gemini Structured Output API
- Response parsing utilities
"""

from .glossary import (
    ExtractedTerms,
    TranslatedTerms,
    TranslatedTerm,
    make_extracted_terms_schema,
    make_translated_terms_schema,
)

from .character_style import (
    CharacterInteraction,
    DialogueAnalysisResult,
    make_dialogue_analysis_schema,
)

from .narrative_style import (
    NarrativeStyleDefinition,
    StyleDeviation,
    make_narrative_style_schema,
    make_style_deviation_schema,
)

from .validation import (
    ValidationCase,
    ValidationResponse,
    make_validation_response_schema,
)

from .segment import SegmentInfo
from .document import TranslationDocumentData
from .illustration import (
    IllustrationStyle,
    IllustrationStatus,
    IllustrationConfig,
    IllustrationData,
    IllustrationBatch,
    CameraDistance,
    CameraAngle,
    IllustrationWorthiness,
    CharacterVisualInfo,
    LightingInfo,
    CameraInfo,
    VisualElements,
)

__all__ = [
    # Glossary
    "ExtractedTerms",
    "TranslatedTerms",
    "TranslatedTerm",
    "make_extracted_terms_schema",
    "make_translated_terms_schema",
    # Character Style
    "CharacterInteraction",
    "DialogueAnalysisResult",
    "make_dialogue_analysis_schema",
    # Narrative Style
    "NarrativeStyleDefinition",
    "StyleDeviation",
    "make_narrative_style_schema",
    "make_style_deviation_schema",
    # Validation
    "ValidationCase",
    "ValidationResponse",
    "make_validation_response_schema",
    # Document and Segment
    "SegmentInfo",
    "TranslationDocumentData",
    # Illustration
    "IllustrationStyle",
    "IllustrationStatus",
    "IllustrationConfig",
    "IllustrationData",
    "IllustrationBatch",
    "CameraDistance",
    "CameraAngle",
    "IllustrationWorthiness",
    "CharacterVisualInfo",
    "LightingInfo",
    "CameraInfo",
    "VisualElements",
]