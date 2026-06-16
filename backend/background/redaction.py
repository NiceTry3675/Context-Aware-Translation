"""Secret redaction helpers for persisted background task metadata."""

from __future__ import annotations

import hashlib
from typing import Any

_SENSITIVE_KEYS = {
    "api_key",
    "backup_api_keys",
    "provider_config",
    "credentials",
    "private_key",
    "service_account",
}


def stable_secret_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:12]


def redact_background_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in _SENSITIVE_KEYS:
                if key == "api_key" and isinstance(item, str) and item:
                    redacted[key] = {"redacted": True, "key_id": stable_secret_id(item)}
                    continue
                if key == "backup_api_keys" and isinstance(item, list):
                    redacted[key] = {
                        "redacted": True,
                        "key_ids": [
                            stable_secret_id(v)
                            for v in item
                            if isinstance(v, str) and v
                        ],
                    }
                    continue
                if key == "credentials" and isinstance(item, dict):
                    safe = {
                        safe_key: item[safe_key]
                        for safe_key in ("project_id", "client_email", "type")
                        if isinstance(item.get(safe_key), str)
                    }
                    safe["redacted"] = True
                    redacted[key] = safe
                    continue
                redacted[key] = {"redacted": True}
                continue
            redacted[key] = redact_background_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_background_payload(item) for item in value]
    return value
