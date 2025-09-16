"""
Storage abstraction layer for file operations.
Supports local filesystem and cloud storage providers.
"""
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, List, AsyncGenerator
from pathlib import Path
import os
import shutil
import hashlib
import mimetypes
import aiofiles
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StorageException(Exception):
    """Base exception for storage operations."""
    pass


class FileNotFoundException(StorageException):
    """Exception raised when a file is not found."""
    pass


class StoragePermissionError(StorageException):
    """Exception raised for permission-related errors."""
    pass


class StorageQuotaExceeded(StorageException):
    """Exception raised when storage quota is exceeded."""
    pass


class StorageMetadata:
    """Metadata for stored files."""
    
    def __init__(
        self,
        path: str,
        size: int,
        content_type: Optional[str] = None,
        created_at: Optional[datetime] = None,
        modified_at: Optional[datetime] = None,
        etag: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        self.path = path
        self.size = size
        self.content_type = content_type or "application/octet-stream"
        self.created_at = created_at or datetime.utcnow()
        self.modified_at = modified_at or datetime.utcnow()
        self.etag = etag
        self.metadata = metadata or {}


class Storage(ABC):
    """Abstract storage interface."""
    
    @abstractmethod
    async def save_file(
        self,
        path: str,
        file: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> StorageMetadata:
        """Save a file to storage."""
        pass
    
    @abstractmethod
    async def open_file(self, path: str) -> AsyncGenerator[bytes, None]:
        """Open a file from storage as an async generator."""
        pass
    
    @abstractmethod
    async def read_file(self, path: str) -> bytes:
        """Read entire file content."""
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file from storage."""
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    async def get_metadata(self, path: str) -> StorageMetadata:
        """Get file metadata."""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = False
    ) -> List[StorageMetadata]:
        """List files in storage."""
        pass
    
    @abstractmethod
    async def copy_file(self, source: str, destination: str) -> StorageMetadata:
        """Copy a file within storage."""
        pass
    
    @abstractmethod
    async def move_file(self, source: str, destination: str) -> StorageMetadata:
        """Move a file within storage."""
        pass
    
    @abstractmethod
    async def get_presigned_url(
        self,
        path: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> str:
        """Get a presigned URL for direct access."""
        pass


class LocalStorage(Storage):
    """Local filesystem storage implementation."""
    
    def __init__(self, base_path: str, max_file_size: int = 100_000_000):
        """
        Initialize local storage.
        
        Args:
            base_path: Base directory for file storage
            max_file_size: Maximum allowed file size in bytes
        """
        self.base_path = Path(base_path)
        self.max_file_size = max_file_size
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized LocalStorage at {self.base_path}")
    
    def _get_full_path(self, path: str) -> Path:
        """Get full path with security checks."""
        # Remove any leading slashes to prevent absolute paths
        clean_path = path.lstrip("/")
        
        # Resolve the full path
        full_path = (self.base_path / clean_path).resolve()
        
        # Security check: ensure path is within base directory
        if not str(full_path).startswith(str(self.base_path.resolve())):
            raise StoragePermissionError(
                f"Path traversal detected: {path}"
            )
        
        return full_path
    
    def _calculate_etag(self, content: bytes) -> str:
        """Calculate ETag for content."""
        return hashlib.md5(content).hexdigest()
    
    async def save_file(
        self,
        path: str,
        file: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> StorageMetadata:
        """Save a file to local storage."""
        full_path = self._get_full_path(path)
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read file content
        content = file.read()
        
        # Check file size
        size = len(content)
        if size > self.max_file_size:
            raise StorageQuotaExceeded(
                f"File size {size} exceeds maximum {self.max_file_size}"
            )
        
        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(full_path))
            content_type = content_type or "application/octet-stream"
        
        # Write file
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
        
        # Calculate ETag
        etag = self._calculate_etag(content)
        
        # Get file stats
        stat = full_path.stat()
        
        logger.debug(f"Saved file: {path} ({size} bytes)")
        
        return StorageMetadata(
            path=path,
            size=size,
            content_type=content_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            etag=etag,
            metadata=metadata
        )
    
    async def open_file(self, path: str) -> AsyncGenerator[bytes, None]:
        """Open a file as an async generator."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise FileNotFoundException(f"File not found: {path}")
        
        async with aiofiles.open(full_path, "rb") as f:
            chunk_size = 8192
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    async def read_file(self, path: str) -> bytes:
        """Read entire file content."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise FileNotFoundException(f"File not found: {path}")
        
        async with aiofiles.open(full_path, "rb") as f:
            content = await f.read()
        
        logger.debug(f"Read file: {path} ({len(content)} bytes)")
        return content
    
    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            return False
        
        try:
            full_path.unlink()
            logger.debug(f"Deleted file: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            raise StorageException(f"Failed to delete file: {e}")
    
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        full_path = self._get_full_path(path)
        return full_path.exists() and full_path.is_file()
    
    async def get_metadata(self, path: str) -> StorageMetadata:
        """Get file metadata."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise FileNotFoundException(f"File not found: {path}")
        
        stat = full_path.stat()
        
        # Detect content type
        content_type, _ = mimetypes.guess_type(str(full_path))
        content_type = content_type or "application/octet-stream"
        
        return StorageMetadata(
            path=path,
            size=stat.st_size,
            content_type=content_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            etag=None  # Would need to read file to calculate
        )
    
    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = False
    ) -> List[StorageMetadata]:
        """List files with optional prefix filter."""
        base_dir = self._get_full_path(prefix) if prefix else self.base_path
        
        if not base_dir.exists():
            return []
        
        files = []
        
        if recursive:
            # Recursive listing
            for root, _, filenames in os.walk(base_dir):
                root_path = Path(root)
                for filename in filenames:
                    file_path = root_path / filename
                    relative_path = file_path.relative_to(self.base_path)
                    
                    try:
                        metadata = await self.get_metadata(str(relative_path))
                        files.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to get metadata for {relative_path}: {e}")
        else:
            # Non-recursive listing
            if base_dir.is_dir():
                for item in base_dir.iterdir():
                    if item.is_file():
                        relative_path = item.relative_to(self.base_path)
                        try:
                            metadata = await self.get_metadata(str(relative_path))
                            files.append(metadata)
                        except Exception as e:
                            logger.warning(f"Failed to get metadata for {relative_path}: {e}")
        
        return files
    
    async def copy_file(self, source: str, destination: str) -> StorageMetadata:
        """Copy a file."""
        source_path = self._get_full_path(source)
        dest_path = self._get_full_path(destination)
        
        if not source_path.exists():
            raise FileNotFoundException(f"Source file not found: {source}")
        
        # Create destination directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(source_path, dest_path)
        
        logger.debug(f"Copied file: {source} -> {destination}")
        
        return await self.get_metadata(destination)
    
    async def move_file(self, source: str, destination: str) -> StorageMetadata:
        """Move a file."""
        source_path = self._get_full_path(source)
        dest_path = self._get_full_path(destination)
        
        if not source_path.exists():
            raise FileNotFoundException(f"Source file not found: {source}")
        
        # Create destination directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(source_path), str(dest_path))
        
        logger.debug(f"Moved file: {source} -> {destination}")
        
        return await self.get_metadata(destination)
    
    async def get_presigned_url(
        self,
        path: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Get a presigned URL for local storage.
        For local storage, this returns a file:// URL.
        In production, this would integrate with your web server.
        """
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise FileNotFoundException(f"File not found: {path}")
        
        # For local storage, return a file URL
        # In production, you'd generate a signed URL for your web server
        return f"file://{full_path}"


class S3Storage(Storage):
    """
    AWS S3 storage implementation.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        """Initialize S3 storage."""
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")

        self.bucket = bucket
        self.region = region

        # Create S3 client with optional credentials
        client_config = Config(
            region_name=region,
            signature_version='v4',
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )

        session_kwargs = {}
        if access_key and secret_key:
            session_kwargs = {
                'aws_access_key_id': access_key,
                'aws_secret_access_key': secret_key
            }

        session = boto3.Session(**session_kwargs)

        self.s3_client = session.client(
            's3',
            config=client_config,
            endpoint_url=endpoint_url
        )

        # Verify bucket exists
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except Exception as e:
            logger.warning(f"Could not verify S3 bucket {bucket}: {e}")

        logger.info(f"Initialized S3Storage with bucket {bucket} in region {region}")
    
    async def save_file(
        self,
        path: str,
        file: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> StorageMetadata:
        raise NotImplementedError()
    
    async def open_file(self, path: str) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError()
    
    async def read_file(self, path: str) -> bytes:
        raise NotImplementedError()
    
    async def delete_file(self, path: str) -> bool:
        raise NotImplementedError()
    
    async def exists(self, path: str) -> bool:
        raise NotImplementedError()
    
    async def get_metadata(self, path: str) -> StorageMetadata:
        raise NotImplementedError()
    
    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = False
    ) -> List[StorageMetadata]:
        raise NotImplementedError()
    
    async def copy_file(self, source: str, destination: str) -> StorageMetadata:
        raise NotImplementedError()
    
    async def move_file(self, source: str, destination: str) -> StorageMetadata:
        raise NotImplementedError()
    
    async def get_presigned_url(
        self,
        path: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> str:
        raise NotImplementedError()


def create_storage(settings) -> Storage:
    """
    Factory function to create storage instance based on settings.
    """
    if settings.storage_backend == "local":
        return LocalStorage(
            base_path=settings.upload_directory,
            max_file_size=settings.max_file_size
        )
    elif settings.storage_backend == "s3":
        if not all([settings.s3_bucket, settings.s3_access_key, settings.s3_secret_key]):
            raise ValueError("S3 storage requires bucket, access key, and secret key")
        
        return S3Storage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            endpoint_url=settings.s3_endpoint_url
        )
    else:
        raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")


def get_storage(settings) -> Storage:
    """
    Get storage instance based on settings.
    Alias for create_storage for consistency with naming conventions.
    """
    return create_storage(settings)