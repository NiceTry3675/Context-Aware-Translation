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

class PhysicalWorld(BaseModel):
    """Physical world and setting details."""
    
    location: str = Field(
        ...,
        description="Primary location with environmental specifics"
    )
    architecture_landscape: Optional[str] = Field(
        None,
        description="Architectural or landscape characteristics"
    )
    technology_period: Optional[str] = Field(
        None,
        description="Technology level and time period indicators"
    )
    scale_spatial: Optional[str] = Field(
        None,
        description="Scale and spatial relationships"
    )
    material_culture: List[str] = Field(
        default_factory=list,
        description="Objects, tools, and furnishings present"
    )


class AtmosphericQualities(BaseModel):
    """Atmospheric and emotional qualities."""
    
    emotional_atmosphere: str = Field(
        ...,
        description="Primary emotional atmosphere and mood"
    )
    tension_level: Literal["calm", "building", "climactic", "aftermath"] = Field(
        ...,
        description="Current tension level in the scene"
    )
    sensory_details: List[str] = Field(
        default_factory=list,
        description="Sensory details (sounds, smells, textures, temperatures)"
    )
    pacing_energy: str = Field(
        ...,
        description="Pacing and narrative energy description"
    )
    implicit_feelings: Optional[str] = Field(
        None,
        description="Implicit feelings and undercurrents"
    )


class VisualMood(BaseModel):
    """Visual mood and aesthetic elements."""
    
    lighting_conditions: str = Field(
        ...,
        description="Dominant lighting conditions and quality"
    )
    color_palette: List[str] = Field(
        default_factory=list,
        description="Color palette (explicit and implied)"
    )
    weather_environment: Optional[str] = Field(
        None,
        description="Weather and environmental conditions"
    )
    visual_texture: Optional[str] = Field(
        None,
        description="Visual texture and contrast description"
    )
    time_indicators: str = Field(
        ...,
        description="Time of day and seasonal indicators"
    )


class CulturalContext(BaseModel):
    """Cultural and social context elements."""
    
    social_dynamics: Optional[str] = Field(
        None,
        description="Social dynamics and power relationships"
    )
    cultural_patterns: List[str] = Field(
        default_factory=list,
        description="Cultural customs or behavioral patterns"
    )
    hierarchy_indicators: Optional[str] = Field(
        None,
        description="Class, status, or hierarchy indicators"
    )
    communication_style: Optional[str] = Field(
        None,
        description="Communication styles and formality levels"
    )
    societal_norms: List[str] = Field(
        default_factory=list,
        description="Implicit societal norms"
    )


class NarrativeElements(BaseModel):
    """Narrative and dramatic elements."""
    
    point_of_focus: str = Field(
        ...,
        description="Point of focus in the scene"
    )
    dramatic_weight: Literal["low", "medium", "high", "climactic"] = Field(
        ...,
        description="Dramatic weight and significance"
    )
    symbolic_elements: List[str] = Field(
        default_factory=list,
        description="Symbolic or thematic elements"
    )
    narrative_connections: Optional[str] = Field(
        None,
        description="Foreshadowing or callbacks to other parts"
    )
    scene_role: str = Field(
        ...,
        description="Scene's role in larger narrative"
    )


