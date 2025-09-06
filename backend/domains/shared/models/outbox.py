from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from .base import Base


class OutboxEvent(Base):
    """
    Outbox pattern implementation for reliable event publishing.
    
    This table stores domain events that need to be processed asynchronously.
    Events are written to this table as part of the same database transaction
    that modifies the domain entities, ensuring consistency.
    """
    __tablename__ = "outbox_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    aggregate_id = Column(String, nullable=False, index=True)  # Changed to String for flexibility
    aggregate_type = Column(String, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    event_metadata = Column(JSON, nullable=True)  # Renamed from metadata
    status = Column(String, default="pending", index=True)  # pending, processed, failed
    processed = Column(Boolean, default=False, index=True)  # Kept for backward compatibility
    processed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)  # Store error messages
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=func.now())  # When event actually occurred
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<OutboxEvent(id={self.id}, event_type={self.event_type}, processed={self.processed})>"