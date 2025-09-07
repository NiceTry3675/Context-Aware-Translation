"""
Event Processor for handling domain events from the outbox.

This module processes events from the outbox table and dispatches them
to appropriate handlers.
"""

import asyncio
import logging
from typing import Dict, List, Type, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .outbox_model import OutboxEvent
from backend.domains.shared.events.contracts import (
    DomainEvent,
    EventType,
    EventFactory,
    EventHandler
)

logger = logging.getLogger(__name__)


class EventProcessor:
    """
    Processes events from the outbox table.
    
    This processor polls the outbox table for pending events and
    dispatches them to registered handlers.
    """
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.handlers: Dict[EventType, List[EventHandler]] = {}
        self.running = False
    
    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def register_handlers(self, handlers_map: Dict[EventType, List[EventHandler]]) -> None:
        """Register multiple handlers at once."""
        for event_type, handlers in handlers_map.items():
            for handler in handlers:
                self.register_handler(event_type, handler)
    
    async def process_pending_events(self, batch_size: int = 100) -> int:
        """
        Process pending events from the outbox.
        Returns the number of events processed.
        """
        async with self.session_factory() as session:
            # Get pending events
            result = await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .where(OutboxEvent.retry_count < 3)  # Max 3 retries
                .order_by(OutboxEvent.occurred_at)
                .limit(batch_size)
            )
            events = result.scalars().all()
            
            processed_count = 0
            for outbox_event in events:
                try:
                    await self._process_single_event(session, outbox_event)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process event {outbox_event.event_id}: {e}")
                    await self._mark_event_failed(session, outbox_event, str(e))
            
            await session.commit()
            return processed_count
    
    async def _process_single_event(
        self, 
        session: AsyncSession, 
        outbox_event: OutboxEvent
    ) -> None:
        """Process a single event from the outbox."""
        try:
            # Convert outbox event to domain event
            event_type = EventType(outbox_event.event_type)
            domain_event = EventFactory.create_event(
                event_type=event_type,
                event_id=outbox_event.event_id,
                aggregate_id=outbox_event.aggregate_id,
                aggregate_type=outbox_event.aggregate_type,
                occurred_at=outbox_event.occurred_at,
                **outbox_event.payload
            )
            
            # Get handlers for this event type
            handlers = self.handlers.get(event_type, [])
            
            # Execute all handlers
            for handler in handlers:
                try:
                    await handler.handle(domain_event)
                except Exception as e:
                    logger.error(
                        f"Handler {handler.__class__.__name__} failed for event "
                        f"{outbox_event.event_id}: {e}"
                    )
                    # Continue with other handlers even if one fails
            
            # Mark event as processed
            await self._mark_event_processed(session, outbox_event)
            
        except Exception as e:
            logger.error(f"Error processing event {outbox_event.event_id}: {e}")
            raise
    
    async def _mark_event_processed(
        self, 
        session: AsyncSession, 
        outbox_event: OutboxEvent
    ) -> None:
        """Mark an event as successfully processed."""
        await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == outbox_event.id)
            .values(
                status="processed",
                processed=True,
                processed_at=datetime.utcnow()
            )
        )
    
    async def _mark_event_failed(
        self, 
        session: AsyncSession, 
        outbox_event: OutboxEvent,
        error_message: str
    ) -> None:
        """Mark an event as failed and increment retry count."""
        new_retry_count = outbox_event.retry_count + 1
        new_status = "failed" if new_retry_count >= 3 else "pending"
        
        await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == outbox_event.id)
            .values(
                status=new_status,
                retry_count=new_retry_count,
                last_retry_at=datetime.utcnow(),
                last_error=error_message[:1000]  # Truncate error message
            )
        )
    
    async def start_processing(
        self, 
        poll_interval: int = 5,
        batch_size: int = 100
    ) -> None:
        """
        Start processing events in a loop.
        
        Args:
            poll_interval: Seconds between polling attempts
            batch_size: Maximum number of events to process in one batch
        """
        self.running = True
        logger.info("Event processor started")
        
        while self.running:
            try:
                processed = await self.process_pending_events(batch_size)
                if processed > 0:
                    logger.info(f"Processed {processed} events")
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(poll_interval)
    
    def stop_processing(self) -> None:
        """Stop the event processing loop."""
        self.running = False
        logger.info("Event processor stopped")
    
    async def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """
        Clean up old processed events.
        
        Args:
            days_to_keep: Number of days to keep processed events
            
        Returns:
            Number of events deleted
        """
        async with self.session_factory() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old processed events
            result = await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.status == "processed")
                .where(OutboxEvent.processed_at < cutoff_date)
            )
            
            old_events = result.scalars().all()
            count = len(old_events)
            
            for event in old_events:
                await session.delete(event)
            
            await session.commit()
            
            logger.info(f"Cleaned up {count} old events")
            return count


# Example event handlers

class LoggingEventHandler(EventHandler):
    """Simple handler that logs events."""
    
    async def handle(self, event: DomainEvent) -> None:
        logger.info(f"Event received: {event.event_type} - {event.dict()}")


class NotificationEventHandler(EventHandler):
    """Handler that sends notifications for certain events."""
    
    def __init__(self, notification_service):
        self.notification_service = notification_service
    
    async def handle(self, event: DomainEvent) -> None:
        # Example: Send notification for translation completion
        if event.event_type == EventType.TRANSLATION_COMPLETED:
            await self.notification_service.send_completion_notification(
                job_id=event.job_id,
                user_id=event.user_id
            )


class MetricsEventHandler(EventHandler):
    """Handler that updates metrics based on events."""
    
    def __init__(self, metrics_service):
        self.metrics_service = metrics_service
    
    async def handle(self, event: DomainEvent) -> None:
        # Update metrics based on event type
        await self.metrics_service.record_event(
            event_type=event.event_type.value,
            aggregate_type=event.aggregate_type,
            metadata=event.metadata
        )