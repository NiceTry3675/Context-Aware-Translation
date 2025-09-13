"""
Centralized Logging Utilities

This module provides centralized logging functionality to eliminate scattered logging logic
across the translation engine. It handles debug prompts, context logging, and structured
logging for translation operations.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class TranslationLogger:
    """
    Centralized logger for translation operations.
    
    This class manages all logging operations including:
    - Debug prompt logging
    - Context information logging  
    - Progress tracking
    - Error logging
    """
    
    def __init__(self, job_id: Optional[int] = None, user_base_filename: Optional[str] = None, job_storage_base: Optional[str] = None, task_type: str = "translation"):
        """
        Initialize the translation logger.
        
        Args:
            job_id: Optional job ID for file naming
            user_base_filename: Base filename for log naming
            job_storage_base: Optional custom path for job storage (defaults to 'logs/jobs')
            task_type: Type of task (translation, validation, postedit, style_analysis, etc.)
        """
        self.job_id = job_id
        self.user_base_filename = user_base_filename
        self.task_type = task_type
        self.start_time = time.time()
        
        # Try to use settings if available, otherwise use default
        if job_storage_base:
            self.job_storage_base = job_storage_base
        else:
            try:
                from backend.config.settings import get_settings
                self.job_storage_base = get_settings().job_storage_base
            except (ImportError, Exception):
                # Backend not available (running in standalone mode) or settings not configured
                self.job_storage_base = "logs/jobs"
        
        # Initialize logging directories
        self._setup_logging_directories()
        
        # Setup log file paths
        self._setup_log_paths()
    
    def _setup_logging_directories(self):
        """Create all necessary logging directories."""
        # Only create job-specific directories if job_id is provided
        if self.job_id:
            job_dir = os.path.join(self.job_storage_base, str(self.job_id))
            subdirs = ["prompts", "context", "validation", "postedit", "progress"]
            for subdir in subdirs:
                os.makedirs(os.path.join(job_dir, subdir), exist_ok=True)
    
    def _setup_log_paths(self):
        """Setup paths for various log files."""
        if self.job_id:
            # Use job-centric directory structure with task-specific filenames
            job_dir = os.path.join(self.job_storage_base, str(self.job_id))
            # Create unique prompt log filename based on task type
            prompt_filename = f"{self.task_type}_prompts.txt"
            context_filename = f"{self.task_type}_context.txt"
            progress_filename = f"{self.task_type}_progress.txt"
            
            self.prompt_log_path = os.path.join(job_dir, "prompts", prompt_filename)
            self.context_log_path = os.path.join(job_dir, "context", context_filename)
            self.progress_log_path = os.path.join(job_dir, "progress", progress_filename)
        else:
            # No logging without job_id
            self.prompt_log_path = None
            self.context_log_path = None
            self.progress_log_path = None
    
    def initialize_session(self):
        """Initialize a new translation session with log headers."""
        if not self.job_id:
            return  # Skip logging without job_id
            
        filename = self.user_base_filename or "unknown_file"
        
        # Initialize prompt log
        with open(self.prompt_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {filename}\n")
            f.write(f"# Job ID: {self.job_id}\n")
            f.write(f"# Started: {datetime.now().isoformat()}\n\n")
        
        # Initialize context log
        with open(self.context_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {filename}\n")
            f.write(f"# Job ID: {self.job_id}\n")
            f.write(f"# Started: {datetime.now().isoformat()}\n\n")
        
        # Initialize progress log
        with open(self.progress_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROGRESS LOG FOR: {filename}\n")
            f.write(f"# Job ID: {self.job_id}\n")
            f.write(f"# Started: {datetime.now().isoformat()}\n\n")
    
    def log_core_narrative_style(self, core_narrative_style: str):
        """
        Log the core narrative style definition.
        
        Args:
            core_narrative_style: The core narrative style text
        """
        if not self.context_log_path:
            return  # Skip logging without job_id
            
        with open(self.context_log_path, 'a', encoding='utf-8') as f:
            f.write("--- Core Narrative Style Defined ---\n")
            f.write(f"{core_narrative_style}\n")
            f.write("="*50 + "\n\n")
    
    def log_translation_prompt(self, segment_index: int, prompt: str):
        """
        Log a translation prompt for debugging.
        
        Args:
            segment_index: Index of the segment being translated
            prompt: The full prompt sent to the AI model
        """
        if not self.prompt_log_path:
            return  # Skip logging without job_id
            
        with open(self.prompt_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
            f.write(prompt)
            f.write("\n\n" + "="*50 + "\n\n")
    
    def log_segment_context(self, segment_index: int, context_data: Dict[str, Any]):
        """
        Log context information for a segment translation.
        
        Args:
            segment_index: Index of the segment
            context_data: Dictionary containing context information
        """
        if not self.context_log_path:
            return  # Skip logging without job_id
            
        with open(self.context_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- CONTEXT FOR SEGMENT {segment_index} ---\n\n")
            
            # Narrative style deviation
            style_deviation = context_data.get('style_deviation', 'N/A')
            f.write("### Narrative Style Deviation:\n")
            f.write(f"{style_deviation}\n\n")
            
            # Contextual glossary
            contextual_glossary = context_data.get('contextual_glossary', {})
            f.write("### Contextual Glossary (For This Segment):\n")
            if contextual_glossary:
                for key, value in contextual_glossary.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- None relevant to this segment.\n")
            f.write("\n")
            
            # Full glossary
            full_glossary = context_data.get('full_glossary', {})
            f.write("### Cumulative Glossary (Full):\n")
            if full_glossary:
                for key, value in full_glossary.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- Empty\n")
            f.write("\n")
            
            # Character styles
            character_styles = context_data.get('character_styles', {})
            f.write("### Cumulative Character Styles:\n")
            if character_styles:
                for key, value in character_styles.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- Empty\n")
            f.write("\n")
            
            # Immediate context
            immediate_context_source = context_data.get('immediate_context_source')
            immediate_context_ko = context_data.get('immediate_context_ko')
            f.write("### Immediate Language Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_source or 'N/A'}\n\n")
            f.write("### Immediate Korean Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_ko or 'N/A'}\n\n")
            f.write("="*50 + "\n\n")
    
    def log_translation_progress(self, segment_index: int, total_segments: int, 
                               elapsed_time: Optional[float] = None):
        """
        Log translation progress.
        
        Args:
            segment_index: Current segment index (0-based)
            total_segments: Total number of segments
            elapsed_time: Optional elapsed time since start
        """
        progress_percent = ((segment_index + 1) / total_segments) * 100
        current_time = time.time()
        
        if elapsed_time is None:
            elapsed_time = current_time - self.start_time
        
        with open(self.progress_log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] ")
            f.write(f"Segment {segment_index + 1}/{total_segments} ")
            f.write(f"({progress_percent:.1f}%) ")
            f.write(f"- Elapsed: {elapsed_time:.1f}s\n")
    
    def log_error(self, error: Exception, segment_index: Optional[int] = None, 
                  context: Optional[str] = None):
        """
        Log an error that occurred during translation.
        
        Args:
            error: The exception that occurred
            segment_index: Optional segment index where error occurred
            context: Optional context description
        """
        error_log_path = f"logs/errors/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        os.makedirs("logs/errors", exist_ok=True)
        
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# ERROR LOG\n")
            f.write(f"# Job ID: {self.job_id}\n")
            f.write(f"# File: {self.user_base_filename}\n")
            f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"# Segment: {segment_index}\n")
            f.write(f"# Context: {context}\n\n")
            f.write(f"Error Type: {type(error).__name__}\n")
            f.write(f"Error Message: {str(error)}\n")
            
            if hasattr(error, '__traceback__'):
                import traceback
                f.write(f"\nTraceback:\n{traceback.format_exc()}")
    
    def log_completion(self, total_segments: int, total_time: Optional[float] = None):
        """
        Log completion of translation job.
        
        Args:
            total_segments: Total number of segments translated
            total_time: Optional total time taken
        """
        if total_time is None:
            total_time = time.time() - self.start_time
        
        completion_message = (
            f"\n--- TRANSLATION COMPLETED ---\n"
            f"Total segments: {total_segments}\n"
            f"Total time: {total_time:.1f}s\n"
            f"Average time per segment: {total_time/total_segments:.1f}s\n"
            f"Completed at: {datetime.now().isoformat()}\n"
            f"="*50 + "\n"
        )
        
        # Log to all active log files
        for log_path in [self.prompt_log_path, self.context_log_path, self.progress_log_path]:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(completion_message)


def get_logger(job_id: Optional[int] = None, filename: Optional[str] = None, job_storage_base: Optional[str] = None, task_type: str = "translation") -> TranslationLogger:
    """
    Get a configured translation logger instance.
    
    Args:
        job_id: Optional job ID
        filename: Optional filename for log naming
        job_storage_base: Optional custom path for job storage
        task_type: Type of task (translation, validation, postedit, style_analysis, etc.)
        
    Returns:
        Configured TranslationLogger instance
    """
    return TranslationLogger(job_id=job_id, user_base_filename=filename, job_storage_base=job_storage_base, task_type=task_type)
