"""
Shared Analysis Module

Provides utility classes for various types of document analysis:
- Style analysis for narrative and writing style
- Glossary extraction and management
- Character appearance and trait analysis
"""

from .style_analysis import StyleAnalysis
from .glossary_analysis import GlossaryAnalysis
from .character_analysis import CharacterAnalysis, APPEARANCE_EXTRA_INSTRUCTIONS

__all__ = [
    'StyleAnalysis',
    'GlossaryAnalysis',
    'CharacterAnalysis',
    'APPEARANCE_EXTRA_INSTRUCTIONS'
]