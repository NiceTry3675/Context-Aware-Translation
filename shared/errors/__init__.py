"""
Context-Aware Translation system errors and exceptions.

This module contains all custom exceptions used throughout the system.
"""

from .base import TranslationError
from .api_errors import ProhibitedException
from .error_logger import ProhibitedContentLogger, prohibited_content_logger

__all__ = [
    'TranslationError',
    'ProhibitedException',
    'ProhibitedContentLogger',
    'prohibited_content_logger',
]