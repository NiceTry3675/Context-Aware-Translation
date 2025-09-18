"""
Domain service for translation validation operations.

This service orchestrates validation logic using the repository pattern,
integrates with the Unit of Work for transaction management,
and publishes domain events for the validation lifecycle.
"""

import os
import json
import traceback
from typing import Optional, Callable, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from core.translation.validator import TranslationValidator
from core.translation.document import TranslationDocument
from shared.utils.logging import get_logger
from backend.domains.translation.models import TranslationJob
from backend.domains.translation.repository import TranslationJobRepository, SqlAlchemyTranslationJobRepository
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import DomainEvent, EventType
from backend.domains.shared.provider_context import ProviderContext
from backend.domains.shared.service_base import DomainServiceBase
from backend.config.settings import get_settings


class ValidationDomainService(DomainServiceBase):
    """Service layer for translation validation operations using domain patterns."""
    
    def __init__(
        self,
        session_factory=None,
        repository: Optional[TranslationJobRepository] = None,
        uow: Optional[SqlAlchemyUoW] = None,
        storage=None
    ):
        """
        Initialize validation service with dependencies.
        
        Args:
            session_factory: Database session factory
            repository: TranslationJob repository (optional, creates default if not provided)
            uow: Unit of Work for transaction management (optional)
            storage: Storage abstraction for file operations (optional)
        """
        super().__init__(session_factory, repository, uow, storage)
    
    def _get_repository(self, session: Session) -> TranslationJobRepository:
        """Get or create repository instance."""
        return self.get_or_create_repository(session, SqlAlchemyTranslationJobRepository)
    
    def prepare_validation(
        self,
        session: Session,
        job_id: int,
        api_key: Optional[str],
        model_name: str = "gemini-2.5-flash-lite",
        provider_context: Optional[ProviderContext] = None,
    ) -> Tuple[TranslationValidator, TranslationDocument, str, Any]:
        """
        Prepare the validator and translation job for validation.
        
        Args:
            session: Database session
            job_id: Translation job ID
            api_key: API key for the model
            model_name: Name of the model to use for validation
            
        Returns:
            Tuple of (validator, validation_document, translated_path, segment_logger)

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
            self.raise_not_found(f"Translation job {job_id}")
        
        logger.info(f"[VALIDATION PREP] Found job: status={job.status}, filepath={job.filepath}")
        
        # Get the translated file path
        translated_path = self._get_translated_file_path(job)
        logger.info(f"[VALIDATION PREP] Translated file path: {translated_path}")
        
        if not self.file_manager.file_exists(translated_path):
            logger.error(f"[VALIDATION PREP] Translated file not found: {translated_path}")
            raise FileNotFoundError(f"Translated file not found: {translated_path}")
        
        logger.info(f"[VALIDATION PREP] Translated file exists, initializing validator...")
        
        # Initialize validator with the model API and logger
        try:
            logger.info(f"[VALIDATION PREP] Creating model API with validate_and_create_model...")
            model_api = self.validate_and_create_model(
                api_key,
                model_name,
                provider_context=provider_context,
            )
            logger.info(f"[VALIDATION PREP] Model API created: {type(model_api)}")

            # Create a logger for segment I/O
            segment_logger = get_logger(
                job_id=job_id,
                filename=job.filename,
                task_type="validation"
            )
            segment_logger.initialize_session()

            validator = TranslationValidator(model_api, logger=segment_logger)
            logger.info(f"[VALIDATION PREP] Validator initialized with segment logger")
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
            # Log the first segment for debugging
            if validation_document.segments:
                first_seg = validation_document.segments[0]
                logger.debug(f"[VALIDATION PREP] First source segment preview: {first_seg.text[:100]}...")
        except Exception as e:
            logger.error(f"[VALIDATION PREP] Error creating validation document: {str(e)}")
            raise
        
        # Load the translated segments from the database
        logger.info(f"[VALIDATION PREP] Loading translated segments from database")
        try:
            if job.translation_segments:
                print(f"[DEBUG] translation_segments exists, type: {type(job.translation_segments)}")
                # The translation_segments field stores both source and translated segments
                segments_data = (
                    json.loads(job.translation_segments) 
                    if isinstance(job.translation_segments, str)
                    else job.translation_segments
                )
                print(f"[DEBUG] segments_data type: {type(segments_data)}, len: {len(segments_data) if hasattr(segments_data, '__len__') else 'N/A'}")
                
                # Extract just the translated segments
                if isinstance(segments_data, list):
                    print(f"[DEBUG] segments_data is list with {len(segments_data)} items")
                    if segments_data:
                        print(f"[DEBUG] First segment keys: {segments_data[0].keys() if isinstance(segments_data[0], dict) else 'not a dict'}")
                    # Each segment is a dict with 'segment_index', 'source_text', and 'translated_text'
                    validation_document.translated_segments = []
                    for seg in segments_data:
                        if isinstance(seg, dict):
                            # Look for 'translated_text' field (the actual field name)
                            if 'translated_text' in seg:
                                validation_document.translated_segments.append(seg['translated_text'])
                            # Fallback to 'translated' if 'translated_text' not found
                            elif 'translated' in seg:
                                validation_document.translated_segments.append(seg['translated'])
                            else:
                                logger.warning(f"[VALIDATION PREP] Segment {seg.get('segment_index', '?')} has no translated_text field")
                elif isinstance(segments_data, dict) and 'translated' in segments_data:
                    # If it's a dict with 'translated' key containing a list
                    validation_document.translated_segments = segments_data['translated']
                else:
                    # Fallback: assume it's a simple list of translated segments
                    validation_document.translated_segments = segments_data
                
                print(f"[DEBUG] Loaded {len(validation_document.translated_segments)} translated segments")
                logger.info(f"[VALIDATION PREP] Loaded {len(validation_document.translated_segments)} segments from DB")
                # Log the first translated segment for debugging
                if validation_document.translated_segments:
                    logger.debug(f"[VALIDATION PREP] First translated segment preview: {validation_document.translated_segments[0][:100]}...")
            else:
                # Fallback to reading from file if DB segments not available
                logger.warning(f"[VALIDATION PREP] No segments in DB, falling back to file reading")
                translated_content = self.file_manager.read_file(translated_path)
                validation_document.translated_segments = [
                    s for s in translated_content.split('\n') if s.strip()
                ]
                logger.info(f"[VALIDATION PREP] Loaded {len(validation_document.translated_segments)} segments from file")
        except Exception as e:
            logger.error(f"[VALIDATION PREP] Error loading translated segments: {str(e)}")
            logger.error(f"[VALIDATION PREP] Error traceback: {traceback.format_exc()}")
            raise
        
        # Verify segment count match
        if len(validation_document.segments) != len(validation_document.translated_segments):
            logger.warning(f"[VALIDATION PREP] Segment count mismatch - "
                          f"Source: {len(validation_document.segments)}, "
                          f"Translated: {len(validation_document.translated_segments)}")
            # Since we're reading from DB, this shouldn't happen unless there's a data issue
            # We'll just log and continue rather than trying to fix it
        
        # Load the glossary from the job if available
        if job.final_glossary:
            validation_document.glossary = (
                json.loads(job.final_glossary) 
                if isinstance(job.final_glossary, str) 
                else job.final_glossary
            )
        
        return validator, validation_document, translated_path, segment_logger
    
    def run_validation(
        self,
        validator: TranslationValidator,
        validation_document: TranslationDocument,
        sample_rate: float = 1.0,
        quick_mode: bool = False,
        progress_callback: Optional[Callable[[int], None]] = None,
        segment_logger=None
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
        print(f"[DEBUG] run_validation called - segments: {len(validation_document.segments)}, translated: {len(validation_document.translated_segments)}")
        results, summary = validator.validate_document(
            validation_document,
            sample_rate=sample_rate,
            quick_mode=quick_mode,
            progress_callback=progress_callback
        )

        # Log completion if logger is available
        if segment_logger:
            segment_logger.log_completion(
                total_segments=summary.get('validated_segments', 0),
                total_time=None
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
        import logging
        logger = logging.getLogger(__name__)
        
        # Use FileManager's standardized path for consistency
        report_path = self.file_manager.get_validation_report_path(job)
        
        # Log the report structure
        logger.info(f"[VALIDATION SERVICE] Saving report for job {job.id}: "
                   f"keys={list(report.keys())}, "
                   f"summary_keys={list(report.get('summary', {}).keys()) if 'summary' in report else 'N/A'}, "
                   f"detailed_results_count={len(report.get('detailed_results', []))}")
        
        # Ensure directory exists
        report_dir = os.path.dirname(report_path)
        os.makedirs(report_dir, exist_ok=True)
        
        # Save the report as JSON
        report_content = json.dumps(report, indent=2, ensure_ascii=False)
        self.file_manager.write_file(report_path, report_content)
        
        logger.info(f"[VALIDATION SERVICE] Report saved to: {report_path}")
        
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
        try:
            with self.unit_of_work() as uow:
                if status == "PROCESSING":
                    event = DomainEvent(
                        event_type=EventType.VALIDATION_STARTED,
                        aggregate_id=job_id,
                        aggregate_type="TranslationJob",
                        payload={"job_id": job_id}
                    )
                    uow.collect_event(event)
                
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
                    uow.collect_event(event)
                
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
                    uow.collect_event(event)
        except ValueError:
            # No UoW configured, skip event collection
            pass
    
    async def validate_translation(
        self,
        session: Session,
        job_id: int,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
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
        # Use FileManager's method to get the correct translated file path
        file_path, _, _ = self.file_manager.get_translated_file_path(job)
        return file_path
