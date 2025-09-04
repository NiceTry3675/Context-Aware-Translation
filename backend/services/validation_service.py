import os
import json
from typing import Optional, Callable
from sqlalchemy.orm import Session

from core.translation.validator import TranslationValidator
from core.translation.document import TranslationDocument
from .base.base_service import BaseService
from .. import crud, models


class ValidationService(BaseService):
    """Service layer for translation validation operations."""
    
    def __init__(self):
        """Initialize validation service."""
        super().__init__()
    
    def prepare_validation(
        self,
        job: models.TranslationJob,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite"
    ) -> tuple[TranslationValidator, TranslationDocument, str]:
        """Prepare the validator and translation job for validation."""
        # Get the translated file path using FileManager (used only as fallback)
        translated_path, _, _ = self.file_manager.get_translated_file_path(job)
        
        # Initialize validator
        model_api = self.create_model_api(api_key, model_name)
        # Structured validator (single mode)
        validator = TranslationValidator(model_api)
        
        # Create validation document
        validation_document = TranslationDocument(
            job.filepath, 
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Prefer DB-stored segments for exact boundaries; fallback to file if missing
        if getattr(job, 'translation_segments', None):
            try:
                # Use edited_translation if present, else translated_text
                validation_document.translated_segments = [
                    (seg.get('edited_translation') or seg.get('translated_text') or '')
                    for seg in job.translation_segments
                ]
            except Exception as e:
                print(f"Warning: Failed to load DB translation_segments for validation: {e}")
        else:
            # Fallback: read entire translated file as a single string (avoid line-based splitting)
            if not self.file_manager.file_exists(translated_path):
                raise FileNotFoundError(f"Translated file not found: {translated_path}")
            with open(translated_path, 'r', encoding='utf-8') as f:
                translated_text = f.read()
                # As a conservative fallback, use one segment per source segment by slicing proportionally
                # to prevent artificial inflation due to line breaks.
                # Split text into N chunks where N = len(source segments)
                n = len(validation_document.segments)
                if n > 0:
                    approx_len = max(1, len(translated_text) // n)
                    chunks = []
                    start = 0
                    for i in range(n - 1):
                        end = start + approx_len
                        chunks.append(translated_text[start:end].strip())
                        start = end
                    chunks.append(translated_text[start:].strip())
                    validation_document.translated_segments = chunks
                else:
                    validation_document.translated_segments = []
        
        # Load the glossary from the job if available
        if job.final_glossary:
            validation_document.glossary = json.loads(job.final_glossary) if isinstance(job.final_glossary, str) else job.final_glossary
        
        return validator, validation_document, translated_path
    
    def run_validation(
        self,
        validator: TranslationValidator,
        validation_document: TranslationDocument,
        sample_rate: float,
        quick_mode: bool,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> dict:
        """Run the validation process and return the report."""
        results, summary = validator.validate_document(
            validation_document,
            sample_rate=sample_rate,
            quick_mode=quick_mode,
            progress_callback=progress_callback
        )
        
        # Create the validation report
        report = {
            'summary': summary,
            'detailed_results': [r.to_dict() for r in results]
        }
        
        return report
    
    def save_validation_report(self, job: models.TranslationJob, report: dict) -> str:
        """Save the validation report to a file."""
        # Use FileManager to get the validation report path
        report_path = self.file_manager.get_validation_report_path(job)
        
        # Save the report using base class utility
        self.save_structured_output(report, report_path)
        
        return report_path
    
    def update_job_validation_status(
        self,
        db: Session,
        job: models.TranslationJob,
        status: str,
        progress: Optional[int] = None,
        report_path: Optional[str] = None
    ):
        """Update the job's validation status in the database."""
        job.validation_status = status
        
        if progress is not None:
            job.validation_progress = progress
        
        if report_path:
            job.validation_report_path = report_path
            
        if status == "COMPLETED":
            from sqlalchemy.sql import func
            job.validation_completed_at = func.now()
        
        db.commit()
