"""
Progress Tracker Module

This module handles progress tracking and database updates for translation jobs.
Extracted from TranslationPipeline to separate concerns.
"""

import time
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..schemas import SegmentInfo


class ProgressTracker:
    """
    Manages progress tracking and database updates for translation jobs.
    
    This class handles:
    - Progress percentage calculation and updates
    - Database finalization with results
    - Usage statistics recording
    """
    
    def __init__(self, db: Optional[Session] = None, job_id: Optional[int] = None):
        """
        Initialize the progress tracker.
        
        Args:
            db: Optional database session
            job_id: Optional job ID for database updates
        """
        self.db = db
        self.job_id = job_id
        self.start_time = time.time()
    
    def update_progress(self, current_index: int, total_segments: int):
        """
        Update translation progress in the database.
        
        Args:
            current_index: Current segment index (0-based)
            total_segments: Total number of segments
        """
        if not self.db or not self.job_id:
            return
            
        progress = int((current_index / total_segments) * 100)
        
        try:
            from backend import crud
            crud.update_job_progress(self.db, self.job_id, progress)
        except ImportError:
            # Backend not available (e.g., running in core-only mode)
            pass
    
    def finalize_translation(self, segments: List[SegmentInfo], 
                           translated_segments: List[str], 
                           glossary: Dict[str, str]):
        """
        Finalize translation by updating database with results.
        
        Args:
            segments: Original source segments
            translated_segments: Translated text segments
            glossary: Final glossary dictionary
        """
        if not self.db or not self.job_id:
            return
            
        try:
            from backend import crud
            
            # Update glossary
            crud.update_job_final_glossary(self.db, self.job_id, glossary)
            
            # Save translation segments for segment view
            segments_data = []
            for i, (source_segment, translated_segment) in enumerate(
                zip(segments, translated_segments)
            ):
                segments_data.append({
                    "segment_index": i,
                    "source_text": source_segment.text,
                    "translated_text": translated_segment
                })
            crud.update_job_translation_segments(self.db, self.job_id, segments_data)
            
        except ImportError:
            # Backend not available (e.g., running in core-only mode)
            pass
    
    def record_usage_log(self, original_text: str, translated_text: str, 
                        model_name: str, error_type: Optional[str] = None):
        """
        Record usage statistics to the database.
        
        Args:
            original_text: The original source text
            translated_text: The translated text
            model_name: Name of the AI model used
            error_type: Optional error type if translation failed
        """
        if not self.db or not self.job_id:
            return
            
        end_time = time.time()
        duration = int(end_time - self.start_time)
        
        try:
            from backend import crud, schemas
            
            log_data = schemas.TranslationUsageLogCreate(
                job_id=self.job_id,
                original_length=len(original_text),
                translated_length=len(translated_text),
                translation_duration_seconds=duration,
                model_used=model_name,
                error_type=error_type
            )
            crud.create_translation_usage_log(self.db, log_data)
            print("\n--- Usage log has been recorded. ---")
            
        except ImportError:
            # Backend not available (e.g., running in core-only mode)
            pass