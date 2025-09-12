"""
Utility modules for the translation engine.

This package provides centralized utilities for:
- File parsing and document I/O
- Text segmentation
- Retry logic and error handling
"""

from .file_parser import parse_document
from .document_io import DocumentOutputManager, DebugLogger
from .text_segmentation import (
    create_segments_for_text, 
    create_segments_for_epub, 
    create_segments_from_plain_text,
    get_segment_statistics
)
from shared.utils.logging import TranslationLogger, get_logger

__all__ = [
    # File operations
    "parse_document",
    "DocumentOutputManager", 
    "DebugLogger",
    # Text segmentation
    "create_segments_for_text",
    "create_segments_for_epub", 
    "create_segments_from_plain_text",
    "get_segment_statistics",
    # Logging
    "TranslationLogger",
    "get_logger",
]
