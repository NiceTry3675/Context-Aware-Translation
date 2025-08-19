"""
Progress Tracker Module

This module handles progress tracking and database updates for translation jobs.
Extracted from TranslationPipeline to separate concerns.
"""

import time
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..schemas import SegmentInfo
from ..utils.logging import TranslationLogger


class ProgressTracker:
    """
    Manages progress tracking and database updates for translation jobs.
    
    This class handles:
    - Progress percentage calculation and updates
    - Database finalization with results
    - Usage statistics recording
    """
    
    def __init__(self, db: Optional[Session] = None, job_id: Optional[int] = None, 
                 filename: Optional[str] = None):
        """
        Initialize the progress tracker.
        
        Args:
            db: Optional database session
            job_id: Optional job ID for database updates
            filename: Optional filename for logging
        """
        self.db = db
        self.job_id = job_id
        self.filename = filename
        self.start_time = time.time()
        self.logger = None
        
        # Initialize logger if we have the necessary info
        if job_id and filename:
            self.logger = TranslationLogger(job_id, filename)
    
    def update_progress(self, current_index: int, total_segments: int):
        """
        Update translation progress in the database.
        
        Args:
            current_index: Current segment index (0-based)
            total_segments: Total number of segments
        """
        progress = int((current_index / total_segments) * 100)
        
        # Log progress to file
        if self.logger:
            elapsed_time = time.time() - self.start_time
            self.logger.log_translation_progress(current_index, total_segments, elapsed_time)
        
        # Update database if available
        if not self.db or not self.job_id:
            return
        
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
        # Log completion
        if self.logger:
            total_time = time.time() - self.start_time
            self.logger.log_completion(len(segments), total_time)
            
            # Log final glossary summary
            with open(self.logger.context_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n--- FINAL TRANSLATION SUMMARY ---\n")
                f.write(f"Total segments: {len(segments)}\n")
                f.write(f"Total glossary entries: {len(glossary)}\n")
                f.write(f"Total time: {total_time:.1f}s\n")
                f.write(f"Average time per segment: {total_time/len(segments):.1f}s\n\n")
        
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
        end_time = time.time()
        duration = int(end_time - self.start_time)
        
        # Log usage statistics to file
        if self.logger:
            with open(self.logger.progress_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n--- USAGE STATISTICS ---\n")
                f.write(f"Model used: {model_name}\n")
                f.write(f"Original text length: {len(original_text)} chars\n")
                f.write(f"Translated text length: {len(translated_text)} chars\n")
                f.write(f"Translation duration: {duration}s\n")
                if error_type:
                    f.write(f"Error type: {error_type}\n")
                f.write(f"{'='*50}\n")
        
        if not self.db or not self.job_id:
            return
        
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