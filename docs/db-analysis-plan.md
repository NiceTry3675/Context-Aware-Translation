# AWS Database Synchronization Plan

## Executive Summary
Plan to implement periodic synchronization of the local SQLite database (`database.db`) to AWS for persistence, backup, and potential multi-instance deployment.

## Current State Analysis

### Database Characteristics
- **Type**: SQLite3
- **Size**: ~978KB (will grow with usage)
- **Tables**: 10 tables (translation_jobs, task_executions, users, etc.)
- **Update Frequency**:
  - High during job processing (every few seconds)
  - Low during idle periods
- **Critical Data**: Translation jobs, user data, task history

### Current Limitations
- Single point of failure (local SQLite)
- No automated backups
- Cannot scale horizontally
- No disaster recovery

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local Environment                        │
│                                                              │
│  ┌──────────────┐        ┌─────────────────────────┐        │
│  │   SQLite     │───────►│   Sync Service          │        │
│  │ database.db  │        │  (Celery Beat Task)     │        │
│  └──────────────┘        └──────────┬─────────────┘        │
│                                      │                       │
└──────────────────────────────────────┼──────────────────────┘
                                       │
                                       │ Periodic Sync
                                       │ (Every 5-15 min)
                                       ▼
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                              │
│  ┌─────────────────────────────────────────────────┐        │
│  │           Option A: S3 + RDS                    │        │
│  │  ┌─────────────┐      ┌──────────────┐         │        │
│  │  │  S3 Bucket  │      │  RDS MySQL/  │         │        │
│  │  │  (Backups)  │      │  PostgreSQL  │         │        │
│  │  └─────────────┘      └──────────────┘         │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
│  ┌─────────────────────────────────────────────────┐        │
│  │           Option B: S3 Only                     │        │
│  │  ┌────────────────────────────────────┐        │        │
│  │  │  S3 Bucket                          │        │        │
│  │  │  - Full backups (.db files)         │        │        │
│  │  │  - Incremental dumps (.sql)         │        │        │
│  │  │  - Versioning enabled               │        │        │
│  │  └────────────────────────────────────┘        │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
│  ┌─────────────────────────────────────────────────┐        │
│  │           Option C: DynamoDB                    │        │
│  │  ┌────────────────────────────────────┐        │        │
│  │  │  DynamoDB Tables                    │        │        │
│  │  │  - Serverless                       │        │        │
│  │  │  - Auto-scaling                     │        │        │
│  │  │  - Point-in-time recovery           │        │        │
│  │  └────────────────────────────────────┘        │        │
│  └─────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Options

### Option A: S3 + RDS (Recommended for Production)

#### Advantages
- Full SQL compatibility with RDS
- S3 for backup redundancy
- Can switch to RDS as primary database later
- Supports complex queries and relationships

#### Implementation Steps
1. **Setup AWS Resources**
   ```bash
   # Create S3 bucket for backups
   aws s3 mb s3://translation-system-backups

   # Create RDS instance (PostgreSQL recommended)
   aws rds create-db-instance \
     --db-instance-identifier translation-db \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --allocated-storage 20
   ```

2. **Create Sync Service**
   ```python
   # backend/celery_tasks/db_sync.py
   from celery import shared_task
   import sqlite3
   import psycopg2
   import boto3
   from datetime import datetime

   @shared_task
   def sync_to_aws():
       # 1. Backup SQLite to S3
       backup_to_s3()

       # 2. Sync changes to RDS
       sync_to_rds()

       # 3. Verify sync
       verify_sync()
   ```

3. **Configure Celery Beat**
   ```python
   # backend/celery_app.py
   from celery.schedules import crontab

   app.conf.beat_schedule = {
       'sync-database': {
           'task': 'backend.celery_tasks.db_sync.sync_to_aws',
           'schedule': crontab(minute='*/15'),  # Every 15 minutes
       },
   }
   ```

### Option B: S3 Only (Recommended for Starting)

