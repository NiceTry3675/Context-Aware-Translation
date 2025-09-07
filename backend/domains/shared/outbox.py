from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, asc

from backend.domains.shared.repository import SqlAlchemyRepository
from backend.domains.shared.events import DomainEvent, EventType


class OutboxRepository:
    """Repository for managing outbox events."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        self.session = session
    
    def add_event(self, event: DomainEvent) -> None:
        """
        Add a domain event to the outbox.
        
        Note: The actual OutboxEvent model will be created via migration.
        For now, this is the interface definition.
        """
        from backend.domains.shared.events.outbox_model import OutboxEvent
        
        outbox_entry = OutboxEvent(
            event_id=event.event_id,
            aggregate_id=str(event.aggregate_id),  # Convert to string for compatibility
            aggregate_type=event.aggregate_type,
            event_type=event.event_type.value if event.event_type else None,
            payload=event.payload,
            event_metadata=event.metadata,  # Updated field name
            status='pending',  # Add status field
            processed=False,
            occurred_at=event.created_at or datetime.utcnow(),  # Add occurred_at field
            created_at=event.created_at
        )
        
        self.session.add(outbox_entry)
        self.session.flush()
    
    def get_unprocessed_events(self, limit: int = 100) -> List[DomainEvent]:
        """Get unprocessed events from the outbox."""
        from backend.domains.shared.events.outbox_model import OutboxEvent
        
        entries = self.session.query(OutboxEvent).filter(
            OutboxEvent.processed == False
        ).order_by(
            asc(OutboxEvent.created_at)
        ).limit(limit).all()
        
        events = []
        for entry in entries:
            event = DomainEvent(
                event_id=entry.event_id,
                event_type=EventType(entry.event_type) if entry.event_type else None,
                aggregate_id=entry.aggregate_id,
                aggregate_type=entry.aggregate_type,
                payload=entry.payload or {},
                metadata=entry.event_metadata or {},  # Updated field name
                created_at=entry.created_at
            )
            events.append(event)
        
        return events
    
    def mark_as_processed(self, event_id: str) -> bool:
        """Mark an event as processed."""
        from backend.domains.shared.events.outbox_model import OutboxEvent
        
        result = self.session.query(OutboxEvent).filter(
            OutboxEvent.event_id == event_id
        ).update({
            OutboxEvent.processed: True,
            OutboxEvent.processed_at: datetime.utcnow()
        })
        
        self.session.flush()
        return result > 0
    
    def mark_batch_as_processed(self, event_ids: List[str]) -> int:
        """Mark multiple events as processed."""
        from backend.domains.shared.events.outbox_model import OutboxEvent
        
        result = self.session.query(OutboxEvent).filter(
            OutboxEvent.event_id.in_(event_ids)
        ).update({
            OutboxEvent.processed: True,
            OutboxEvent.processed_at: datetime.utcnow()
        }, synchronize_session=False)
        
        self.session.flush()
        return result
    
    def delete_processed_events(self, older_than_days: int = 7) -> int:
        """Delete processed events older than specified days."""
        from backend.domains.shared.events.outbox_model import OutboxEvent
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        result = self.session.query(OutboxEvent).filter(
            and_(
                OutboxEvent.processed == True,
                OutboxEvent.created_at < cutoff_date
            )
        ).delete()
        
        self.session.flush()
        return result
    
    def get_failed_events(self, limit: int = 100) -> List[DomainEvent]:
        """Get events that failed processing (for retry)."""
        from backend.domains.shared.events.outbox_model import OutboxEvent
        
        # Events are considered failed if they're old and unprocessed
        from datetime import timedelta
        retry_threshold = datetime.utcnow() - timedelta(minutes=5)
        
        entries = self.session.query(OutboxEvent).filter(
            and_(
                OutboxEvent.processed == False,
                OutboxEvent.created_at < retry_threshold,
                OutboxEvent.retry_count < 3  # Max 3 retries
            )
        ).order_by(
            asc(OutboxEvent.created_at)
        ).limit(limit).all()
        
        events = []
        for entry in entries:
            event = DomainEvent(
                event_id=entry.event_id,
                event_type=EventType(entry.event_type) if entry.event_type else None,
                aggregate_id=entry.aggregate_id,
                aggregate_type=entry.aggregate_type,
                payload=entry.payload or {},
                metadata=entry.event_metadata or {},  # Updated field name
                created_at=entry.created_at
            )
            events.append(event)
        
        return events
    
    def increment_retry_count(self, event_id: str) -> bool:
        """Increment the retry count for an event."""
        from backend.domains.shared.events.outbox_model import OutboxEvent
        
        result = self.session.query(OutboxEvent).filter(
            OutboxEvent.event_id == event_id
        ).update({
            OutboxEvent.retry_count: OutboxEvent.retry_count + 1,
            OutboxEvent.last_retry_at: datetime.utcnow()
        })
        
        self.session.flush()
        return result > 0


class OutboxEventProcessor:
    """Processes events from the outbox."""
    
    def __init__(self, outbox_repo: OutboxRepository, event_dispatcher):
        """
        Initialize the processor.
        
        Args:
            outbox_repo: Repository for accessing outbox events
            event_dispatcher: Dispatcher for handling events
        """
        self.outbox_repo = outbox_repo
        self.event_dispatcher = event_dispatcher
    
    def process_events(self, batch_size: int = 100) -> int:
        """
        Process unprocessed events from the outbox.
        
        Returns:
            Number of events processed
        """
        events = self.outbox_repo.get_unprocessed_events(limit=batch_size)
        processed_count = 0
        
        for event in events:
            try:
                # Dispatch the event
                self.event_dispatcher.dispatch(event)
                
                # Mark as processed
                self.outbox_repo.mark_as_processed(event.event_id)
                processed_count += 1
                
            except Exception as e:
                # Log error and increment retry count
                print(f"Error processing event {event.event_id}: {e}")
                self.outbox_repo.increment_retry_count(event.event_id)
        
        return processed_count
    
    def retry_failed_events(self, batch_size: int = 50) -> int:
        """
        Retry processing of failed events.
        
        Returns:
            Number of events retried
        """
        events = self.outbox_repo.get_failed_events(limit=batch_size)
        retried_count = 0
        
        for event in events:
            try:
                # Increment retry count first
                self.outbox_repo.increment_retry_count(event.event_id)
                
                # Try to dispatch the event
                self.event_dispatcher.dispatch(event)
                
                # Mark as processed if successful
                self.outbox_repo.mark_as_processed(event.event_id)
                retried_count += 1
                
            except Exception as e:
                # Log error, retry count already incremented
                print(f"Error retrying event {event.event_id}: {e}")
        
        return retried_count
    
    def cleanup_old_events(self, days: int = 7) -> int:
        """
        Clean up old processed events.
        
        Returns:
            Number of events deleted
        """
        return self.outbox_repo.delete_processed_events(older_than_days=days)