"""
Task execution tracking model for Celery tasks.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from ..shared.db_base import Base


class TaskStatus(str, enum.Enum):
    """Task execution status."""
    PENDING = "pending"
    STARTED = "started"
    RETRY = "retry"
    SUCCESS = "success"
    FAILURE = "failure"
    REVOKED = "revoked"
    RUNNING = "running"


class TaskKind(str, enum.Enum):
    """Types of background tasks."""
    TRANSLATION = "translation"
    VALIDATION = "validation"
    POST_EDIT = "post_edit"
    ILLUSTRATION = "illustration"
    EVENT_PROCESSING = "event_processing"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class TaskExecution(Base):
    """
    Track execution of Celery tasks.
    """
    __tablename__ = "task_executions"
    
    # Primary key is the Celery task ID
    id = Column(String, primary_key=True)
    
    # Task metadata
    kind = Column(SQLEnum(TaskKind), nullable=False, default=TaskKind.OTHER)
    name = Column(String, nullable=False)  # Full task name
    
    # Related job (if applicable)
    job_id = Column(Integer, ForeignKey("translation_jobs.id", ondelete="CASCADE"), nullable=True)
    job = relationship("TranslationJob", backref="task_executions")
    
    # Task status
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    
    # Task arguments and results
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    
    # Retry tracking
    attempts = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Performance metrics
    queue_time = Column(DateTime, nullable=True)  # When task was queued
    start_time = Column(DateTime, nullable=True)  # When task started
    end_time = Column(DateTime, nullable=True)    # When task completed
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # User tracking
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", backref="task_executions")
    
    # Additional metadata
    extra_data = Column(JSON, nullable=True)
    
    @property
    def duration(self) -> float:
        """Calculate task duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def queue_duration(self) -> float:
        """Calculate time spent in queue."""
        if self.queue_time and self.start_time:
            return (self.start_time - self.queue_time).total_seconds()
        return 0.0
    
    def __repr__(self):
        return f"<TaskExecution(id='{self.id}', kind={self.kind}, status={self.status})>"