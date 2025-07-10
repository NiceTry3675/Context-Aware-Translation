"""
Centralized error logging utility for prohibited content errors.
"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from .exceptions import ProhibitedException


class ProhibitedContentLogger:
    """
    Handles logging of prohibited content errors in a standardized format.
    """
    
    def __init__(self, base_dir: str = "prohibited_content_logs"):
        """
        Initialize the logger with a base directory for log files.
        
        Args:
            base_dir: Directory where prohibited content logs will be stored
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
    def log_prohibited_content(self, 
                             exception: ProhibitedException,
                             job_filename: str,
                             segment_index: Optional[int] = None) -> str:
        """
        Log a prohibited content error to a file.
        
        Args:
            exception: The ProhibitedException containing error details
            job_filename: The base filename of the translation job
            segment_index: Optional segment index where the error occurred
            
        Returns:
            The path to the created log file
        """
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
                                    source_text: str = None,
                                    error_message: str = None,
                                    job_filename: str = "unknown",
                                    segment_index: Optional[int] = None,
                                    context: Dict[str, Any] = None) -> str:
        """
        Convenience method to log prohibited content without creating an exception object.
        
        This is useful for updating existing code that doesn't yet use ProhibitedException.
        
        Returns:
            The path to the created log file
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