from typing import Any, Dict, Optional, List, Type
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import uuid


class EventType(Enum):
    """Enumeration of domain event types."""
    # Translation events
    TRANSLATION_JOB_CREATED = "translation.job.created"
    TRANSLATION_JOB_STARTED = "translation.job.started"
    TRANSLATION_JOB_COMPLETED = "translation.job.completed"
    TRANSLATION_JOB_FAILED = "translation.job.failed"
    
    # Validation events
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    VALIDATION_FAILED = "validation.failed"
    
    # Post-edit events
    POST_EDIT_STARTED = "post_edit.started"
    POST_EDIT_COMPLETED = "post_edit.completed"
    POST_EDIT_FAILED = "post_edit.failed"
    
    # Illustration events
    ILLUSTRATION_GENERATION_STARTED = "illustration.generation.started"
    ILLUSTRATION_GENERATION_COMPLETED = "illustration.generation.completed"
    ILLUSTRATION_GENERATION_FAILED = "illustration.generation.failed"
    
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_ROLE_CHANGED = "user.role_changed"
    
    # Community events
    POST_CREATED = "post.created"
    POST_UPDATED = "post.updated"
    POST_DELETED = "post.deleted"
    COMMENT_CREATED = "comment.created"
    COMMENT_DELETED = "comment.deleted"
    
    # Announcement events
    ANNOUNCEMENT_CREATED = "announcement.created"
    ANNOUNCEMENT_UPDATED = "announcement.updated"
    ANNOUNCEMENT_DEACTIVATED = "announcement.deactivated"


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = None
    aggregate_id: int = None
    aggregate_type: str = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if self.event_type else None,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "payload": self.payload,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary."""
        event_type = data.get("event_type")
        if event_type:
            event_type = EventType(event_type)
        
        return cls(
            event_id=data.get("event_id"),
            event_type=event_type,
            aggregate_id=data.get("aggregate_id"),
            aggregate_type=data.get("aggregate_type"),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at"))
        )


# Specific event classes for type safety

@dataclass
class TranslationJobCreatedEvent(DomainEvent):
    """Event raised when a translation job is created."""
    
    def __init__(self, job_id: int, user_id: int, filename: str, **kwargs):
        super().__init__(
            event_type=EventType.TRANSLATION_JOB_CREATED,
            aggregate_id=job_id,
            aggregate_type="TranslationJob",
            payload={
                "job_id": job_id,
                "user_id": user_id,
                "filename": filename,
                **kwargs
            }
        )


@dataclass
class TranslationJobCompletedEvent(DomainEvent):
    """Event raised when a translation job is completed."""
    
    def __init__(self, job_id: int, duration_seconds: int, **kwargs):
        super().__init__(
            event_type=EventType.TRANSLATION_JOB_COMPLETED,
            aggregate_id=job_id,
            aggregate_type="TranslationJob",
            payload={
                "job_id": job_id,
                "duration_seconds": duration_seconds,
                **kwargs
            }
        )


@dataclass
class TranslationJobFailedEvent(DomainEvent):
    """Event raised when a translation job fails."""
    
    def __init__(self, job_id: int, error_message: str, **kwargs):
        super().__init__(
            event_type=EventType.TRANSLATION_JOB_FAILED,
            aggregate_id=job_id,
            aggregate_type="TranslationJob",
            payload={
                "job_id": job_id,
                "error_message": error_message,
                **kwargs
            }
        )


@dataclass
class UserCreatedEvent(DomainEvent):
    """Event raised when a new user is created."""
    
    def __init__(self, user_id: int, clerk_user_id: str, email: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=EventType.USER_CREATED,
            aggregate_id=user_id,
            aggregate_type="User",
            payload={
                "user_id": user_id,
                "clerk_user_id": clerk_user_id,
                "email": email,
                **kwargs
            }
        )


@dataclass
class UserRoleChangedEvent(DomainEvent):
    """Event raised when a user's role is changed."""
    
    def __init__(self, user_id: int, old_role: str, new_role: str, **kwargs):
        super().__init__(
            event_type=EventType.USER_ROLE_CHANGED,
            aggregate_id=user_id,
            aggregate_type="User",
            payload={
                "user_id": user_id,
                "old_role": old_role,
                "new_role": new_role,
                **kwargs
            }
        )


@dataclass
class PostCreatedEvent(DomainEvent):
    """Event raised when a new post is created."""
    
    def __init__(self, post_id: int, author_id: int, category_id: int, title: str, **kwargs):
        super().__init__(
            event_type=EventType.POST_CREATED,
            aggregate_id=post_id,
            aggregate_type="Post",
            payload={
                "post_id": post_id,
                "author_id": author_id,
                "category_id": category_id,
                "title": title,
                **kwargs
            }
        )


@dataclass
class CommentCreatedEvent(DomainEvent):
    """Event raised when a new comment is created."""
    
    def __init__(self, comment_id: int, post_id: int, author_id: int, parent_id: Optional[int] = None, **kwargs):
        super().__init__(
            event_type=EventType.COMMENT_CREATED,
            aggregate_id=comment_id,
            aggregate_type="Comment",
            payload={
                "comment_id": comment_id,
                "post_id": post_id,
                "author_id": author_id,
                "parent_id": parent_id,
                **kwargs
            }
        )


class EventHandler:
    """Base class for event handlers."""
    
    def handle(self, event: DomainEvent) -> None:
        """Handle the event."""
        raise NotImplementedError


class EventDispatcher:
    """Dispatches domain events to registered handlers."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
    
    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def dispatch(self, event: DomainEvent) -> None:
        """Dispatch an event to all registered handlers."""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as e:
                # Log error but don't stop dispatching to other handlers
                print(f"Error dispatching event {event.event_id} to handler: {e}")
    
    def dispatch_batch(self, events: List[DomainEvent]) -> None:
        """Dispatch multiple events."""
        for event in events:
            self.dispatch(event)


class EventStore:
    """Interface for storing and retrieving domain events."""
    
    def append(self, event: DomainEvent) -> None:
        """Append an event to the store."""
        raise NotImplementedError
    
    def get_events(
        self, 
        aggregate_id: Optional[int] = None,
        aggregate_type: Optional[str] = None,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Retrieve events from the store."""
        raise NotImplementedError


class InMemoryEventStore(EventStore):
    """In-memory implementation of event store for testing."""
    
    def __init__(self):
        self._events: List[DomainEvent] = []
    
    def append(self, event: DomainEvent) -> None:
        """Append an event to the store."""
        self._events.append(event)
    
    def get_events(
        self, 
        aggregate_id: Optional[int] = None,
        aggregate_type: Optional[str] = None,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Retrieve events from the store."""
        events = self._events
        
        if aggregate_id is not None:
            events = [e for e in events if e.aggregate_id == aggregate_id]
        
        if aggregate_type is not None:
            events = [e for e in events if e.aggregate_type == aggregate_type]
        
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        
        if since is not None:
            events = [e for e in events if e.created_at >= since]
        
        return events[:limit]