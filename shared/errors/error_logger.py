"""
Centralized error logging utility for prohibited content errors.
"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from .api_errors import ProhibitedException


class ProhibitedContentLogger:
    """
    Handles logging of prohibited content errors in a standardized format.
    """

    def __init__(self, job_id: Optional[int] = None, base_dir: Optional[str] = None):
        """
        Initialize the logger with a base directory for log files.

        Args:
            job_id: Optional job ID for job-specific logging
            base_dir: Optional custom base directory (defaults to job-specific directory if job_id provided)
        """
        self.job_id = job_id
        self._base_dir = base_dir
        self._dir_created = False

    def set_job_id(self, job_id: Optional[int]):
        """Update the job ID after initialization. This will change the log directory."""
        self.job_id = job_id
        self._dir_created = False  # Reset to allow new directory creation

    @property
    def base_dir(self) -> str:
        """Get the base directory for log files."""
        if self.job_id:
            # Use job-specific directory
            return os.path.join("logs", "jobs", str(self.job_id), "prohibited_content")
        elif self._base_dir:
            return self._base_dir
        else:
            # Don't create legacy directory unless actually logging
            # This prevents creation on import
            return None

    def _ensure_dir_exists(self):
        """Create the directory only when needed (lazy creation)."""
        if not self._dir_created and self.base_dir:
            os.makedirs(self.base_dir, exist_ok=True)
            self._dir_created = True
        
    def log_prohibited_content(self,
                             exception: ProhibitedException,
                             job_filename: str,
                             segment_index: Optional[int] = None) -> Optional[str]:
        """
        Log a prohibited content error to a file.

        Args:
            exception: The ProhibitedException containing error details
            job_filename: The base filename of the translation job
            segment_index: Optional segment index where the error occurred

        Returns:
            The path to the created log file, or None if logging is disabled
        """
        # If no base_dir is configured and no job_id set, skip logging
        if not self.base_dir:
            return None

        # Ensure directory exists before writing
        self._ensure_dir_exists()

        # Create a timestamp for the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Construct the log filename
        segment_part = f"_segment_{segment_index}" if segment_index is not None else ""
        api_type_part = f"_{exception.api_call_type}" if exception.api_call_type else ""
        filename = f"prohibited_{job_filename}{api_type_part}{segment_part}_{timestamp}.txt"
        log_path = os.path.join(self.base_dir, filename)
        
        # Write the log file
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROHIBITED CONTENT ERROR LOG\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            
            # Basic information
            f.write(f"## Error Information\n")
            f.write(f"- Job File: {job_filename}\n")
            if segment_index is not None:
                f.write(f"- Segment Index: {segment_index}\n")
            f.write(f"- API Call Type: {exception.api_call_type or 'Unknown'}\n")
            f.write(f"- Error Message: {str(exception)}\n\n")
            
            # Source text
            if exception.source_text:
                f.write(f"## Source Text\n")
                f.write("```\n")
                f.write(exception.source_text)
                f.write("\n```\n\n")
            
            # Full prompt
            if exception.prompt:
                f.write(f"## Full Prompt Sent to API\n")
                f.write("```\n")
                f.write(exception.prompt)
                f.write("\n```\n\n")
            
            # API response/error details
            if exception.api_response:
                f.write(f"## API Response/Error Details\n")
                f.write("```\n")
                f.write(str(exception.api_response))
                f.write("\n```\n\n")
            
            # Additional context
            if exception.context:
                f.write(f"## Additional Context\n")
                f.write("```json\n")
                f.write(json.dumps(exception.context, indent=2, ensure_ascii=False))
                f.write("\n```\n")
        
        return log_path
    
    def log_simple_prohibited_content(self,
                                    api_call_type: str,
                                    prompt: str,
                                    source_text: Optional[str] = None,
                                    error_message: Optional[str] = None,
                                    job_filename: str = "unknown",
                                    segment_index: Optional[int] = None,
                                    context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convenience method to log prohibited content without creating an exception object.

        This is useful for updating existing code that doesn't yet use ProhibitedException.

        Returns:
            The path to the created log file, or None if logging is disabled
        """
        exception = ProhibitedException(
            message=error_message or "Content blocked by safety settings",
            prompt=prompt,
            source_text=source_text,
            context=context,
            api_call_type=api_call_type
        )
        
        return self.log_prohibited_content(exception, job_filename, segment_index)


# Global logger instance
prohibited_content_logger = ProhibitedContentLogger()