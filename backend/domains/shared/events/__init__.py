"""
Domain Events module for cross-domain communication.
"""

from .contracts import (
    EventType,
    DomainEvent,
    TranslationStartedEvent,
    TranslationCompletedEvent,
    TranslationFailedEvent,
    ValidationCompletedEvent,
    PostEditCompletedEvent,
    UserCreatedEvent,
    UserUpdatedEvent,
    UserDeletedEvent,
    UserRoleChangedEvent,
    PostCreatedEvent,
    PostUpdatedEvent,
    PostDeletedEvent,
    CommentAddedEvent,
    CommentDeletedEvent,
    AnnouncementCreatedEvent,
    EventFactory,
    EventHandler,
)

from .publisher import (
    EventPublisher,
    EventStore,
)

__all__ = [
    # Event types and base
    "EventType",
    "DomainEvent",
    
    # Translation events
    "TranslationStartedEvent",
    "TranslationCompletedEvent",
    "TranslationFailedEvent",
    "ValidationCompletedEvent",
    "PostEditCompletedEvent",
    
    # User events
    "UserCreatedEvent",
    "UserUpdatedEvent",
    "UserDeletedEvent",
    "UserRoleChangedEvent",
    
    # Community events
    "PostCreatedEvent",
    "PostUpdatedEvent",
    "PostDeletedEvent",
    "CommentAddedEvent",
    "CommentDeletedEvent",
    "AnnouncementCreatedEvent",
    
    # Utilities
    "EventFactory",
    "EventHandler",
    "EventPublisher",
    "EventStore",
]