#### Advantages
- Simplest to implement
- Lowest cost
- Good for backup/recovery
- No database migration needed

#### Implementation Steps
1. **S3 Backup Strategy**
   ```python
   # backend/services/backup_service.py
   import boto3
   import sqlite3
   import gzip
   from datetime import datetime

   class BackupService:
       def __init__(self):
           self.s3 = boto3.client('s3')
           self.bucket = 'translation-system-backups'

       def backup_full(self):
           """Full database backup"""
           timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

           # Compress database
           with open('database.db', 'rb') as f_in:
               with gzip.open(f'/tmp/backup_{timestamp}.db.gz', 'wb') as f_out:
                   f_out.writelines(f_in)

           # Upload to S3
           self.s3.upload_file(
               f'/tmp/backup_{timestamp}.db.gz',
               self.bucket,
               f'full/{timestamp}/database.db.gz'
           )

       def backup_incremental(self, last_sync_time):
           """Incremental backup of changes"""
           conn = sqlite3.connect('database.db')

           # Export recent changes
           for table in ['translation_jobs', 'task_executions']:
               cursor = conn.execute(
                   f"SELECT * FROM {table} WHERE updated_at > ?",
                   (last_sync_time,)
               )
               # Convert to JSON and upload
   ```

2. **Recovery Process**
   ```python
   def restore_from_s3(backup_date):
       """Restore database from S3 backup"""
       # Download latest backup
       # Decompress
       # Replace local database
       # Verify integrity
   ```

### Option C: DynamoDB (For Serverless Future)

#### Advantages
- Serverless, no maintenance
- Auto-scaling
- Built-in backup and recovery
- Global tables for multi-region

#### Challenges
- NoSQL requires schema redesign
- Complex migrations from SQL
- Different query patterns

## Synchronization Strategies

### 1. Full Backup Strategy
```
Every 1 hour:
  - Create complete SQLite backup
  - Compress with gzip
  - Upload to S3 with timestamp
  - Maintain last 24 hourly, 7 daily, 4 weekly backups
```

### 2. Incremental Sync Strategy
```
Every 5 minutes:
  - Track last_sync_timestamp
  - Query changed records (updated_at > last_sync)
  - Upload changes as JSON to S3
  - Apply changes to RDS (if using)
```

### 3. Real-time Sync Strategy
```
On every database write:
  - Capture change via SQLAlchemy events
  - Queue change in Redis
  - Process queue asynchronously
  - Write to AWS
```

## Implementation Plan

### Phase 1: S3 Backup (Week 1)
- [ ] Create AWS S3 bucket
- [ ] Implement BackupService class
- [ ] Add Celery beat task for hourly backups
- [ ] Test backup and restore process
- [ ] Add monitoring and alerts

### Phase 2: Incremental Sync (Week 2)
- [ ] Add updated_at timestamps to all tables
- [ ] Implement incremental backup logic
- [ ] Create sync_status tracking table
- [ ] Add retry logic for failed syncs
- [ ] Implement backup verification

### Phase 3: RDS Migration Prep (Week 3-4)
- [ ] Provision RDS PostgreSQL instance
- [ ] Create schema migration scripts
- [ ] Implement dual-write logic
- [ ] Test data consistency
- [ ] Create rollback procedures

### Phase 4: Monitoring & Recovery (Week 4)
- [ ] CloudWatch alarms for sync failures
- [ ] Automated recovery testing
- [ ] Documentation and runbooks
- [ ] Performance optimization

## Code Implementation

### 1. Environment Configuration
```bash
# .env additions
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
S3_BACKUP_BUCKET=translation-system-backups
RDS_HOST=xxx.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=translation_db
RDS_USERNAME=admin
RDS_PASSWORD=xxx
SYNC_INTERVAL_MINUTES=15
BACKUP_RETENTION_DAYS=30
```