class WorldAtmosphereAnalysis(BaseModel):
    """Comprehensive world and atmosphere analysis for a text segment."""

    segment_summary: str = Field(
        ...,
        description="Concise narrative summary (1-3 sentences) capturing main events, actions, and character interactions"
    )
    physical_world: PhysicalWorld = Field(
        ...,
        description="Physical world and setting details"
    )
    atmosphere: AtmosphericQualities = Field(
        ...,
        description="Atmospheric and emotional qualities"
    )
    visual_mood: VisualMood = Field(
        ...,
        description="Visual mood and aesthetic elements"
    )
    cultural_context: CulturalContext = Field(
        ...,
        description="Cultural and social context"
    )
    narrative_elements: NarrativeElements = Field(
        ...,
        description="Narrative and dramatic elements"
    )
    
    def to_prompt_format(self) -> str:
        """Format for inclusion in translation prompts."""
        lines = [
            "**World & Atmosphere Context:**",
            f"- Setting: {self.physical_world.location}",
            f"- Atmosphere: {self.atmosphere.emotional_atmosphere} ({self.atmosphere.tension_level})",
            f"- Visual: {self.visual_mood.lighting_conditions}, {self.visual_mood.time_indicators}",
            f"- Focus: {self.narrative_elements.point_of_focus}"
        ]
        if self.cultural_context.social_dynamics:
            lines.append(f"- Social: {self.cultural_context.social_dynamics}")
        return "\n".join(lines)
    
    def to_illustration_context(self) -> Dict[str, Any]:
        """Format for use in illustration generation."""
        return {
            "summary": self.segment_summary,
            "setting": self.physical_world.location,
            "setting_details": [
                self.physical_world.architecture_landscape,
                self.physical_world.technology_period
            ],
            "mood": self.atmosphere.emotional_atmosphere,
            "lighting": self.visual_mood.lighting_conditions,
            "colors": self.visual_mood.color_palette,
            "weather": self.visual_mood.weather_environment,
            "time": self.visual_mood.time_indicators,
            "tension": self.atmosphere.tension_level,
            "focus": self.narrative_elements.point_of_focus,
            "dramatic_weight": self.narrative_elements.dramatic_weight
        }

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

def make_world_atmosphere_schema() -> Dict[str, Any]:
    """
    Create JSON schema for world and atmosphere analysis.
    
    Returns:
        JSON schema for analyzing world and atmosphere
    """
    return {
        "type": "object",
        "properties": {
            "segment_summary": {
                "type": "string",
                "description": "Concise narrative summary (1-3 sentences) capturing main events, actions, and character interactions"
            },
            "physical_world": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "architecture_landscape": {"type": "string"},
                    "technology_period": {"type": "string"},
                    "scale_spatial": {"type": "string"},
                    "material_culture": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["location"]
            },
            "atmosphere": {
                "type": "object",
                "properties": {
                    "emotional_atmosphere": {"type": "string"},
                    "tension_level": {
                        "type": "string",
                        "enum": ["calm", "building", "climactic", "aftermath"]
                    },
                    "sensory_details": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "pacing_energy": {"type": "string"},
                    "implicit_feelings": {"type": "string"}
                },
                "required": ["emotional_atmosphere", "tension_level", "pacing_energy"]
            },
            "visual_mood": {
                "type": "object",
                "properties": {
                    "lighting_conditions": {"type": "string"},
                    "color_palette": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "weather_environment": {"type": "string"},
                    "visual_texture": {"type": "string"},
                    "time_indicators": {"type": "string"}
                },
                "required": ["lighting_conditions", "time_indicators"]
            },
            "cultural_context": {
                "type": "object",
                "properties": {
                    "social_dynamics": {"type": "string"},
                    "cultural_patterns": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "hierarchy_indicators": {"type": "string"},
                    "communication_style": {"type": "string"},
                    "societal_norms": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": []
            },
            "narrative_elements": {
                "type": "object",
                "properties": {
                    "point_of_focus": {"type": "string"},
                    "dramatic_weight": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "climactic"]
                    },
                    "symbolic_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "narrative_connections": {"type": "string"},
                    "scene_role": {"type": "string"}
                },
                "required": ["point_of_focus", "dramatic_weight", "scene_role"]
            }
        },
        "required": ["segment_summary", "physical_world", "atmosphere", "visual_mood", "cultural_context", "narrative_elements"]
    }


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

def parse_world_atmosphere_response(response: Dict[str, Any]) -> WorldAtmosphereAnalysis:
    """Parse JSON response into WorldAtmosphereAnalysis model."""
    return WorldAtmosphereAnalysis(**response)


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