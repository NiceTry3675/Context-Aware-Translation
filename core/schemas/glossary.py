"""
Glossary-related schemas for structured output.

This module defines schemas for:
- Extracting proper nouns from text
- Translating terms with consistency
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# --------------------
# Pydantic Models
# --------------------

class ExtractedTerms(BaseModel):
    """Response model for proper noun extraction."""
    
    terms: List[str] = Field(
        default_factory=list,
        description="List of unique proper nouns found in the text. Empty list if none found."
    )
    
    def to_comma_separated(self) -> str:
        """Convert to comma-separated string for backward compatibility."""
        if not self.terms:
            return "N/A"
        return ", ".join(sorted(set(self.terms)))


class TranslatedTerm(BaseModel):
    """Single term translation pair."""
    
    source: str = Field(..., description="Source term in English")
    korean: str = Field(..., description="Korean translation")


class TranslatedTerms(BaseModel):
    """Response model for term translation."""
    
    translations: List[TranslatedTerm] = Field(
        default_factory=list,
        description="List of term translations"
    )
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for backward compatibility."""
        return {t.source: t.korean for t in self.translations}


# --------------------
# JSON Schema Builders (for Gemini API)
# --------------------

def make_extracted_terms_schema() -> Dict[str, Any]:
    """
    Create JSON schema for proper noun extraction.
    
    Gemini Structured Output uses simplified schemas:
    - No minimum/maximum constraints
    - Prefer enum for specific values
    - Keep structure simple and flat when possible
    """
    return {
        "type": "object",
        "properties": {
            "terms": {
                "type": "array",
                "description": "List of unique proper nouns found in the text. Empty array if none found.",
                "items": {
                    "type": "string",
                    "description": "A proper noun (person name, place, organization, or unique concept)"
                }
            }
        },
        "required": ["terms"]
    }


def make_translated_terms_schema(source_terms: List[str]) -> Dict[str, Any]:
    """
    Create JSON schema for term translation.
    
    Args:
        source_terms: List of terms that need translation
        
    Returns:
        JSON schema with specific terms enumerated
    """
    return {
        "type": "object",
        "properties": {
            "translations": {
                "type": "array",
                "description": "List of term translations",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "enum": source_terms,  # Constrain to specific terms
                            "description": "Source term in English"
                        },
                        "korean": {
                            "type": "string",
                            "description": "Korean translation of the term"
                        }
                    },
                    "required": ["source", "korean"]
                }
            }
        },
        "required": ["translations"]
    }


# --------------------
# Helper Functions
# --------------------

def parse_extracted_terms_response(response: Dict[str, Any]) -> ExtractedTerms:
    """Parse JSON response into ExtractedTerms model."""
    return ExtractedTerms(**response)


def parse_translated_terms_response(response: Dict[str, Any]) -> TranslatedTerms:
    """Parse JSON response into TranslatedTerms model."""
    return TranslatedTerms(**response)