"""Cloud Run Job entrypoint for background tasks."""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from backend.config.database import SessionLocal
from backend.domains.tasks.models import TaskExecution, TaskKind, TaskStatus

from .executor import PAYLOAD_ENV
from .redaction import redact_background_payload
from .tasks import (
    CLEANUP_TEMP_FILES_TASK,
    GENERATE_ILLUSTRATIONS_TASK,
    PROCESS_OUTBOX_EVENTS_TASK,
    PROCESS_POST_EDIT_TASK,
    PROCESS_TRANSLATION_TASK,
    PROCESS_VALIDATION_TASK,
    REGENERATE_BASE_TASK,
    REGENERATE_ILLUSTRATION_TASK,
    RUN_MAINTENANCE_TASK,
    WATCHDOG_STALLED_JOBS_TASK,
)

logger = logging.getLogger(__name__)
_RUN_LOCK = threading.RLock()


@dataclass(frozen=True)
class TaskSpec:
    name: str
    kind: TaskKind
    task: Any = None
    runner: Optional[Callable[..., Any]] = None
    module: Any = None


class _ProgressProxy:
    def __init__(self, task_id: str):
        self.task_id = task_id

    def update_state(self, state: str | None = None, meta: dict[str, Any] | None = None, **_: Any) -> None:
        db = SessionLocal()
        try:
            task = db.query(TaskExecution).filter_by(id=self.task_id).first()
            if not task:
                return
            extra = dict(task.extra_data or {})
            progress = dict(meta or {})
            if state:
                progress["state"] = state
            extra["progress"] = progress
            task.extra_data = extra
            if task.status in {TaskStatus.PENDING, TaskStatus.STARTED}:
                task.status = TaskStatus.RUNNING
            db.commit()
        finally:
            db.close()


class _EagerTaskResult:
    def __init__(self, task_id: str):
        self.id = task_id


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    payload = payload_from_env()
    run_payload(payload)


def payload_from_env() -> dict[str, Any]:
    raw_payload = os.getenv(PAYLOAD_ENV)
    if raw_payload:
        payload = json.loads(raw_payload)
    else:
        payload = {
            "task_id": os.getenv("TASK_EXECUTION_ID") or str(uuid.uuid4()),
            "task_name": os.getenv("BACKGROUND_TASK_NAME") or RUN_MAINTENANCE_TASK,
            "task_kind": os.getenv("BACKGROUND_TASK_KIND") or TaskKind.MAINTENANCE.value,
            "job_id": _parse_int_env("BACKGROUND_JOB_ID"),
            "user_id": _parse_int_env("BACKGROUND_USER_ID"),
            "kwargs": _json_env("BACKGROUND_TASK_KWARGS", {}),
        }

    payload.setdefault("task_id", str(uuid.uuid4()))
    payload.setdefault("task_name", RUN_MAINTENANCE_TASK)
    payload.setdefault("task_kind", TaskKind.MAINTENANCE.value)
    payload.setdefault("kwargs", {})
    return payload


def run_payload(payload: dict[str, Any]) -> Any:
    task_name = payload["task_name"]
    task_id = payload["task_id"]
    kwargs = dict(payload.get("kwargs") or {})
    args = list(payload.get("args") or [])
    kind = _task_kind(payload.get("task_kind"), task_name)
    job_id = payload.get("job_id") or kwargs.get("job_id")
    user_id = payload.get("user_id") or kwargs.get("user_id")

    _ensure_task_execution(
        task_id=task_id,
        task_name=task_name,
        task_kind=kind,
        job_id=job_id,
        user_id=user_id,
        args=args,
        kwargs=kwargs,
    )
    return _execute_task(task_name, task_id, args, kwargs)


def _execute_task(
    task_name: str,
    task_id: str,
    args: list[Any],
    kwargs: dict[str, Any],
) -> Any:
    spec = _task_registry()[task_name]
    _mark_started(task_id)
    with _RUN_LOCK:
        with _patched_celery_context(task_id):
            try:
                logger.info("Running background task %s (%s)", task_name, task_id)
                if spec.runner:
                    result = spec.runner(*args, **kwargs)
                else:
                    result = _run_celery_task_object(spec.task, args, kwargs)
                _mark_success(task_id, result)
                return result
            except Exception as exc:
                _mark_failure(task_id, exc)
                raise