### 2. Sync Service Implementation
```python
# backend/services/aws_sync_service.py
import os
import sqlite3
import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AWSSyncService:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket = os.getenv('S3_BACKUP_BUCKET')
        self.local_db_path = 'database.db'

    def sync_to_aws(self) -> Dict:
        """Main sync orchestrator"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'steps': []
        }

        try:
            # Step 1: Full backup to S3
            backup_result = self.backup_full_to_s3()
            results['steps'].append(backup_result)

            # Step 2: Incremental sync
            sync_result = self.sync_incremental()
            results['steps'].append(sync_result)

            # Step 3: Cleanup old backups
            cleanup_result = self.cleanup_old_backups()
            results['steps'].append(cleanup_result)

            results['success'] = True

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            results['error'] = str(e)

        return results

    def backup_full_to_s3(self) -> Dict:
        """Create and upload full database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_key = f"backups/full/{timestamp}/database.db"

        # Upload with metadata
        metadata = {
            'timestamp': timestamp,
            'size': str(os.path.getsize(self.local_db_path)),
            'tables': ','.join(self.get_table_names()),
            'record_counts': json.dumps(self.get_record_counts())
        }

        self.s3.upload_file(
            self.local_db_path,
            self.bucket,
            backup_key,
            ExtraArgs={'Metadata': metadata}
        )

        return {
            'step': 'full_backup',
            'success': True,
            'key': backup_key,
            'size': metadata['size']
        }

    def sync_incremental(self) -> Dict:
        """Sync recent changes only"""
        last_sync = self.get_last_sync_time()

        changes = {
            'translation_jobs': self.get_table_changes('translation_jobs', last_sync),
            'task_executions': self.get_table_changes('task_executions', last_sync),
            'translation_usage_logs': self.get_table_changes('translation_usage_logs', last_sync)
        }

        # Upload changes as JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        changes_key = f"backups/incremental/{timestamp}/changes.json"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=changes_key,
            Body=json.dumps(changes, default=str),
            ContentType='application/json'
        )

        # Update last sync time
        self.update_last_sync_time()

        return {
            'step': 'incremental_sync',
            'success': True,
            'changes_key': changes_key,
            'records_synced': sum(len(v) for v in changes.values())
        }
```

### 3. Celery Task Configuration
```python
# backend/celery_tasks/aws_sync.py
from celery import shared_task
from backend.services.aws_sync_service import AWSSyncService
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def sync_database_to_aws(self):
    """Periodic task to sync database to AWS"""
    try:
        service = AWSSyncService()
        result = service.sync_to_aws()

        if not result['success']:
            raise Exception(f"Sync failed: {result.get('error')}")

        logger.info(f"Database sync completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Database sync failed: {exc}")
        raise self.retry(exc=exc)
```

### 4. Migration Script for RDS
```python
# scripts/migrate_to_rds.py
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

def migrate_sqlite_to_postgres():
    """One-time migration from SQLite to PostgreSQL"""

    # Connect to both databases
    sqlite_conn = sqlite3.connect('database.db')
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(
        host=os.getenv('RDS_HOST'),
        database=os.getenv('RDS_DATABASE'),
        user=os.getenv('RDS_USERNAME'),
        password=os.getenv('RDS_PASSWORD')
    )

    # Migrate each table
    tables = [
        'users',
        'translation_jobs',
        'task_executions',
        'translation_usage_logs',
        'posts',
        'comments',
        'announcements'
    ]

    for table in tables:
        migrate_table(sqlite_conn, pg_conn, table)

    pg_conn.commit()
```

## Security Considerations

### 1. AWS IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::translation-system-backups/*",
        "arn:aws:s3:::translation-system-backups"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:CreateDBSnapshot"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Encryption
- Enable S3 bucket encryption (AES-256)
- Use SSL/TLS for data in transit
- Encrypt sensitive data before backup
- RDS encryption at rest

