"""AWS S3 Service for Celery Task Output Persistence

This service handles:
- Uploading task outputs from logs/jobs/{job_id} to S3
- Preserving directory structure in S3
- Automatic sync when tasks complete
- Optional compression for large files
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import mimetypes
import gzip
import tempfile

logger = logging.getLogger(__name__)


class AWSTaskOutputService:
    """Service for persisting Celery task outputs to AWS S3"""

    def __init__(self):
        """Initialize AWS S3 client and configuration"""
        self.s3_client = None
        self.bucket = os.getenv('S3_TASK_OUTPUT_BUCKET', os.getenv('S3_BUCKET', 'translation-system-outputs'))
        self.aws_region = os.getenv('S3_REGION', 'us-east-1')
        self.enabled = os.getenv('S3_TASK_PERSISTENCE_ENABLED', 'false').lower() == 'true'
        self.compress_threshold = int(os.getenv('S3_COMPRESS_THRESHOLD_MB', '10')) * 1024 * 1024  # Convert to bytes

        # Initialize S3 client only if enabled and credentials are configured
        if self.enabled and self._has_aws_credentials():
            try:
                import boto3
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.aws_region,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                # Verify bucket exists
                self.s3_client.head_bucket(Bucket=self.bucket)
                logger.info(f"AWS Task Output Service initialized with bucket: {self.bucket}")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}. Task output persistence disabled.")
                self.enabled = False
        elif self.enabled:
            logger.warning("S3 task persistence enabled but AWS credentials not configured")
            self.enabled = False

    def _has_aws_credentials(self) -> bool:
        """Check if AWS credentials are configured"""
        return bool(
            os.getenv('AWS_ACCESS_KEY_ID') and
            os.getenv('AWS_SECRET_ACCESS_KEY')
        )

    def persist_job_outputs(self, job_id: int, task_id: str, task_name: str) -> Dict[str, Any]:
        """
        Persist all outputs for a job to S3

        Args:
            job_id: Translation job ID
            task_id: Celery task ID
            task_name: Celery task name

        Returns:
            Dict with persistence results
        """
        if not self.enabled or not self.s3_client:
            return {
                'success': False,
                'reason': 'S3 persistence not enabled or configured'
            }

        results = {
            'timestamp': datetime.now().isoformat(),
            'job_id': job_id,
            'task_id': task_id,
            'task_name': task_name,
            'success': False,
            'uploaded_files': [],
            'errors': []
        }

        try:
            # Get the job output directory
            job_dir = Path(f"logs/jobs/{job_id}")

            if not job_dir.exists():
                logger.debug(f"No output directory found for job {job_id}")
                return {
                    'success': False,
                    'reason': f'No output directory at {job_dir}'
                }

            # Upload all files in the job directory
            uploaded_count = 0
            total_size = 0

            for file_path in job_dir.rglob('*'):
                if file_path.is_file():
                    try:
                        # Calculate S3 key preserving directory structure
                        relative_path = file_path.relative_to(job_dir)
                        s3_key = f"task-outputs/jobs/{job_id}/{relative_path}"

                        # Upload file
                        upload_result = self._upload_file(file_path, s3_key)

                        if upload_result['success']:
                            uploaded_count += 1
                            total_size += upload_result.get('size', 0)
                            results['uploaded_files'].append({
                                'local_path': str(file_path),
                                's3_key': s3_key,
                                'size': upload_result.get('size', 0),
                                'compressed': upload_result.get('compressed', False)
                            })
                        else:
                            results['errors'].append(upload_result.get('error', 'Unknown error'))

                    except Exception as e:
                        error_msg = f"Failed to upload {file_path}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)

            results['success'] = uploaded_count > 0
            results['uploaded_count'] = uploaded_count
            results['total_size'] = total_size

            if uploaded_count > 0:
                logger.info(f"Persisted {uploaded_count} files ({total_size:,} bytes) to S3 for job {job_id}")

        except Exception as e:
            logger.error(f"Failed to persist job outputs: {e}")
            results['error'] = str(e)

        return results

    def _upload_file(self, file_path: Path, s3_key: str) -> Dict[str, Any]:
        """
        Upload a single file to S3, with optional compression

        Args:
            file_path: Local file path
            s3_key: S3 object key

        Returns:
            Dict with upload result
        """
        try:
            file_size = file_path.stat().st_size
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or 'application/octet-stream'

            # Prepare metadata
            metadata = {
                'original-filename': file_path.name,
                'upload-timestamp': datetime.now().isoformat(),
                'original-size': str(file_size)
            }

            # Determine if we should compress
            should_compress = (
                file_size > self.compress_threshold and
                file_path.suffix not in ['.gz', '.zip', '.jpg', '.jpeg', '.png', '.mp4', '.avi']
            )

            upload_path = file_path
            actual_s3_key = s3_key

            if should_compress:
                # Compress file to temp location
                with tempfile.NamedTemporaryFile(suffix='.gz', delete=False) as temp_file:
                    with open(file_path, 'rb') as f_in:
                        with gzip.open(temp_file.name, 'wb', compresslevel=6) as f_out:
                            f_out.write(f_in.read())

                    upload_path = Path(temp_file.name)
                    actual_s3_key = f"{s3_key}.gz"
                    metadata['compressed'] = 'true'
                    metadata['compression'] = 'gzip'
                    compressed_size = upload_path.stat().st_size
                    metadata['compressed-size'] = str(compressed_size)

                    logger.debug(f"Compressed {file_path.name}: {file_size:,} -> {compressed_size:,} bytes")

            # Upload to S3
            extra_args = {
                'Metadata': metadata,
                'ContentType': content_type
            }

            # Add server-side encryption if specified
            if os.getenv('S3_SERVER_SIDE_ENCRYPTION'):
                extra_args['ServerSideEncryption'] = 'AES256'

            self.s3_client.upload_file(
                str(upload_path),
                self.bucket,
                actual_s3_key,
                ExtraArgs=extra_args
            )

            # Clean up temp file if compressed
            if should_compress and upload_path != file_path:
                upload_path.unlink()

            return {
                'success': True,
                'size': file_size,
                'compressed': should_compress,
                's3_key': actual_s3_key
            }

        except Exception as e:
            logger.error(f"Failed to upload {file_path} to S3: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def persist_task_output(self, task_id: str, task_name: str, output_data: Any) -> Dict[str, Any]:
        """
        Persist a specific task output (JSON serializable data) to S3

        Args:
            task_id: Celery task ID
            task_name: Task name
            output_data: Task output data (must be JSON serializable)

        Returns:
            Dict with persistence result
        """
        if not self.enabled or not self.s3_client:
            return {
                'success': False,
                'reason': 'S3 persistence not enabled or configured'
            }

        try:
            # Create S3 key for task output
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"task-outputs/tasks/{task_name}/{timestamp}_{task_id}.json"

            # Serialize output data
            output_json = json.dumps(output_data, ensure_ascii=False, indent=2, default=str)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=output_json.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'task-id': task_id,
                    'task-name': task_name,
                    'timestamp': timestamp
                }
            )

            logger.debug(f"Persisted task output to S3: {s3_key}")

            return {
                'success': True,
                's3_key': s3_key,
                'size': len(output_json)
            }

        except Exception as e:
            logger.error(f"Failed to persist task output: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_job_outputs_url(self, job_id: int, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for accessing job outputs

        Args:
            job_id: Job ID
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL or None
        """
        if not self.enabled or not self.s3_client:
            return None

        try:
            # Generate presigned URL for the job directory listing
            url = self.s3_client.generate_presigned_url(
                'list_objects_v2',
                Params={
                    'Bucket': self.bucket,
                    'Prefix': f'task-outputs/jobs/{job_id}/'
                },
                ExpiresIn=expires_in
            )
            return url

        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

# Global instance for easy access
_service_instance = None

def get_task_output_service() -> AWSTaskOutputService:
    """Get or create the task output service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = AWSTaskOutputService()
    return _service_instance