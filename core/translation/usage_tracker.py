"""Utilities for collecting token usage during translation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class UsageEvent:
    """Represents a single model invocation's token usage."""

    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    timestamp: Optional[datetime] = None

    def normalized(self) -> "UsageEvent":
        """Return a copy with guaranteed non-negative integer values."""
        prompt = int(self.prompt_tokens or 0)
        completion = int(self.completion_tokens or 0)
        total = int(self.total_tokens or (prompt + completion))
        return UsageEvent(
            model_name=self.model_name,
            prompt_tokens=max(prompt, 0),
            completion_tokens=max(completion, 0),
            total_tokens=max(total, 0),
            timestamp=self.timestamp,
        )


class TokenUsageCollector:
    """Accumulates token usage events emitted by model wrappers."""

    def __init__(self) -> None:
        self._events: List[UsageEvent] = []

    def record_event(self, event: UsageEvent) -> None:
        """Store a usage event if it contains meaningful data."""
        if not isinstance(event, UsageEvent):
            return
        normalized = event.normalized()
        # Ignore events that report no tokens at all
        if (
            normalized.prompt_tokens == 0
            and normalized.completion_tokens == 0
            and normalized.total_tokens == 0
        ):
            # Still record to keep call count? We keep it for traceability.
            self._events.append(normalized)
            return
        self._events.append(normalized)

    def events(self) -> List[UsageEvent]:
        """Return a copy of recorded events."""
        return list(self._events)

    def clear(self) -> None:
        """Remove all recorded events."""
        self._events.clear()