### 3. Access Control
- Use IAM roles, not root credentials
- Rotate access keys regularly
- VPC endpoints for S3 access
- RDS security groups

## Monitoring & Alerts

### 1. CloudWatch Metrics
```python
# Custom metrics to track
metrics = {
    'BackupSize': size_in_bytes,
    'BackupDuration': duration_seconds,
    'RecordsSynced': count,
    'SyncFailures': count,
    'LastSuccessfulSync': timestamp
}
```

### 2. Alarms
- Backup failure (no successful backup in 2 hours)
- Backup size anomaly (>50% change)
- Sync duration exceeds threshold
- Storage usage approaching limit

### 3. Dashboards
- Backup timeline visualization
- Sync success rate
- Data growth trends
- Recovery point objectives (RPO)

## Disaster Recovery

### Recovery Procedures
1. **Local Failure**
   ```bash
   # Download latest backup from S3
   aws s3 cp s3://translation-system-backups/backups/full/latest/database.db ./database.db

   # Apply incremental changes
   python scripts/apply_incremental.py --since=last_full_backup
   ```

2. **Point-in-Time Recovery**
   ```bash
   # Restore to specific timestamp
   python scripts/restore_to_timestamp.py --timestamp="2024-01-15T10:30:00"
   ```

3. **RDS Failover**
   ```bash
   # Switch to RDS as primary
   python scripts/switch_to_rds.py
   ```

## Cost Estimation

### S3 Storage
- Storage: $0.023 per GB/month
- Requests: $0.0004 per 1,000 requests
- **Estimated**: ~$5/month for 200GB with versioning

### RDS (PostgreSQL)
- db.t3.micro: $0.018 per hour
- Storage: $0.115 per GB/month
- **Estimated**: ~$15/month for basic instance

### Total Monthly Cost
- **Minimal (S3 only)**: ~$5-10
- **Full (S3 + RDS)**: ~$20-30

## Testing Strategy

### 1. Unit Tests
```python
# tests/test_aws_sync.py
def test_backup_creation():
    """Test backup file creation"""

def test_incremental_sync():
    """Test incremental change detection"""

def test_restore_from_backup():
    """Test database restoration"""
```

### 2. Integration Tests
- Test S3 upload/download
- Test RDS connectivity
- Test full sync cycle

### 3. Disaster Recovery Drills
- Monthly backup restoration test
- Quarterly full DR simulation
- Document recovery times

## Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1 | Setup & S3 Backup | S3 bucket, basic backup service |
| 2 | Incremental Sync | Change tracking, incremental backups |
| 3 | Monitoring | CloudWatch, alerts, dashboards |
| 4 | Testing & Documentation | Full testing, runbooks |
| 5-6 | RDS Migration (Optional) | PostgreSQL setup, dual-write |
| 7-8 | Production Rollout | Gradual rollout, monitoring |

## Next Steps

1. **Immediate Actions**
   - [ ] Review and approve architecture
   - [ ] Create AWS account and configure IAM
   - [ ] Set up S3 bucket with versioning

2. **Development Tasks**
   - [ ] Implement BackupService class
   - [ ] Add Celery beat configuration
   - [ ] Create restore scripts
   - [ ] Write tests

3. **Documentation**
   - [ ] Create operational runbook
   - [ ] Document recovery procedures
   - [ ] Update system architecture docs

## Conclusion

This plan provides a phased approach to implementing AWS database synchronization, starting with simple S3 backups and potentially evolving to a full RDS deployment. The incremental approach minimizes risk while providing immediate backup benefits.

### Key Benefits
- **Data Durability**: Multiple backup copies in AWS
- **Disaster Recovery**: Quick restoration capabilities
- **Scalability Path**: Ready for multi-instance deployment
- **Cost-Effective**: Starting at ~$5/month
- **Monitoring**: Full visibility into sync health

### Recommended Starting Point
Begin with **Option B (S3 Only)** for immediate backup protection, then evaluate the need for RDS based on scaling requirements.