"""
Task execution schemas for Celery task tracking.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    STARTED = "started"
    RETRY = "retry"
    SUCCESS = "success"
    FAILURE = "failure"
    REVOKED = "revoked"


class TaskKind(str, Enum):
    """Types of background tasks."""
    TRANSLATION = "translation"
    VALIDATION = "validation"
    POST_EDIT = "post_edit"
    ILLUSTRATION = "illustration"
    EVENT_PROCESSING = "event_processing"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class TaskExecutionResponse(BaseModel):
    """Response model for task execution status."""
    id: str
    kind: TaskKind
    name: str
    status: TaskStatus
    job_id: Optional[int] = None
    
    # Progress info
    progress: Optional[int] = None
    message: Optional[str] = None
    
    # Retry info
    attempts: int
    max_retries: int
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    
    # Performance metrics
    queue_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    queue_duration: Optional[float] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # User tracking
    user_id: Optional[int] = None
    
    # Celery state (if available)
    celery_state: Optional[str] = None
    celery_info: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class TaskExecutionListResponse(BaseModel):
    """Response for list of task executions."""
    tasks: List[TaskExecutionResponse]
    total: int
    page: int
    page_size: int
    
    
class TaskStatsResponse(BaseModel):
    """Statistics about task execution."""
    total_tasks: int
    by_status: Dict[str, int]
    by_kind: Dict[str, int]
    avg_duration: float
    avg_queue_time: float
    success_rate: float
    failure_rate: float
    recent_failures: List[TaskExecutionResponse]