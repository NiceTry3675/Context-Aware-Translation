"""
Celery tasks for processing domain events from the outbox.
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from ..celery_app import celery_app
from .base import DatabaseTask
from ..database import SessionLocal
from ..domains.shared.models.outbox import OutboxEvent
from ..domains.tasks.models import TaskKind
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class EventProcessorTask(DatabaseTask):
    """Event processor task."""
    task_kind = TaskKind.EVENT_PROCESSING
    name = "backend.tasks.event_processor.process_outbox_events"


@celery_app.task(
    base=EventProcessorTask,
    bind=True,
    name="backend.tasks.event_processor.process_outbox_events",
    max_retries=0  # Don't retry this task - it runs periodically
)
def process_outbox_events(self, batch_size: int = 100):
    """
    Process pending events from the outbox table.
    This is a periodic task that runs every 30 seconds (configured in celery_app.py).
    
    Args:
        batch_size: Maximum number of events to process in one batch
    """
    db = None
    processed_count = 0
    failed_count = 0
    
    try:
        # Get database session
        db = self.db_session
        
        # Get pending events (not processed and not failed too many times)
        pending_events = db.query(OutboxEvent).filter(
            and_(
                OutboxEvent.processed_at.is_(None),
                OutboxEvent.retry_count < 5  # Max 5 retries
            )
        ).order_by(OutboxEvent.created_at).limit(batch_size).all()
        
        if not pending_events:
            logger.debug("No pending events to process")
            return {
                'processed': 0,
                'failed': 0,
                'status': 'no_events'
            }
        
        logger.info(f"Processing {len(pending_events)} events from outbox")
        
        for event in pending_events:
            try:
                # Process the event based on its type
                process_event(event)
                
                # Mark as processed
                event.processed_at = datetime.utcnow()
                db.commit()
                
                processed_count += 1
                logger.debug(f"Processed event {event.id} of type {event.event_type}")
                
            except Exception as e:
                # Handle event processing failure
                logger.error(f"Failed to process event {event.id}: {e}")
                
                event.retry_count += 1
                event.last_error = str(e)
                event.next_retry_at = datetime.utcnow() + timedelta(
                    minutes=5 * (2 ** event.retry_count)  # Exponential backoff
                )
                db.commit()
                
                failed_count += 1
        
        logger.info(f"Event processing completed: {processed_count} processed, {failed_count} failed")
        
        return {
            'processed': processed_count,
            'failed': failed_count,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Error in event processor: {e}")
        raise
        
    finally:
        if db:
            db.close()


def process_event(event: OutboxEvent):
    """
    Process a single event based on its type.
    
    This is where you would implement the actual event handling logic.
    For example, sending emails, updating caches, triggering other services, etc.
    """
    event_data = json.loads(event.event_data) if event.event_data else {}
    
    if event.event_type == "TranslationJobCreated":
        handle_translation_job_created(event.aggregate_id, event_data)
    elif event.event_type == "TranslationJobCompleted":
        handle_translation_job_completed(event.aggregate_id, event_data)
    elif event.event_type == "TranslationJobFailed":
        handle_translation_job_failed(event.aggregate_id, event_data)
    elif event.event_type == "UserCreated":
        handle_user_created(event.aggregate_id, event_data)
    elif event.event_type == "PostCreated":
        handle_post_created(event.aggregate_id, event_data)
    else:
        logger.warning(f"Unknown event type: {event.event_type}")


def handle_translation_job_created(job_id: str, data: dict):
    """Handle TranslationJobCreated event."""
    logger.info(f"Translation job {job_id} created: {data.get('filename')}")
    # Could send notification, update analytics, etc.


def handle_translation_job_completed(job_id: str, data: dict):
    """Handle TranslationJobCompleted event."""
    logger.info(f"Translation job {job_id} completed")
    # Could send email notification, trigger downstream processes, etc.


def handle_translation_job_failed(job_id: str, data: dict):
    """Handle TranslationJobFailed event."""
    logger.info(f"Translation job {job_id} failed: {data.get('error')}")
    # Could send alert, trigger retry logic, etc.


def handle_user_created(user_id: str, data: dict):
    """Handle UserCreated event."""
    logger.info(f"User {user_id} created: {data.get('email')}")
    # Could send welcome email, create default settings, etc.


def handle_post_created(post_id: str, data: dict):
    """Handle PostCreated event."""
    logger.info(f"Post {post_id} created: {data.get('title')}")
    # Could update search index, send notifications to followers, etc.


@celery_app.task(name="backend.tasks.event_processor.cleanup_old_events")
def cleanup_old_events(days: int = 30):
    """
    Clean up old processed events from the outbox.
    This can be run periodically (e.g., daily) to keep the outbox table size manageable.
    
    Args:
        days: Delete events older than this many days
    """
    db = None
    
    try:
        db = SessionLocal()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Delete old processed events
        deleted_count = db.query(OutboxEvent).filter(
            and_(
                OutboxEvent.processed_at.isnot(None),
                OutboxEvent.created_at < cutoff_date
            )
        ).delete()
        
        db.commit()
        
        logger.info(f"Deleted {deleted_count} old events from outbox")
        
        return {
            'deleted': deleted_count,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old events: {e}")
        if db:
            db.rollback()
        raise
        
    finally:
        if db:
            db.close()