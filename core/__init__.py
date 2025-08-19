"""
Core module for Context-Aware Translation system.
This module provides the main components for literary translation.
"""

# Import translation components
from .translation.translation_pipeline import TranslationPipeline
from .translation.document import TranslationDocument
from .translation.models.gemini import GeminiModel

# Configuration components
from .config.builder import DynamicConfigBuilder
from .config.loader import load_config
from .config.glossary import GlossaryManager
from .config.character_style import CharacterStyleManager

# Prompt components
from .prompts.builder import PromptBuilder
from .prompts.manager import PromptManager
from .prompts.sanitizer import PromptSanitizer

# Utility components
from .utils.file_parser import parse_document
from .utils.retry import retry_with_softer_prompt, retry_on_prohibited_segment

# Error handling
from .errors import (
    ProhibitedException,
    TranslationError,
    prohibited_content_logger
)

__all__ = [
    # Translation components
    'TranslationPipeline',
    'TranslationDocument',
    'GeminiModel',
    
    # Configuration
    'DynamicConfigBuilder',
    'load_config',
    'GlossaryManager',
    'CharacterStyleManager',
    
    # Prompts
    'PromptBuilder',
    'PromptManager',
    'PromptSanitizer',
    
    # Utils
    'parse_document',
    'retry_with_softer_prompt',
    'retry_on_prohibited_segment',
    
    # Errors
    'ProhibitedException',
    'TranslationError',
    'prohibited_content_logger'
]