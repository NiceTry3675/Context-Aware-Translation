import os
import json
from typing import Optional, Callable
from sqlalchemy.orm import Session

from core.translation.validator import TranslationValidator
from core.translation.document import TranslationDocument
from .base.base_service import BaseService
from .. import models


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
        # Get the translated file path using FileManager
        translated_path, _, _ = self.file_manager.get_translated_file_path(job)
        
        if not self.file_manager.file_exists(translated_path):
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
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
        
        # Load the translated segments from the translated file
        with open(translated_path, 'r', encoding='utf-8') as f:
            translated_text = f.read()
            validation_document.translated_segments = translated_text.split('\n')
            # Filter out empty strings from the list
            validation_document.translated_segments = [s for s in validation_document.translated_segments if s.strip()]
        
        # Handle segment count mismatch
        if len(validation_document.segments) != len(validation_document.translated_segments):
            print(f"Warning: Segment count mismatch - Source: {len(validation_document.segments)}, Translated: {len(validation_document.translated_segments)}")
            if len(validation_document.translated_segments) > len(validation_document.segments):
                # Too many translated segments, might be due to line breaks
                combined_segments = []
                lines_per_segment = len(validation_document.translated_segments) // len(validation_document.segments)
                for i in range(0, len(validation_document.translated_segments), lines_per_segment):
                    combined_segments.append('\n'.join(validation_document.translated_segments[i:i+lines_per_segment]))
                validation_document.translated_segments = combined_segments[:len(validation_document.segments)]
        
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