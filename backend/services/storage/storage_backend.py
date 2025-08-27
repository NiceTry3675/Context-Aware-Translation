from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    def save(self, src_path: str, dest_path: str) -> str:
        """Save a local file to storage and return the storage path."""

    @abstractmethod
    def get(self, path: str) -> str:
        """Retrieve a file from storage to a local path and return the local path."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file exists in storage."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete a file from storage."""

    @abstractmethod
    def generate_presigned_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for downloading a file."""


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def save(self, src_path: str, dest_path: str) -> str:  # pragma: no cover - simple file ops
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        if src_path != dest_path:
            shutil.move(src_path, dest_path)
        return dest_path

    def get(self, path: str) -> str:  # pragma: no cover - simple file ops
        return path

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def delete(self, path: str) -> None:  # pragma: no cover - simple file ops
        if os.path.exists(path):
            os.remove(path)

    def generate_presigned_url(self, path: str, expires_in: int = 3600) -> Optional[str]:  # pragma: no cover - local usage
        return None


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend (e.g., Cloudflare R2)."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        import boto3

        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def save(self, src_path: str, dest_path: str) -> str:
        key = dest_path.replace("\\", "/")
        self.client.upload_file(src_path, self.bucket_name, key)
        if os.path.exists(src_path):
            os.remove(src_path)
        return key

    def get(self, path: str) -> str:
        local_path = path
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.client.download_file(self.bucket_name, path, local_path)
        return local_path

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=path)
        except Exception:
            pass

    def generate_presigned_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": path},
            ExpiresIn=expires_in,
        )