def _run_celery_task_object(task: Any, args: list[Any], kwargs: dict[str, Any]) -> Any:
    original_max_retries = getattr(task, "max_retries", None)
    try:
        if hasattr(task, "max_retries"):
            task.max_retries = 0
        return task.run(*args, **kwargs)
    finally:
        if original_max_retries is not None:
            task.max_retries = original_max_retries
        try:
            from backend.celery_tasks.base import _db_session_ctx

            _db_session_ctx.set(None)
        except Exception:
            logger.debug("Could not reset Celery DB session context", exc_info=True)


@contextmanager
def _patched_celery_context(task_id: str):
    registry = _task_registry()
    modules = [spec.module for spec in registry.values() if spec.module is not None]
    proxy = _ProgressProxy(task_id)
    current_task_patches = []
    method_patches = []
    try:
        for module in modules:
            if hasattr(module, "current_task"):
                current_task_patches.append((module, getattr(module, "current_task")))
                setattr(module, "current_task", proxy)

        for spec in registry.values():
            if not spec.task:
                continue
            old_delay = getattr(spec.task, "delay", None)
            old_apply_async = getattr(spec.task, "apply_async", None)
            method_patches.append((spec.task, old_delay, old_apply_async))
            setattr(spec.task, "delay", _make_delay(spec))
            setattr(spec.task, "apply_async", _make_apply_async(spec))

        yield
    finally:
        for task, old_delay, old_apply_async in reversed(method_patches):
            if old_delay is not None:
                setattr(task, "delay", old_delay)
            if old_apply_async is not None:
                setattr(task, "apply_async", old_apply_async)
        for module, old_current_task in reversed(current_task_patches):
            setattr(module, "current_task", old_current_task)


def _make_delay(spec: TaskSpec):
    def delay(*args: Any, **kwargs: Any) -> _EagerTaskResult:
        return _run_child_task(spec, list(args), kwargs, None)

    return delay


def _make_apply_async(spec: TaskSpec):
    def apply_async(
        args: list[Any] | tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        task_id: str | None = None,
        **_: Any,
    ) -> _EagerTaskResult:
        return _run_child_task(spec, list(args or []), dict(kwargs or {}), task_id)

    return apply_async


def _run_child_task(
    spec: TaskSpec,
    args: list[Any],
    kwargs: dict[str, Any],
    task_id: str | None,
) -> _EagerTaskResult:
    child_task_id = task_id or str(uuid.uuid4())
    _ensure_task_execution(
        task_id=child_task_id,
        task_name=spec.name,
        task_kind=spec.kind,
        job_id=kwargs.get("job_id"),
        user_id=kwargs.get("user_id"),
        args=args,
        kwargs=kwargs,
    )
    _execute_task(spec.name, child_task_id, args, kwargs)
    return _EagerTaskResult(child_task_id)


def _run_maintenance() -> dict[str, Any]:
    registry = _task_registry()
    results = {
        "outbox": _run_celery_task_object(registry[PROCESS_OUTBOX_EVENTS_TASK].task, [], {"batch_size": 100}),
        "cleanup_temp_files": _run_celery_task_object(registry[CLEANUP_TEMP_FILES_TASK].task, [], {}),
        "watchdog": _run_celery_task_object(registry[WATCHDOG_STALLED_JOBS_TASK].task, [], {}),
    }
    return {"status": "completed", "results": results}


