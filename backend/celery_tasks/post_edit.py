"""
Celery tasks for post-edit processing.
"""
import traceback
import os
from typing import Dict, Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

from ..celery_app import celery_app
from .base import TrackedTask
from ..config.database import SessionLocal
from ..domains.post_edit.service import PostEditDomainService
from ..domains.tasks.models import TaskKind
from ..domains.translation.repository import SqlAlchemyTranslationJobRepository
from ..domains.shared.provider_context import provider_context_from_payload

logger = logging.getLogger(__name__)


class PostEditTask(TrackedTask):
    """Post-edit task with tracking."""
    task_kind = TaskKind.POST_EDIT
    name = "backend.celery_tasks.post_edit.process_post_edit_task"


@celery_app.task(
    base=PostEditTask,
    bind=True,
    name="backend.celery_tasks.post_edit.process_post_edit_task",
    max_retries=3,
    default_retry_delay=60
)
def process_post_edit_task(
    self,
    job_id: int,
    api_key: Optional[str],
    model_name: str = "gemini-2.5-flash-lite",
    selected_cases: Optional[dict] = None,
    modified_cases: Optional[dict] = None,
    default_select_all: bool = True,
    user_id: Optional[int] = None,
    provider_context: Optional[Dict[str, object]] = None,
):
    """
    Process a post-edit task using Celery.
    
    Args:
        job_id: Translation job ID to post-edit
        api_key: API key for the model
        model_name: Model to use for post-editing
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
        
        # Update job status and post_edit_status
        repo.set_status(job_id, "POST_EDITING")
        repo.update_post_edit_status(job_id, "IN_PROGRESS", progress=0)
        db.commit()
        context = provider_context_from_payload(provider_context)
        provider_name = context.name if context else "gemini"

        logger.info(
            f"Starting post-edit for Job ID: {job_id}, Model: {model_name}, Provider: {provider_name}"
        )

        if not api_key and provider_name != "vertex":
            from backend.config.settings import get_settings

            settings = get_settings()
            api_key = settings.gemini_api_key
            if not api_key:
                raise ValueError("API key is required for post-editing")
        
        # Update task progress
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Starting post-editing...'}
        )
        
        # Run post-editing
        post_edit_service = PostEditDomainService()
        
        # Prepare post-editing components
        post_editor, translation_document, translated_path, segment_logger = post_edit_service.prepare_post_edit(
            session=db,
            job_id=job_id,
            api_key=api_key,
            model_name=model_name,
            provider_context=context,
        )
        
        # Get validation report path from job (stored in database)
        validation_report_path = job.validation_report_path if hasattr(job, 'validation_report_path') else None
        if not validation_report_path or not os.path.exists(validation_report_path):
            # If not found in DB or file doesn't exist, try FileManager's standard path
            from backend.domains.shared.utils import FileManager
            file_manager = FileManager()
            validation_report_path = file_manager.get_validation_report_path(job)
            if not os.path.exists(validation_report_path):
                # No validation report found
                validation_report_path = None
        
        # Run the post-editing
        def update_progress(p: int):
            """Update both Celery task state and database progress."""
            current_task.update_state(
                state='PROCESSING',
                meta={'current': p, 'total': 100, 'status': f'Post-editing... {p}%'}
            )
            # Also update database progress
            repo.update_post_edit_status(job_id, "IN_PROGRESS", progress=p)
            db.commit()
        
        edited_segments = post_edit_service.run_post_edit(
            post_editor=post_editor,
            translation_document=translation_document,
            translated_path=translated_path,
            validation_report_path=validation_report_path,
            selected_cases=selected_cases,
            modified_cases=modified_cases,
            default_select_all=default_select_all,
            progress_callback=update_progress,
            job_id=job_id,
            segment_logger=segment_logger
        )
        
        # Create result paths
        post_edit_result = {
            'edited_path': translated_path,  # The file is edited in place
            'log_path': post_edit_service.get_post_edit_log_path(job)
        }
        
        # Store post-edit results
        if post_edit_result:
            # Update job with post-edit results
            job.post_edit_completed = True
            job.post_edit_log_path = post_edit_result.get('log_path')
            job.final_translation = post_edit_result.get('edited_path')
            
            # Update post-edit status using repository method
            repo.update_post_edit_status(
                job_id, 
                "COMPLETED", 
                progress=100,
                log_path=post_edit_result.get('log_path')
            )
            
            # Restore the main job status back to COMPLETED
            repo.set_status(job_id, "COMPLETED")
            db.commit()
            
            logger.info(f"Post-edit completed for Job ID: {job_id}")
            
            # Update final progress
            current_task.update_state(
                state='SUCCESS',
                meta={'current': 100, 'total': 100, 'status': 'Post-editing completed'}
            )
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'edited_path': post_edit_result.get('edited_path'),
                'log_path': post_edit_result.get('log_path'),
                'changes_made': post_edit_result.get('changes_made', 0)
            }
        else:
            raise ValueError("Post-edit failed to produce results")
            
    except SoftTimeLimitExceeded:
        # Handle soft time limit
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(
                job_id, "FAILED", 
                error="Post-edit took too long and was terminated"
            )
            repo.update_post_edit_status(job_id, "FAILED")
            db.commit()
        logger.error(f"Post-edit task {self.request.id} exceeded time limit")
        raise
        
    except Exception as e:
        # Handle other exceptions
        error_message = f"Post-edit failed: {str(e)}"
        
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(job_id, "FAILED", error=error_message)
            repo.update_post_edit_status(job_id, "FAILED")
            db.commit()
        
        logger.error(f"Post-edit error for Job ID {job_id}: {e}")
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
        logger.debug(f"Post-edit for Job ID {job_id} finished. DB session closed.")


# Backward compatibility wrapper
def run_post_edit_in_background(
    job_id: int,
    api_key: str,
    model_name: str = "gemini-2.5-flash-lite"
):
    """
    Backward compatibility wrapper for existing code.
    This launches the Celery task asynchronously.
    """
    task = process_post_edit_task.delay(
        job_id=job_id,
        api_key=api_key,
        model_name=model_name
    )
    
    logger.info(f"Launched post-edit task {task.id} for job {job_id}")
    return task.id
