"""
Character dialogue style schemas for structured output.

This module defines schemas for:
- Analyzing character dialogue patterns
- Determining speech styles (반말, 해요체, 하십시오체)
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field


# --------------------
# Pydantic Models
# --------------------

class CharacterInteraction(BaseModel):
    """Single interaction between protagonist and another character."""
    
    character_name: str = Field(..., description="Name of the character the protagonist is speaking to")
    speech_style: Literal["반말", "해요체", "하십시오체"] = Field(
        ...,
        description="Korean speech style used (반말 for informal, 해요체 for polite informal, 하십시오체 for formal)"
    )


class DialogueAnalysisResult(BaseModel):
    """Result of dialogue style analysis for a text segment."""
    
    protagonist_name: str = Field(..., description="Name of the protagonist")
    interactions: List[CharacterInteraction] = Field(
        default_factory=list,
        description="List of character interactions found in this segment"
    )
    has_dialogue: bool = Field(
        default=False,
        description="Whether the protagonist has any dialogue in this segment"
    )
    
    def to_style_dict(self) -> Dict[str, str]:
        """Convert to style dictionary for backward compatibility."""
        if not self.interactions:
            return {}
        return {
            f"{self.protagonist_name}->{i.character_name}": i.speech_style 
            for i in self.interactions
        }
    
    def merge_with_existing(self, existing_styles: Dict[str, str]) -> Dict[str, str]:
        """Merge new interactions with existing styles, updating when necessary."""
        updated_styles = existing_styles.copy()
        for interaction in self.interactions:
            style_key = f"{self.protagonist_name}->{interaction.character_name}"
            updated_styles[style_key] = interaction.speech_style
        return updated_styles


# --------------------
# JSON Schema Builders (for Gemini API)
# --------------------

def make_dialogue_analysis_schema(protagonist_name: str) -> Dict[str, Any]:
    """
    Create JSON schema for dialogue style analysis.
    
    Args:
        protagonist_name: Name of the protagonist to analyze
        
    Returns:
        JSON schema for dialogue analysis
    """
    return {
        "type": "object",
        "properties": {
            "protagonist_name": {
                "type": "string",
                "enum": [protagonist_name],  # Constrain to specific protagonist
                "description": "Name of the protagonist"
            },
            "has_dialogue": {
                "type": "boolean",
                "description": "Whether the protagonist has any dialogue in this segment"
            },
            "interactions": {
                "type": "array",
                "description": "List of character interactions found in this segment",
                "items": {
                    "type": "object",
                    "properties": {
                        "character_name": {
                            "type": "string",
                            "description": "Name of the character the protagonist is speaking to"
                        },
                        "speech_style": {
                            "type": "string",
                            "enum": ["반말", "해요체", "하십시오체"],
                            "description": "Korean speech style used"
                        }
                    },
                    "required": ["character_name", "speech_style"]
                }
            }
        },
        "required": ["protagonist_name", "has_dialogue", "interactions"]
    }


# --------------------
# Helper Functions
# --------------------

def parse_dialogue_analysis_response(response: Dict[str, Any]) -> DialogueAnalysisResult:
    """Parse JSON response into DialogueAnalysisResult model."""
    return DialogueAnalysisResult(**response)


def format_speech_styles_for_prompt(styles: Dict[str, str]) -> str:
    """
    Format speech styles dictionary for inclusion in translation prompts.
    
    Args:
        styles: Dictionary mapping "Protagonist->Character" to speech style
        
    Returns:
        Formatted string for prompt inclusion
    """
    if not styles:
        return "N/A"
    
    lines = []
    for interaction, style in styles.items():
        # Extract character name from "Protagonist->Character" format
        if "->" in interaction:
            _, character = interaction.split("->", 1)
            lines.append(f"{character}: {style}")
    
    return "\n".join(lines) if lines else "N/A"