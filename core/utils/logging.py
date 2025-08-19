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
    
    def __init__(self, job_id: Optional[int] = None, user_base_filename: Optional[str] = None):
        """
        Initialize the translation logger.
        
        Args:
            job_id: Optional job ID for file naming
            user_base_filename: Base filename for log naming
        """
        self.job_id = job_id
        self.user_base_filename = user_base_filename
        self.start_time = time.time()
        
        # Initialize logging directories
        self._setup_logging_directories()
        
        # Setup log file paths
        self._setup_log_paths()
    
    def _setup_logging_directories(self):
        """Create all necessary logging directories."""
        log_dirs = [
            "logs/debug_prompts",
            "logs/context_log", 
            "logs/validation_logs",
            "logs/postedit_logs",
            "logs/prohibited_content_logs",
            "logs/progress_logs"
        ]
        
        for log_dir in log_dirs:
            os.makedirs(log_dir, exist_ok=True)
    
    def _setup_log_paths(self):
        """Setup paths for various log files."""
        if self.job_id and self.user_base_filename:
            # Job-specific log paths
            self.prompt_log_path = f"logs/debug_prompts/prompts_job_{self.job_id}_{self.user_base_filename}.txt"
            self.context_log_path = f"logs/context_log/context_job_{self.job_id}_{self.user_base_filename}.txt"
            self.progress_log_path = f"logs/progress_logs/progress_job_{self.job_id}_{self.user_base_filename}.txt"
        else:
            # Generic log paths
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.prompt_log_path = f"logs/debug_prompts/prompts_{timestamp}.txt"
            self.context_log_path = f"logs/context_log/context_{timestamp}.txt"
            self.progress_log_path = f"logs/progress_logs/progress_{timestamp}.txt"
    
    def initialize_session(self):
        """Initialize a new translation session with log headers."""
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


class StructuredLogger:
    """
    Logger for structured data like validation reports and post-edit logs.
    """
    
    @staticmethod
    def log_validation_report(job_id: int, filename: str, report_data: Dict[str, Any]):
        """
        Log a validation report in structured format.
        
        Args:
            job_id: Job ID
            filename: Source filename
            report_data: Validation report data
        """
        os.makedirs("logs/validation_logs", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"logs/validation_logs/validation_job_{job_id}_{timestamp}.json"
        
        import json
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'job_id': job_id,
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'report': report_data
            }, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def log_post_edit_report(job_id: int, filename: str, edit_data: Dict[str, Any]):
        """
        Log a post-edit report in structured format.
        
        Args:
            job_id: Job ID
            filename: Source filename
            edit_data: Post-edit data
        """
        os.makedirs("logs/postedit_logs", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"logs/postedit_logs/postedit_job_{job_id}_{timestamp}.json"
        
        import json
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'job_id': job_id,
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'edit_data': edit_data
            }, f, indent=2, ensure_ascii=False)


def get_logger(job_id: Optional[int] = None, filename: Optional[str] = None) -> TranslationLogger:
    """
    Get a configured translation logger instance.
    
    Args:
        job_id: Optional job ID
        filename: Optional filename for log naming
        
    Returns:
        Configured TranslationLogger instance
    """
    return TranslationLogger(job_id=job_id, user_base_filename=filename)