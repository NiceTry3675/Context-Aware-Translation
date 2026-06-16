"""Canonical background task names used outside Celery."""

PROCESS_TRANSLATION_TASK = "backend.celery_tasks.translation.process_translation_task"
PROCESS_VALIDATION_TASK = "backend.celery_tasks.validation.process_validation_task"
PROCESS_POST_EDIT_TASK = "backend.celery_tasks.post_edit.process_post_edit_task"
GENERATE_ILLUSTRATIONS_TASK = "backend.celery_tasks.illustrations.generate_illustrations_task"
REGENERATE_ILLUSTRATION_TASK = "backend.celery_tasks.illustrations.regenerate_single_illustration"
REGENERATE_BASE_TASK = "backend.celery_tasks.illustrations.regenerate_single_base"

PROCESS_OUTBOX_EVENTS_TASK = "backend.celery_tasks.event_processor.process_outbox_events"
CLEANUP_TEMP_FILES_TASK = "backend.celery_tasks.maintenance.cleanup_temp_files"
WATCHDOG_STALLED_JOBS_TASK = "backend.celery_tasks.maintenance.watchdog_stalled_jobs"

RUN_MAINTENANCE_TASK = "backend.background.maintenance.run_maintenance"
