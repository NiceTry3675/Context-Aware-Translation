"""
Domain service for translation validation operations.

This service orchestrates validation logic using the repository pattern,
integrates with the Unit of Work for transaction management,
and publishes domain events for the validation lifecycle.
"""

import os
import json
from typing import Optional, Callable, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from core.translation.validator import TranslationValidator
from core.translation.document import TranslationDocument
from backend.models.translation import TranslationJob
from backend.domains.translation.repository import TranslationJobRepository, SqlAlchemyTranslationJobRepository
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import DomainEvent, EventType
from backend.domains.shared.utils import FileManager
from backend.config.settings import get_settings


class ValidationDomainService:
    """Service layer for translation validation operations using domain patterns."""
    
    def __init__(
        self,
        repository: Optional[TranslationJobRepository] = None,
        uow: Optional[SqlAlchemyUoW] = None,
        file_manager: Optional[FileManager] = None
    ):
        """
        Initialize validation service with dependencies.
        
        Args:
            repository: TranslationJob repository (optional, creates default if not provided)
            uow: Unit of Work for transaction management (optional)
            file_manager: File manager for file operations (optional, uses default if not provided)
        """
        self._repository = repository
        self._uow = uow
        self._file_manager = file_manager or FileManager()
    
    def _get_repository(self, session: Session) -> TranslationJobRepository:
        """Get or create repository instance."""
        if self._repository:
            return self._repository
        return SqlAlchemyTranslationJobRepository(session)
    
    def prepare_validation(
        self,
        session: Session,
        job_id: int,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp"
    ) -> Tuple[TranslationValidator, TranslationDocument, str]:
        """
        Prepare the validator and translation job for validation.
        
        Args:
            session: Database session
            job_id: Translation job ID
            api_key: API key for the model
            model_name: Name of the model to use for validation
            
        Returns:
            Tuple of (validator, validation_document, translated_path)
            
        Raises:
            ValueError: If job not found
            FileNotFoundError: If translated file not found
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[VALIDATION PREP] Starting validation preparation for job_id={job_id}")
        api_key_display = f"{api_key[:8]}..." if api_key else "None"
        logger.info(f"[VALIDATION PREP] Model: {model_name}, API key: {api_key_display}")
        
        repository = self._get_repository(session)
        job = repository.get(job_id)
        
        if not job:
            logger.error(f"[VALIDATION PREP] Translation job {job_id} not found")
            raise ValueError(f"Translation job {job_id} not found")
        
        logger.info(f"[VALIDATION PREP] Found job: status={job.status}, filepath={job.filepath}")
        
        # Get the translated file path
        translated_path = self._get_translated_file_path(job)
        logger.info(f"[VALIDATION PREP] Translated file path: {translated_path}")
        
        if not self._file_manager.file_exists(translated_path):
            logger.error(f"[VALIDATION PREP] Translated file not found: {translated_path}")
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        logger.info(f"[VALIDATION PREP] Translated file exists, initializing validator...")
        
        # Initialize validator with the model API
        try:
            from backend.domains.shared.base.model_factory import ModelAPIFactory
            model_factory = ModelAPIFactory()
            logger.info(f"[VALIDATION PREP] Creating model API with factory...")
            model_api = model_factory.create(api_key, model_name)
            logger.info(f"[VALIDATION PREP] Model API created: {type(model_api)}")
            validator = TranslationValidator(model_api)
            logger.info(f"[VALIDATION PREP] Validator initialized")
        except Exception as e:
            logger.error(f"[VALIDATION PREP] Error creating validator: {str(e)}")
            raise
        
        # Create validation document
        logger.info(f"[VALIDATION PREP] Creating validation document from {job.filepath}")
        try:
            validation_document = TranslationDocument(
                job.filepath,
                original_filename=job.filename,
                target_segment_size=job.segment_size
            )
            logger.info(f"[VALIDATION PREP] Validation document created with {len(validation_document.segments)} segments")
        except Exception as e:
            logger.error(f"[VALIDATION PREP] Error creating validation document: {str(e)}")
            raise
        
        # Load the translated segments from the translated file
        logger.info(f"[VALIDATION PREP] Loading translated segments from {translated_path}")
        try:
            translated_content = self._file_manager.read_file(translated_path)
            logger.info(f"[VALIDATION PREP] Read {len(translated_content)} characters from translated file")
            validation_document.translated_segments = translated_content.split('\n')
            logger.info(f"[VALIDATION PREP] Split into {len(validation_document.translated_segments)} segments")
        except Exception as e:
            logger.error(f"[VALIDATION PREP] Error loading translated segments: {str(e)}")
            raise
        # Filter out empty strings from the list
        validation_document.translated_segments = [
            s for s in validation_document.translated_segments if s.strip()
        ]
        
        # Handle segment count mismatch
        if len(validation_document.segments) != len(validation_document.translated_segments):
            print(f"Warning: Segment count mismatch - "
                  f"Source: {len(validation_document.segments)}, "
                  f"Translated: {len(validation_document.translated_segments)}")
            
            if len(validation_document.translated_segments) > len(validation_document.segments):
                # Too many translated segments, might be due to line breaks
                combined_segments = []
                lines_per_segment = (
                    len(validation_document.translated_segments) // 
                    len(validation_document.segments)
                )
                for i in range(0, len(validation_document.translated_segments), lines_per_segment):
                    combined_segments.append(
                        '\n'.join(validation_document.translated_segments[i:i+lines_per_segment])
                    )
                validation_document.translated_segments = combined_segments[:len(validation_document.segments)]
        
        # Load the glossary from the job if available
        if job.final_glossary:
            validation_document.glossary = (
                json.loads(job.final_glossary) 
                if isinstance(job.final_glossary, str) 
                else job.final_glossary
            )
        
        return validator, validation_document, translated_path
    
    def run_validation(
        self,
        validator: TranslationValidator,
        validation_document: TranslationDocument,
        sample_rate: float = 1.0,
        quick_mode: bool = False,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """
        Run the validation process and return the report.
        
        Args:
            validator: TranslationValidator instance
            validation_document: Document to validate
            sample_rate: Percentage of segments to validate (0.0-1.0)
            quick_mode: Whether to use quick validation mode
            progress_callback: Optional callback for progress updates
            
        Returns:
            Validation report dictionary
        """
        results, summary = validator.validate_document(
            validation_document,
            sample_rate=sample_rate,
            quick_mode=quick_mode,
            progress_callback=progress_callback
        )
        
        # Create the validation report
        report = {
            'summary': summary,
            'detailed_results': [r.to_dict() for r in results],
            'validated_at': datetime.utcnow().isoformat(),
            'sample_rate': sample_rate,
            'quick_mode': quick_mode
        }
        
        return report
    
    def save_validation_report(
        self,
        job: TranslationJob,
        report: Dict[str, Any]
    ) -> str:
        """
        Save the validation report to a file.
        
        Args:
            job: Translation job
            report: Validation report to save
            
        Returns:
            Path to the saved report
        """
        # Use FileManager's standardized path for consistency
        report_path = self._file_manager.get_validation_report_path(job)
        
        # Ensure directory exists
        report_dir = os.path.dirname(report_path)
        os.makedirs(report_dir, exist_ok=True)
        
        # Save the report as JSON
        report_content = json.dumps(report, indent=2, ensure_ascii=False)
        self._file_manager.write_file(report_path, report_content)
        
        return report_path
    
    def update_job_validation_status(
        self,
        session: Session,
        job_id: int,
        status: str,
        progress: Optional[int] = None,
        report_path: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update the job's validation status in the database.
        
        Args:
            session: Database session
            job_id: Translation job ID
            status: New validation status
            progress: Optional progress percentage (0-100)
            report_path: Optional path to validation report
            error_message: Optional error message for failed validations
        """
        repository = self._get_repository(session)
        
        # Update validation status using repository
        repository.update_validation_status(
            job_id,
            status,
            progress=progress,
            report_path=report_path
        )
        
        # Emit appropriate domain event
        if self._uow:
            if status == "PROCESSING":
                event = DomainEvent(
                    event_type=EventType.VALIDATION_STARTED,
                    aggregate_id=job_id,
                    aggregate_type="TranslationJob",
                    payload={"job_id": job_id}
                )
                self._uow.collect_event(event)
            
            elif status == "COMPLETED":
                event = DomainEvent(
                    event_type=EventType.VALIDATION_COMPLETED,
                    aggregate_id=job_id,
                    aggregate_type="TranslationJob",
                    payload={
                        "job_id": job_id,
                        "report_path": report_path
                    }
                )
                self._uow.collect_event(event)
            
            elif status == "FAILED":
                event = DomainEvent(
                    event_type=EventType.VALIDATION_FAILED,
                    aggregate_id=job_id,
                    aggregate_type="TranslationJob",
                    payload={
                        "job_id": job_id,
                        "error_message": error_message
                    }
                )
                self._uow.collect_event(event)
    
    async def validate_translation(
        self,
        session: Session,
        job_id: int,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        sample_rate: float = 1.0,
        quick_mode: bool = False,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """
        Complete validation workflow for a translation job.
        
        This is the main entry point that orchestrates the entire validation process.
        
        Args:
            session: Database session
            job_id: Translation job ID
            api_key: API key for the model
            model_name: Model to use for validation
            sample_rate: Percentage of segments to validate
            quick_mode: Whether to use quick validation
            progress_callback: Optional progress callback
            
        Returns:
            Validation report dictionary
            
        Raises:
            ValueError: If job not found or not ready for validation
            FileNotFoundError: If translated file not found
        """
        repository = self._get_repository(session)
        
        # Start validation
        self.update_job_validation_status(
            session, job_id, "PROCESSING", progress=0
        )
        
        try:
            # Prepare validation
            validator, validation_document, translated_path = self.prepare_validation(
                session, job_id, api_key, model_name
            )
            
            # Run validation
            report = self.run_validation(
                validator,
                validation_document,
                sample_rate,
                quick_mode,
                progress_callback
            )
            
            # Save report
            job = repository.get(job_id)
            report_path = self.save_validation_report(job, report)
            
            # Update status to completed
            self.update_job_validation_status(
                session, job_id, "COMPLETED", 
                progress=100, 
                report_path=report_path
            )
            
            return report
            
        except Exception as e:
            # Update status to failed
            self.update_job_validation_status(
                session, job_id, "FAILED",
                error_message=str(e)
            )
            raise
    
    def _get_translated_file_path(self, job: TranslationJob) -> str:
        """Get the path to the translated file for a job."""
        # The translated files are saved in the translated_novel directory
        # with the pattern: {job_id}_{original_filename_without_ext}_translated.txt
        base_filename = os.path.splitext(job.filename)[0]  # Remove extension
        translated_filename = f"{job.id}_{base_filename}_translated.txt"
        return os.path.join("translated_novel", translated_filename)