"""
Simple watchdog to mark stalled jobs as FAILED when there's no active Celery task.

Intended to be triggered periodically (e.g., via a Celery beat or external scheduler).
"""
from datetime import datetime, timedelta
import logging
from celery.result import AsyncResult

from backend.config.database import SessionLocal
from backend.celery_app import celery_app
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
from backend.domains.tasks.repository import TaskRepository
from backend.domains.tasks.models import TaskKind

logger = logging.getLogger(__name__)


def mark_stalled_jobs(
    max_inprogress_minutes: int = 60,
    lookback_hours: int = 24,
) -> dict:
    """
    Scan recent jobs and mark IN_PROGRESS validation/post-edit/illustration as FAILED if no active Celery task.

    Returns a summary dict with counts.
    """
    db = SessionLocal()
    repo = SqlAlchemyTranslationJobRepository(db)
    task_repo = TaskRepository(db)
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=lookback_hours)

    # Query with limit to prevent unbounded result sets in production
    from backend.domains.translation.models import TranslationJob
    jobs = (
        db.query(TranslationJob)
        .filter(TranslationJob.created_at >= cutoff)
        .order_by(TranslationJob.created_at.desc())
        .limit(1000)  # Prevent memory issues with large datasets
        .all()
    )

    stalled = {"validation": 0, "post_edit": 0, "illustrations": 0}

    for job in jobs:
        # Helper to decide if a phase is stalled: IN_PROGRESS for too long and no active task
        def is_stalled(kind: TaskKind, started_at_field: str | None, status_value: str | None) -> bool:
            if status_value != "IN_PROGRESS":
                return False
            # Find most recent task for this job and kind
            tasks = task_repo.get_job_tasks(job.id)
            recent = next((t for t in tasks if t.kind == kind), None)
            if recent:
                state = AsyncResult(recent.id, app=celery_app).state
                if state in ("PENDING", "STARTED", "RETRY"):
                    return False
            # Fallback: use created_at/validation_completed_at timestamps to estimate staleness
            started_at = getattr(job, started_at_field) if started_at_field else job.created_at
            if not started_at:
                return True
            return (now - (started_at or cutoff)) > timedelta(minutes=max_inprogress_minutes)

        # Validation
        if is_stalled(TaskKind.VALIDATION, "validation_completed_at", job.validation_status):
            repo.update_validation_status(job.id, "FAILED")
            db.commit()
            stalled["validation"] += 1

        # Post-edit
        if is_stalled(TaskKind.POST_EDIT, "post_edit_completed_at", job.post_edit_status):
            repo.update_post_edit_status(job.id, "FAILED")
            db.commit()
            stalled["post_edit"] += 1

        # Illustrations
        if is_stalled(TaskKind.ILLUSTRATION, None, job.illustrations_status):
            repo.update_illustration_status(job.id, "FAILED")
            db.commit()
            stalled["illustrations"] += 1

    logger.info(f"Watchdog: stalled summary: {stalled}")
    db.close()
    return stalled

