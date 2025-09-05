"""
Celery tasks for translation validation.
"""
import traceback
from typing import Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

from ..celery_app import celery_app
from .base import TrackedTask
from ..database import SessionLocal
from ..domains.translation.validation_service import ValidationDomainService
from ..models import TaskKind
from ..domains.translation.repository import SqlAlchemyTranslationJobRepository

logger = logging.getLogger(__name__)


class ValidationTask(TrackedTask):
    """Validation task with tracking."""
    task_kind = TaskKind.VALIDATION
    name = "backend.tasks.validation.process_validation_task"


@celery_app.task(
    base=ValidationTask,
    bind=True,
    name="backend.tasks.validation.process_validation_task",
    max_retries=3,
    default_retry_delay=60
)
def process_validation_task(
    self,
    job_id: int,
    api_key: str,
    model_name: str = "gemini-1.5-pro",
    validation_mode: str = "comprehensive",
    sample_rate: float = 1.0,
    user_id: Optional[int] = None
):
    """
    Process a validation task using Celery.
    
    Args:
        job_id: Translation job ID to validate
        api_key: API key for the model
        model_name: Model to use for validation
        validation_mode: Validation mode (quick, comprehensive)
        sample_rate: Sample rate for validation (0.0 to 1.0)
        user_id: Optional user ID for tracking
    """
    db = None
    
    try:
        # Get database session
        db = self.db_session
        
        # Get the job
        repo = SqlAlchemyTranslationJobRepository(db)
        job = repo.get(job_id)
        if not job:
            logger.error(f"Job ID {job_id} not found")
            raise ValueError(f"Job ID {job_id} not found")
        
        # Update job status
        repo.set_status(job_id, "VALIDATING")
        db.commit()
        logger.info(f"Starting validation for Job ID: {job_id}, Mode: {validation_mode}, Sample Rate: {sample_rate}")
        
        # Update task progress
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Starting validation...'}
        )
        
        # Run validation
        validation_service = ValidationDomainService()
        validation_result = validation_service.validate_translation(
            job_id=job_id,
            api_key=api_key,
            model_name=model_name,
            validation_mode=validation_mode,
            sample_rate=sample_rate
        )
        
        # Store validation results
        if validation_result:
            # Update job with validation results
            job.validation_completed = True
            job.validation_report = validation_result.get('report_path')
            db.commit()
            
            logger.info(f"Validation completed for Job ID: {job_id}")
            
            # Update final progress
            current_task.update_state(
                state='SUCCESS',
                meta={'current': 100, 'total': 100, 'status': 'Validation completed'}
            )
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'report_path': validation_result.get('report_path'),
                'issues_found': validation_result.get('issues_found', 0)
            }
        else:
            raise ValueError("Validation failed to produce results")
            
    except SoftTimeLimitExceeded:
        # Handle soft time limit
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(
                job_id, "FAILED", 
                error="Validation took too long and was terminated"
            )
            db.commit()
        logger.error(f"Validation task {self.request.id} exceeded time limit")
        raise
        
    except Exception as e:
        # Handle other exceptions
        error_message = f"Validation failed: {str(e)}"
        
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(job_id, "FAILED", error=error_message)
            db.commit()
        
        logger.error(f"Validation error for Job ID {job_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Retry the task if retries are available
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {self.request.id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        raise
        
    finally:
        # Clean up
        if db:
            db.close()
        logger.debug(f"Validation for Job ID {job_id} finished. DB session closed.")


# Backward compatibility wrapper
def run_validation_in_background(
    job_id: int,
    api_key: str,
    model_name: str = "gemini-1.5-pro",
    validation_mode: str = "comprehensive",
    sample_rate: float = 1.0
):
    """
    Backward compatibility wrapper for existing code.
    This launches the Celery task asynchronously.
    """
    task = process_validation_task.delay(
        job_id=job_id,
        api_key=api_key,
        model_name=model_name,
        validation_mode=validation_mode,
        sample_rate=sample_rate
    )
    
    logger.info(f"Launched validation task {task.id} for job {job_id}")
    return task.id