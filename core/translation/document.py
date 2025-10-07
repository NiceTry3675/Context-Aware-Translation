"""
Translation Document Module

This module provides a simplified wrapper around TranslationDocumentData
for document management during translation. It focuses purely on data storage
and uses centralized utilities for I/O and segmentation operations.
"""

import os
import json
from pathlib import Path
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
                 target_segment_size: int = 15000, job_id: Optional[int] = None,
                 storage_handler=None):
        """
        Initialize a translation document.
        
        Args:
            filepath: Path to the source document
            original_filename: Original filename for user-facing display
            target_segment_size: Target size for each segment in characters
            job_id: Optional job ID for saving to job-specific directory
            storage_handler: Optional storage handler for backend integration
        """
        # Store job_id and storage handler for storage operations
        self._job_id = job_id
        self._storage_handler = storage_handler
        
        # Setup filenames
        user_base_filename, unique_base_filename, input_format = self._setup_filenames(
            filepath, original_filename
        )
        
        # Setup output path
        output_filename = DocumentOutputManager.setup_output_path(
            filepath, original_filename
        )
        
        # Setup job-specific output path if job_id is provided
        job_output_filename = None
        if job_id:
            job_output_filename = DocumentOutputManager.setup_job_output_path(
                job_id, original_filename, input_format
            )
        
        # Initialize the data model
        self._data = TranslationDocumentData(
            filepath=filepath,
            original_filename=original_filename,
            user_base_filename=user_base_filename,
            unique_base_filename=unique_base_filename,
            input_format=input_format,
            output_filename=output_filename,
            job_output_filename=job_output_filename,
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
        saved_with_storage = False

        # Try to save using storage abstraction if job_id available
        if hasattr(self, '_job_id') and self._job_id:
            saved_paths = DocumentOutputManager.save_to_storage_sync(
                self._data.translated_segments,
                self._job_id,
                self._data.original_filename or self._data.user_base_filename,
                self._storage_handler
            )
            self._persist_partial_segment_cache()
            if saved_paths:
                # Storage save succeeded, no need for fallback write
                saved_with_storage = True

        if saved_with_storage:
            return

        # Fallback to traditional file saving
        if self._data.input_format == '.epub':
            # Save to main output location
            DocumentOutputManager.save_epub_output(
                self._data.filepath,
                self._data.translated_segments,
                self._data.output_filename,
                self._data.style_map
            )
            # Also save to job-specific location if available
            if self._data.job_output_filename:
                DocumentOutputManager.save_epub_output(
                    self._data.filepath,
                    self._data.translated_segments,
                    self._data.job_output_filename,
                    self._data.style_map
                )
        else:
            # Save to main output location
            DocumentOutputManager.save_text_output(
                self._data.translated_segments,
                self._data.output_filename
            )
            # Also save to job-specific location if available
            if self._data.job_output_filename:
                DocumentOutputManager.save_text_output(
                    self._data.translated_segments,
                    self._data.job_output_filename
                )

        if hasattr(self, '_job_id') and self._job_id:
            self._persist_partial_segment_cache()
    
    def save_final_output(self):
        """Save the final output based on the input file format."""
        print(f"\nSaving final output to {self._data.output_filename}...")
        if self._data.job_output_filename:
            print(f"Also saving to job directory: {self._data.job_output_filename}")
        # Always persist the text output via existing mechanism (may use storage handler)
        self.save_partial_output()

        # If the original input is EPUB, also emit a proper EPUB artifact locally
        # even when a storage handler is present (which short-circuits file writes).
        if self._data.input_format == '.epub':
            try:
                # Main output location
                DocumentOutputManager.save_epub_output(
                    self._data.filepath,
                    self._data.translated_segments,
                    self._data.output_filename,
                    self._data.style_map,
                )

                # Job-scoped output location (if configured)
                if self._data.job_output_filename:
                    DocumentOutputManager.save_epub_output(
                        self._data.filepath,
                        self._data.translated_segments,
                        self._data.job_output_filename,
                        self._data.style_map,
                    )
            except Exception as exc:
                # Surface but do not block TXT availability; EPUB is best-effort
                print(f"Warning: Failed to write EPUB artifacts during final save: {exc}")
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

    def _persist_partial_segment_cache(self):
        """Persist partial translation segments for accurate resume support."""
        job_id = getattr(self, '_job_id', None)
        if not job_id:
            return

        try:
            cache_dir = Path("logs") / "jobs" / str(job_id) / "output"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "partial_segments.json"
            with open(cache_path, 'w', encoding='utf-8') as cache_file:
                json.dump(self._data.translated_segments, cache_file, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover - best effort cache
            print(f"Warning: Failed to persist partial segments for job {job_id}: {exc}")
    
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
