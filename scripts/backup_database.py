#!/usr/bin/env python3
"""
Manual database backup script

Usage:
    python scripts/backup_database.py                      # Run backup
    python scripts/backup_database.py --list              # List available backups
    python scripts/backup_database.py --restore           # Restore latest backup
    python scripts/backup_database.py --restore KEY       # Restore specific backup
    python scripts/backup_database.py --async-mode        # Run backup via Celery
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.aws_backup_service import AWSBackupService


def run_backup(use_async: bool = False):
    """
    Run database backup

    Args:
        use_async: If True, run via Celery task queue
    """
    print(f"Starting database backup at {datetime.now().isoformat()}")
    print("=" * 60)

    if use_async:
        # Run via Celery task
        try:
            from backend.celery_tasks.backup_tasks import backup_database_to_s3
            result = backup_database_to_s3.delay()
            print(f"Backup task queued with ID: {result.id}")
            print("Check Celery worker logs for progress")
            return
        except ImportError:
            print("Error: Celery not available. Running synchronously instead.")

    # Run synchronously
    backup_service = AWSBackupService()

    # Check if AWS is configured
    if not backup_service.s3_client:
        print("WARNING: AWS credentials not configured.")
        print("Running in dry-run mode (local backup only)")
        print()

    # Perform backup
    result = backup_service.backup_to_s3()

    # Display results
    print(f"Backup {'SUCCESSFUL' if result['success'] else 'FAILED'}")
    print(f"Mode: {result.get('mode', 'unknown')}")
    print()

    # Display step details
    for step in result.get('steps', []):
        step_name = step.get('step', 'unknown')
        step_success = step.get('success', False)
        status = "✓" if step_success else "✗"

        print(f"{status} {step_name.replace('_', ' ').title()}")

        if step_name == 'create_backup' and step_success:
            print(f"  - Original size: {step.get('original_size', 0):,} bytes")
            print(f"  - Compressed size: {step.get('compressed_size', 0):,} bytes")
            print(f"  - Compression ratio: {step.get('compression_ratio', 0):.1f}%")

            if 'statistics' in step:
                stats = step['statistics']
                print(f"  - Database stats:")
                print(f"    - Tables: {stats.get('table_count', 0)}")
                print(f"    - Total records: {stats.get('total_records', 0):,}")
                if 'tables' in stats:
                    for table, count in stats['tables'].items():
                        print(f"      - {table}: {count:,} records")

        elif step_name == 'upload' and step_success:
            print(f"  - Bucket: {step.get('s3_bucket', 'N/A')}")
            print(f"  - Key: {step.get('s3_key', 'N/A')}")
            print(f"  - Size: {step.get('size', 0):,} bytes")

        elif step_name == 'cleanup' and step_success:
            print(f"  - Deleted: {step.get('deleted_count', 0)} old backups")
            print(f"  - Freed space: {step.get('deleted_size', 0):,} bytes")
            print(f"  - Retention: {step.get('retention_days', 0)} days")

        elif not step_success:
            print(f"  - Error: {step.get('error', 'Unknown error')}")

    if not result['success']:
        print()
        print(f"ERROR: {result.get('error', 'Backup failed')}")
        sys.exit(1)

    print()
    print("Backup completed successfully!")


def list_backups(limit: int = 10):
    """
    List available backups in S3

    Args:
        limit: Maximum number of backups to show
    """
    print(f"Listing available backups (max {limit})")
    print("=" * 60)

    backup_service = AWSBackupService()

    if not backup_service.s3_client:
        print("Error: AWS credentials not configured")
        sys.exit(1)

    backups = backup_service.list_backups(limit=limit)

    if not backups:
        print("No backups found")
        return

    print(f"Found {len(backups)} backup(s):")
    print()

    for i, backup in enumerate(backups, 1):
        modified = datetime.fromisoformat(backup['last_modified'].replace('Z', '+00:00'))
        size_mb = backup['size'] / (1024 * 1024)

        print(f"{i}. {backup['key']}")
        print(f"   - Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - Size: {size_mb:.2f} MB")

        metadata = backup.get('metadata', {})
        if metadata:
            print(f"   - Original size: {int(metadata.get('original-size', 0)):,} bytes")
            print(f"   - Type: {metadata.get('backup-type', 'unknown')}")

        print()


def restore_backup(backup_key: str = None):
    """
    Restore database from backup

    Args:
        backup_key: S3 key of backup to restore (latest if None)
    """
    print(f"Restoring database from backup")
    print("=" * 60)

    if backup_key:
        print(f"Restoring from: {backup_key}")
    else:
        print("Restoring from latest backup")

    # Confirm restoration
    print()
    print("WARNING: This will replace the current database!")
    response = input("Continue? (yes/no): ")

    if response.lower() != 'yes':
        print("Restoration cancelled")
        return

    backup_service = AWSBackupService()

    if not backup_service.s3_client:
        print("Error: AWS credentials not configured")
        sys.exit(1)

    print("Starting restoration...")
    result = backup_service.restore_from_s3(backup_key=backup_key)

    if result['success']:
        print("✓ Database restored successfully")
        print(f"  - From: {result.get('restored_from', 'unknown')}")
        print(f"  - To: {result.get('restored_to', 'unknown')}")
        if 'previous_backup' in result:
            print(f"  - Previous database backed up to: {result['previous_backup']}")
    else:
        print(f"✗ Restoration failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Database backup management tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Run backup now
  %(prog)s --async-mode        # Queue backup via Celery
  %(prog)s --list              # List available backups
  %(prog)s --restore           # Restore latest backup
  %(prog)s --restore KEY       # Restore specific backup
        """
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List available backups'
    )

    parser.add_argument(
        '--restore',
        nargs='?',
        const='',
        help='Restore from backup (latest if no key specified)'
    )

    parser.add_argument(
        '--async-mode',
        action='store_true',
        help='Run backup asynchronously via Celery'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of backups to list (default: 10)'
    )

    args = parser.parse_args()

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    try:
        if args.list:
            list_backups(limit=args.limit)
        elif args.restore is not None:
            backup_key = args.restore if args.restore else None
            restore_backup(backup_key)
        else:
            run_backup(use_async=args.async_mode)
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()