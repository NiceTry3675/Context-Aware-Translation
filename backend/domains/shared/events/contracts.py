"""
Domain Event Contracts for Cross-Domain Communication

These contracts define the structure of events that can be emitted by domains
to communicate state changes without direct coupling.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Enumeration of all domain event types."""
    
    # Translation Events
    TRANSLATION_STARTED = "translation.started"
    TRANSLATION_COMPLETED = "translation.completed"
    TRANSLATION_FAILED = "translation.failed"
    VALIDATION_COMPLETED = "validation.completed"
    POST_EDIT_COMPLETED = "post_edit.completed"
    
    # User Events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role_changed"
    
    # Community Events
    POST_CREATED = "post.created"
    POST_UPDATED = "post.updated"
    POST_DELETED = "post.deleted"
    COMMENT_ADDED = "comment.added"
    COMMENT_DELETED = "comment.deleted"
    ANNOUNCEMENT_CREATED = "announcement.created"


class DomainEvent(BaseModel):
    """Base class for all domain events."""
    
    event_id: str = Field(description="Unique identifier for this event instance")
    event_type: EventType = Field(description="Type of the event")
    aggregate_id: str = Field(description="ID of the aggregate that emitted this event")
    aggregate_type: str = Field(description="Type of the aggregate (e.g., 'TranslationJob', 'User')")
    occurred_at: datetime = Field(default_factory=datetime.utcnow, description="When the event occurred")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Translation Domain Events

class TranslationStartedEvent(DomainEvent):
    """Emitted when a translation job starts processing."""
    
    event_type: EventType = EventType.TRANSLATION_STARTED
    aggregate_type: str = "TranslationJob"
    
    job_id: int
    user_id: Optional[int] = None
    filename: str
    segment_size: int
    validation_enabled: bool = False
    post_edit_enabled: bool = False


class TranslationCompletedEvent(DomainEvent):
    """Emitted when a translation job completes successfully."""
    
    event_type: EventType = EventType.TRANSLATION_COMPLETED
    aggregate_type: str = "TranslationJob"
    
    job_id: int
    user_id: Optional[int] = None
    filename: str
    duration_seconds: int
    output_path: str
    segment_count: int
    total_characters: int


class TranslationFailedEvent(DomainEvent):
    """Emitted when a translation job fails."""
    
    event_type: EventType = EventType.TRANSLATION_FAILED
    aggregate_type: str = "TranslationJob"
    
    job_id: int
    user_id: Optional[int] = None
    error_message: str
    error_type: str
    failed_at_segment: Optional[int] = None


class ValidationCompletedEvent(DomainEvent):
    """Emitted when validation completes for a translation job."""
    
    event_type: EventType = EventType.VALIDATION_COMPLETED
    aggregate_type: str = "TranslationJob"
    
    job_id: int
    user_id: Optional[int] = None
    total_issues: int
    critical_issues: int
    report_path: str
    validation_score: Optional[float] = None


class PostEditCompletedEvent(DomainEvent):
    """Emitted when post-editing completes for a translation job."""
    
    event_type: EventType = EventType.POST_EDIT_COMPLETED
    aggregate_type: str = "TranslationJob"
    
    job_id: int
    user_id: Optional[int] = None
    corrections_applied: int
    output_path: str
    log_path: str


# User Domain Events

class UserCreatedEvent(DomainEvent):
    """Emitted when a new user is created."""
    
    event_type: EventType = EventType.USER_CREATED
    aggregate_type: str = "User"
    
    user_id: int
    clerk_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str = "user"


class UserUpdatedEvent(DomainEvent):
    """Emitted when user information is updated."""
    
    event_type: EventType = EventType.USER_UPDATED
    aggregate_type: str = "User"
    
    user_id: int
    updated_fields: List[str]
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]


