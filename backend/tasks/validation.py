"""
Celery tasks for translation validation.
"""
import traceback
from typing import Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
import logging
import os
from datetime import datetime

from ..celery_app import celery_app
from .base import TrackedTask
from ..database import SessionLocal
from ..domains.translation.validation_service import ValidationDomainService
from ..domains.shared.models.task_execution import TaskKind
from ..domains.translation.repository import SqlAlchemyTranslationJobRepository

logger = logging.getLogger(__name__)

# Set up file-based logging for validation tasks
log_dir = "logs/validation_task_logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)


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
    
    # Log to both console and file immediately
    logger.info(f"[VALIDATION TASK START] ========================================")
    logger.info(f"[VALIDATION TASK START] Task ID: {self.request.id if self.request else 'N/A'}")
    logger.info(f"[VALIDATION TASK START] Job ID: {job_id}")
    logger.info(f"[VALIDATION TASK START] Log file: {log_file}")
    logger.info(f"[VALIDATION TASK START] ========================================")
    
    try:
        logger.info(f"[VALIDATION TASK] Starting validation task for job_id={job_id}")
        api_key_display = f"{api_key[:8]}..." if api_key else "None"
        logger.info(f"[VALIDATION TASK] Parameters: api_key={api_key_display}, model={model_name}, mode={validation_mode}, sample_rate={sample_rate}")
        
        # Check if API key is provided, use default from settings if not
        if not api_key:
            logger.info(f"[VALIDATION TASK] No API key provided, using default Gemini API key from settings")
            from backend.config.settings import get_settings
            settings = get_settings()
            api_key = settings.gemini_api_key
            if not api_key:
                logger.error(f"[VALIDATION TASK] No API key provided and no default Gemini API key in settings")
                raise ValueError("API key is required for validation")
        
        # Get database session
        db = self.db_session
        logger.debug(f"[VALIDATION TASK] Database session obtained: {db}")
        
        # Get the job
        repo = SqlAlchemyTranslationJobRepository(db)
        job = repo.get(job_id)
        if not job:
            logger.error(f"[VALIDATION TASK] Job ID {job_id} not found in database")
            raise ValueError(f"Job ID {job_id} not found")
        
        logger.info(f"[VALIDATION TASK] Found job: id={job.id}, status={job.status}, filepath={job.filepath}")
        
        # Update job status
        repo.set_status(job_id, "VALIDATING")
        db.commit()
        logger.info(f"[VALIDATION TASK] Updated job status to VALIDATING")
        logger.info(f"[VALIDATION TASK] Starting validation for Job ID: {job_id}, Mode: {validation_mode}, Sample Rate: {sample_rate}")
        
        # Update task progress
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Starting validation...'}
        )
        
        # Run validation
        validation_service = ValidationDomainService()
        logger.info(f"[VALIDATION TASK] Created ValidationDomainService")
        
        # Prepare validation components
        try:
            logger.info(f"[VALIDATION TASK] Preparing validation components...")
            validator, validation_document, translated_path = validation_service.prepare_validation(
                session=db,
                job_id=job_id,
                api_key=api_key,
                model_name=model_name
            )
            logger.info(f"[VALIDATION TASK] Validation components prepared successfully")
            logger.info(f"[VALIDATION TASK] Translated file path: {translated_path}")
            logger.info(f"[VALIDATION TASK] Document segments: {len(validation_document.segments) if validation_document else 0}")
            logger.info(f"[VALIDATION TASK] Translated segments: {len(validation_document.translated_segments) if validation_document and hasattr(validation_document, 'translated_segments') else 0}")
        except Exception as e:
            logger.error(f"[VALIDATION TASK] Error during validation preparation: {str(e)}")
            logger.error(f"[VALIDATION TASK] Preparation error traceback: {traceback.format_exc()}")
            raise
        
        # Run the validation
        quick_mode = validation_mode == 'quick'
        logger.info(f"[VALIDATION TASK] Running validation with quick_mode={quick_mode}, sample_rate={sample_rate}")
        
        try:
            validation_result = validation_service.run_validation(
                validator=validator,
                validation_document=validation_document,
                sample_rate=sample_rate,
                quick_mode=quick_mode,
                progress_callback=lambda p: current_task.update_state(
                    state='PROCESSING',
                    meta={'current': p, 'total': 100, 'status': f'Validating... {p}%'}
                )
            )
            logger.info(f"[VALIDATION TASK] Validation run completed, result: {validation_result is not None}")
        except Exception as e:
            logger.error(f"[VALIDATION TASK] Error during validation run: {str(e)}")
            logger.error(f"[VALIDATION TASK] Run error traceback: {traceback.format_exc()}")
            raise
        
        # Store validation results
        if validation_result:
            # Save the validation report
            report_path = validation_service.save_validation_report(
                job=job,
                report=validation_result
            )
            
            # Update job with validation results
            job.validation_completed = True
            job.validation_report_path = report_path
            validation_service.update_job_validation_status(
                session=db,
                job_id=job_id,
                status="COMPLETED",
                progress=100,
                report_path=report_path
            )
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