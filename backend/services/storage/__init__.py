import os
from .storage_backend import (
    StorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
)


def _init_storage_backend() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        bucket = os.getenv("R2_BUCKET_NAME")
        endpoint = os.getenv("R2_ENDPOINT_URL")
        access_key = os.getenv("R2_ACCESS_KEY_ID")
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        if not all([bucket, endpoint, access_key, secret_key]):
            raise ValueError("Missing R2 storage configuration environment variables")
        return S3StorageBackend(
            bucket_name=bucket,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
        )
    return LocalStorageBackend()


storage_backend: StorageBackend = _init_storage_backend()

__all__ = [
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "storage_backend",
]
