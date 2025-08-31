"""
Segment Schema Module

This module defines the unified SegmentInfo model used throughout the translation engine
to eliminate code duplication and provide a single source of truth for segment data.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SegmentInfo(BaseModel):
    """
    Container for segment data and its context.
    
    This model represents a single segment of text within a document, 
    along with contextual information about its source location and
    optional illustration data.
    """
    text: str = Field(..., description="The text content of the segment")
    chapter_title: Optional[str] = Field(
        default=None, 
        description="The title of the chapter this segment belongs to"
    )
    chapter_filename: Optional[str] = Field(
        default=None, 
        description="The filename of the chapter this segment belongs to"
    )
    # Illustration fields
    illustration_path: Optional[str] = Field(
        default=None,
        description="Path to the generated illustration for this segment"
    )
    illustration_prompt: Optional[str] = Field(
        default=None,
        description="The prompt used to generate the illustration"
    )
    illustration_status: Optional[str] = Field(
        default=None,
        description="Status of illustration generation (pending, generated, failed)"
    )
    
    class Config:
        """Pydantic configuration"""
        str_strip_whitespace = True
        validate_assignment = True
        
    def __str__(self) -> str:
        """String representation of the segment"""
        if self.chapter_title:
            return f"Segment from '{self.chapter_title}': {self.text[:50]}..."
        return f"Segment: {self.text[:50]}..."
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (f"SegmentInfo(text='{self.text[:30]}...', "
                f"chapter_title='{self.chapter_title}', "
                f"chapter_filename='{self.chapter_filename}')")