"""
Storage dependency injection for FastAPI.
"""
from typing import Generator
from fastapi import Depends

from .settings import Settings, get_settings
from ..domains.shared.storage import Storage, create_storage

# Cache storage instance
_storage_instance = None


def get_storage(settings: Settings = Depends(get_settings)) -> Storage:
    """
    Get storage instance with dependency injection.
    Uses singleton pattern to avoid recreating storage instances.
    """
    global _storage_instance
    
    if _storage_instance is None:
        _storage_instance = create_storage(settings)
    
    return _storage_instance


# Convenience dependency for direct use in endpoints
StorageDep = Depends(get_storage)