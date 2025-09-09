"""
Maintenance Celery tasks (e.g., temp file cleanup).
"""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import List

from ..celery_app import celery_app
from ..config.settings import get_settings


@celery_app.task(
    name="backend.celery_tasks.maintenance.cleanup_temp_files",
    max_retries=0,
)
def cleanup_temp_files(max_age_seconds: int | None = None) -> dict:
    """
    Remove files older than a threshold from temp and job storage directories.

    Args:
        max_age_seconds: Optional override of age threshold. If not provided,
            defaults to settings.cleanup_interval.

    Returns:
        Dictionary with summary of cleanup results.
    """
    settings = get_settings()
    age_threshold = max_age_seconds or settings.cleanup_interval
    cutoff_ts = datetime.now().timestamp() - age_threshold

    target_dirs: List[str] = [settings.temp_directory, settings.job_storage_base]
    deleted = 0
    errors = 0

    for d in target_dirs:
        try:
            base = Path(d)
            if not base.exists():
                continue
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    fpath = Path(root) / fname
                    try:
                        if fpath.stat().st_mtime < cutoff_ts:
                            fpath.unlink(missing_ok=True)
                            deleted += 1
                    except Exception:
                        errors += 1
                        continue
        except Exception:
            # Ignore per-directory errors to keep the task resilient
            errors += 1
            continue

    return {
        "status": "completed",
        "deleted": deleted,
        "errors": errors,
        "dirs": target_dirs,
        "age_threshold_seconds": age_threshold,
    }

