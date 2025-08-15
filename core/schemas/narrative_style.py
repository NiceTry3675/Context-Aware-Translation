"""
Narrative style schemas for structured output.

This module defines schemas for:
- Defining core narrative style
- Detecting style deviations in segments
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field


# --------------------
# Pydantic Models
# --------------------

class NarrationStyle(BaseModel):
    """Narration style details."""
    
    description: str = Field(
        ...,
        description="Brief description of the narrator's voice (e.g., 'A neutral, third-person observer's voice')"
    )
    ending_style: str = Field(
        default="해라체",
        description="Korean sentence ending style for narration (almost always 해라체)"
    )


class NarrativeStyleDefinition(BaseModel):
    """Core narrative style definition for the entire work."""
    
    protagonist_name: str = Field(
        ...,
        description="The single most central character's name. If unclear, 'Protagonist'"
    )
    narration_style: NarrationStyle = Field(
        ...,
        description="Style and endings for narrative text"
    )
    core_tone_keywords: List[str] = Field(
        ...,
        description="3-5 keywords describing the overall mood (Korean)",
        min_length=1,
        max_length=5
    )
    golden_rule: str = Field(
        ...,
        description="Overarching rule for the novel's feel and rhythm"
    )
    
    def to_prompt_format(self) -> str:
        """Format for inclusion in translation prompts."""
        lines = [
            f"1. **Protagonist Name:** {self.protagonist_name}",
            f"2. **Narration Style & Endings (서술 문체 및 어미):**",
            f"   - **Description:** {self.narration_style.description}",
            f"   - **Ending Style:** {self.narration_style.ending_style}",
            f"3. **Core Tone & Keywords (전체 분위기):** {', '.join(self.core_tone_keywords)}",
            f"4. **Key Stylistic Rule (The \"Golden Rule\"):** {self.golden_rule}"
        ]
        return "\n".join(lines)


class StyleDeviation(BaseModel):
    """Style deviation detected in a segment."""
    
    has_deviation: bool = Field(
        ...,
        description="Whether a style deviation was detected"
    )
    starts_with: Optional[str] = Field(
        None,
        description="The first few words of the deviating part"
    )
    instruction: Optional[str] = Field(
        None,
        description="Direct command for the translator regarding this deviation"
    )
    
    def to_prompt_format(self) -> str:
        """Format for inclusion in translation prompts."""
        if not self.has_deviation:
            return "N/A"
        if self.starts_with and self.instruction:
            return f"**Starts with:** {self.starts_with}\n**Instruction:** {self.instruction}"
        return "N/A"


# --------------------
# JSON Schema Builders (for Gemini API)
# --------------------

def make_narrative_style_schema() -> Dict[str, Any]:
    """
    Create JSON schema for narrative style definition.
    
    Returns:
        JSON schema for defining core narrative style
    """
    return {
        "type": "object",
        "properties": {
            "protagonist_name": {
                "type": "string",
                "description": "The single most central character's name"
            },
            "narration_style": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Brief description of the narrator's voice"
                    },
                    "ending_style": {
                        "type": "string",
                        "enum": ["해라체", "해요체", "하십시오체"],
                        "description": "Korean sentence ending style for narration"
                    }
                },
                "required": ["description", "ending_style"]
            },
            "core_tone_keywords": {
                "type": "array",
                "description": "3-5 keywords describing the overall mood in Korean",
                "items": {
                    "type": "string"
                },
                "minItems": 1,
                "maxItems": 5
            },
            "golden_rule": {
                "type": "string",
                "description": "Overarching rule for the novel's feel and rhythm"
            }
        },
        "required": ["protagonist_name", "narration_style", "core_tone_keywords", "golden_rule"]
    }


def make_style_deviation_schema() -> Dict[str, Any]:
    """
    Create JSON schema for style deviation detection.
    
    Returns:
        JSON schema for detecting style deviations
    """
    return {
        "type": "object",
        "properties": {
            "has_deviation": {
                "type": "boolean",
                "description": "Whether a style deviation was detected"
            },
            "starts_with": {
                "type": "string",
                "description": "The first few words of the deviating part (null if no deviation)"
            },
            "instruction": {
                "type": "string",
                "description": "Direct command for the translator (null if no deviation)"
            }
        },
        "required": ["has_deviation"]
    }


# --------------------
# Helper Functions
# --------------------

def parse_narrative_style_response(response: Dict[str, Any]) -> NarrativeStyleDefinition:
    """Parse JSON response into NarrativeStyleDefinition model."""
    return NarrativeStyleDefinition(**response)


def parse_style_deviation_response(response: Dict[str, Any]) -> StyleDeviation:
    """Parse JSON response into StyleDeviation model."""
    return StyleDeviation(**response)


def extract_protagonist_from_style(style_text: str) -> str:
    """
    Extract protagonist name from legacy text-based style analysis.
    
    Args:
        style_text: Text output from style analysis
        
    Returns:
        Protagonist name or "Protagonist" if not found
    """
    # Look for pattern like "1. **Protagonist Name:** John"
    import re
    match = re.search(r'Protagonist Name[:\s]+([^\n]+)', style_text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        # Clean up any markdown or extra characters
        name = re.sub(r'[*_`]', '', name)
        return name if name else "Protagonist"
    return "Protagonist"