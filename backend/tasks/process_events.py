"""
Celery tasks for processing domain events from the outbox.
"""

import logging
from typing import Optional

from celery import Task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.celery_app import celery_app
from backend.config import settings
from backend.domains.shared.events.processor import (
    EventProcessor,
    LoggingEventHandler,
)
from backend.domains.shared.events.contracts import EventType

logger = logging.getLogger(__name__)


# Create async engine for event processing
engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(
    bind=True,
    name="process_outbox_events",
    max_retries=3,
    default_retry_delay=60
)
def process_outbox_events(self: Task, batch_size: int = 100) -> dict:
    """
    Process pending events from the outbox table.
    
    This task is designed to be run periodically (e.g., every minute)
    to process any pending domain events.
    """
    import asyncio
    
    async def _process():
        processor = EventProcessor(AsyncSessionLocal)
        
        # Register handlers (in production, these would be more sophisticated)
        processor.register_handler(
            EventType.TRANSLATION_COMPLETED,
            LoggingEventHandler()
        )
        processor.register_handler(
            EventType.VALIDATION_COMPLETED,
            LoggingEventHandler()
        )
        processor.register_handler(
            EventType.POST_EDIT_COMPLETED,
            LoggingEventHandler()
        )
        
        # Process pending events
        processed_count = await processor.process_pending_events(batch_size)
        
        return {
            "status": "success",
            "processed_count": processed_count
        }
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_process())
        
        logger.info(f"Processed {result['processed_count']} events")
        return result
        
    except Exception as e:
        logger.error(f"Error processing events: {e}")
        raise self.retry(exc=e)
    finally:
        loop.close()


@celery_app.task(
    name="cleanup_old_events",
    max_retries=1
)
def cleanup_old_events(days_to_keep: int = 30) -> dict:
    """
    Clean up old processed events from the outbox table.
    
    This task should be run daily to prevent the outbox table
    from growing indefinitely.
    """
    import asyncio
    
    async def _cleanup():
        processor = EventProcessor(AsyncSessionLocal)
        deleted_count = await processor.cleanup_old_events(days_to_keep)
        
        return {
            "status": "success",
            "deleted_count": deleted_count
        }
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_cleanup())
        
        logger.info(f"Cleaned up {result['deleted_count']} old events")
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up events: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        loop.close()


# Register periodic tasks with Celery Beat
from celery.schedules import crontab

celery_app.conf.beat_schedule.update({
    'process-outbox-events': {
        'task': 'process_outbox_events',
        'schedule': 60.0,  # Run every minute
        'args': (100,)  # Process up to 100 events per batch
    },
    'cleanup-old-events': {
        'task': 'cleanup_old_events',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
        'args': (30,)  # Keep events for 30 days
    }
})