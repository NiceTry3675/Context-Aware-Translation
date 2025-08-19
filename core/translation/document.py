"""
Translation Document Module

This module provides a simplified wrapper around TranslationDocumentData
for document management during translation. It focuses purely on data storage
and uses centralized utilities for I/O and segmentation operations.
"""

import os
from typing import List, Optional

from ..schemas import SegmentInfo, TranslationDocumentData
from ..utils import create_segments_for_text, create_segments_for_epub
from ..utils.document_io import DocumentOutputManager


class TranslationDocument:
    """
    Simplified document wrapper for translation operations.
    
    This class provides a convenient interface around TranslationDocumentData
    and delegates I/O operations to centralized utilities.
    """
    
    def __init__(self, filepath: str, original_filename: Optional[str] = None, 
                 target_segment_size: int = 15000):
        """
        Initialize a translation document.
        
        Args:
            filepath: Path to the source document
            original_filename: Original filename for user-facing display
            target_segment_size: Target size for each segment in characters
        """
        # Setup filenames
        user_base_filename, unique_base_filename, input_format = self._setup_filenames(
            filepath, original_filename
        )
        
        # Setup output path
        output_filename = DocumentOutputManager.setup_output_path(
            filepath, original_filename
        )
        
        # Initialize the data model
        self._data = TranslationDocumentData(
            filepath=filepath,
            original_filename=original_filename,
            user_base_filename=user_base_filename,
            unique_base_filename=unique_base_filename,
            input_format=input_format,
            output_filename=output_filename,
            target_segment_size=target_segment_size
        )
        
        # Create segments using centralized utilities
        self._create_segments()
    
    def _setup_filenames(self, filepath: str, original_filename: Optional[str]) -> tuple:
        """
        Setup user-facing and unique filenames.
        
        Returns:
            Tuple of (user_base_filename, unique_base_filename, input_format)
        """
        # User-facing filename
        user_facing_filename = original_filename if original_filename else os.path.basename(filepath)
        user_base_filename = os.path.splitext(user_facing_filename)[0]
        
        # Unique base filename for saving
        unique_base_filename = os.path.splitext(os.path.basename(filepath))[0]
        
        # Input format
        input_format = os.path.splitext(user_facing_filename.lower())[1] \
                      if original_filename else os.path.splitext(filepath.lower())[1]
        
        return user_base_filename, unique_base_filename, input_format
    
    def _create_segments(self):
        """Create segments using centralized segmentation utilities."""
        if self._data.input_format == '.epub':
            segments = create_segments_for_epub(
                self._data.filepath, 
                self._data.target_segment_size
            )
        else:
            segments = create_segments_for_text(
                self._data.filepath, 
                self._data.target_segment_size
            )
        
        # Store segments in data model
        self._data.segments = segments
        self._data.update_total_segments()
    
    # Delegate properties to data model
    @property
    def filepath(self) -> str:
        return self._data.filepath
    
    @property
    def user_base_filename(self) -> str:
        return self._data.user_base_filename
    
    @property
    def unique_base_filename(self) -> str:
        return self._data.unique_base_filename
    
    @property
    def input_format(self) -> str:
        return self._data.input_format
    
    @property
    def output_filename(self) -> str:
        return self._data.output_filename
    
    @property
    def segments(self) -> List[SegmentInfo]:
        return self._data.segments
    
    @property
    def translated_segments(self) -> List[str]:
        return self._data.translated_segments
    
    @translated_segments.setter
    def translated_segments(self, value: List[str]):
        self._data.translated_segments = value
    
    @property
    def glossary(self) -> dict:
        return self._data.glossary
    
    @glossary.setter
    def glossary(self, value: dict):
        self._data.glossary = value
    
    @property
    def character_styles(self) -> dict:
        return self._data.character_styles
    
    @character_styles.setter
    def character_styles(self, value: dict):
        self._data.character_styles = value
    
    @property
    def style_map(self) -> dict:
        return self._data.style_map
    
    @style_map.setter
    def style_map(self, value: dict):
        self._data.style_map = value
    
    # Translation operations
    def append_translated_segment(self, translated_text: str, original_segment: SegmentInfo):
        """
        Append a translated segment.
        
        Args:
            translated_text: The translated text
            original_segment: The original segment info (for compatibility)
        """
        self._data.add_translation(translated_text)
    
    def get_previous_segment(self, current_index: int) -> str:
        """
        Get the text of the previous segment.
        
        Args:
            current_index: Current segment index
            
        Returns:
            Previous segment text or empty string
        """
        prev_segment = self._data.get_segment_at_index(current_index - 1)
        return prev_segment.text if prev_segment else ""
    
    def get_previous_translation(self, current_index: int) -> str:
        """
        Get the translation of the previous segment.
        
        Args:
            current_index: Current segment index
            
        Returns:
            Previous translation or empty string
        """
        return self._data.get_translation_at_index(current_index - 1) or ""
    
    # Output operations using centralized utilities
    def save_partial_output(self):
        """Save the currently translated segments to the output file."""
        if self._data.input_format == '.epub':
            DocumentOutputManager.save_epub_output(
                self._data.filepath,
                self._data.translated_segments,
                self._data.output_filename,
                self._data.style_map
            )
        else:
            DocumentOutputManager.save_text_output(
                self._data.translated_segments,
                self._data.output_filename
            )
    
    def save_final_output(self):
        """Save the final output based on the input file format."""
        print(f"\nSaving final output to {self._data.output_filename}...")
        self.save_partial_output()
        print("Save complete.")
    
    def save_translation(self, output_path: Optional[str] = None):
        """
        Save the translation to a specified path or default output filename.
        
        Args:
            output_path: Optional custom output path
        """
        if output_path:
            # Save based on format
            if self._data.input_format == '.epub' and output_path.endswith('.epub'):
                DocumentOutputManager.save_epub_output(
                    self._data.filepath,
                    self._data.translated_segments,
                    output_path,
                    self._data.style_map
                )
            else:
                # Default to text format for post-edited versions
                DocumentOutputManager.save_text_output(
                    self._data.translated_segments,
                    output_path
                )
        else:
            self.save_final_output()
    
    # Data model access
    def get_data_model(self) -> TranslationDocumentData:
        """Get the underlying data model."""
        return self._data
    
    def get_progress(self) -> float:
        """Get translation progress as a percentage."""
        return self._data.get_progress()
    
    def is_translation_complete(self) -> bool:
        """Check if translation is complete."""
        return self._data.is_translation_complete()