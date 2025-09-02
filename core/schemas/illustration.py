"""
Illustration Schema Module

This module defines the schemas for illustration generation configuration
and data models used throughout the translation engine.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class IllustrationStyle(str, Enum):
    """Enumeration of available illustration styles."""
    REALISTIC = "realistic"
    ARTISTIC = "artistic"
    WATERCOLOR = "watercolor"
    DIGITAL_ART = "digital_art"
    SKETCH = "sketch"
    ANIME = "anime"
    VINTAGE = "vintage"
    MINIMALIST = "minimalist"


class IllustrationStatus(str, Enum):
    """Status of illustration generation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    GENERATED = "generated"
    FAILED = "failed"
    SKIPPED = "skipped"


class IllustrationConfig(BaseModel):
    """
    Configuration for illustration generation.
    
    This model defines the settings and preferences for generating
    illustrations for translation segments.
    """
    enabled: bool = Field(
        default=False,
        description="Whether illustration generation is enabled"
    )
    style: IllustrationStyle = Field(
        default=IllustrationStyle.DIGITAL_ART,
        description="The artistic style for generated illustrations"
    )
    style_hints: str = Field(
        default="",
        description="Additional style hints or preferences for illustration generation"
    )
    segments_per_illustration: int = Field(
        default=1,
        description="Number of segments to combine for each illustration"
    )
    max_illustrations: Optional[int] = Field(
        default=None,
        description="Maximum number of illustrations to generate (None for unlimited)"
    )
    skip_dialogue_heavy: bool = Field(
        default=True,
        description="Skip illustration for segments that are mostly dialogue"
    )
    min_segment_length: int = Field(
        default=500,
        description="Minimum segment length (characters) to generate illustration"
    )
    cache_enabled: bool = Field(
        default=True,
        description="Whether to cache generated illustrations"
    )
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True


class IllustrationData(BaseModel):
    """
    Data model for a generated illustration.
    
    This model contains all the information about a single generated
    illustration, including its location, metadata, and generation details.
    """
    segment_index: int = Field(
        ...,
        description="Index of the segment this illustration belongs to"
    )
    file_path: str = Field(
        ...,
        description="File path to the generated illustration"
    )
    prompt: str = Field(
        ...,
        description="The prompt used to generate this illustration"
    )
    status: IllustrationStatus = Field(
        ...,
        description="Current status of the illustration"
    )
    style: IllustrationStyle = Field(
        ...,
        description="The style used for this illustration"
    )
    width: Optional[int] = Field(
        default=None,
        description="Width of the illustration in pixels"
    )
    height: Optional[int] = Field(
        default=None,
        description="Height of the illustration in pixels"
    )
    file_size: Optional[int] = Field(
        default=None,
        description="File size in bytes"
    )
    generation_time: Optional[float] = Field(
        default=None,
        description="Time taken to generate the illustration in seconds"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if generation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the illustration"
    )
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True


class IllustrationBatch(BaseModel):
    """
    Container for batch illustration generation results.
    
    This model holds the results of generating illustrations for
    multiple segments in a batch operation.
    """
    job_id: Optional[int] = Field(
        default=None,
        description="Translation job ID this batch belongs to"
    )
    total_segments: int = Field(
        ...,
        description="Total number of segments processed"
    )
    successful_generations: int = Field(
        default=0,
        description="Number of successfully generated illustrations"
    )
    failed_generations: int = Field(
        default=0,
        description="Number of failed illustration generations"
    )
    skipped_segments: int = Field(
        default=0,
        description="Number of segments skipped for illustration"
    )
    illustrations: List[IllustrationData] = Field(
        default_factory=list,
        description="List of generated illustrations"
    )
    config: IllustrationConfig = Field(
        ...,
        description="Configuration used for this batch"
    )
    total_generation_time: float = Field(
        default=0.0,
        description="Total time taken for batch generation in seconds"
    )
    output_directory: str = Field(
        ...,
        description="Directory where illustrations are stored"
    )
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the illustration batch.
        
        Returns:
            Dictionary containing batch statistics
        """
        return {
            'total_segments': self.total_segments,
            'successful': self.successful_generations,
            'failed': self.failed_generations,
            'skipped': self.skipped_segments,
            'success_rate': (self.successful_generations / self.total_segments * 100) 
                          if self.total_segments > 0 else 0,
            'average_generation_time': (self.total_generation_time / self.successful_generations)
                                      if self.successful_generations > 0 else 0
        }


class CharacterProfile(BaseModel):
    """
    A lightweight character profile to drive consistent base images and scenes.
    """
    name: Optional[str] = Field(default=None, description="Character name (not rendered in image)")
    gender: Optional[str] = Field(default=None, description="Gender or presentation (e.g., male, female, androgynous)")
    age: Optional[str] = Field(default=None, description="Apparent age (e.g., teen, 20s, 30s)")
    hair_color: Optional[str] = Field(default=None, description="Primary hair color")
    hair_style: Optional[str] = Field(default=None, description="Hair style (e.g., short, long, ponytail)")
    eye_color: Optional[str] = Field(default=None, description="Eye color")
    eye_shape: Optional[str] = Field(default=None, description="Eye shape/style (e.g., sharp, round)")
    skin_tone: Optional[str] = Field(default=None, description="Skin tone")
    body_type: Optional[str] = Field(default=None, description="Body type or build")
    clothing: Optional[str] = Field(default=None, description="Default outfit description")
    accessories: Optional[str] = Field(default=None, description="Accessories/jewelry")
    style: IllustrationStyle = Field(default=IllustrationStyle.DIGITAL_ART, description="Art style preference")
    extra_style_hints: Optional[str] = Field(default=None, description="Additional stylistic hints")

    class Config:
        use_enum_values = True
