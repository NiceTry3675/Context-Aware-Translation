"""Shared world atmosphere analysis provider.

This module exposes a small helper that ensures world/atmosphere analysis is
available for both the translation pipeline and asynchronous illustration
workers. The provider abstracts common logic around reusing cached analysis
results and invoking ``DynamicConfigBuilder.analyze_world_atmosphere`` when the
analysis has not been computed yet.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple

from pydantic import ValidationError

from core.config.builder import DynamicConfigBuilder
from core.schemas.narrative_style import WorldAtmosphereAnalysis


class WorldAtmosphereProvider:
    """Provide world/atmosphere analysis for segments on demand."""

    def __init__(self, dyn_config_builder: Optional[DynamicConfigBuilder]):
        self._dyn_config_builder = dyn_config_builder

    @staticmethod
    def _extract_world_atmosphere(segment_info: Any) -> Optional[Any]:
        """Return raw world/atmosphere data from a segment container."""
        if segment_info is None:
            return None

        if isinstance(segment_info, dict):
            return segment_info.get("world_atmosphere")

        return getattr(segment_info, "world_atmosphere", None)

    @staticmethod
    def _store_world_atmosphere(segment_info: Any, value: Dict[str, Any]) -> None:
        """Persist world/atmosphere data back onto the segment container."""
        if segment_info is None:
            return

        if isinstance(segment_info, dict):
            segment_info["world_atmosphere"] = value
            return

        try:
            setattr(segment_info, "world_atmosphere", value)
        except Exception:
            # Best-effort storage; the caller can still use the returned dict
            pass

    @staticmethod
    def _normalize_world_atmosphere(raw_value: Any) -> Optional[WorldAtmosphereAnalysis]:
        """Convert stored raw data to ``WorldAtmosphereAnalysis`` if possible."""
        if raw_value is None:
            return None

        if isinstance(raw_value, WorldAtmosphereAnalysis):
            return raw_value

        if isinstance(raw_value, dict):
            try:
                return WorldAtmosphereAnalysis.model_validate(raw_value)
            except ValidationError:
                return None

        return None

    def ensure_world_atmosphere(
        self,
        segment_info: Any,
        glossary: Dict[str, str],
        previous_context: Optional[str],
        segment_index: Optional[int],
        job_base_filename: str,
    ) -> Optional[WorldAtmosphereAnalysis]:
        """Ensure world/atmosphere analysis is available for the given segment.

        When a cached analysis is found on the segment it is reused. Otherwise,
        ``DynamicConfigBuilder.analyze_world_atmosphere`` is invoked (when the
        provider was initialised with a builder). The resulting analysis is
        stored back on the ``segment_info`` container for downstream reuse.
        """

        existing = self._normalize_world_atmosphere(
            self._extract_world_atmosphere(segment_info)
        )
        if existing is not None:
            return existing

        if not self._dyn_config_builder:
            return None

        if isinstance(segment_info, dict):
            segment_text = (
                segment_info.get("source_text")
                or segment_info.get("text")
                or ""
            )
        else:
            segment_text = getattr(segment_info, "text", "") or ""

        analysis = self._dyn_config_builder.analyze_world_atmosphere(
            segment_text=segment_text,
            previous_context=previous_context,
            glossary=glossary,
            job_base_filename=job_base_filename,
            segment_index=segment_index,
        )

        if analysis is not None:
            self._store_world_atmosphere(segment_info, analysis.model_dump())

        return analysis

    def get_world_atmosphere_dict(self, segment_info: Any) -> Optional[Dict[str, Any]]:
        """Return world/atmosphere data in dictionary form if available."""
        raw_value = self._extract_world_atmosphere(segment_info)

        if isinstance(raw_value, dict):
            return raw_value

        if isinstance(raw_value, WorldAtmosphereAnalysis):
            return raw_value.model_dump()

        normalized = self._normalize_world_atmosphere(raw_value)
        if normalized is None:
            return None
        return normalized.model_dump()


__all__ = ["WorldAtmosphereProvider", "extract_world_atmosphere_dict", "ensure_world_atmosphere_data"]


def extract_world_atmosphere_dict(segment: Any) -> Optional[Dict[str, Any]]:
    """Return world/atmosphere data from a segment as a dictionary."""

    if segment is None:
        return None

    if isinstance(segment, dict):
        raw_value = segment.get("world_atmosphere")
    else:
        raw_value = getattr(segment, "world_atmosphere", None)

    if isinstance(raw_value, dict):
        return raw_value

    if isinstance(raw_value, WorldAtmosphereAnalysis):
        return raw_value.model_dump()

    return None


def ensure_world_atmosphere_data(
    provider: Optional[WorldAtmosphereProvider],
    segments: List[Any],
    target_index: int,
    glossary: Dict[str, str],
    job_base_filename: str,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Ensure world/atmosphere data exists for a segment within a list."""

    if not (0 <= target_index < len(segments)):
        return None, False

    segment_entry = segments[target_index]
    existing = extract_world_atmosphere_dict(segment_entry)
    if existing:
        return existing, False

    if provider is None:
        return None, False

    previous_context: Optional[str] = None
    if target_index > 0:
        prev_segment = segments[target_index - 1]
        if isinstance(prev_segment, dict):
            previous_context = prev_segment.get('source_text') or prev_segment.get('text') or None
        else:
            previous_context = getattr(prev_segment, 'text', None)

    if isinstance(segment_entry, dict):
        segment_position = segment_entry.get('segment_index')
    else:
        segment_position = getattr(segment_entry, 'segment_index', None)

    if segment_position is None:
        segment_position = target_index + 1

    analysis = provider.ensure_world_atmosphere(
        segment_info=segment_entry,
        glossary=glossary,
        previous_context=previous_context,
        segment_index=segment_position,
        job_base_filename=job_base_filename,
    )

    if analysis is None:
        return None, False

    dict_value = provider.get_world_atmosphere_dict(segment_entry)
    if isinstance(segment_entry, dict) and dict_value is not None:
        segment_entry['world_atmosphere'] = dict_value
        if 'segment_summary' not in segment_entry and 'segment_summary' in dict_value:
            segment_entry['segment_summary'] = dict_value.get('segment_summary')

    return dict_value, True
