"""
Document Schema Module

This module defines the unified TranslationDocument data model used throughout the translation engine
to eliminate duplication between TranslationJob and TranslationDocument classes.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from pathlib import Path

from .segment import SegmentInfo


class TranslationDocumentData(BaseModel):
    """
    Core data model for translation documents.
    
    This model represents the essential data structure for a document
    being processed through the translation pipeline.
    """
    
    # File information
    filepath: str = Field(..., description="Path to the source document file")
    original_filename: Optional[str] = Field(
        default=None, 
        description="Original filename provided by user"
    )
    user_base_filename: str = Field(..., description="User-facing base filename")
    unique_base_filename: str = Field(..., description="Unique base filename for internal use")
    input_format: str = Field(..., description="Input file format (e.g., '.txt', '.epub')")
    output_filename: str = Field(..., description="Full path to output file")
    
    # Processing parameters
    target_segment_size: int = Field(
        default=15000, 
        description="Target character count for each segment"
    )
    
    # Content data
    segments: List[SegmentInfo] = Field(
        default_factory=list, 
        description="List of text segments for translation"
    )
    translated_segments: List[str] = Field(
        default_factory=list, 
        description="List of translated text segments"
    )
    
    # Context and style data
    glossary: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Extracted glossary terms and translations"
    )
    character_styles: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Character dialogue styles and patterns"
    )
    style_map: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Style mapping for EPUB formatting"
    )
    
    # Metadata
    total_segments: int = Field(default=0, description="Total number of segments")
    processing_status: str = Field(default="initialized", description="Current processing status")
    
    class Config:
        """Pydantic configuration"""
        str_strip_whitespace = True
        validate_assignment = True
        arbitrary_types_allowed = True
    
    @validator('filepath')
    def validate_filepath_exists(cls, v):
        """Validate that the source file exists"""
        if not Path(v).exists():
            raise ValueError(f"The file '{v}' does not exist.")
        return v
    
    @validator('input_format')
    def validate_input_format(cls, v):
        """Validate input format starts with dot"""
        if not v.startswith('.'):
            return f'.{v}'
        return v.lower()
    
    @validator('target_segment_size')
    def validate_segment_size(cls, v):
        """Validate segment size is reasonable"""
        if v < 1000:
            raise ValueError("Target segment size must be at least 1000 characters")
        if v > 50000:
            raise ValueError("Target segment size should not exceed 50000 characters")
        return v
    
    def update_total_segments(self):
        """Update the total segments count based on current segments"""
        self.total_segments = len(self.segments)
    
    def add_segment(self, segment: SegmentInfo):
        """Add a segment and update count"""
        self.segments.append(segment)
        self.update_total_segments()
    
    def add_translation(self, translation: str):
        """Add a translation for the next segment"""
        self.translated_segments.append(translation)
    
    def get_progress(self) -> float:
        """Get translation progress as a percentage"""
        if self.total_segments == 0:
            return 0.0
        return (len(self.translated_segments) / self.total_segments) * 100
    
    def is_translation_complete(self) -> bool:
        """Check if translation is complete"""
        return len(self.translated_segments) == self.total_segments
    
    def get_segment_at_index(self, index: int) -> Optional[SegmentInfo]:
        """Get segment at specific index"""
        if 0 <= index < len(self.segments):
            return self.segments[index]
        return None
    
    def get_translation_at_index(self, index: int) -> Optional[str]:
        """Get translation at specific index"""
        if 0 <= index < len(self.translated_segments):
            return self.translated_segments[index]
        return None