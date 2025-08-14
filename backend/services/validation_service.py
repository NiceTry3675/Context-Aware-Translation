import os
import json
from typing import Optional, Callable
from sqlalchemy.orm import Session

from core.validation.validator import TranslationValidator
from core.translation.job import TranslationJob
from .translation_service import TranslationService
from .. import crud, models


class ValidationService:
    """Service layer for translation validation operations."""
    
    @staticmethod
    def prepare_validation(
        job: models.TranslationJob,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite"
    ) -> tuple[TranslationValidator, TranslationJob, str]:
        """Prepare the validator and translation job for validation."""
        # Get the translated file path
        unique_base = os.path.splitext(os.path.basename(job.filepath))[0]
        original_ext = os.path.splitext(job.filename)[1].lower()
        
        if original_ext == '.epub':
            output_ext = '.epub'
        else:
            output_ext = '.txt'
        
        translated_filename = f"{unique_base}_translated{output_ext}"
        translated_path = os.path.join("translated_novel", translated_filename)
        
        if not os.path.exists(translated_path):
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        # Initialize validator
        from core.config.loader import load_config
        config = load_config()
        model_api = TranslationService.get_model_api(api_key, model_name, config)
        # Structured validator (single mode)
        validator = TranslationValidator(model_api)
        
        # Create validation job
        validation_job = TranslationJob(
            job.filepath, 
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Load the translated segments from the translated file
        with open(translated_path, 'r', encoding='utf-8') as f:
            translated_text = f.read()
            validation_job.translated_segments = translated_text.split('\n')
            # Filter out empty strings from the list
            validation_job.translated_segments = [s for s in validation_job.translated_segments if s.strip()]
        
        # Handle segment count mismatch
        if len(validation_job.segments) != len(validation_job.translated_segments):
            print(f"Warning: Segment count mismatch - Source: {len(validation_job.segments)}, Translated: {len(validation_job.translated_segments)}")
            if len(validation_job.translated_segments) > len(validation_job.segments):
                # Too many translated segments, might be due to line breaks
                combined_segments = []
                lines_per_segment = len(validation_job.translated_segments) // len(validation_job.segments)
                for i in range(0, len(validation_job.translated_segments), lines_per_segment):
                    combined_segments.append('\n'.join(validation_job.translated_segments[i:i+lines_per_segment]))
                validation_job.translated_segments = combined_segments[:len(validation_job.segments)]
        
        # Load the glossary from the job if available
        if job.final_glossary:
            validation_job.glossary = json.loads(job.final_glossary) if isinstance(job.final_glossary, str) else job.final_glossary
        
        return validator, validation_job, translated_path
    
    @staticmethod
    def run_validation(
        validator: TranslationValidator,
        validation_job: TranslationJob,
        sample_rate: float,
        quick_mode: bool,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> dict:
        """Run the validation process and return the report."""
        results, summary = validator.validate_job(
            validation_job,
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
    
    @staticmethod
    def save_validation_report(job: models.TranslationJob, report: dict) -> str:
        """Save the validation report to a file."""
        os.makedirs("validation_logs", exist_ok=True)
        # Include job ID to prevent conflicts with duplicate filenames
        report_filename = f"{job.id}_{os.path.splitext(job.filename)[0]}_validation_report.json"
        report_path = os.path.join("validation_logs", report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report_path
    
    @staticmethod
    def update_job_validation_status(
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