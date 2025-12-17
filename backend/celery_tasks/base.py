"""
Base task class for Celery tasks with common functionality.
"""
import logging
import uuid
import hashlib
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional, Sequence

from celery import Task
from celery.signals import task_prerun, task_postrun, task_failure

from ..config.database import SessionLocal
from ..domains.tasks.models import TaskExecution, TaskStatus, TaskKind
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

_db_session_ctx: ContextVar[Optional[Any]] = ContextVar("celery_db_session", default=None)

_SENSITIVE_KEYS = {
    # User-provided secrets
    "api_key",
    "backup_api_keys",
    "provider_config",
    # Vertex credential payloads
    "credentials",
    "private_key",
    "service_account",
}


def _stable_secret_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:12]


def _redact_task_payload(value: Any) -> Any:
    """Redact secrets before persisting task args/kwargs to the DB.

    Celery task invocation still receives the original args/kwargs; this is for
    TaskExecution tracking only.
    """
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for k, v in value.items():
            if k in _SENSITIVE_KEYS:
                if k == "api_key" and isinstance(v, str) and v:
                    redacted[k] = {"redacted": True, "key_id": _stable_secret_id(v)}
                    continue
                if k == "backup_api_keys" and isinstance(v, list):
                    key_ids = []
                    for item in v:
                        if isinstance(item, str) and item:
                            key_ids.append(_stable_secret_id(item))
                    redacted[k] = {"redacted": True, "key_ids": key_ids}
                    continue
                if k == "credentials" and isinstance(v, dict):
                    safe = {}
                    for safe_key in ("project_id", "client_email", "type"):
                        if safe_key in v and isinstance(v.get(safe_key), str):
                            safe[safe_key] = v[safe_key]
                    safe["redacted"] = True
                    redacted[k] = safe
                    continue
                redacted[k] = {"redacted": True}
                continue

            redacted[k] = _redact_task_payload(v)
        return redacted
    if isinstance(value, list):
        return [_redact_task_payload(v) for v in value]
    return value


def _extract_job_id(
    task_execution: Optional[TaskExecution],
    args: Optional[Sequence[Any]],
    kwargs: Optional[Dict[str, Any]]
) -> Optional[int]:
    """Derive job_id from task execution context and invocation arguments."""

    if task_execution and getattr(task_execution, "job_id", None):
        return task_execution.job_id

    if kwargs:
        job_id = kwargs.get("job_id")
        if isinstance(job_id, int):
            return job_id

    if args:
        first_arg = args[0]
        if isinstance(first_arg, int):
            return first_arg

    return None


class DatabaseTask(Task):
    """Base task with database session management and tracking."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    @property
    def db_session(self):
        """Get database session scoped to the current task execution context."""
        session = _db_session_ctx.get()
        if session is None:
            session = SessionLocal()
            _db_session_ctx.set(session)
        return session
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up database session after task execution."""
        session = _db_session_ctx.get()
        if session is not None:
            session.close()
            _db_session_ctx.set(None)
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
                args=_redact_task_payload(list(args) if args else []),
                kwargs=_redact_task_payload(dict(kwargs) if kwargs else {}),
                start_time=datetime.utcnow(),
                queue_time=datetime.utcnow(),  # Approximation
                attempts=1
            )
            
            extracted_job_id = _extract_job_id(None, args, kwargs)
            if extracted_job_id is not None:
                task_execution.job_id = extracted_job_id
            
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
    """Handle task completion - update task execution record and persist to S3."""
    if not isinstance(task, TrackedTask):
        return

    db_session = None
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

            # Persist task outputs to S3 if configured and task succeeded
            if state == 'SUCCESS':
                try:
                    from backend.services.aws_task_output_service import get_task_output_service

                    job_id = _extract_job_id(task_execution, args, kwargs)

                    if job_id is not None:
                        service = get_task_output_service()
                        if service.enabled:
                            # Run S3 persistence in background to not block task completion
                            persist_result = service.persist_job_outputs(
                                job_id=job_id,
                                task_id=task_id,
                                task_name=task.name
                            )

                            if persist_result.get('success'):
                                logger.info(
                                    f"Persisted outputs to S3 for job {job_id}: "
                                    f"{persist_result.get('uploaded_count', 0)} files, "
                                    f"{persist_result.get('total_size', 0):,} bytes"
                                )
                            elif persist_result.get('reason') != 'S3 persistence not enabled or configured':
                                logger.warning(f"Failed to persist outputs to S3: {persist_result}")

                except Exception as e:
                    # Don't let S3 persistence failures affect task completion
                    logger.error(f"Error during S3 persistence for task {task_id}: {e}")

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
            args=_redact_task_payload(args or []),
            kwargs=_redact_task_payload(kwargs or {}),
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
