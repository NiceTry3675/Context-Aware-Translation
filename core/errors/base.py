"""
Base exception classes for the Context-Aware Translation system.
"""

class TranslationError(Exception):
    """
    Base exception class for all translation-related errors.
    
    This serves as the parent class for all custom exceptions
    in the translation system, providing a common interface
    for error handling and logging.
    """
    
    def __init__(self, message: str, **kwargs):
        """
        Initialize the TranslationError.
        
        Args:
            message: The error message
            **kwargs: Additional context information that subclasses can use
        """
        super().__init__(message)
        self.message = message
        self.context = kwargs
    
    def __str__(self):
        """Return a string representation of the error."""
        return self.message
    
    def to_dict(self):
        """
        Convert the exception to a dictionary for logging or API responses.
        
        Returns:
            dict: A dictionary containing error details
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'context': self.context
        }