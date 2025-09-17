"""AWS S3 Backup Service for SQLite Database

This service handles:
- Full database backups to S3
- Incremental change tracking
- Backup rotation and cleanup
- Restoration from backups
"""

import os
import sqlite3
import boto3
import gzip
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
import shutil
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class AWSBackupService:
    """Service for backing up SQLite database to AWS S3"""

    def __init__(self):
        """Initialize AWS S3 client and configuration"""
        self.s3_client = None
        settings = get_settings()
        self.bucket = os.getenv('S3_BACKUP_BUCKET', 'translation-system-backups')
        # Extract database path from database_url
        if settings.database_url.startswith('sqlite:///'):
            self.local_db_path = settings.database_url.replace('sqlite:///', '')
        else:
            # For non-SQLite databases, this service doesn't apply
            self.local_db_path = None
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        self.aws_region = settings.s3_region or 'us-east-1'

        # Initialize S3 client only if AWS credentials are configured
        if self._has_aws_credentials():
            self.s3_client = boto3.client(
                's3',
                region_name=self.aws_region,
                aws_access_key_id=get_settings().s3_access_key or os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=get_settings().s3_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
            )
        else:
            logger.warning("AWS credentials not configured. Backup service will run in dry-run mode.")

    def _has_aws_credentials(self) -> bool:
        """Check if AWS credentials are configured"""
        settings = get_settings()
        return bool(
            (settings.s3_access_key or os.getenv('AWS_ACCESS_KEY_ID')) and
            (settings.s3_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY'))
        )

    def backup_to_s3(self) -> Dict[str, Any]:
        """
        Main backup orchestrator

        Returns:
            Dict with backup results and metadata
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'steps': [],
            'mode': 'live' if self.s3_client else 'dry-run'
        }

        try:
            # Step 1: Create compressed backup
            logger.info("Starting database backup to S3...")
            backup_result = self._create_full_backup()
            results['steps'].append(backup_result)

            if backup_result.get('skip'):
                logger.info("Skipping remaining backup steps: %s", backup_result.get('note', 'No SQLite database configured'))
                results['success'] = True
                return results

            # Step 2: Upload to S3
            if self.s3_client:
                upload_result = self._upload_backup(backup_result['backup_file'])
                results['steps'].append(upload_result)
            else:
                results['steps'].append({
                    'step': 'upload',
                    'success': True,
                    'note': 'Skipped (dry-run mode)'
                })

            # Step 3: Clean up old backups
            if self.s3_client:
                cleanup_result = self._cleanup_old_backups()
                results['steps'].append(cleanup_result)

            # Step 4: Verify backup integrity
            verify_result = self._verify_backup(backup_result['backup_file'])
            results['steps'].append(verify_result)

            results['success'] = all(step.get('success', False) for step in results['steps'])

            # Clean up temp file
            if 'backup_file' in backup_result and os.path.exists(backup_result['backup_file']):
                os.remove(backup_result['backup_file'])

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            results['error'] = str(e)

        return results

    def _create_full_backup(self) -> Dict[str, Any]:
        """
        Create a compressed backup of the database

        Returns:
            Dict with backup file path and metadata
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_dir = tempfile.gettempdir()
        backup_filename = f"backup_{timestamp}.db.gz"
        backup_path = os.path.join(temp_dir, backup_filename)

        if not self.local_db_path:
            note = "SQLite database path not configured; skipping backup."
            logger.info(note)
            return {
                'step': 'create_backup',
                'success': True,
                'skip': True,
                'note': note
            }

        try:
            # Get database statistics before backup
            stats = self._get_database_stats()

            # Create compressed backup
            with open(self.local_db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            original_size = os.path.getsize(self.local_db_path)
            compressed_size = os.path.getsize(backup_path)
            compression_ratio = (1 - compressed_size / original_size) * 100

            logger.info(f"Backup created: {backup_filename} "
                       f"(compressed {compression_ratio:.1f}%: "
                       f"{original_size:,} -> {compressed_size:,} bytes)")

            return {
                'step': 'create_backup',
                'success': True,
                'backup_file': backup_path,
                'backup_filename': backup_filename,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'statistics': stats,
                'timestamp': timestamp
            }

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return {
                'step': 'create_backup',
                'success': False,
                'error': str(e)
            }

    def _upload_backup(self, backup_file: str) -> Dict[str, Any]:
        """
        Upload backup file to S3 with metadata

        Args:
            backup_file: Path to the backup file

        Returns:
            Dict with upload results
        """
        if not self.s3_client:
            return {
                'step': 'upload',
                'success': False,
                'error': 'S3 client not initialized'
            }

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_key = f"backups/full/{timestamp}/database.db.gz"

            # Prepare metadata
            metadata = {
                'timestamp': timestamp,
                'original-size': str(os.path.getsize(self.local_db_path)),
                'compressed-size': str(os.path.getsize(backup_file)),
                'backup-type': 'full',
                'database-path': self.local_db_path
            }

            # Upload to S3
            self.s3_client.upload_file(
                backup_file,
                self.bucket,
                backup_key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ServerSideEncryption': 'AES256'
                }
            )

            logger.info(f"Backup uploaded to S3: s3://{self.bucket}/{backup_key}")

            return {
                'step': 'upload',
                'success': True,
                's3_bucket': self.bucket,
                's3_key': backup_key,
                'size': os.path.getsize(backup_file)
            }

        except Exception as e:
            logger.error(f"Failed to upload backup to S3: {e}")
            return {
                'step': 'upload',
                'success': False,
                'error': str(e)
            }

    def _cleanup_old_backups(self) -> Dict[str, Any]:
        """
        Remove backups older than retention period

        Returns:
            Dict with cleanup results
        """
        if not self.s3_client:
            return {
                'step': 'cleanup',
                'success': False,
                'error': 'S3 client not initialized'
            }

        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_count = 0
            deleted_size = 0

            # List all backups
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix='backups/full/'
            )

            objects_to_delete = []

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        objects_to_delete.append({'Key': obj['Key']})
                        deleted_size += obj.get('Size', 0)
                        deleted_count += 1

            # Delete old backups in batches
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i+1000]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket,
                        Delete={'Objects': batch}
                    )

                logger.info(f"Cleaned up {deleted_count} old backups "
                           f"({deleted_size:,} bytes)")

            return {
                'step': 'cleanup',
                'success': True,
                'deleted_count': deleted_count,
                'deleted_size': deleted_size,
                'retention_days': self.retention_days
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return {
                'step': 'cleanup',
                'success': False,
                'error': str(e)
            }

    def _verify_backup(self, backup_file: str) -> Dict[str, Any]:
        """
        Verify backup integrity

        Args:
            backup_file: Path to the backup file

        Returns:
            Dict with verification results
        """
        try:
            # Decompress and verify SQLite header
            with gzip.open(backup_file, 'rb') as f:
                header = f.read(16)
                if header != b'SQLite format 3\x00':
                    raise ValueError("Invalid SQLite database header")

            logger.info("Backup verification successful")

            return {
                'step': 'verify',
                'success': True,
                'verified': True
            }

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return {
                'step': 'verify',
                'success': False,
                'error': str(e)
            }

    def _get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Dict with database statistics
        """
        stats = {}

        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()

            # Get table counts
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = cursor.fetchall()

            stats['tables'] = {}
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats['tables'][table_name] = count

            # Get database size
            stats['total_records'] = sum(stats['tables'].values())
            stats['table_count'] = len(stats['tables'])

            conn.close()

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            stats['error'] = str(e)

        return stats

    def restore_from_s3(self, backup_key: Optional[str] = None,
                       restore_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore database from S3 backup

        Args:
            backup_key: S3 key of the backup to restore (latest if None)
            restore_path: Path to restore to (replaces current DB if None)

        Returns:
            Dict with restoration results
        """
        if not self.s3_client:
            return {
                'success': False,
                'error': 'S3 client not initialized'
            }

        results = {
            'timestamp': datetime.now().isoformat(),
            'success': False
        }

        temp_file = None

        try:
            # Find latest backup if not specified
            if not backup_key:
                backup_key = self._find_latest_backup()
                if not backup_key:
                    raise ValueError("No backups found in S3")

            # Download backup
            temp_file = tempfile.NamedTemporaryFile(suffix='.db.gz', delete=False)
            self.s3_client.download_file(self.bucket, backup_key, temp_file.name)

            # Decompress backup
            restore_target = restore_path or self.local_db_path
            restore_temp = f"{restore_target}.restore_tmp"

            with gzip.open(temp_file.name, 'rb') as f_in:
                with open(restore_temp, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Verify restored database
            conn = sqlite3.connect(restore_temp)
            conn.execute("SELECT 1")
            conn.close()

            # Replace current database (with backup)
            if not restore_path:
                backup_current = f"{self.local_db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if os.path.exists(self.local_db_path):
                    shutil.move(self.local_db_path, backup_current)
                    results['previous_backup'] = backup_current

            shutil.move(restore_temp, restore_target)

            results['success'] = True
            results['restored_from'] = backup_key
            results['restored_to'] = restore_target

            logger.info(f"Database restored from {backup_key}")

        except Exception as e:
            logger.error(f"Failed to restore from S3: {e}")
            results['error'] = str(e)

        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

        return results

    def _find_latest_backup(self) -> Optional[str]:
        """
        Find the most recent backup in S3

        Returns:
            S3 key of the latest backup or None
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix='backups/full/',
                MaxKeys=1000
            )

            if 'Contents' not in response:
                return None

            # Sort by LastModified and get the most recent
            objects = sorted(
                response['Contents'],
                key=lambda x: x['LastModified'],
                reverse=True
            )

            return objects[0]['Key'] if objects else None

        except Exception as e:
            logger.error(f"Failed to find latest backup: {e}")
            return None

    def list_backups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List available backups in S3

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup metadata
        """
        if not self.s3_client:
            return []

        backups = []

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix='backups/full/',
                MaxKeys=limit * 2  # Get extra to account for filtering
            )

            if 'Contents' not in response:
                return []

            # Sort by LastModified (newest first)
            objects = sorted(
                response['Contents'],
                key=lambda x: x['LastModified'],
                reverse=True
            )[:limit]

            for obj in objects:
                # Get object metadata
                meta_response = self.s3_client.head_object(
                    Bucket=self.bucket,
                    Key=obj['Key']
                )

                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'metadata': meta_response.get('Metadata', {}),
                    'storage_class': obj.get('StorageClass', 'STANDARD')
                })

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")

        return backups