def _task_registry() -> dict[str, TaskSpec]:
    from backend.celery_tasks import event_processor, illustrations, maintenance, post_edit, translation, validation

    return {
        PROCESS_TRANSLATION_TASK: TaskSpec(
            PROCESS_TRANSLATION_TASK,
            TaskKind.TRANSLATION,
            task=translation.process_translation_task,
            module=translation,
        ),
        PROCESS_VALIDATION_TASK: TaskSpec(
            PROCESS_VALIDATION_TASK,
            TaskKind.VALIDATION,
            task=validation.process_validation_task,
            module=validation,
        ),
        PROCESS_POST_EDIT_TASK: TaskSpec(
            PROCESS_POST_EDIT_TASK,
            TaskKind.POST_EDIT,
            task=post_edit.process_post_edit_task,
            module=post_edit,
        ),
        GENERATE_ILLUSTRATIONS_TASK: TaskSpec(
            GENERATE_ILLUSTRATIONS_TASK,
            TaskKind.ILLUSTRATION,
            task=illustrations.generate_illustrations_task,
            module=illustrations,
        ),
        REGENERATE_ILLUSTRATION_TASK: TaskSpec(
            REGENERATE_ILLUSTRATION_TASK,
            TaskKind.ILLUSTRATION,
            task=illustrations.regenerate_single_illustration,
            module=illustrations,
        ),
        REGENERATE_BASE_TASK: TaskSpec(
            REGENERATE_BASE_TASK,
            TaskKind.ILLUSTRATION,
            task=illustrations.regenerate_single_base,
            module=illustrations,
        ),
        PROCESS_OUTBOX_EVENTS_TASK: TaskSpec(
            PROCESS_OUTBOX_EVENTS_TASK,
            TaskKind.EVENT_PROCESSING,
            task=event_processor.process_outbox_events,
            module=event_processor,
        ),
        CLEANUP_TEMP_FILES_TASK: TaskSpec(
            CLEANUP_TEMP_FILES_TASK,
            TaskKind.MAINTENANCE,
            task=maintenance.cleanup_temp_files,
            module=maintenance,
        ),
        WATCHDOG_STALLED_JOBS_TASK: TaskSpec(
            WATCHDOG_STALLED_JOBS_TASK,
            TaskKind.MAINTENANCE,
            task=maintenance.watchdog_stalled_jobs,
            module=maintenance,
        ),
        RUN_MAINTENANCE_TASK: TaskSpec(
            RUN_MAINTENANCE_TASK,
            TaskKind.MAINTENANCE,
            runner=_run_maintenance,
        ),
    }


def _ensure_task_execution(
    *,
    task_id: str,
    task_name: str,
    task_kind: TaskKind,
    job_id: int | None,
    user_id: int | None,
    args: list[Any],
    kwargs: dict[str, Any],
) -> None:
    db = SessionLocal()
    try:
        task = db.query(TaskExecution).filter_by(id=task_id).first()
        if task:
            return
        task = TaskExecution(
            id=task_id,
            name=task_name,
            kind=task_kind,
            status=TaskStatus.PENDING,
            job_id=job_id,
            user_id=user_id,
            args=redact_background_payload(args),
            kwargs=redact_background_payload(kwargs),
            max_retries=0,
            queue_time=datetime.utcnow(),
            extra_data={"executor": "cloud_run_job"},
        )
        db.add(task)
        db.commit()
    finally:
        db.close()


def _mark_started(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = db.query(TaskExecution).filter_by(id=task_id).first()
        if not task:
            return
        if task.status == TaskStatus.REVOKED:
            raise RuntimeError("Task was cancelled before it started")
        task.status = TaskStatus.STARTED
        task.start_time = datetime.utcnow()
        task.attempts = (task.attempts or 0) + 1
        db.commit()
    finally:
        db.close()


def _mark_success(task_id: str, result: Any) -> None:
    db = SessionLocal()
    try:
        task = db.query(TaskExecution).filter_by(id=task_id).first()
        if not task:
            return
        task.status = TaskStatus.SUCCESS
        task.end_time = datetime.utcnow()
        if isinstance(result, (dict, list, str, int, float, bool)) or result is None:
            task.result = result
        db.commit()
    finally:
        db.close()


def _mark_failure(task_id: str, exc: Exception) -> None:
    db = SessionLocal()
    try:
        task = db.query(TaskExecution).filter_by(id=task_id).first()
        if not task:
            return
        if task.status != TaskStatus.REVOKED:
            task.status = TaskStatus.FAILURE
        task.end_time = datetime.utcnow()
        task.last_error = str(exc)
        db.commit()
    finally:
        db.close()


def _task_kind(value: str | None, task_name: str) -> TaskKind:
    if value:
        try:
            return TaskKind(value)
        except ValueError:
            pass
    spec = _task_registry().get(task_name)
    return spec.kind if spec else TaskKind.OTHER


def _json_env(name: str, default: Any) -> Any:
    value = os.getenv(name)
    if not value:
        return default
    return json.loads(value)


def _parse_int_env(name: str) -> int | None:
    value = os.getenv(name)
    if not value:
        return None
    return int(value)


if __name__ == "__main__":
    main()
