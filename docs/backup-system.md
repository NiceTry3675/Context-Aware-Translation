# Database Backup System

AWS S3-based backup system for SQLite database with automated daily backups and manual trigger support.

## Features

- **Automated Daily Backups**: Scheduled via Celery Beat
- **Manual Backup Trigger**: On-demand backup script
- **Compression**: Gzip compression for efficient storage
- **Retention Policy**: Automatic cleanup of old backups
- **Restoration**: Easy database restoration from any backup
- **Dry-Run Mode**: Works without AWS credentials for testing

## Setup

### 1. AWS Configuration

Add the following to your `.env` file:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# S3 Backup Configuration
S3_BACKUP_BUCKET=translation-system-backups
BACKUP_RETENTION_DAYS=30

# Database Path
DATABASE_PATH=database.db
```

### 2. Create S3 Bucket

```bash
# Using AWS CLI
aws s3 mb s3://translation-system-backups --region us-east-1

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
  --bucket translation-system-backups \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket translation-system-backups \
  --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
```

### 3. IAM Policy

Create an IAM user with the following policy:

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
    }
  ]
}
```

## Usage

### Manual Backup

```bash
# Run backup immediately
python scripts/backup_database.py

# Run backup via Celery (async)
python scripts/backup_database.py --async-mode

# List available backups
python scripts/backup_database.py --list

# Restore latest backup
python scripts/backup_database.py --restore

# Restore specific backup
python scripts/backup_database.py --restore backups/full/20240113_120000/database.db.gz
```

### Automated Daily Backup

The system automatically backs up once daily via Celery Beat:

```bash
# Start Celery worker
celery -A backend.celery_app worker --loglevel=info

# Start Celery beat scheduler (in separate terminal)
celery -A backend.celery_app beat --loglevel=info
```

The backup runs every 24 hours and includes:
1. Full database backup with compression
2. Upload to S3 with metadata
3. Cleanup of backups older than retention period
4. Verification of backup integrity

### Monitor Backup Status

```python
# Via Celery task
from backend.celery_tasks.backup_tasks import backup_database_to_s3

# Trigger manually
result = backup_database_to_s3.delay()
print(f"Task ID: {result.id}")

# Check status
task_status = result.get(timeout=300)
```

## Backup Structure

### S3 Organization

```
s3://translation-system-backups/
├── backups/
│   └── full/
│       ├── 20240113_120000/
│       │   └── database.db.gz
│       ├── 20240114_120000/
│       │   └── database.db.gz
│       └── ...
```

### Metadata

Each backup includes metadata:
- `timestamp`: Backup creation time
- `original-size`: Uncompressed database size
- `compressed-size`: Compressed backup size
- `backup-type`: "full" (incremental planned for future)
- `database-path`: Source database path

## Restoration

### Restore Latest Backup

```bash
python scripts/backup_database.py --restore
```

This will:
1. Download the latest backup from S3
2. Decompress the backup
3. Create a backup of current database
4. Replace current database with restored version

### Restore Specific Backup

```bash
# List available backups
python scripts/backup_database.py --list

# Restore specific backup
python scripts/backup_database.py --restore backups/full/20240113_120000/database.db.gz
```

### Programmatic Restoration

```python
from backend.services.aws_backup_service import AWSBackupService

service = AWSBackupService()

# Restore latest
result = service.restore_from_s3()

# Restore specific backup
result = service.restore_from_s3(
    backup_key="backups/full/20240113_120000/database.db.gz"
)

# Restore to different location
result = service.restore_from_s3(
    restore_path="/tmp/restored_database.db"
)
```

## Monitoring

### Backup Statistics

The backup process logs detailed statistics:

```
Backup statistics:
  - Original size: 978,432 bytes
  - Compressed size: 145,234 bytes
  - Compression ratio: 85.2%
  - Tables: 10
  - Total records: 1,543
```

### Celery Monitoring

Monitor backup tasks via Flower:

```bash
celery -A backend.celery_app flower
# Open http://localhost:5555
```

### Logs

Check logs for backup status:

```bash
# Celery worker logs
tail -f celery.log | grep backup

# Application logs
grep "backup" app.log
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   - Verify `.env` file contains AWS keys
   - Check IAM user has correct permissions
   - System works in dry-run mode without credentials

2. **S3 Bucket Access Denied**
   - Verify bucket name in configuration
   - Check IAM policy includes bucket ARN
   - Ensure bucket exists in correct region

3. **Backup Task Not Running**
   - Ensure Celery Beat is running
   - Check Redis is available
   - Verify task is registered in Celery

4. **Restoration Fails**
   - Check backup file exists in S3
   - Verify AWS credentials have GetObject permission
   - Ensure sufficient disk space for restoration

### Manual Recovery

If automated restoration fails:

```bash
# Download backup manually
aws s3 cp s3://translation-system-backups/backups/full/latest/database.db.gz ./backup.db.gz

# Decompress
gunzip backup.db.gz

# Replace database
cp database.db database.db.backup
mv backup.db database.db
```

## Performance

### Backup Metrics

- **Compression**: ~85% reduction in size
- **Upload Speed**: Depends on network, typically 1-5 MB/s
- **Backup Duration**: ~5-30 seconds for typical database
- **Storage Cost**: ~$0.023 per GB/month on S3

### Optimization Tips

1. **Adjust Retention Period**: Reduce `BACKUP_RETENTION_DAYS` to save storage
2. **Schedule During Low Usage**: Change backup time in Celery Beat
3. **Use S3 Lifecycle Rules**: Move old backups to Glacier for cost savings
4. **Enable S3 Transfer Acceleration**: For faster uploads from distant regions

## Security

### Best Practices

1. **Encryption**: All backups are encrypted at rest (AES-256)
2. **Access Control**: Use IAM roles instead of keys when possible
3. **Versioning**: Enable S3 versioning for additional protection
4. **MFA Delete**: Enable for production buckets
5. **Audit Logging**: Enable CloudTrail for S3 access logging

### Sensitive Data

- Database may contain user data and API keys
- Ensure S3 bucket is private (no public access)
- Consider additional encryption for sensitive fields
- Regularly audit access logs

## Future Enhancements

- [ ] Incremental backups for efficiency
- [ ] Cross-region replication
- [ ] PostgreSQL/MySQL support
- [ ] Backup verification tests
- [ ] CloudWatch alarms for failures
- [ ] Backup encryption with customer keys
- [ ] Point-in-time recovery
- [ ] Automated disaster recovery testing