#!/usr/bin/env python3
"""
Check backup system status and configuration

Usage:
    python scripts/check_backup_status.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_environment():
    """Check environment configuration"""
    print("=" * 60)
    print("BACKUP SYSTEM STATUS CHECK")
    print("=" * 60)
    print()

    # Check AWS configuration
    print("AWS Configuration:")
    aws_configured = bool(
        os.getenv('AWS_ACCESS_KEY_ID') and
        os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    if aws_configured:
        print("  ✓ AWS credentials configured")
        print(f"  - Region: {os.getenv('AWS_REGION', 'us-east-1')}")
        print(f"  - Bucket: {os.getenv('S3_BACKUP_BUCKET', 'translation-system-backups')}")
        print(f"  - Retention: {os.getenv('BACKUP_RETENTION_DAYS', '30')} days")
    else:
        print("  ✗ AWS credentials not configured")
        print("    System will run in dry-run mode (local backup only)")
        print("    To enable S3 backups, set:")
        print("      - AWS_ACCESS_KEY_ID")
        print("      - AWS_SECRET_ACCESS_KEY")

    print()

    # Check database
    print("Database Configuration:")
    db_path = os.getenv('DATABASE_PATH', 'database.db')
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"  ✓ Database found: {db_path}")
        print(f"  - Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
        modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        print(f"  - Last modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"  ✗ Database not found at: {db_path}")

    print()

    # Check Redis
    print("Redis Configuration:")
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    print(f"  - URL: {redis_url}")

    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        print("  ✓ Redis connection successful")
    except Exception as e:
        print(f"  ✗ Redis connection failed: {e}")
        print("    Automated backups require Redis for Celery")

    print()

    # Check Celery
    print("Celery Configuration:")
    try:
        from backend.celery_app import celery_app
        print("  ✓ Celery app configured")

        # Check if backup task is registered
        if 'backup.database_to_s3' in celery_app.tasks:
            print("  ✓ Backup task registered")
        else:
            print("  ✗ Backup task not registered")

        # Check beat schedule
        beat_schedule = celery_app.conf.beat_schedule
        if 'backup-database-daily' in beat_schedule:
            schedule = beat_schedule['backup-database-daily']
            print(f"  ✓ Daily backup scheduled")
            print(f"    - Task: {schedule['task']}")
            print(f"    - Interval: Every {schedule['schedule']} seconds")
        else:
            print("  ✗ Daily backup not scheduled")

    except Exception as e:
        print(f"  ✗ Celery configuration failed: {e}")

    print()

    # Check backup service
    print("Backup Service Test:")
    try:
        from backend.services.aws_backup_service import AWSBackupService
        service = AWSBackupService()

        if service.s3_client:
            print("  ✓ S3 client initialized")

            # Try to list backups
            try:
                backups = service.list_backups(limit=1)
                if backups:
                    print(f"  ✓ Can access S3 bucket")
                    print(f"    - Found {len(backups)} recent backup(s)")
                else:
                    print("  ✓ Can access S3 bucket (no backups yet)")
            except Exception as e:
                print(f"  ✗ Cannot access S3 bucket: {e}")
        else:
            print("  ⚠ Running in dry-run mode (no S3 access)")

        # Test backup creation (dry-run)
        stats = service._get_database_stats()
        print(f"  ✓ Database statistics retrieved")
        print(f"    - Tables: {stats.get('table_count', 0)}")
        print(f"    - Records: {stats.get('total_records', 0):,}")

    except Exception as e:
        print(f"  ✗ Backup service test failed: {e}")

    print()
    print("=" * 60)

    # Summary
    if aws_configured:
        print("✅ Backup system is fully configured")
        print()
        print("To start automated backups:")
        print("  1. Start Celery worker: celery -A backend.celery_app worker")
        print("  2. Start Celery beat:  celery -A backend.celery_app beat")
        print()
        print("To run manual backup:")
        print("  python scripts/backup_database.py")
    else:
        print("⚠️  Backup system in dry-run mode")
        print()
        print("The system will create local backups but won't upload to S3.")
        print("To enable S3 uploads, configure AWS credentials in .env")

    print("=" * 60)


if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    try:
        check_environment()
    except KeyboardInterrupt:
        print("\nCheck cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)