"""
Celery tasks for translation processing.
"""
import traceback
import gc
from typing import Dict, Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

from ..celery_app import celery_app
from .base import TrackedTask
from ..config.database import SessionLocal
from ..domains.translation.service import TranslationDomainService
from ..domains.tasks.models import TaskKind
from ..domains.translation.repository import SqlAlchemyTranslationJobRepository
from ..domains.shared.provider_context import provider_context_from_payload
from ..domains.shared.uow import SqlAlchemyUoW

logger = logging.getLogger(__name__)


class TranslationTask(TrackedTask):
    """Translation task with tracking."""
    task_kind = TaskKind.TRANSLATION
    name = "backend.celery_tasks.translation.process_translation_task"


@celery_app.task(
    base=TranslationTask,
    bind=True,
    name="backend.celery_tasks.translation.process_translation_task",
    max_retries=3,
    default_retry_delay=60
)
def process_translation_task(
    self,
    job_id: int,
    api_key: str,
    model_name: str,
    style_data: Optional[str] = None,
    glossary_data: Optional[str] = None,
    translation_model_name: Optional[str] = None,
    style_model_name: Optional[str] = None,
    glossary_model_name: Optional[str] = None,
    user_id: Optional[int] = None,
    provider_context: Optional[Dict[str, object]] = None,
    resume: bool = False,
):
    """
    Process a translation job using Celery.
    
    Args:
        job_id: Translation job ID
        api_key: API key for the model
        model_name: Base model name
        style_data: Optional style data
        glossary_data: Optional glossary data
        translation_model_name: Optional override for translation model
        style_model_name: Optional override for style model
        glossary_model_name: Optional override for glossary model
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
        repo.set_status(job_id, "PROCESSING")
        db.commit()
        logger.info(f"Starting translation for Job ID: {job_id}, File: {job.filename}, Model: {model_name}")
        
        if translation_model_name or style_model_name or glossary_model_name:
            logger.info(f"Per-task models: "
                       f"main={translation_model_name or model_name}, "
                       f"style={style_model_name or model_name}, "
                       f"glossary={glossary_model_name or model_name}")
        
        # Update task progress (Celery feature)
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Preparing translation...'}
        )
        
        # Prepare translation components
        from backend.config.database import SessionLocal
        translation_service = TranslationDomainService(SessionLocal)
        context = provider_context_from_payload(provider_context)
        components = translation_service.prepare_translation_job(
            job_id=job_id,
            job=job,
            api_key=api_key,
            model_name=model_name,
            style_data=style_data,
            glossary_data=glossary_data,
            translation_model_name=translation_model_name,
            style_model_name=style_model_name,
            glossary_model_name=glossary_model_name,
            provider_context=context,
            resume=resume,
        )
        
        # Update progress
        current_task.update_state(
            state='PROCESSING',
            meta={'current': 10, 'total': 100, 'status': 'Running translation...'}
        )
        
        # Run the translation
        TranslationDomainService.run_translation(
            job_id=job_id,
            translation_document=components['translation_document'],
            model_api=components['model_api'],
            style_model_api=components.get('style_model_api'),
            glossary_model_api=components.get('glossary_model_api'),
            protagonist_name=components['protagonist_name'],
            initial_glossary=components['initial_glossary'],
            initial_core_style_text=components['initial_core_style_text'],
            db=db,
            usage_collector=components.get('usage_collector'),
        )
        
        # Mark as completed
        repo.set_status(job_id, "COMPLETED")
        db.commit()
        logger.info(f"Translation finished for Job ID: {job_id}, File: {job.filename}")
        
        # Update final progress
        current_task.update_state(
            state='SUCCESS',
            meta={'current': 100, 'total': 100, 'status': 'Translation completed'}
        )

        # Auto-trigger validation if enabled on the job
        try:
            job = repo.get(job_id)
            if job and getattr(job, 'validation_enabled', False):
                # Pre-mark validation status so UI reflects immediate progress
                repo.set_status(job_id, "VALIDATING")
                repo.update_validation_status(job_id, "IN_PROGRESS", progress=0)
                db.commit()

                # Import locally to avoid potential circular imports
                from .validation import process_validation_task

                validation_mode = "quick" if getattr(job, 'quick_validation', False) else "comprehensive"
                sample_rate = (getattr(job, 'validation_sample_rate', 100) or 100) / 100.0

                process_validation_task.delay(
                    job_id=job_id,
                    api_key=api_key,
                    model_name=model_name,
                    validation_mode=validation_mode,
                    sample_rate=sample_rate,
                    user_id=user_id,
                    autotrigger_post_edit=True,
                    provider_context=provider_context,
                )
                logger.info(f"Queued validation task for Job ID: {job_id} (mode={validation_mode}, sample_rate={sample_rate})")
        except Exception as e:
            logger.error(f"Failed to auto-trigger validation for Job ID {job_id}: {e}")

        return {
            'job_id': job_id,
            'status': 'completed',
            'filename': job.filename
        }
        
    except SoftTimeLimitExceeded:
        # Handle soft time limit
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(
                job_id, "FAILED", 
                error="Translation took too long and was terminated"
            )
            db.commit()
        logger.error(f"Translation task {self.request.id} exceeded time limit")
        raise
        
    except Exception as e:
        # Handle other exceptions
        error_message = f"Translation failed: {str(e)}"
        
        if db and job_id:
            repo = SqlAlchemyTranslationJobRepository(db)
            repo.set_status(job_id, "FAILED", error=error_message)
            db.commit()
        
        logger.error(f"Translation error for Job ID {job_id}: {e}")
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
        gc.collect()
        logger.debug(f"Job ID {job_id} finished. DB session closed and GC collected.")


# Backward compatibility wrapper
def run_translation_in_background(
    job_id: int,
    api_key: str,
    model_name: str,
    style_data: Optional[str] = None,
    glossary_data: Optional[str] = None,
    translation_model_name: Optional[str] = None,
    style_model_name: Optional[str] = None,
    glossary_model_name: Optional[str] = None,
    provider_context: Optional[Dict[str, object]] = None,
):
    """
    Backward compatibility wrapper for existing code.
    This launches the Celery task asynchronously.
    """
    task = process_translation_task.delay(
        job_id=job_id,
        api_key=api_key,
        model_name=model_name,
        style_data=style_data,
        glossary_data=glossary_data,
        translation_model_name=translation_model_name,
        style_model_name=style_model_name,
        glossary_model_name=glossary_model_name,
        provider_context=provider_context,
    )
    
    logger.info(f"Launched translation task {task.id} for job {job_id}")
    return task.id
