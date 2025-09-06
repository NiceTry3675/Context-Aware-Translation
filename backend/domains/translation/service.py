"""
Translation domain service using repository pattern and Unit of Work.

This service demonstrates how to use the new architecture with:
- Repository pattern for data access
- Unit of Work for transaction management
- Domain events for decoupled communication
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from core.translation.document import TranslationDocument
from core.translation.translation_pipeline import TranslationPipeline
from core.config.builder import DynamicConfigBuilder
from backend.domains.shared.base import ServiceBase
from backend.domains.analysis import StyleAnalysis, GlossaryAnalysis
from backend.domains.shared import (
    SqlAlchemyUoW,
    OutboxRepository,
    TranslationJobCreatedEvent,
    TranslationJobCompletedEvent,
    TranslationJobFailedEvent,
)
from backend.domains.translation import SqlAlchemyTranslationJobRepository
from backend.domains.translation.models import TranslationJob

logger = logging.getLogger(__name__)


class TranslationDomainService(ServiceBase):
    """
    Domain service for translation operations.
    
    This service coordinates between repositories, handles business logic,
    and publishes domain events. Also includes translation preparation and
    execution functionality.
    """
    
    def __init__(self, session_factory):
        """
        Initialize the service with a session factory.
        
        Args:
            session_factory: Factory function that creates SQLAlchemy sessions
        """
        super().__init__()
        self.session_factory = session_factory
    
    def create_translation_job(
        self,
        filename: str,
        owner_id: int,
        idempotency_key: Optional[str] = None,
        **kwargs
    ) -> TranslationJob:
        """
        Create a new translation job with idempotency support.
        
        Args:
            filename: Name of the file to translate
            owner_id: ID of the user creating the job
            idempotency_key: Optional key for idempotent requests
            **kwargs: Additional job parameters
            
        Returns:
            Created or existing TranslationJob instance
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            # Create repositories
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            outbox_repo = OutboxRepository(uow.session)
            
            # Check for idempotent request
            if idempotency_key:
                existing_job = job_repo.find_by_idempotency_key(owner_id, idempotency_key)
                if existing_job:
                    logger.info(f"Idempotent request detected for key {idempotency_key}, returning existing job {existing_job.id}")
                    return existing_job
            
            # Create new job
            job = TranslationJob(
                filename=filename,
                owner_id=owner_id,
                status="PENDING",
                progress=0,
                created_at=datetime.utcnow(),
                **kwargs
            )
            
            # Add to repository
            job = job_repo.add(job)
            
            # Store the job ID immediately after creation to ensure it's available
            job_id = job.id
            
            # Store idempotency key if provided
            if idempotency_key:
                job_repo.store_idempotency_key(owner_id, idempotency_key, job_id)
            
            # Create and publish domain event
            event = TranslationJobCreatedEvent(
                job_id=job_id,
                user_id=owner_id,
                filename=filename
            )
            outbox_repo.add_event(event)
            
            # Commit transaction (this will also flush the outbox)
            uow.commit()
            
            logger.info(f"Created translation job {job_id} for user {owner_id}")
            
            # Create a simple object with just the ID to avoid detached instance issues
            # The caller can re-fetch the full job if needed
            result = TranslationJob()
            result.id = job_id
            return result
    
    def start_translation(self, job_id: int) -> bool:
        """
        Mark a translation job as started.
        
        Args:
            job_id: ID of the job to start
            
        Returns:
            True if successful, False if job not found
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            
            # Update job status
            job_repo.set_status(job_id, "PROCESSING", progress=0)
            
            # Commit transaction
            uow.commit()
            
            logger.info(f"Started translation job {job_id}")
            return True
    
    def complete_translation(
        self,
        job_id: int,
        duration_seconds: int,
        translation_segments: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Mark a translation job as completed.
        
        Args:
            job_id: ID of the job to complete
            duration_seconds: Time taken for translation
            translation_segments: Optional translation result data
            
        Returns:
            True if successful, False if job not found
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            outbox_repo = OutboxRepository(uow.session)
            
            # Get the job
            job = job_repo.get(job_id)
            if not job:
                return False
            
            # Update job
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            if translation_segments:
                job.translation_segments = translation_segments
            
            # Create completion event
            event = TranslationJobCompletedEvent(
                job_id=job_id,
                duration_seconds=duration_seconds
            )
            outbox_repo.add_event(event)
            
            # Commit transaction
            uow.commit()
            
            logger.info(f"Completed translation job {job_id} in {duration_seconds} seconds")
            return True
    
    def fail_translation(self, job_id: int, error_message: str) -> bool:
        """
        Mark a translation job as failed.
        
        Args:
            job_id: ID of the job that failed
            error_message: Error description
            
        Returns:
            True if successful, False if job not found
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            outbox_repo = OutboxRepository(uow.session)
            
            # Update job status
            job_repo.set_status(job_id, "FAILED", error=error_message)
            
            # Create failure event
            event = TranslationJobFailedEvent(
                job_id=job_id,
                error_message=error_message
            )
            outbox_repo.add_event(event)
            
            # Commit transaction
            uow.commit()
            
            logger.error(f"Translation job {job_id} failed: {error_message}")
            return True
    
    def update_progress(self, job_id: int, progress: int) -> bool:
        """
        Update the progress of a translation job.
        
        Args:
            job_id: ID of the job
            progress: Progress percentage (0-100)
            
        Returns:
            True if successful, False if job not found
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            
            # Update progress
            job_repo.update_progress(job_id, progress)
            
            # Commit transaction
            uow.commit()
            
            logger.debug(f"Updated progress for job {job_id}: {progress}%")
            return True
    
    def get_user_jobs(
        self,
        user_id: int,
        limit: int = 100,
        cursor: Optional[int] = None
    ) -> list:
        """
        Get translation jobs for a user with pagination.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of jobs to return
            cursor: Job ID to start from (for pagination)
            
        Returns:
            List of TranslationJob instances
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            
            jobs = job_repo.list_by_user(user_id, limit=limit, cursor=cursor)
            
            # No need to commit for read-only operation
            return jobs
    
    def start_validation(
        self,
        job_id: int,
        sample_rate: int = 100,
        quick_validation: bool = False
    ) -> bool:
        """
        Start validation for a translation job.
        
        Args:
            job_id: ID of the job to validate
            sample_rate: Percentage of segments to validate
            quick_validation: Whether to use quick validation mode
            
        Returns:
            True if validation started, False if job not found
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            
            # Get the job
            job = job_repo.get(job_id)
            if not job or job.status != "COMPLETED":
                return False
            
            # Update validation fields
            job.validation_enabled = True
            job.validation_status = "IN_PROGRESS"
            job.validation_progress = 0
            job.validation_sample_rate = sample_rate
            job.quick_validation = quick_validation
            
            # Commit transaction
            uow.commit()
            
            logger.info(f"Started validation for job {job_id} with sample rate {sample_rate}%")
            return True
    
    def complete_validation(
        self,
        job_id: int,
        report_path: str
    ) -> bool:
        """
        Mark validation as completed for a job.
        
        Args:
            job_id: ID of the job
            report_path: Path to the validation report
            
        Returns:
            True if successful, False if job not found
        """
        with SqlAlchemyUoW(self.session_factory) as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            
            # Update validation status
            job_repo.update_validation_status(
                job_id,
                "COMPLETED",
                progress=100,
                report_path=report_path
            )
            
            # Commit transaction
            uow.commit()
            
            logger.info(f"Completed validation for job {job_id}")
            return True
    
    def prepare_translation_job(
        self,
        job_id: int,
        job: TranslationJob,  # Pass the full job object
        api_key: str,
        model_name: str,
        style_data: Optional[str] = None,
        glossary_data: Optional[str] = None,
        translation_model_name: Optional[str] = None,
        style_model_name: Optional[str] = None,
        glossary_model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare all the necessary components for a translation job."""
        # Fallbacks: if specific per-task models are not provided, use the top-level model_name
        translation_model_name = translation_model_name or model_name
        style_model_name = style_model_name or model_name
        glossary_model_name = glossary_model_name or model_name

        # Create per-task model APIs
        model_api = self.create_model_api(api_key, translation_model_name)
        style_model_api = self.create_model_api(api_key, style_model_name) if style_model_name else model_api
        glossary_model_api = self.create_model_api(api_key, glossary_model_name) if glossary_model_name else model_api
        
        translation_document = TranslationDocument(
            job.filepath,
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Process style data using StyleAnalysisService
        initial_core_style_text = None
        protagonist_name = "protagonist"
        
        try:
            print(f"--- Analyzing style for Job ID: {job_id} ---")
            # Create model API for style analysis
            style_model_api_for_analysis = self.create_model_api(api_key, style_model_name)
            
            # Create StyleAnalysis instance with model API
            style_service = StyleAnalysis()
            style_service.set_model_api(style_model_api_for_analysis)
            
            # Call analyze_style without api_key and model_name parameters
            style_result = style_service.analyze_style(
                filepath=job.filepath,
                user_style_data=style_data
            )
            
            protagonist_name = style_result['protagonist_name']
            initial_core_style_text = style_result['style_text']
            
            if style_result['source'] == 'user_provided':
                print(f"--- Using user-defined style for Job ID: {job_id} ---")
            else:
                print(f"--- Automatic style analysis complete for Job ID: {job_id} ---")
                
        except Exception as e:
            print(f"--- WARNING: Style analysis failed for Job ID: {job_id}. Error: {e} ---")
            # Use fallback values
            protagonist_name = "protagonist"
            initial_core_style_text = None
        
        # Process glossary data using GlossaryAnalysisService
        initial_glossary = None
        try:
            if glossary_data:
                print(f"--- Processing user-defined glossary for Job ID: {job_id} ---")
            else:
                print(f"--- Extracting automatic glossary for Job ID: {job_id} ---")
            
            # Create model API for glossary analysis
            glossary_model_api_for_analysis = self.create_model_api(api_key, glossary_model_name)
            
            # Create GlossaryAnalysis instance with model API
            glossary_service = GlossaryAnalysis()
            glossary_service.set_model_api(glossary_model_api_for_analysis)
            
            # Call analyze_glossary without api_key and model_name parameters
            initial_glossary = glossary_service.analyze_glossary(
                filepath=job.filepath,
                user_glossary_data=glossary_data
            )
            
            if initial_glossary:
                print(f"--- Glossary prepared with {len(initial_glossary)} terms for Job ID: {job_id} ---")
                
        except Exception as e:
            print(f"--- WARNING: Glossary analysis failed for Job ID: {job_id}. Error: {e} ---")
            initial_glossary = None
        
        return {
            'translation_document': translation_document,
            'model_api': model_api,
            'style_model_api': style_model_api,
            'glossary_model_api': glossary_model_api,
            'protagonist_name': protagonist_name,
            'initial_glossary': initial_glossary,
            'initial_core_style_text': initial_core_style_text
        }
    
    @staticmethod
    def run_translation(
        job_id: int,
        translation_document: TranslationDocument,
        model_api,
        style_model_api,
        glossary_model_api,
        protagonist_name: str,
        initial_glossary: Optional[dict],
        initial_core_style_text: Optional[str],
        db: Session
    ):
        """Execute the translation process."""
        # Always use structured output for configuration extraction
        # Prefer the glossary/analysis model for dynamic guides if it supports structured output
        dyn_model_for_guides = glossary_model_api if hasattr(glossary_model_api, 'generate_structured') else model_api
        if dyn_model_for_guides is model_api and glossary_model_api is not None and glossary_model_api is not model_api:
            print("Warning: Selected glossary/analysis model does not support structured output. Falling back to main model for dynamic guides.")

        dyn_config_builder = DynamicConfigBuilder(
            dyn_model_for_guides,
            protagonist_name,
            initial_glossary=initial_glossary
        )
        
        pipeline = TranslationPipeline(
            model_api,
            dyn_config_builder,
            db=db,
            job_id=job_id,
            initial_core_style=initial_core_style_text,
            style_model_api=style_model_api,
        )
        
        pipeline.translate_document(translation_document)