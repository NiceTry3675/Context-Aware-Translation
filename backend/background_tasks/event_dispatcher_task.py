"""
Background task for processing domain events from the outbox table.

This task runs periodically to:
1. Process unprocessed events from the outbox
2. Retry failed events
3. Clean up old processed events
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.domains.shared import (
    OutboxRepository,
    OutboxEventProcessor,
    EventDispatcher,
    EventType,
    DomainEvent
)
from backend.domains.shared.events import (
    TranslationJobCompletedEvent,
    UserCreatedEvent,
    PostCreatedEvent,
)

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handler for sending notifications based on events."""
    
    def handle(self, event: DomainEvent) -> None:
        """Handle notification events."""
        # This is a placeholder - actual notification logic would go here
        logger.info(f"Notification handler processing event: {event.event_type.value}")
        
        if event.event_type == EventType.TRANSLATION_JOB_COMPLETED:
            # Send email/notification to user about job completion
            logger.info(f"Translation job {event.aggregate_id} completed")
        elif event.event_type == EventType.USER_CREATED:
            # Send welcome email to new user
            logger.info(f"New user created: {event.payload.get('email')}")
        elif event.event_type == EventType.POST_CREATED:
            # Notify followers about new post
            logger.info(f"New post created: {event.payload.get('title')}")


class MetricsHandler:
    """Handler for updating metrics based on events."""
    
    def handle(self, event: DomainEvent) -> None:
        """Handle metrics events."""
        # This is a placeholder - actual metrics logic would go here
        logger.info(f"Metrics handler processing event: {event.event_type.value}")
        
        # Example: Track translation job metrics
        if event.event_type == EventType.TRANSLATION_JOB_COMPLETED:
            duration = event.payload.get('duration_seconds')
            logger.info(f"Job {event.aggregate_id} completed in {duration} seconds")


class AuditLogHandler:
    """Handler for creating audit logs based on events."""
    
    def handle(self, event: DomainEvent) -> None:
        """Handle audit log events."""
        # This is a placeholder - actual audit logging would go here
        logger.info(f"Audit handler processing event: {event.event_type.value}")
        
        # Log important user actions
        if event.event_type == EventType.USER_ROLE_CHANGED:
            old_role = event.payload.get('old_role')
            new_role = event.payload.get('new_role')
            logger.info(f"User {event.aggregate_id} role changed from {old_role} to {new_role}")


def create_event_dispatcher() -> EventDispatcher:
    """
    Create and configure the event dispatcher with handlers.
    
    Returns:
        Configured EventDispatcher instance
    """
    dispatcher = EventDispatcher()
    
    # Register notification handlers
    notification_handler = NotificationHandler()
    dispatcher.register_handler(EventType.TRANSLATION_JOB_COMPLETED, notification_handler)
    dispatcher.register_handler(EventType.TRANSLATION_JOB_FAILED, notification_handler)
    dispatcher.register_handler(EventType.USER_CREATED, notification_handler)
    dispatcher.register_handler(EventType.POST_CREATED, notification_handler)
    
    # Register metrics handlers
    metrics_handler = MetricsHandler()
    dispatcher.register_handler(EventType.TRANSLATION_JOB_COMPLETED, metrics_handler)
    dispatcher.register_handler(EventType.TRANSLATION_JOB_STARTED, metrics_handler)
    dispatcher.register_handler(EventType.VALIDATION_COMPLETED, metrics_handler)
    dispatcher.register_handler(EventType.POST_EDIT_COMPLETED, metrics_handler)
    
    # Register audit handlers
    audit_handler = AuditLogHandler()
    dispatcher.register_handler(EventType.USER_ROLE_CHANGED, audit_handler)
    dispatcher.register_handler(EventType.ANNOUNCEMENT_CREATED, audit_handler)
    dispatcher.register_handler(EventType.POST_DELETED, audit_handler)
    dispatcher.register_handler(EventType.COMMENT_DELETED, audit_handler)
    
    return dispatcher


async def process_outbox_events(
    batch_size: int = 100,
    cleanup_days: int = 7
) -> dict:
    """
    Process events from the outbox table.
    
    Args:
        batch_size: Number of events to process in one batch
        cleanup_days: Number of days to keep processed events
        
    Returns:
        Dictionary with processing statistics
    """
    db: Optional[Session] = None
    
    try:
        # Create database session
        db = SessionLocal()
        
        # Create repositories and processor
        outbox_repo = OutboxRepository(db)
        dispatcher = create_event_dispatcher()
        processor = OutboxEventProcessor(outbox_repo, dispatcher)
        
        # Process unprocessed events
        processed_count = processor.process_events(batch_size=batch_size)
        logger.info(f"Processed {processed_count} new events")
        
        # Retry failed events
        retried_count = processor.retry_failed_events(batch_size=batch_size // 2)
        logger.info(f"Retried {retried_count} failed events")
        
        # Clean up old events
        cleaned_count = processor.cleanup_old_events(days=cleanup_days)
        logger.info(f"Cleaned up {cleaned_count} old events")
        
        # Commit all changes
        db.commit()
        
        return {
            "processed": processed_count,
            "retried": retried_count,
            "cleaned": cleaned_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing outbox events: {str(e)}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


async def dispatch_single_event(event: DomainEvent) -> bool:
    """
    Dispatch a single event immediately (for testing).
    
    Args:
        event: The domain event to dispatch
        
    Returns:
        True if successful, False otherwise
    """
    try:
        dispatcher = create_event_dispatcher()
        dispatcher.dispatch(event)
        return True
    except Exception as e:
        logger.error(f"Error dispatching event {event.event_id}: {str(e)}")
        return False


# This can be called periodically by a scheduler (e.g., every minute)
if __name__ == "__main__":
    import asyncio
    
    async def main():
        """Run the event processor once."""
        stats = await process_outbox_events()
        print(f"Event processing completed: {stats}")
    
    asyncio.run(main())