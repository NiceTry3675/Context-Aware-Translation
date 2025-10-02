"""
Storage adapter for injecting backend storage into core components.

This module provides adapter functions that can be injected into core
components to enable storage operations without creating circular dependencies.
"""

import asyncio
from typing import List, Optional

from backend.config.settings import get_settings
from backend.domains.shared.storage import create_storage
from backend.domains.translation.storage_utils import TranslationStorageManager


def create_storage_handler():
    """
    Create a storage handler function that can be injected into core components.
    
    Returns:
        A callable that handles storage operations synchronously
    """
    def storage_handler(job_id: int, content: str, original_filename: str) -> Optional[List[str]]:
        """
        Save content to storage using backend infrastructure.
        
        Args:
            job_id: Job ID for the translation
            content: Content to save
            original_filename: Original filename
            
        Returns:
            List of saved paths, or None if save failed
        """
        try:
            # Get settings and create storage
            settings = get_settings()
            storage = create_storage(settings)
            manager = TranslationStorageManager(storage)
            
            # Run async save in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                saved_paths = loop.run_until_complete(
                    manager.save_translation_output(
                        job_id=job_id,
                        content=content,
                        original_filename=original_filename,
                        save_to_legacy=True
                    )
                )
                return saved_paths
            finally:
                loop.close()
        except Exception as e:
            print(f"Storage handler error: {e}")
            return None
    
    return storage_handler