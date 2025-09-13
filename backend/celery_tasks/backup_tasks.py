"""Celery tasks for database backup operations"""

import logging
from datetime import datetime
from typing import Dict, Any
from celery import shared_task
from backend.services.aws_backup_service import AWSBackupService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='backup.database_to_s3',
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def backup_database_to_s3(self) -> Dict[str, Any]:
    """
    Periodic task to backup database to AWS S3

    This task is scheduled to run daily via Celery Beat.
    Can also be triggered manually.

    Returns:
        Dict with backup results and metadata
    """
    try:
        logger.info(f"Starting scheduled database backup at {datetime.now().isoformat()}")

        # Initialize backup service
        backup_service = AWSBackupService()

        # Perform backup
        result = backup_service.backup_to_s3()

        if not result['success']:
            error_msg = result.get('error', 'Unknown error during backup')
            logger.error(f"Database backup failed: {error_msg}")
            raise Exception(error_msg)

        logger.info(f"Database backup completed successfully: {result}")

        # Log statistics
        for step in result.get('steps', []):
            if step.get('step') == 'create_backup' and step.get('success'):
                logger.info(
                    f"Backup statistics: "
                    f"Original size: {step.get('original_size', 0):,} bytes, "
                    f"Compressed size: {step.get('compressed_size', 0):,} bytes, "
                    f"Compression ratio: {step.get('compression_ratio', 0):.1f}%"
                )
                if 'statistics' in step:
                    stats = step['statistics']
                    logger.info(
                        f"Database statistics: "
                        f"Tables: {stats.get('table_count', 0)}, "
                        f"Total records: {stats.get('total_records', 0):,}"
                    )

        return result

    except Exception as exc:
        logger.error(f"Database backup task failed: {exc}")
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))


@shared_task(
    bind=True,
    name='backup.restore_from_s3',
    max_retries=2,
    default_retry_delay=60
)
def restore_database_from_s3(self, backup_key: str = None) -> Dict[str, Any]:
    """
    Task to restore database from S3 backup

    Args:
        backup_key: S3 key of the backup to restore (latest if None)

    Returns:
        Dict with restoration results
    """
    try:
        logger.info(f"Starting database restoration from S3")

        # Initialize backup service
        backup_service = AWSBackupService()

        # Perform restoration
        result = backup_service.restore_from_s3(backup_key=backup_key)

        if not result['success']:
            error_msg = result.get('error', 'Unknown error during restoration')
            logger.error(f"Database restoration failed: {error_msg}")
            raise Exception(error_msg)

        logger.info(f"Database restoration completed successfully: {result}")

        return result

    except Exception as exc:
        logger.error(f"Database restoration task failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name='backup.list_available_backups'
)
def list_available_backups(limit: int = 10) -> list:
    """
    List available backups in S3

    Args:
        limit: Maximum number of backups to return

    Returns:
        List of backup metadata
    """
    try:
        backup_service = AWSBackupService()
        backups = backup_service.list_backups(limit=limit)

        logger.info(f"Found {len(backups)} backups in S3")

        return backups

    except Exception as exc:
        logger.error(f"Failed to list backups: {exc}")
        return []


@shared_task(
    name='backup.cleanup_old_backups'
)
def cleanup_old_backups() -> Dict[str, Any]:
    """
    Task to cleanup old backups beyond retention period

    This can be scheduled separately if needed.

    Returns:
        Dict with cleanup results
    """
    try:
        logger.info("Starting old backup cleanup")

        backup_service = AWSBackupService()

        # The cleanup is already part of the main backup process,
        # but this task allows for independent cleanup if needed
        result = backup_service._cleanup_old_backups()

        if result['success']:
            logger.info(
                f"Cleanup completed: Deleted {result.get('deleted_count', 0)} backups "
                f"({result.get('deleted_size', 0):,} bytes)"
            )
        else:
            logger.error(f"Cleanup failed: {result.get('error', 'Unknown error')}")

        return result

    except Exception as exc:
        logger.error(f"Backup cleanup task failed: {exc}")
        return {
            'success': False,
            'error': str(exc)
        }