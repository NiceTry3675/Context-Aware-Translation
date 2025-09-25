"""Storage utilities for translation job outputs."""

import os
import io
from typing import Optional, List
from pathlib import Path
import logging

from backend.domains.shared.storage import Storage
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class TranslationStorageManager:
    """Manages storage of translation outputs using the storage abstraction."""
    
    def __init__(self, storage: Storage):
        """
        Initialize with a storage backend.
        
        Args:
            storage: Storage implementation (local, S3, etc.)
        """
        self.storage = storage
    
    async def save_translation_output(
        self,
        job_id: int,
        content: str,
        original_filename: str,
        save_to_legacy: bool = True
    ) -> List[str]:
        """
        Save translation output to storage.
        
        Args:
            job_id: Job ID
            content: Translation content to save
            original_filename: Original filename
            save_to_legacy: Whether to also save to legacy translated_novel/ directory
            
        Returns:
            List of paths where the file was saved
        """
        saved_paths = []
        
        # Prepare content as bytes
        content_bytes = content.encode('utf-8')
        
        # Determine base filename
        base_name = Path(original_filename).stem
        
        # Save directly to job storage base directory (outside of storage abstraction)
        base_dir = Path(get_settings().job_storage_base)
        logs_output_dir = base_dir / str(job_id) / "output"
        logs_output_dir.mkdir(parents=True, exist_ok=True)
        logs_output_path = logs_output_dir / "translated.txt"
        
        try:
            # Save directly to logs/jobs directory
            with open(logs_output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            saved_paths.append(str(logs_output_path))
            logger.info(f"Saved translation output to: {logs_output_path}")
        except Exception as e:
            logger.error(f"Failed to save to logs directory: {e}")
        
        # Save to legacy directory if requested
        if save_to_legacy:
            legacy_dir = Path(get_settings().legacy_translated_dir)
            legacy_dir.mkdir(parents=True, exist_ok=True)
            legacy_path = legacy_dir / f"{job_id}_{base_name}_translated.txt"
            try:
                with open(legacy_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_paths.append(str(legacy_path))
                logger.info(f"Saved translation output to legacy path: {legacy_path}")
            except Exception as e:
                logger.error(f"Failed to save to legacy directory: {e}")
        
        return saved_paths
    
    async def save_segments(
        self,
        job_id: int,
        segments: List[dict]
    ) -> Optional[str]:
        """
        Save translation segments as JSON for frontend display.
        
        Args:
            job_id: Job ID
            segments: List of segment dictionaries
            
        Returns:
            Path where segments were saved, or None if failed
        """
        import json
        
        # Save directly to job storage base directory
        base_dir = Path(get_settings().job_storage_base)
        segments_dir = base_dir / str(job_id) / "output"
        segments_dir.mkdir(parents=True, exist_ok=True)
        segments_path = segments_dir / "segments.json"
        
        try:
            content = json.dumps(segments, ensure_ascii=False, indent=2)
            with open(segments_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Saved translation segments to: {segments_path}")
            return str(segments_path)
        except Exception as e:
            logger.error(f"Failed to save segments: {e}")
            return None
    
    async def read_translation_output(
        self,
        job_id: int,
        original_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Read translation output from storage.
        
        Args:
            job_id: Job ID
            original_filename: Original filename (optional)
            
        Returns:
            Translation content as string, or None if not found
        """
        # Try job-specific directory first
        base_dir = Path(get_settings().job_storage_base)
        job_path = base_dir / str(job_id) / "output" / "translated.txt"
        
        try:
            if job_path.exists():
                with open(job_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to read from job directory: {e}")
        
        # Try legacy directory as fallback
        if original_filename:
            base_name = Path(original_filename).stem
            legacy_dir = Path(get_settings().legacy_translated_dir)
            legacy_path = legacy_dir / f"{job_id}_{base_name}_translated.txt"
            try:
                if legacy_path.exists():
                    with open(legacy_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                logger.error(f"Failed to read from legacy directory: {e}")

        return None

    def read_partial_segments(self, job_id: int) -> Optional[List[str]]:
        """Read partial translated segments stored for resume support."""
        import json

        base_dir = Path(get_settings().job_storage_base)
        cache_path = base_dir / str(job_id) / "output" / "partial_segments.json"
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as cache_file:
                data = json.load(cache_file)
                if isinstance(data, list):
                    return [str(segment) for segment in data]
        except Exception as exc:
            logger.error(f"Failed to read partial segments for job {job_id}: {exc}")

        return None
