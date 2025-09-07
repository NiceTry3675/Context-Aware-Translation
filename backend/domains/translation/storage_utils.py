"""Storage utilities for translation job outputs."""

import os
import io
from typing import Optional, List
from pathlib import Path
import logging

from backend.domains.shared.storage import Storage

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
        
        # Save directly to logs/jobs directory (outside of storage abstraction)
        logs_output_dir = Path(f"logs/jobs/{job_id}/output")
        logs_output_dir.mkdir(parents=True, exist_ok=True)
        logs_output_path = logs_output_dir / f"{base_name}_translated.txt"
        
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
            legacy_dir = Path("translated_novel")
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
        
        # Save directly to logs/jobs directory
        segments_dir = Path(f"logs/jobs/{job_id}/output")
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
        if original_filename:
            base_name = Path(original_filename).stem
            job_path = Path(f"logs/jobs/{job_id}/output/{base_name}_translated.txt")
        else:
            job_path = Path(f"logs/jobs/{job_id}/output/translated.txt")
        
        try:
            if job_path.exists():
                with open(job_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to read from job directory: {e}")
        
        # Try legacy directory as fallback
        if original_filename:
            base_name = Path(original_filename).stem
            legacy_path = Path(f"translated_novel/{job_id}_{base_name}_translated.txt")
            try:
                if legacy_path.exists():
                    with open(legacy_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                logger.error(f"Failed to read from legacy directory: {e}")
        
        return None