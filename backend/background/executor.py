"""Background task enqueueing for local execution and Cloud Run Jobs."""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.domains.tasks.models import TaskExecution, TaskKind, TaskStatus

from .cloud_run import CloudRunJobClient
from .redaction import redact_background_payload

logger = logging.getLogger(__name__)

PAYLOAD_ENV = "BACKGROUND_TASK_PAYLOAD"


def enqueue_background_task(
    db: Session,
    *,
    task_name: str,
    task_kind: TaskKind,
    kwargs: dict[str, Any],
    job_id: Optional[int] = None,
    user_id: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Create a TaskExecution row and launch the configured executor."""

    task_id = task_id or str(uuid.uuid4())
    payload = {
        "task_id": task_id,
        "task_name": task_name,
        "task_kind": task_kind.value if isinstance(task_kind, TaskKind) else str(task_kind),
        "job_id": job_id,
        "user_id": user_id,
        "kwargs": kwargs,
    }

    task_execution = TaskExecution(
        id=task_id,
        name=task_name,
        kind=task_kind,
        status=TaskStatus.PENDING,
        job_id=job_id,
        user_id=user_id,
        args=[],
        kwargs=redact_background_payload(kwargs),
        max_retries=0,
        queue_time=datetime.utcnow(),
        extra_data={"executor": _executor_name()},
    )

    try:
        db.add(task_execution)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("TaskExecution %s already exists; reusing it", task_id)
    except Exception:
        db.rollback()
        raise

    try:
        _launch_payload(payload)
    except Exception as exc:
        _mark_launch_failed(db, task_id, exc)
        raise

    return task_id


def _launch_payload(payload: dict[str, Any]) -> None:
    executor = _executor_name()
    if executor == "cloud_run":
        _launch_cloud_run(payload)
    elif executor == "sync":
        from .job_runner import run_payload

        run_payload(payload)
    elif executor == "inline_thread":
        from .job_runner import run_payload

        thread = threading.Thread(
            target=run_payload,
            args=(payload,),
            name=f"background-task-{payload['task_id']}",
            daemon=True,
        )
        thread.start()
    else:
        raise ValueError(
            "Unsupported BACKGROUND_EXECUTOR "
            f"{executor!r}; expected cloud_run, inline_thread, or sync"
        )


def _launch_cloud_run(payload: dict[str, Any]) -> None:
    settings = get_settings()
    project_id = (
        settings.google_cloud_project
        or os.getenv("GCP_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    region = (
        settings.google_cloud_location
        or os.getenv("GCP_REGION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
    )
    client = CloudRunJobClient(
        project_id=project_id or "",
        region=region or "",
        job_name=settings.cloud_run_background_job or "",
    )
    payload_json = json.dumps(payload, separators=(",", ":"), default=str)
    execution = client.run_with_env(
        {
            PAYLOAD_ENV: payload_json,
            "TASK_EXECUTION_ID": payload["task_id"],
            "BACKGROUND_TASK_NAME": payload["task_name"],
            "BACKGROUND_TASK_KIND": payload["task_kind"],
        },
        timeout=settings.cloud_run_job_timeout,
    )

    from backend.config.database import SessionLocal

    db = SessionLocal()
    try:
        task = db.query(TaskExecution).filter_by(id=payload["task_id"]).first()
        if task:
            extra = dict(task.extra_data or {})
            extra.update(
                {
                    "executor": "cloud_run",
                    "cloud_run_operation": execution.operation_name,
                    "cloud_run_execution": execution.execution_name,
                }
            )
            task.extra_data = extra
            db.commit()
    finally:
        db.close()


def _mark_launch_failed(db: Session, task_id: str, exc: Exception) -> None:
    task = db.query(TaskExecution).filter_by(id=task_id).first()
    if not task:
        return
    task.status = TaskStatus.FAILURE
    task.end_time = datetime.utcnow()
    task.last_error = f"Failed to launch background task: {exc}"
    extra = dict(task.extra_data or {})
    extra["launch_error"] = str(exc)
    task.extra_data = extra
    db.commit()


def _executor_name() -> str:
    return os.getenv("BACKGROUND_EXECUTOR") or get_settings().background_executor
