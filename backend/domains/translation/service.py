"""
Translation domain service using repository pattern and Unit of Work.

This service demonstrates how to use the new architecture with:
- Repository pattern for data access
- Unit of Work for transaction management
- Domain events for decoupled communication
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from backend.domains.shared import (
    SqlAlchemyUoW,
    OutboxRepository,
    TranslationJobCreatedEvent,
    TranslationJobCompletedEvent,
    TranslationJobFailedEvent,
)
from backend.domains.translation import SqlAlchemyTranslationJobRepository
from backend.models.translation import TranslationJob

logger = logging.getLogger(__name__)


class TranslationDomainService:
    """
    Domain service for translation operations.
    
    This service coordinates between repositories, handles business logic,
    and publishes domain events.
    """
    
    def __init__(self, session_factory):
        """
        Initialize the service with a session factory.
        
        Args:
            session_factory: Factory function that creates SQLAlchemy sessions
        """
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
            
            # Store idempotency key if provided
            if idempotency_key:
                job_repo.store_idempotency_key(owner_id, idempotency_key, job.id)
            
            # Create and publish domain event
            event = TranslationJobCreatedEvent(
                job_id=job.id,
                user_id=owner_id,
                filename=filename
            )
            outbox_repo.add_event(event)
            
            # Commit transaction (this will also flush the outbox)
            uow.commit()
            
            logger.info(f"Created translation job {job.id} for user {owner_id}")
            return job
    
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