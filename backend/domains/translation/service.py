"""
Translation domain service using repository pattern and Unit of Work.

This service demonstrates how to use the new architecture with:
- Repository pattern for data access
- Unit of Work for transaction management
- Domain events for decoupled communication
"""

import os
import re
import shutil
import json
import logging
import uuid
from typing import Optional, Dict, Any, List, Tuple
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.translation.document import TranslationDocument
from core.translation.translation_pipeline import TranslationPipeline
from core.translation.usage_tracker import TokenUsageCollector
from .storage_adapter import create_storage_handler
from core.config.builder import DynamicConfigBuilder
from backend.domains.shared.provider_context import (
    ProviderContext,
    provider_context_to_payload,
)
from backend.domains.shared.storage import create_storage
from backend.config.settings import get_settings
from .storage_utils import TranslationStorageManager
from backend.domains.shared.service_base import DomainServiceBase
from backend.domains.analysis import StyleAnalysis, GlossaryAnalysis
from backend.domains.shared import (
    OutboxRepository,
    TranslationStartedEvent,
    TranslationCompletedEvent,
    TranslationFailedEvent,
)
from backend.domains.translation import SqlAlchemyTranslationJobRepository
from backend.domains.translation.models import TranslationJob
from backend.domains.translation.schemas import TranslationJob as TranslationJobSchema
from backend.domains.user.models import User

logger = logging.getLogger(__name__)


