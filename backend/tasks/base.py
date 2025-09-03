"""
Base task class for Celery tasks with common functionality.
"""
from celery import Task
from celery.signals import task_prerun, task_postrun, task_failure
from datetime import datetime
from typing import Any, Dict, Optional
import logging
import uuid

from ..database import SessionLocal
from ..models import TaskExecution, TaskStatus, TaskKind
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management and tracking."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def __init__(self):
        """Initialize task."""
        super().__init__()
        self._db_session = None
    
    @property
    def db_session(self):
        """Get database session."""
        if self._db_session is None:
            self._db_session = SessionLocal()
        return self._db_session
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up database session after task execution."""
        if self._db_session:
            self._db_session.close()
            self._db_session = None
        super().after_return(status, retval, task_id, args, kwargs, einfo)


class TrackedTask(DatabaseTask):
    """Task that tracks execution in the database."""
    
    task_kind = TaskKind.OTHER
    
    def apply_async(self, args=None, kwargs=None, task_id=None, **options):
        """Override to generate task_id if not provided."""
        if task_id is None:
            task_id = str(uuid.uuid4())
        return super().apply_async(args=args, kwargs=kwargs, task_id=task_id, **options)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """Handle task start - update task execution record."""
    if not isinstance(task, TrackedTask):
        return
    
    try:
        db_session = SessionLocal()
        
        # Try to get existing task execution or create new one
        task_execution = db_session.query(TaskExecution).filter_by(id=task_id).first()
        
        if not task_execution:
            # Create new task execution record
            task_execution = TaskExecution(
                id=task_id,
                name=task.name,
                kind=task.task_kind,
                status=TaskStatus.STARTED,
                args=list(args) if args else [],
                kwargs=dict(kwargs) if kwargs else {},
                start_time=datetime.utcnow(),
                queue_time=datetime.utcnow(),  # Approximation
                attempts=1
            )
            
            # Extract job_id if present in kwargs
            if 'job_id' in kwargs:
                task_execution.job_id = kwargs['job_id']
            elif args and isinstance(args[0], int):
                # Assume first arg is job_id for backward compatibility
                task_execution.job_id = args[0]
            
            # Extract user_id if present
            if 'user_id' in kwargs:
                task_execution.user_id = kwargs['user_id']
            
            db_session.add(task_execution)
        else:
            # Update existing record
            task_execution.status = TaskStatus.STARTED
            task_execution.start_time = datetime.utcnow()
            task_execution.attempts = (task_execution.attempts or 0) + 1
        
        db_session.commit()
        logger.info(f"Task {task_id} ({task.name}) started")
        
    except Exception as e:
        logger.error(f"Failed to update task prerun status: {e}")
    finally:
        if db_session:
            db_session.close()


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw):
    """Handle task completion - update task execution record."""
    if not isinstance(task, TrackedTask):
        return
    
    try:
        db_session = SessionLocal()
        
        task_execution = db_session.query(TaskExecution).filter_by(id=task_id).first()
        
        if task_execution:
            if state == 'SUCCESS':
                task_execution.status = TaskStatus.SUCCESS
            elif state == 'RETRY':
                task_execution.status = TaskStatus.RETRY
            elif state == 'FAILURE':
                task_execution.status = TaskStatus.FAILURE
            else:
                task_execution.status = TaskStatus.SUCCESS  # Default to success
            
            task_execution.end_time = datetime.utcnow()
            
            # Store result if it's serializable
            if retval and isinstance(retval, (dict, list, str, int, float, bool)):
                task_execution.result = retval
            
            db_session.commit()
            logger.info(f"Task {task_id} ({task.name}) completed with state {state}")
        
    except Exception as e:
        logger.error(f"Failed to update task postrun status: {e}")
    finally:
        if db_session:
            db_session.close()


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    """Handle task failure - update task execution record."""
    if not isinstance(sender, TrackedTask):
        return
    
    try:
        db_session = SessionLocal()
        
        task_execution = db_session.query(TaskExecution).filter_by(id=task_id).first()
        
        if task_execution:
            task_execution.status = TaskStatus.FAILURE
            task_execution.end_time = datetime.utcnow()
            task_execution.last_error = str(exception) if exception else "Unknown error"
            
            db_session.commit()
            logger.error(f"Task {task_id} ({sender.name}) failed: {exception}")
        
    except Exception as e:
        logger.error(f"Failed to update task failure status: {e}")
    finally:
        if db_session:
            db_session.close()


def create_task_execution(
    task_id: str,
    task_name: str,
    task_kind: TaskKind,
    job_id: Optional[int] = None,
    user_id: Optional[int] = None,
    args: Optional[list] = None,
    kwargs: Optional[dict] = None
) -> Optional[TaskExecution]:
    """
    Create a task execution record before launching a task.
    This is useful when you want to track a task before it's actually started.
    """
    db_session = SessionLocal()
    try:
        task_execution = TaskExecution(
            id=task_id,
            name=task_name,
            kind=task_kind,
            status=TaskStatus.PENDING,
            job_id=job_id,
            user_id=user_id,
            args=args or [],
            kwargs=kwargs or {},
            queue_time=datetime.utcnow()
        )
        
        db_session.add(task_execution)
        db_session.commit()
        db_session.refresh(task_execution)
        
        logger.info(f"Created task execution record for {task_id} ({task_name})")
        return task_execution
        
    except IntegrityError:
        # Task already exists
        db_session.rollback()
        return db_session.query(TaskExecution).filter_by(id=task_id).first()
    except Exception as e:
        logger.error(f"Failed to create task execution record: {e}")
        db_session.rollback()
        return None
    finally:
        db_session.close()