"""
Celery tasks for post-edit processing.
"""
import traceback
from typing import Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

from ..celery_app import celery_app
from .base import TrackedTask
from ..database import SessionLocal
from ..services.post_edit_service import PostEditService
from ..models import TaskKind
from ..domains.translation.repository import SqlAlchemyTranslationJobRepository

logger = logging.getLogger(__name__)


class PostEditTask(TrackedTask):
    """Post-edit task with tracking."""
    task_kind = TaskKind.POST_EDIT
    name = "backend.tasks.post_edit.process_post_edit_task"


@celery_app.task(
    base=PostEditTask,
    bind=True,
    name="backend.tasks.post_edit.process_post_edit_task",
    max_retries=3,
    default_retry_delay=60
)
def process_post_edit_task(
    self,
    job_id: int,
    api_key: str,
    model_name: str = "gemini-1.5-pro",
    user_id: Optional[int] = None
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
        
        # Update job status
        repo.set_status(job_id, "POST_EDITING")
        db.commit()
        logger.info(f"Starting post-edit for Job ID: {job_id}, Model: {model_name}")
        
        # Update task progress
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Starting post-editing...'}
        )
        
        # Run post-editing
        post_edit_service = PostEditService()
        post_edit_result = post_edit_service.apply_post_edit(
            job_id=job_id,
            api_key=api_key,
            model_name=model_name
        )
        
        # Store post-edit results
        if post_edit_result:
            # Update job with post-edit results
            job.post_edit_completed = True
            job.post_edit_log = post_edit_result.get('log_path')
            job.final_translation = post_edit_result.get('edited_path')
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
            db.commit()
        logger.error(f"Post-edit task {self.request.id} exceeded time limit")
        raise
        
    except Exception as e:
        # Handle other exceptions
        error_message = f"Post-edit failed: {str(e)}"
        
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(job_id, "FAILED", error=error_message)
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
    model_name: str = "gemini-1.5-pro"
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