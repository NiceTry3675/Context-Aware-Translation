"""
Custom exceptions for the Context-Aware Translation system.
"""

class ProhibitedException(Exception):
    """
    Exception raised when the Gemini API blocks content due to safety settings.
    
    This exception captures detailed information about the prohibited content
    to help with debugging and error logging.
    """
    
    def __init__(self, 
                 message: str,
                 prompt: str = None,
                 source_text: str = None,
                 context: dict = None,
                 api_response: str = None,
                 api_call_type: str = None):
        """
        Initialize the ProhibitedException with detailed error information.
        
        Args:
            message: The error message
            prompt: The full prompt that was sent to the API
            source_text: The original source text being processed
            context: Additional context (e.g., segment index, glossary, etc.)
            api_response: The raw API response or error details
            api_call_type: Type of API call (e.g., 'translation', 'glossary', 'style_analysis')
        """
        super().__init__(message)
        self.prompt = prompt
        self.source_text = source_text
        self.context = context or {}
        self.api_response = api_response
        self.api_call_type = api_call_type
        
    def __str__(self):
        """Return a formatted string representation of the exception."""
        base_msg = super().__str__()
        if self.api_call_type:
            return f"[{self.api_call_type}] {base_msg}"
        return base_msg