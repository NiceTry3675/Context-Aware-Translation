"""
Celery tasks for translation validation.
"""
import traceback
from typing import Dict, Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
import logging
import os
from datetime import datetime

from ..celery_app import celery_app
from .base import TrackedTask
from ..config.database import SessionLocal
from ..domains.validation.service import ValidationDomainService
from ..domains.tasks.models import TaskKind
from ..domains.translation.repository import SqlAlchemyTranslationJobRepository
from ..domains.shared.provider_context import provider_context_from_payload

logger = logging.getLogger(__name__)

# Note: File-based logging will be set up per-job in the task function
logger.setLevel(logging.DEBUG)


class ValidationTask(TrackedTask):
    """Validation task with tracking."""
    task_kind = TaskKind.VALIDATION
    name = "backend.celery_tasks.validation.process_validation_task"


@celery_app.task(
    base=ValidationTask,
    bind=True,
    name="backend.celery_tasks.validation.process_validation_task",
    max_retries=3,
    default_retry_delay=60,
    time_limit=None,  # No time limit for validation tasks
    soft_time_limit=None
)
def process_validation_task(
    self,
    job_id: int,
    api_key: str,
    backup_api_keys: Optional[list[str]] = None,
    requests_per_minute: Optional[int] = None,
    model_name: str = "gemini-flash-lite-latest",
    thinking_level: Optional[str] = None,
    validation_mode: str = "comprehensive",
    sample_rate: float = 1.0,
    user_id: Optional[int] = None,
    autotrigger_post_edit: bool = False,
    provider_context: Optional[Dict[str, object]] = None,
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
    
    # Set up job-specific file logging
    log_dir = os.path.join("logs", "jobs", str(job_id), "tasks")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"validation_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Create a job-specific file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to task_logger for this task
    task_logger = logging.getLogger(f"{__name__}.job_{job_id}")
    task_logger.addHandler(file_handler)
    task_logger.setLevel(logging.DEBUG)

    # Log to both console and file immediately
    task_logger.info(f"[VALIDATION TASK START] ========================================")
    task_logger.info(f"[VALIDATION TASK START] Task ID: {self.request.id if self.request else 'N/A'}")
    task_logger.info(f"[VALIDATION TASK START] Job ID: {job_id}")
    task_logger.info(f"[VALIDATION TASK START] Log file: {log_file}")
    task_logger.info(f"[VALIDATION TASK START] ========================================")

    try:
        context = provider_context_from_payload(provider_context)
        provider_name = context.name if context else "gemini"

        task_logger.info(f"[VALIDATION TASK] Starting validation task for job_id={job_id}")
        api_key_display = f"{api_key[:8]}..." if api_key else "None"
        task_logger.info(
            f"[VALIDATION TASK] Parameters: api_key={api_key_display}, model={model_name}, thinking_level={thinking_level}, mode={validation_mode}, sample_rate={sample_rate}, provider={provider_name}"
        )
        
        # Check if API key is provided when required
        if provider_name != "vertex" and not (api_key or backup_api_keys):
            task_logger.error(
                "[VALIDATION TASK] No API key provided for non-Vertex provider"
            )
            raise ValueError("API key is required for validation")
        
        # Get database session
        db = self.db_session
        task_logger.debug(f"[VALIDATION TASK] Database session obtained: {db}")
        
        # Get the job
        repo = SqlAlchemyTranslationJobRepository(db)
        job = repo.get(job_id)
        if not job:
            task_logger.error(f"[VALIDATION TASK] Job ID {job_id} not found in database")
            raise ValueError(f"Job ID {job_id} not found")
        
        task_logger.info(f"[VALIDATION TASK] Found job: id={job.id}, status={job.status}, filepath={job.filepath}")
        
        # Update job status and validation_status
        repo.set_status(job_id, "VALIDATING")
        repo.update_validation_status(job_id, "IN_PROGRESS", progress=0)
        db.commit()
        task_logger.info(f"[VALIDATION TASK] Updated job status to VALIDATING and validation_status to IN_PROGRESS")
        task_logger.info(f"[VALIDATION TASK] Starting validation for Job ID: {job_id}, Mode: {validation_mode}, Sample Rate: {sample_rate}")
        
        # Update task progress
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Starting validation...'}
        )
        
        # Run validation
        validation_service = ValidationDomainService()
        task_logger.info(f"[VALIDATION TASK] Created ValidationDomainService")
        
        # Prepare validation components
        try:
            task_logger.info(f"[VALIDATION TASK] Preparing validation components...")
            validator, validation_document, translated_path, segment_logger, usage_collector = validation_service.prepare_validation(
                session=db,
                job_id=job_id,
                api_key=api_key,
                backup_api_keys=backup_api_keys,
                requests_per_minute=requests_per_minute,
                model_name=model_name,
                thinking_level=thinking_level,
                provider_context=context,
            )
            task_logger.info(f"[VALIDATION TASK] Validation components prepared successfully")
            task_logger.info(f"[VALIDATION TASK] Translated file path: {translated_path}")
            task_logger.info(f"[VALIDATION TASK] Document segments: {len(validation_document.segments) if validation_document else 0}")
            task_logger.info(f"[VALIDATION TASK] Translated segments: {len(validation_document.translated_segments) if validation_document and hasattr(validation_document, 'translated_segments') else 0}")
        except Exception as e:
            task_logger.error(f"[VALIDATION TASK] Error during validation preparation: {str(e)}")
            task_logger.error(f"[VALIDATION TASK] Preparation error traceback: {traceback.format_exc()}")
            raise
        
        # Run the validation
        quick_mode = validation_mode == 'quick'
        task_logger.info(f"[VALIDATION TASK] Running validation with quick_mode={quick_mode}, sample_rate={sample_rate}")
        
        def update_progress(p: int):
            """Update both Celery task state and database progress."""
            current_task.update_state(
                state='PROCESSING',
                meta={'current': p, 'total': 100, 'status': f'Validating... {p}%'}
            )
            # Also update database progress
            repo.update_validation_status(job_id, "IN_PROGRESS", progress=p)
            db.commit()
        
        try:
            validation_result = validation_service.run_validation(
                validator=validator,
                validation_document=validation_document,
                sample_rate=sample_rate,
                quick_mode=quick_mode,
                progress_callback=update_progress,
                segment_logger=segment_logger
            )
            task_logger.info(f"[VALIDATION TASK] Validation run completed, result: {validation_result is not None}")
        except Exception as e:
            task_logger.error(f"[VALIDATION TASK] Error during validation run: {str(e)}")
            task_logger.error(f"[VALIDATION TASK] Run error traceback: {traceback.format_exc()}")
            raise
        
        # Store validation results
        if validation_result:
            task_logger.info(f"[VALIDATION TASK] Validation result structure: "
                       f"keys={list(validation_result.keys())}, "
                       f"summary={validation_result.get('summary', {})}, "
                       f"detailed_results_count={len(validation_result.get('detailed_results', []))}")
            
            # Save the validation report
            report_path = validation_service.save_validation_report(
                job=job,
                report=validation_result
            )
            
            # Save token usage from validation
            try:
                from core.translation.progress_tracker import ProgressTracker
                events = usage_collector.events() if usage_collector else []
                if events:
                    progress_tracker = ProgressTracker(db=db, job_id=job_id, filename=job.filename)
                    progress_tracker.record_usage_log(
                        original_text="validation_process",
                        translated_text="validation_completed",
                        model_name=model_name,
                        token_events=events,
                    )
                    task_logger.info(f"[VALIDATION TASK] Recorded {len(events)} token usage events")
                else:
                    task_logger.warning(f"[VALIDATION TASK] No token usage events found")
            except Exception as e:
                task_logger.error(f"[VALIDATION TASK] Failed to record token usage: {e}")

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
            
            # Restore the main job status back to COMPLETED
            repo.set_status(job_id, "COMPLETED")
            db.commit()
            
            task_logger.info(f"[VALIDATION TASK] Validation completed for Job ID: {job_id}, report saved to: {report_path}")
            
            # Update final progress
            current_task.update_state(
                state='SUCCESS',
                meta={'current': 100, 'total': 100, 'status': 'Validation completed'}
            )

            # Auto-trigger post-edit only when explicitly allowed by caller
            try:
                job = repo.get(job_id)
                if autotrigger_post_edit and job and getattr(job, 'post_edit_enabled', False):
                    # Pre-mark post-edit status so UI reflects immediate progress
                    repo.set_status(job_id, "POST_EDITING")
                    repo.update_post_edit_status(job_id, "IN_PROGRESS", progress=0)
                    db.commit()

                    # Import locally to avoid circular imports
                    from .post_edit import process_post_edit_task
                    process_post_edit_task.delay(
                        job_id=job_id,
                        api_key=api_key,
                        backup_api_keys=backup_api_keys,
                        requests_per_minute=requests_per_minute,
                        model_name=model_name,
                        thinking_level=thinking_level,
                        default_select_all=True,
                        user_id=user_id,
                        provider_context=provider_context,
                    )
                    task_logger.info(f"[VALIDATION TASK] Queued post-edit task for Job ID: {job_id}")
            except Exception as e:
                task_logger.error(f"[VALIDATION TASK] Failed to auto-trigger post-edit for Job ID {job_id}: {e}")
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'report_path': report_path,
                'issues_found': len(validation_result.get('detailed_results', []))
            }
        else:
            task_logger.error(f"[VALIDATION TASK] Validation failed to produce results for job {job_id}")
            raise ValueError("Validation failed to produce results")
            
    except SoftTimeLimitExceeded:
        # Handle soft time limit
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(
                job_id, "FAILED", 
                error="Validation took too long and was terminated"
            )
            repo.update_validation_status(job_id, "FAILED")
            db.commit()
        task_logger.error(f"Validation task {self.request.id} exceeded time limit")
        raise
        
    except Exception as e:
        # Handle other exceptions
        error_message = f"Validation failed: {str(e)}"
        
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(job_id, "FAILED", error=error_message)
            repo.update_validation_status(job_id, "FAILED")
            db.commit()
        
        task_logger.error(f"Validation error for Job ID {job_id}: {e}")
        task_logger.error(traceback.format_exc())
        
        # Retry the task if retries are available
        if self.request.retries < self.max_retries:
            task_logger.info(f"Retrying task {self.request.id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        raise
        
    finally:
        # Clean up
        if db:
            db.close()
        task_logger.debug(f"Validation for Job ID {job_id} finished. DB session closed.")


# Backward compatibility wrapper
def run_validation_in_background(
    job_id: int,
    api_key: str,
    backup_api_keys: Optional[list[str]] = None,
    requests_per_minute: Optional[int] = None,
    model_name: str = "gemini-flash-lite-latest",
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
        backup_api_keys=backup_api_keys,
        requests_per_minute=requests_per_minute,
        model_name=model_name,
        validation_mode=validation_mode,
        sample_rate=sample_rate
    )
    
    logger.info(f"Launched validation task {task.id} for job {job_id}")
    return task.id
