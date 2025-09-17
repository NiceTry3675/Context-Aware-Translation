"""
Cache Manager for Illustration Generation

Handles caching of generated illustrations to avoid redundant API calls.
"""
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any


class IllustrationCacheManager:
    """Manages caching for generated illustrations."""

    def __init__(self, output_dir: Path, enable_caching: bool = True):
        """
        Initialize the cache manager.

        Args:
            output_dir: Directory to store cache metadata
            enable_caching: Whether to enable caching
        """
        self.output_dir = output_dir
        self.enable_caching = enable_caching
        self.cache: Dict[str, Any] = {} if enable_caching else None
        self._load_cache_metadata()

    def _load_cache_metadata(self):
        """Load existing cache metadata from disk if available."""
        if not self.enable_caching:
            return

        cache_file = self.output_dir / "cache_metadata.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logging.info(f"Loaded {len(self.cache)} cached entries")
            except Exception as e:
                logging.warning(f"Failed to load cache metadata: {e}")
                self.cache = {}

    def save_cache_metadata(self):
        """Save cache metadata to disk."""
        if not self.enable_caching or not self.cache:
            return

        cache_file = self.output_dir / "cache_metadata.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logging.debug(f"Saved cache metadata with {len(self.cache)} entries")
        except Exception as e:
            logging.warning(f"Failed to save cache metadata: {e}")

    def get_cache_key(self, text: str, style_hints: str = "", extra: str = "") -> str:
        """
        Generate a cache key for the given text and style hints.

        Args:
            text: The source text
            style_hints: Optional style hints
            extra: Additional data to include in key (e.g., reference image hash)

        Returns:
            MD5 hash as cache key
        """
        combined = f"{text}|||{style_hints}|||{extra}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get_cached_illustration(self, cache_key: str) -> Optional[tuple[str, str]]:
        """
        Retrieve cached illustration if it exists.

        Args:
            cache_key: The cache key to look up

        Returns:
            Tuple of (image_path, prompt) if cached and file exists, None otherwise
        """
        if not self.enable_caching or cache_key not in self.cache:
            return None

        cached_data = self.cache[cache_key]
        cached_path = cached_data['path']
        cached_prompt = cached_data['prompt']

        if Path(cached_path).exists():
            logging.info(f"Found cached illustration: {cached_path}")
            return cached_path, cached_prompt
        else:
            # Remove invalid cache entry
            del self.cache[cache_key]
            return None

    def add_to_cache(self, cache_key: str, image_path: str, prompt: str, segment_index: int):
        """
        Add a generated illustration to the cache.

        Args:
            cache_key: The cache key
            image_path: Path to the generated image
            prompt: The prompt used to generate the image
            segment_index: Index of the segment
        """
        if not self.enable_caching or not cache_key:
            return

        self.cache[cache_key] = {
            'path': str(image_path),
            'prompt': prompt,
            'segment_index': segment_index
        }
        self.save_cache_metadata()

    def clear_cache(self):
        """Clear all cache entries."""
        if self.enable_caching:
            self.cache = {}
            self.save_cache_metadata()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enable_caching:
            return {'enabled': False}

        return {
            'enabled': True,
            'total_entries': len(self.cache),
            'valid_entries': sum(1 for entry in self.cache.values()
                               if Path(entry['path']).exists())
        }