class TranslationDomainService(DomainServiceBase):
    """
    Domain service for translation operations.
    
    This service coordinates between repositories, handles business logic,
    and publishes domain events. Also includes translation preparation and
    execution functionality.
    """
    
    def __init__(self, session_factory=None):
        """
        Initialize the service with a session factory.
        
        Args:
            session_factory: Factory function that creates SQLAlchemy sessions
        """
        super().__init__(session_factory=session_factory)
    
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
        with self.unit_of_work() as uow:
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
            # Extract segment_size from kwargs with default value
            segment_size = kwargs.get('segment_size', 500)
            event = TranslationStartedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(job_id),
                job_id=job_id,
                user_id=owner_id,
                filename=filename,
                segment_size=segment_size,
                validation_enabled=False,
                post_edit_enabled=False
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
        with self.unit_of_work() as uow:
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
        with self.unit_of_work() as uow:
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
            event = TranslationCompletedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(job_id),
                job_id=job_id,
                user_id=job.owner_id,
                filename=job.filename,
                duration_seconds=duration_seconds,
                output_path=job.output_path or "",
                segment_count=len(translation_segments) if translation_segments else 0,
                total_characters=sum(len(str(seg)) for seg in (translation_segments or {}).values())
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
        with self.unit_of_work() as uow:
            job_repo = SqlAlchemyTranslationJobRepository(uow.session)
            outbox_repo = OutboxRepository(uow.session)
            
            # Update job status
            job_repo.set_status(job_id, "FAILED", error=error_message)
            
            # Create failure event
            event = TranslationFailedEvent(
                event_id=str(uuid.uuid4()),
                aggregate_id=str(job_id),
                job_id=job_id,
                user_id=None,  # May not have user context when failing
                error_message=error_message,
                error_type="TranslationError",
                failed_at_segment=None
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
        with self.unit_of_work() as uow:
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
        with self.unit_of_work() as uow:
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
        with self.unit_of_work() as uow:
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
        with self.unit_of_work() as uow:
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
        api_key: Optional[str],
        model_name: str,
        style_data: Optional[str] = None,
        glossary_data: Optional[str] = None,
        translation_model_name: Optional[str] = None,
        style_model_name: Optional[str] = None,
        glossary_model_name: Optional[str] = None,
        provider_context: Optional[ProviderContext] = None,
        resume: bool = False,
        turbo_mode: bool = False,
    ) -> Dict[str, Any]:
        """Prepare all the necessary components for a translation job."""
        # Fallbacks: if specific per-task models are not provided, use the top-level model_name
        translation_model_name = translation_model_name or model_name
        style_model_name = style_model_name or model_name
        glossary_model_name = glossary_model_name or model_name

        # Track token usage for all downstream model calls
        usage_collector = TokenUsageCollector()

        # Create per-task model APIs using inherited method
        model_api = self.validate_and_create_model(
            api_key,
            translation_model_name,
            provider_context=provider_context,
            usage_callback=usage_collector.record_event,
        )
        style_model_api = (
            self.validate_and_create_model(
                api_key,
                style_model_name,
                provider_context=provider_context,
                usage_callback=usage_collector.record_event,
            )
            if style_model_name else model_api
        )
        glossary_model_api = (
            self.validate_and_create_model(
                api_key,
                glossary_model_name,
                provider_context=provider_context,
                usage_callback=usage_collector.record_event,
            )
            if glossary_model_name else model_api
        )
        
        # Create storage handler for core integration
        storage_handler = create_storage_handler()
        
        translation_document = TranslationDocument(
            job.filepath,
            original_filename=job.filename,
            target_segment_size=job.segment_size,
            job_id=job_id,
            storage_handler=storage_handler
        )

        # If resuming, prefill translated segments from existing partial file
        if resume:
            try:
                manager = TranslationStorageManager(create_storage(get_settings()))
                cached_segments = manager.read_partial_segments(job_id)
                if cached_segments:
                    prefill_count = min(len(cached_segments), len(translation_document.segments))
                    translation_document.translated_segments = cached_segments[:prefill_count]
                else:
                    existing = asyncio.run(manager.read_translation_output(job_id, job.filename))
                    if existing:
                        print(
                            f"--- Partial segment cache missing for Job ID: {job_id}; "
                            "resume will retranslate from the beginning. ---"
                        )
            except Exception as e:
                print(f"--- WARNING: Failed to load cached segments for Job ID: {job_id}. Error: {e} ---")
        
        # Process style data using StyleAnalysisService
        initial_core_style_text = None
        protagonist_name = "protagonist"
        
        try:
            print(f"--- Analyzing style for Job ID: {job_id} ---")
            # Create model API for style analysis
            style_model_api_for_analysis = self.validate_and_create_model(
                api_key,
                style_model_name,
                provider_context=provider_context,
                usage_callback=usage_collector.record_event,
            )
            
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
            glossary_model_api_for_analysis = self.validate_and_create_model(
                api_key,
                glossary_model_name,
                provider_context=provider_context,
                usage_callback=usage_collector.record_event,
            )
            
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
            'initial_core_style_text': initial_core_style_text,
            'usage_collector': usage_collector,
            'turbo_mode': turbo_mode,
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
        db: Session,
        usage_collector: TokenUsageCollector | None = None,
        turbo_mode: bool = False,
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
            initial_glossary=initial_glossary,
            character_style_model=style_model_api,
            turbo_mode=turbo_mode,
        )
        
        pipeline = TranslationPipeline(
            model_api,
            dyn_config_builder,
            db=db,
            job_id=job_id,
            initial_core_style=initial_core_style_text,
            style_model_api=style_model_api,
            usage_collector=usage_collector,
            turbo_mode=turbo_mode,
        )

        pipeline.translate_document(translation_document)
    
    def list_jobs(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[TranslationJobSchema]:
        """
        List all translation jobs for a user with skip/limit pagination.
        
        Args:
            user_id: ID of the user
            skip: Number of jobs to skip
            limit: Maximum number of jobs to return
            
        Returns:
            List of translation jobs
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            
            # Get jobs with limit
            jobs = repo.list_by_user(user_id, limit=limit + skip)
            
            # Apply skip manually for now
            if skip > 0:
                jobs = jobs[skip:]
            
            # Limit to requested amount
            if len(jobs) > limit:
                jobs = jobs[:limit]
            
            # Convert SQLAlchemy models to Pydantic schemas while session is active
            return [TranslationJobSchema.model_validate(job) for job in jobs]
    
    def create_job(
        self,
        user: User,
        file: UploadFile,
        api_key: Optional[str],
        model_name: str = "gemini-2.5-flash-lite",
        translation_model_name: Optional[str] = None,
        style_model_name: Optional[str] = None,
        glossary_model_name: Optional[str] = None,
        style_data: Optional[str] = None,
        glossary_data: Optional[str] = None,
        segment_size: int = 15000,
        # Validation & Post-Edit toggles
        enable_validation: bool = False,
        quick_validation: bool = False,
        validation_sample_rate: float = 1.0,
        enable_post_edit: bool = False,
        api_provider: str = "gemini",
        provider_config: Optional[str] = None,
        turbo_mode: bool = False,
    ) -> TranslationJobSchema:
        """
        Create a new translation job with file upload.
        
        Args:
            user: Current user
            file: Uploaded file
            api_key: API key for translation service (ignored for Vertex)
            model_name: Default model name
            translation_model_name: Optional override for translation model
            style_model_name: Optional override for style model
            glossary_model_name: Optional override for glossary model
            style_data: Optional style data
            glossary_data: Optional glossary data
            segment_size: Segment size for translation
            enable_validation: Whether to run validation automatically after translation
            quick_validation: Whether to use quick validation mode
            validation_sample_rate: Portion of segments to validate (0.0-1.0)
            enable_post_edit: Whether to run post-edit automatically after validation
            api_provider: Selected provider identifier ('gemini', 'vertex', 'openrouter')
            provider_config: Raw provider payload (JSON string/dict) for Vertex credentials
            
        Returns:
            Created translation job
            
        Raises:
            HTTPException: If API key is invalid or file save fails
        """
        provider_context = self.build_provider_context(api_provider, provider_config)

        # Use provider-specific default models
        fallback_model = "gemini-2.5-flash-lite"
        if provider_context and provider_context.name == "vertex":
            fallback_model = "gemini-2.5-flash"
        elif provider_context and provider_context.name == "openrouter":
            fallback_model = "google/gemini-2.5-flash-lite"

        model_name = model_name or provider_context.default_model or self.config.get(
            "default_model", fallback_model
        )

        # Validate credentials using inherited helper (raises if invalid)
        self.validate_and_create_model(
            api_key,
            model_name,
            provider_context=provider_context,
        )
        
        # Create job
        job_with_id = self.create_translation_job(
            filename=file.filename,
            owner_id=user.id,
            segment_size=segment_size,
            # Persist toggles into job record
            validation_enabled=enable_validation,
            quick_validation=quick_validation,
            validation_sample_rate=int(max(0, min(1.0, validation_sample_rate)) * 100),
            post_edit_enabled=enable_post_edit
        )
        
        # Fetch the complete job using the ID
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            job = repo.get(job_with_id.id)
            
            # Save uploaded file using FileManager
            # Use inherited file_manager property
            try:
                file_path = self.file_manager.save_job_file(file, job.id, file.filename)
            except Exception as e:
                # Update job status to failed
                repo.set_status(job.id, "FAILED", error=f"Failed to save file: {e}")
                uow.commit()
                raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
            
            # Update job with file path
            job.filepath = file_path
            uow.commit()
            
            # Store job and user IDs before session closes
            job_id = job.id
            user_id = user.id
        
        # Start translation in background using Celery
        # Import here to avoid circular dependency
        from backend.celery_tasks.translation import process_translation_task
        
        provider_payload = provider_context_to_payload(provider_context)

        process_translation_task.delay(
            job_id=job_id,
            api_key=api_key,
            model_name=model_name,
            style_data=style_data,
            glossary_data=glossary_data,
            translation_model_name=translation_model_name,
            style_model_name=style_model_name,
            glossary_model_name=glossary_model_name,
            user_id=user_id,
            provider_context=provider_payload,
            turbo_mode=turbo_mode,
        )
        
        # Fetch the job again and convert to Pydantic schema
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            job = repo.get(job_id)
            
            # Convert SQLAlchemy model to Pydantic schema while session is active
            return TranslationJobSchema.model_validate(job)
    
    def get_job(self, job_id: int) -> TranslationJobSchema:
        """
        Get a translation job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Translation job
            
        Raises:
            HTTPException: If job not found
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            job = repo.get(job_id)
            
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Convert SQLAlchemy model to Pydantic schema while session is active
            return TranslationJobSchema.model_validate(job)
    
    def delete_job(
        self,
        user: User,
        job_id: int,
        is_admin: bool = False
    ) -> None:
        """
        Delete a translation job and its associated files.
        
        Args:
            user: Current user
            job_id: Job ID
            is_admin: Whether the user is an admin
            
        Raises:
            HTTPException: If job not found or user not authorized
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            job = repo.get(job_id)
            
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Check ownership or admin role
            if not job.owner or (job.owner.clerk_user_id != user.clerk_user_id and not is_admin):
                raise HTTPException(status_code=403, detail="Not authorized to delete this job")
            
            # Delete associated files
            try:
                # Use inherited file_manager property
                self.file_manager.delete_job_files(job)
            except Exception as e:
                # Log the error but proceed with deleting the DB record
                logger.error(f"Error deleting files for job {job_id}: {e}")
            
            # Nullify dependent usage logs when DB cascade isn't present or is SET NULL
            try:
                from sqlalchemy import update as sa_update
                TUL = __import__('backend.domains.translation.models', fromlist=['TranslationUsageLog']).TranslationUsageLog
                uow.session.execute(
                    sa_update(TUL)
                    .where(TUL.job_id == job.id)
                    .values(job_id=None)
                )
            except Exception as e:
                logger.warning(f"Failed to nullify usage logs for job {job_id}: {e}")
            
            # Delete the job from the database
            repo.delete(job.id)
            uow.commit()
    
    def download_job_output(
        self,
        user: User,
        job_id: int,
        is_admin: bool = False
    ) -> FileResponse:
        """
        Download the output of a translation job.
        
        Args:
            user: Current user
            job_id: Job ID
            is_admin: Whether the user is an admin
            
        Returns:
            FileResponse with the translated file
            
        Raises:
            HTTPException: If job not found, not authorized, or file not available
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            db_job = repo.get(job_id)
            
            if db_job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Check ownership
            if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
                if not is_admin:
                    raise HTTPException(status_code=403, detail="Not authorized to download this file")
            
            if db_job.status not in ["COMPLETED", "FAILED"]:
                raise HTTPException(status_code=400, detail=f"Translation is not completed yet. Current status: {db_job.status}")
            
            if not db_job.filepath:
                raise HTTPException(status_code=404, detail="Filepath not found for this job.")
            
            # Use inherited file_manager property
            file_path, user_translated_filename, media_type = self.file_manager.get_translated_file_path(db_job)
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Translated file not found at path: {file_path}")
            
            return FileResponse(path=file_path, filename=user_translated_filename, media_type=media_type)
    
    def download_job_log(
        self,
        user: User,
        job_id: int,
        log_type: str,
        is_admin: bool = False
    ) -> FileResponse:
        """
        Download log files for a translation job.
        
        Args:
            user: Current user
            job_id: Job ID
            log_type: Type of log ('prompts' or 'context')
            is_admin: Whether the user is an admin
            
        Returns:
            FileResponse with the log file
            
        Raises:
            HTTPException: If job not found, not authorized, or log not available
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            db_job = repo.get(job_id)
            
            if db_job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Check ownership
            if not db_job.owner or db_job.owner.clerk_user_id != user.clerk_user_id:
                if not is_admin:
                    raise HTTPException(status_code=403, detail="Not authorized to download this log")
            
            # Use inherited file_manager property
            if log_type == "prompts":
                log_path = self.file_manager.get_job_prompt_log_path(job_id)
            elif log_type == "context":
                log_path = self.file_manager.get_job_context_log_path(job_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid log type. Must be 'prompts' or 'context'")
            
            if not os.path.exists(log_path):
                raise HTTPException(status_code=404, detail=f"{log_type.capitalize()} log not found for this job")
            
            return FileResponse(
                path=log_path,
                filename=f"job_{job_id}_{log_type}.json",
                media_type="application/json"
            )
    
    def get_job_content(
        self,
        job_id: int
    ) -> dict:
        """
        Get the complete content of a translation job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dict containing the job content and segments
            
        Raises:
            HTTPException: If job not found or content not available
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            job = repo.get(job_id)
            
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Allow access if translation is completed OR if validation/post-edit is completed
            can_access = (
                job.status == "COMPLETED" or
                (job.status == "VALIDATING" and job.validation_status == "COMPLETED") or
                (job.status == "POST_EDITING" and job.post_edit_status == "COMPLETED")
            )
            
            if not can_access:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Job not accessible. Status: {job.status}, Validation: {job.validation_status}, Post-edit: {job.post_edit_status}"
                )
            
            # Try to get segments from database first
            segments = job.translation_segments or []
            
            # If no segments in DB, try to read from file
            if not segments:
                import json
                from pathlib import Path
                
                from backend.config.settings import get_settings
                base_dir = Path(get_settings().job_storage_base)
                segments_path = base_dir / str(job_id) / "output" / "segments.json"
                if segments_path.exists():
                    try:
                        with open(segments_path, 'r', encoding='utf-8') as f:
                            segments = json.load(f)
                    except Exception as e:
                        logger.error(f"Failed to read segments from file: {e}")
            
            # Return the translation segments data
            return {
                "job_id": job.id,
                "status": job.status,
                "segments": segments
            }
    
    def get_job_segments(
        self,
        job_id: int,
        offset: int = 0,
        limit: int = 200
    ) -> dict:
        """
        Get segments from a translation job with pagination.
        
        Args:
            job_id: Job ID
            offset: Number of segments to skip
            limit: Maximum number of segments to return
            
        Returns:
            Dict containing paginated segments
            
        Raises:
            HTTPException: If job not found or segments not available
        """
        with self.unit_of_work() as uow:
            repo = SqlAlchemyTranslationJobRepository(uow.session)
            job = repo.get(job_id)
            
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Allow access if translation is completed OR if validation/post-edit is completed
            can_access = (
                job.status in ["COMPLETED", "FAILED"] or
                (job.status == "VALIDATING" and job.validation_status == "COMPLETED") or
                (job.status == "POST_EDITING" and job.post_edit_status == "COMPLETED")
            )
            
            if not can_access:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Job not accessible. Status: {job.status}, Validation: {job.validation_status}, Post-edit: {job.post_edit_status}"
                )
            
            segments = job.translation_segments or []
            
            # If no segments in DB, try to read from file
            if not segments:
                import json
                from pathlib import Path
                
                from backend.config.settings import get_settings
                base_dir = Path(get_settings().job_storage_base)
                segments_path = base_dir / str(job_id) / "output" / "segments.json"
                if segments_path.exists():
                    try:
                        with open(segments_path, 'r', encoding='utf-8') as f:
                            segments = json.load(f)
                    except Exception as e:
                        logger.error(f"Failed to read segments from file: {e}")
            
            # If no segments available, return appropriate message
            if not segments and job.status == "FAILED":
                raise HTTPException(status_code=404, detail="No segments available - job failed during processing")
            total = len(segments)
            
            # Apply pagination
            paginated_segments = segments[offset:offset + limit]
            
            return {
                "job_id": job.id,
                "status": job.status,
                "segments": paginated_segments,
                "total": total,
                "offset": offset,
                "limit": limit
            }
