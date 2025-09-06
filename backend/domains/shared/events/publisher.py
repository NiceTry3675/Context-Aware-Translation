"""
Domain Event Publisher with Outbox Pattern Integration

This module provides event publishing capabilities using the outbox pattern
to ensure reliable event delivery across domains.
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domains.shared.models.outbox import OutboxEvent
from backend.domains.shared.events.contracts import (
    DomainEvent,
    EventType,
    TranslationCompletedEvent,
    TranslationFailedEvent,
    ValidationCompletedEvent,
    PostEditCompletedEvent,
    UserCreatedEvent,
    PostCreatedEvent,
    CommentAddedEvent
)


class EventPublisher:
    """
    Publishes domain events using the outbox pattern.
    Events are first stored in the database and then processed asynchronously.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a single domain event.
        The event is stored in the outbox table for reliable delivery.
        """
        outbox_event = OutboxEvent(
            event_id=event.event_id or str(uuid.uuid4()),
            event_type=event.event_type.value,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            payload=event.dict(exclude={"event_id", "event_type", "aggregate_id", "aggregate_type"}),
            occurred_at=event.occurred_at,
            status="pending"
        )
        
        self.session.add(outbox_event)
        # Note: Commit should be handled by the Unit of Work pattern
    
    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """Publish multiple domain events in a single transaction."""
        for event in events:
            await self.publish(event)
    
    # Convenience methods for common events
    
    async def publish_translation_completed(
        self,
        job_id: int,
        user_id: Optional[int],
        filename: str,
        duration_seconds: int,
        output_path: str,
        segment_count: int,
        total_characters: int
    ) -> None:
        """Publish a translation completed event."""
        event = TranslationCompletedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(job_id),
            job_id=job_id,
            user_id=user_id,
            filename=filename,
            duration_seconds=duration_seconds,
            output_path=output_path,
            segment_count=segment_count,
            total_characters=total_characters
        )
        await self.publish(event)
    
    async def publish_translation_failed(
        self,
        job_id: int,
        user_id: Optional[int],
        error_message: str,
        error_type: str,
        failed_at_segment: Optional[int] = None
    ) -> None:
        """Publish a translation failed event."""
        event = TranslationFailedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(job_id),
            job_id=job_id,
            user_id=user_id,
            error_message=error_message,
            error_type=error_type,
            failed_at_segment=failed_at_segment
        )
        await self.publish(event)
    
    async def publish_validation_completed(
        self,
        job_id: int,
        user_id: Optional[int],
        total_issues: int,
        critical_issues: int,
        report_path: str,
        validation_score: Optional[float] = None
    ) -> None:
        """Publish a validation completed event."""
        event = ValidationCompletedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(job_id),
            job_id=job_id,
            user_id=user_id,
            total_issues=total_issues,
            critical_issues=critical_issues,
            report_path=report_path,
            validation_score=validation_score
        )
        await self.publish(event)
    
    async def publish_post_edit_completed(
        self,
        job_id: int,
        user_id: Optional[int],
        corrections_applied: int,
        output_path: str,
        log_path: str
    ) -> None:
        """Publish a post-edit completed event."""
        event = PostEditCompletedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(job_id),
            job_id=job_id,
            user_id=user_id,
            corrections_applied=corrections_applied,
            output_path=output_path,
            log_path=log_path
        )
        await self.publish(event)
    
    async def publish_user_created(
        self,
        user_id: int,
        clerk_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        role: str = "user"
    ) -> None:
        """Publish a user created event."""
        event = UserCreatedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(user_id),
            user_id=user_id,
            clerk_id=clerk_id,
            email=email,
            name=name,
            role=role
        )
        await self.publish(event)
    
    async def publish_post_created(
        self,
        post_id: int,
        author_id: int,
        category_id: int,
        title: str,
        is_pinned: bool = False,
        is_private: bool = False
    ) -> None:
        """Publish a post created event."""
        event = PostCreatedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(post_id),
            post_id=post_id,
            author_id=author_id,
            category_id=category_id,
            title=title,
            is_pinned=is_pinned,
            is_private=is_private
        )
        await self.publish(event)
    
    async def publish_comment_added(
        self,
        comment_id: int,
        post_id: int,
        author_id: int,
        parent_id: Optional[int] = None,
        is_private: bool = False
    ) -> None:
        """Publish a comment added event."""
        event = CommentAddedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(comment_id),
            comment_id=comment_id,
            post_id=post_id,
            author_id=author_id,
            parent_id=parent_id,
            is_private=is_private
        )
        await self.publish(event)


class EventStore:
    """
    Provides event storage and retrieval capabilities.
    This can be used for event sourcing or audit logging.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_events_for_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get all events for a specific aggregate."""
        from sqlalchemy import select
        
        query = select(OutboxEvent).where(
            OutboxEvent.aggregate_type == aggregate_type,
            OutboxEvent.aggregate_id == aggregate_id
        )
        
        if since:
            query = query.where(OutboxEvent.occurred_at > since)
        
        query = query.order_by(OutboxEvent.occurred_at)
        
        result = await self.session.execute(query)
        events = result.scalars().all()
        
        return [self._outbox_to_dict(event) for event in events]
    
    async def get_pending_events(self, limit: int = 100) -> List[OutboxEvent]:
        """Get pending events from the outbox."""
        from sqlalchemy import select
        
        query = select(OutboxEvent).where(
            OutboxEvent.status == "pending"
        ).order_by(
            OutboxEvent.occurred_at
        ).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def mark_event_processed(self, event_id: str) -> None:
        """Mark an event as processed."""
        from sqlalchemy import update
        
        await self.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.event_id == event_id)
            .values(
                status="processed",
                processed_at=datetime.utcnow()
            )
        )
    
    async def mark_event_failed(
        self,
        event_id: str,
        error_message: str,
        retry_count: int
    ) -> None:
        """Mark an event as failed."""
        from sqlalchemy import update
        
        await self.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.event_id == event_id)
            .values(
                status="failed" if retry_count >= 3 else "pending",
                retry_count=retry_count,
                last_error=error_message
            )
        )
    
    def _outbox_to_dict(self, event: OutboxEvent) -> Dict[str, Any]:
        """Convert outbox event to dictionary."""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "payload": event.payload,
            "occurred_at": event.occurred_at.isoformat(),
            "status": event.status,
            "processed_at": event.processed_at.isoformat() if event.processed_at else None
        }