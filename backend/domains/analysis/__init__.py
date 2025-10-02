"""Analysis Domain

Provides document analysis services including:
- Style analysis for narrative and writing style
- Glossary extraction and management 
- Character appearance and trait analysis
"""

from .service import AnalysisService
from .style_analysis import StyleAnalysis
from .glossary_analysis import GlossaryAnalysis
from .character_analysis import CharacterAnalysis, APPEARANCE_EXTRA_INSTRUCTIONS

__all__ = [
    'AnalysisService',
    'StyleAnalysis',
    'GlossaryAnalysis',
    'CharacterAnalysis',
    'APPEARANCE_EXTRA_INSTRUCTIONS'
]