class UserDeletedEvent(DomainEvent):
    """Emitted when a user is deleted."""
    
    event_type: EventType = EventType.USER_DELETED
    aggregate_type: str = "User"
    
    user_id: int
    clerk_id: str
    deleted_by: Optional[int] = None


class UserRoleChangedEvent(DomainEvent):
    """Emitted when a user's role changes."""
    
    event_type: EventType = EventType.USER_ROLE_CHANGED
    aggregate_type: str = "User"
    
    user_id: int
    old_role: str
    new_role: str
    changed_by: Optional[int] = None


# Community Domain Events

class PostCreatedEvent(DomainEvent):
    """Emitted when a new post is created."""
    
    event_type: EventType = EventType.POST_CREATED
    aggregate_type: str = "Post"
    
    post_id: int
    author_id: int
    category_id: int
    title: str
    is_pinned: bool = False
    is_private: bool = False


class PostUpdatedEvent(DomainEvent):
    """Emitted when a post is updated."""
    
    event_type: EventType = EventType.POST_UPDATED
    aggregate_type: str = "Post"
    
    post_id: int
    author_id: int
    updated_fields: List[str]
    updated_by: int


class PostDeletedEvent(DomainEvent):
    """Emitted when a post is deleted."""
    
    event_type: EventType = EventType.POST_DELETED
    aggregate_type: str = "Post"
    
    post_id: int
    author_id: int
    deleted_by: int
    reason: Optional[str] = None


class CommentAddedEvent(DomainEvent):
    """Emitted when a comment is added to a post."""
    
    event_type: EventType = EventType.COMMENT_ADDED
    aggregate_type: str = "Comment"
    
    comment_id: int
    post_id: int
    author_id: int
    parent_id: Optional[int] = None
    is_private: bool = False


class CommentDeletedEvent(DomainEvent):
    """Emitted when a comment is deleted."""
    
    event_type: EventType = EventType.COMMENT_DELETED
    aggregate_type: str = "Comment"
    
    comment_id: int
    post_id: int
    author_id: int
    deleted_by: int


class AnnouncementCreatedEvent(DomainEvent):
    """Emitted when an announcement is created."""
    
    event_type: EventType = EventType.ANNOUNCEMENT_CREATED
    aggregate_type: str = "Announcement"
    
    announcement_id: int
    message: str
    created_by: Optional[int] = None
    is_active: bool = True


# Event Factory

class EventFactory:
    """Factory for creating domain events with proper validation."""
    
    @staticmethod
    def create_event(event_type: EventType, **kwargs) -> DomainEvent:
        """Create a domain event based on its type."""
        
        event_map = {
            EventType.TRANSLATION_STARTED: TranslationStartedEvent,
            EventType.TRANSLATION_COMPLETED: TranslationCompletedEvent,
            EventType.TRANSLATION_FAILED: TranslationFailedEvent,
            EventType.VALIDATION_COMPLETED: ValidationCompletedEvent,
            EventType.POST_EDIT_COMPLETED: PostEditCompletedEvent,
            EventType.USER_CREATED: UserCreatedEvent,
            EventType.USER_UPDATED: UserUpdatedEvent,
            EventType.USER_DELETED: UserDeletedEvent,
            EventType.USER_ROLE_CHANGED: UserRoleChangedEvent,
            EventType.POST_CREATED: PostCreatedEvent,
            EventType.POST_UPDATED: PostUpdatedEvent,
            EventType.POST_DELETED: PostDeletedEvent,
            EventType.COMMENT_ADDED: CommentAddedEvent,
            EventType.COMMENT_DELETED: CommentDeletedEvent,
            EventType.ANNOUNCEMENT_CREATED: AnnouncementCreatedEvent,
        }
        
        event_class = event_map.get(event_type)
        if not event_class:
            raise ValueError(f"Unknown event type: {event_type}")
        
        return event_class(**kwargs)


# Event Handler Interface

class EventHandler:
    """Interface for handling domain events."""
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""
        raise NotImplementedError("Event handlers must implement the handle method")