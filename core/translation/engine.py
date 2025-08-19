"""
Backward Compatibility Module

This module provides backward compatibility for code that still imports from engine.py.
It re-exports the refactored classes with their old names.
"""

from .translation_pipeline import TranslationPipeline, get_segment_ending, _extract_translation_from_response
from .translation_document import TranslationDocument
from sqlalchemy.orm import Session

# Backward compatibility: Rename TranslationPipeline to TranslationEngine
class TranslationEngine(TranslationPipeline):
    """
    Backward compatibility wrapper for TranslationPipeline.
    
    This class maintains the old TranslationEngine name for compatibility
    while using the new TranslationPipeline implementation.
    """
    def __init__(self, gemini_api, dyn_config_builder, db=None, job_id=None, initial_core_style=None):
        super().__init__(gemini_api, dyn_config_builder, db, job_id, initial_core_style)

    def translate_job(self, job):
        """
        Backward compatibility method that wraps translate_document.
        
        Args:
            job: Either a TranslationJob (old) or TranslationDocument (new)
        """
        # If it's actually a TranslationDocument, use it directly
        # Otherwise assume it's the old TranslationJob which has similar interface
        self.translate_document(job)


# Backward compatibility: Rename TranslationDocument to TranslationJob
TranslationJob = TranslationDocument