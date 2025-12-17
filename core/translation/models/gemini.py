import json
import hashlib
import os
import random
import threading
import time
from datetime import datetime
from typing import Callable, Optional, Tuple

from google import genai
from google.genai import errors as genai_errors
from shared.errors import ProhibitedException
from ...utils.retry import retry_with_softer_prompt
from ..usage_tracker import UsageEvent

try:
    # Prefer typed helpers from the new google-genai package
    from google.genai import types as genai_types
except Exception:  # pragma: no cover
    genai_types = None

try:  # Backwards-compat when google-api-core is still available
    from google.api_core import exceptions as google_api_exceptions
except ImportError:  # pragma: no cover - optional dependency only in older stacks
    google_api_exceptions = None

API_ERROR_TYPES: Tuple[type[BaseException], ...] = (genai_errors.APIError,)
if google_api_exceptions is not None:  # pragma: no branch - tuple concat only if present
    API_ERROR_TYPES = API_ERROR_TYPES + (google_api_exceptions.GoogleAPIError,)


def _error_code(exc: Exception) -> Optional[int]:
    code = getattr(exc, "code", None)
    try:
        return int(code) if code is not None else None
    except (TypeError, ValueError):
        return None


def _error_status(exc: Exception) -> str:
    for attr in ("status", "reason"):
        value = getattr(exc, attr, None)
        if isinstance(value, str):
            return value.upper()
    return ""


def _error_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    return message if isinstance(message, str) and message else str(exc)

def _key_id(api_key: str) -> str:
    """Generate a stable, non-reversible identifier for an API key (for logs/Redis keys)."""
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return digest[:12]


def _is_permission_denied_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(exc, google_api_exceptions.PermissionDenied):
        return True
    code = _error_code(exc)
    if code == 403:
        return True
    return "PERMISSION_DENIED" in _error_status(exc)


def _is_invalid_argument_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(exc, google_api_exceptions.InvalidArgument):
        return True
    code = _error_code(exc)
    if code == 400:
        return True
    return "INVALID_ARGUMENT" in _error_status(exc)


def _looks_like_safety_block(exc: Exception) -> bool:
    candidate = f"{_error_message(exc)}".upper()
    return any(token in candidate for token in ("PROHIBITED", "SAFETY", "BLOCK"))

def _is_not_found_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(exc, google_api_exceptions.NotFound):
        return True
    code = _error_code(exc)
    if code == 404:
        return True
    return "NOT_FOUND" in _error_status(exc)


def _is_rate_limited_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(exc, (google_api_exceptions.ResourceExhausted, google_api_exceptions.TooManyRequests)):
        return True
    code = _error_code(exc)
    if code == 429:
        return True
    status = _error_status(exc)
    if "RESOURCE_EXHAUSTED" in status or "TOO_MANY_REQUESTS" in status:
        return True
    message = _error_message(exc).upper()
    return any(token in message for token in ("RESOURCE_EXHAUSTED", "TOO MANY REQUESTS", "RATE LIMIT", "QUOTA"))


def _is_transient_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(
        exc,
        (
            google_api_exceptions.InternalServerError,
            google_api_exceptions.ServiceUnavailable,
            google_api_exceptions.DeadlineExceeded,
            google_api_exceptions.Aborted,
        ),
    ):
        return True
    code = _error_code(exc)
    if code in (500, 502, 503, 504):
        return True
    status = _error_status(exc)
    return any(token in status for token in ("INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED", "ABORTED"))


def _retry_delay_seconds(exc: Exception) -> Optional[float]:
    """Best-effort retry delay extraction (when SDK provides it)."""
    for attr in ("retry_delay", "retry_after", "retry_after_seconds"):
        value = getattr(exc, attr, None)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


class _ApiKeyPool:
    """In-memory API key rotation with cooldown + disable support."""

    def __init__(self, api_keys: list[str]):
        self._api_keys = api_keys[:]
        self._current_index = 0
        self._disabled: set[str] = set()
        self._cooldown_until: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def api_keys(self) -> tuple[str, ...]:
        return tuple(self._api_keys)

    def current(self, now: float) -> Optional[str]:
        with self._lock:
            if not self._api_keys:
                return None
            key = self._api_keys[self._current_index]
            if key in self._disabled:
                return None
            until = self._cooldown_until.get(key)
            if until is not None and until > now:
                return None
            return key

    def mark_disabled(self, api_key: str) -> None:
        with self._lock:
            self._disabled.add(api_key)
            self._cooldown_until.pop(api_key, None)

    def mark_cooldown(self, api_key: str, *, seconds: float, now: float) -> None:
        if seconds <= 0:
            return
        with self._lock:
            if api_key in self._disabled:
                return
            self._cooldown_until[api_key] = max(self._cooldown_until.get(api_key, 0.0), now + seconds)

    def next_available(self, now: float) -> Optional[str]:
        with self._lock:
            if not self._api_keys:
                return None
            start = self._current_index
            for offset in range(len(self._api_keys)):
                idx = (start + offset) % len(self._api_keys)
                key = self._api_keys[idx]
                if key in self._disabled:
                    continue
                until = self._cooldown_until.get(key)
                if until is not None and until > now:
                    continue
                self._current_index = idx
                return key
            return None

    def rotate(self, now: float) -> Optional[str]:
        with self._lock:
            if not self._api_keys:
                return None
            self._current_index = (self._current_index + 1) % len(self._api_keys)
        return self.next_available(now)

    def next_ready_in_seconds(self, now: float) -> Optional[float]:
        with self._lock:
            candidates = []
            for key in self._api_keys:
                if key in self._disabled:
                    continue
                until = self._cooldown_until.get(key)
                if until is None or until <= now:
                    return 0.0
                candidates.append(until)
            if not candidates:
                return None
            return max(0.0, min(candidates) - now)


class _RequestsPerMinuteLimiter:
    """Per-API-key request pacing; uses Redis when available for cross-worker coordination."""

    def __init__(self, requests_per_minute: int, *, redis_url: str | None = None):
        self._rpm = int(requests_per_minute)
        self._interval_ms = int((60.0 / max(1, self._rpm)) * 1000.0)
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = None
        self._redis_lock = threading.Lock()
        self._local_next_allowed_ms: dict[str, int] = {}
        self._lua = None

    def _get_redis(self):
        if not self._redis_url:
            return None
        with self._redis_lock:
            if self._redis is not None:
                return self._redis
            try:
                import redis  # type: ignore

                self._redis = redis.Redis.from_url(self._redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None
            return self._redis

    def _redis_next_allowed_ms(self, key_id: str, now_ms: int) -> Optional[int]:
        r = self._get_redis()
        if r is None:
            return None
        if self._lua is None:
            self._lua = r.register_script(
                """
                local current = redis.call('GET', KEYS[1])
                local now = tonumber(ARGV[1])
                local interval = tonumber(ARGV[2])
                local allowed = now
                if current then
                  local next_allowed = tonumber(current)
                  if next_allowed and next_allowed > now then
                    allowed = next_allowed
                  end
                end
                local new_next = allowed + interval
                redis.call('SET', KEYS[1], new_next)
                local ttl = math.max(interval * 2, 120000)
                redis.call('PEXPIRE', KEYS[1], ttl)
                return allowed
                """
            )
        try:
            redis_key = f"gemini:rpm:{key_id}"
            allowed = self._lua(keys=[redis_key], args=[now_ms, self._interval_ms])
            return int(allowed) if allowed is not None else None
        except Exception:
            return None

    def wait(self, api_key: str) -> None:
        if self._rpm <= 0:
            return
        key_id = _key_id(api_key)
        now_ms = int(time.time() * 1000)

        allowed_ms = self._redis_next_allowed_ms(key_id, now_ms)
        if allowed_ms is None:
            # Local fallback (per-process only)
            next_allowed = self._local_next_allowed_ms.get(key_id, 0)
            allowed_ms = max(now_ms, next_allowed)
            self._local_next_allowed_ms[key_id] = allowed_ms + self._interval_ms

        delay_ms = allowed_ms - now_ms
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)


class GeminiModel:
    """
    A wrapper class for the Google Gemini API to handle text generation,
    including configuration, API calls, and retry logic.
    """
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        safety_settings: list,
        generation_config: dict,
        enable_soft_retry: bool = True,
        client: genai.Client | None = None,
        usage_callback: Callable[[UsageEvent], None] | None = None,
        *,
        backup_api_keys: list[str] | None = None,
        requests_per_minute: int | None = None,
        client_factory: Callable[[str], genai.Client] | None = None,
    ):
        """
        Initializes the Gemini model client.
        
        Args:
            api_key: The API key for Gemini
            model_name: The model name to use
            safety_settings: Safety settings for the model
            generation_config: Generation configuration
            enable_soft_retry: Whether to enable retry with softer prompts for ProhibitedException
        """
        if client is not None:
            self.client = client
            self.api_key = None
            self._api_key_pool = None
            self._clients_by_key: dict[str, genai.Client] = {}
            self._client_factory = None
            self._rpm_limiter = None
        else:
            api_keys: list[str] = []
            if isinstance(api_key, str) and api_key.strip():
                api_keys.append(api_key.strip())
            if backup_api_keys:
                api_keys.extend([k.strip() for k in backup_api_keys if isinstance(k, str) and k.strip()])
            # Deduplicate while preserving order
            seen: set[str] = set()
            deduped: list[str] = []
            for k in api_keys:
                if k in seen:
                    continue
                seen.add(k)
                deduped.append(k)
            if not deduped:
                raise ValueError("API key or Vertex credentials required.")

            self._api_key_pool = _ApiKeyPool(deduped)
            self._clients_by_key = {}
            self._client_factory = client_factory or (lambda k: genai.Client(api_key=k))

            # Initialize with the first available key
            first_key = self._api_key_pool.next_available(time.time())
            if not first_key:
                raise ValueError("No usable API keys provided.")
            self.client = self._client_factory(first_key)
            self._clients_by_key[first_key] = self.client
            self.api_key = first_key
            self._rpm_limiter = (
                _RequestsPerMinuteLimiter(int(requests_per_minute))
                if requests_per_minute is not None and int(requests_per_minute) > 0
                else None
            )
        self._client_lock = threading.Lock()
        self.model_name = model_name
        self.safety_settings = safety_settings
        self.generation_config = generation_config
        self.enable_soft_retry = enable_soft_retry
        self.usage_callback = usage_callback
        self.last_usage: UsageEvent | None = None
        print(f"GeminiModel initialized with model: {model_name}, soft_retry: {enable_soft_retry}")

    def _active_api_key(self) -> Optional[str]:
        return self.api_key if isinstance(self.api_key, str) and self.api_key else None

    def _select_client_for_request(self) -> tuple[Optional[str], genai.Client]:
        """Select a usable client (and its key) for the next request.

        For Vertex-injected clients, returns (None, self.client).
        """
        if self._api_key_pool is None:
            return None, self.client

        while True:
            now = time.time()
            key = self._api_key_pool.current(now) or self._api_key_pool.next_available(now)
            if key is None:
                ready_in = self._api_key_pool.next_ready_in_seconds(now)
                if ready_in is None:
                    raise ValueError("No usable API keys available.")
                if ready_in > 0:
                    time.sleep(min(ready_in, 10.0))
                    continue
                # ready_in == 0.0 but key selection still failed; loop again
                continue

            with self._client_lock:
                client = self._clients_by_key.get(key)
                if client is None:
                    if not self._client_factory:
                        raise ValueError("Client factory missing for Gemini API key mode.")
                    client = self._client_factory(key)
                    self._clients_by_key[key] = client
                # Keep backward-compatible attributes updated for logs/debugging
                self.client = client
                self.api_key = key
                return key, client

    def _pace_requests_if_needed(self, api_key: Optional[str]) -> None:
        if not api_key or not self._rpm_limiter:
            return
        self._rpm_limiter.wait(api_key)

    def _rotate_or_disable_key(self, api_key: Optional[str], *, cooldown_seconds: float | None = None) -> bool:
        """Rotate away from the current key when possible.

        Returns True if rotation selected another usable key, False otherwise.
        """
        if not api_key or self._api_key_pool is None:
            return False
        now = time.time()
        if cooldown_seconds is not None and cooldown_seconds > 0:
            self._api_key_pool.mark_cooldown(api_key, seconds=cooldown_seconds, now=now)
        else:
            self._api_key_pool.mark_disabled(api_key)

        next_key = self._api_key_pool.rotate(now)
        return bool(next_key and next_key != api_key)

    def _compute_backoff_seconds(self, attempt: int, *, base: float, cap: float, jitter_ratio: float = 0.25) -> float:
        delay = min(cap, base * (2 ** max(0, attempt)))
        jitter = delay * jitter_ratio * random.random()
        return delay + jitter

    def _emit_usage_event(self, response) -> None:
        """Extract usage metadata from a response and notify listeners."""
        event = self._extract_usage_event(response)
        if not event:
            return
        self.last_usage = event
        if self.usage_callback:
            try:
                self.usage_callback(event)
            except Exception as exc:  # pragma: no cover - best effort logging
                print(f"[GeminiModel] Failed to emit usage event: {exc}")

    def _extract_usage_event(self, response) -> UsageEvent | None:
        metadata = getattr(response, "usage_metadata", None)
        if metadata is None:
            return None

        # Extract token counts with proper field name mapping
        prompt = getattr(metadata, "prompt_token_count", None)
        if prompt is None:
            prompt = getattr(metadata, "input_token_count", None)

        # The correct field name for output tokens is 'candidates_token_count'
        completion = getattr(metadata, "candidates_token_count", None)
        if completion is None:
            completion = getattr(metadata, "output_token_count", None)
        if completion is None:
            completion = getattr(metadata, "completion_token_count", None)

        total = getattr(metadata, "total_token_count", None)

        try:
            prompt_tokens = int(prompt) if prompt is not None else 0
        except (TypeError, ValueError):
            prompt_tokens = 0
        try:
            completion_tokens = int(completion) if completion is not None else 0
        except (TypeError, ValueError):
            completion_tokens = 0
        try:
            total_tokens = int(total) if total is not None else prompt_tokens + completion_tokens
        except (TypeError, ValueError):
            total_tokens = prompt_tokens + completion_tokens

        return UsageEvent(
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            timestamp=datetime.utcnow(),
        )

    def _build_generation_config(self, overrides: dict | None = None):
        """Merge base generation_config with overrides and embed safety settings.

        Returns either a typed GenerateContentConfig when available or a plain dict
        that the SDK can coerce.
        """
        base = dict(self.generation_config or {})
        # Carry over safety settings in the config shape expected by google-genai
        if getattr(self, 'safety_settings', None):
            built_safety = self._build_safety_settings(self.safety_settings)
            if built_safety:
                base["safety_settings"] = built_safety
        if overrides:
            base.update(overrides)
        # Prefer typed config when available; fall back to plain dict (SDK will coerce)
        if genai_types and hasattr(genai_types, "GenerateContentConfig"):
            try:
                return genai_types.GenerateContentConfig(**base)
            except Exception:
                # If typed config construction fails (e.g., unknown fields),
                # fall back to plain dict; the SDK often coerces dicts internally.
                return base
        return base

    def _build_safety_settings(self, safety_settings: list | None):
        """Convert legacy safety settings to google-genai typed SafetySetting list if possible.

        Accepts a list of dicts like {"category": "HARM_CATEGORY_*", "threshold": "BLOCK_*"}.
        Returns list of genai_types.SafetySetting if available, otherwise returns original value.
        """
        if not safety_settings:
            return None
        if not genai_types:
            return safety_settings
        try:
            SafetySetting = getattr(genai_types, 'SafetySetting', None)
            HarmCategory = getattr(genai_types, 'HarmCategory', None) or getattr(genai_types, 'SafetyCategory', None)
            BlockThreshold = getattr(genai_types, 'BlockThreshold', None) or getattr(genai_types, 'SafetyThreshold', None)
            if not (SafetySetting and HarmCategory and BlockThreshold):
                return safety_settings

            def to_enum(enum_cls, name: str):
                if enum_cls is None or not name:
                    return None
                # Try exact attribute first
                val = getattr(enum_cls, name, None)
                if val is not None:
                    return val
                # Try removing known prefixes
                simplified = name
                simplified = simplified.replace('HARM_CATEGORY_', '')
                simplified = simplified.replace('BLOCK_', '')
                val = getattr(enum_cls, simplified, None)
                if val is not None:
                    return val
                # Try title/upper variants
                val = getattr(enum_cls, simplified.upper(), None)
                if val is not None:
                    return val
                return None

            result = []
            for s in safety_settings:
                category = s.get('category') if isinstance(s, dict) else None
                threshold = s.get('threshold') if isinstance(s, dict) else None
                cat_enum = to_enum(HarmCategory, category)
                thr_enum = to_enum(BlockThreshold, threshold)
                # If mapping fails, keep original string to let SDK try coercion
                cat_val = cat_enum if cat_enum is not None else category
                thr_val = thr_enum if thr_enum is not None else threshold
                result.append(SafetySetting(category=cat_val, threshold=thr_val))
            return result
        except Exception:
            # Fall back to passing-through the legacy dicts
            return safety_settings
    
    def _attempt_json_repair(self, truncated_json: str) -> str:
        """Attempt to repair truncated JSON by closing open structures."""
        # Count open brackets and braces
        open_braces = truncated_json.count('{') - truncated_json.count('}')
        open_brackets = truncated_json.count('[') - truncated_json.count(']')
        
        # Check if we're in the middle of a string
        in_string = False
        escape_next = False
        for char in truncated_json:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
        
        # Build repair string
        repair = truncated_json
        if in_string:
            repair += '"'  # Close the open string
        
        # Close any open objects/arrays in nested order
        # We need to close arrays before their containing objects
        while open_brackets > 0 or open_braces > 0:
            # Find what needs to be closed next by looking at the end
            last_open_brace = repair.rfind('{')
            last_open_bracket = repair.rfind('[')
            last_close_brace = repair.rfind('}')
            last_close_bracket = repair.rfind(']')
            
            # Determine what to close next
            if open_brackets > 0 and (last_open_bracket > last_open_brace or open_braces == 0):
                repair += ']'
                open_brackets -= 1
            elif open_braces > 0:
                repair += '}'
                open_braces -= 1
        
        return repair

    def _retry_or_raise(self, error: Exception, attempt: int, max_retries: int, label: str) -> None:
        """Legacy helper (kept for backward compatibility); uses exponential backoff."""
        print(f"\nRetriable {label} failed on attempt {attempt + 1}/{max_retries}. Error: {error}")
        if attempt < max_retries - 1:
            delay = self._compute_backoff_seconds(attempt, base=1.0, cap=10.0)
            print(f"Retrying in {delay:.1f} seconds...")
            time.sleep(delay)
        else:
            raise Exception(f"All {max_retries} {label} attempts failed. Last error: {error}") from error

    @staticmethod
    def validate_api_key(api_key: str, model_name: str = "gemini-flash-lite-latest") -> bool:
        """
        Validates the provided API key by checking if the specified model can be accessed.
        Returns True if valid, False otherwise.
        """
        if not api_key:
            return False
        try:
            client = genai.Client(api_key=api_key)
            return GeminiModel.validate_with_client(client, model_name)
        except API_ERROR_TYPES as exc:
            # Hard failures: bad key / model / permission.
            if _looks_like_safety_block(exc):
                # Safety blocks don't indicate key validity; treat as valid for access checks.
                return True
            if _is_permission_denied_error(exc) or _is_invalid_argument_error(exc) or _is_not_found_error(exc):
                return False
            # Soft failures: rate limits / transient issues shouldn't block starting a job.
            if _is_rate_limited_error(exc) or _is_transient_error(exc):
                return True
            # Conservative default: unknown API errors => allow (caller will handle at runtime).
            return True
        except Exception:
            # Conservatively return False on other errors.
            return False

    @staticmethod
    def validate_with_client(client: genai.Client, model_name: str) -> bool:
        """Validate model access using an existing google-genai client."""
        try:
            try:
                client.models.get(model=model_name)
                return True
            except Exception:
                client.models.generate_content(model=model_name, contents="ping")
                return True
        except API_ERROR_TYPES as exc:
            if _looks_like_safety_block(exc):
                return True
            if _is_permission_denied_error(exc) or _is_invalid_argument_error(exc) or _is_not_found_error(exc):
                return False
            if _is_rate_limited_error(exc) or _is_transient_error(exc):
                return True
            return True
        except Exception:
            return False

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generates text using the Gemini API, with a built-in retry mechanism
        that distinguishes between retriable and non-retriable errors.
        
        If enable_soft_retry is True, will also retry ProhibitedException with softer prompts.
        """
        if self.enable_soft_retry:
            return self._generate_text_with_soft_retry(prompt, max_retries)
        else:
            return self._generate_text_base(prompt, max_retries)
    
    def _generate_text_base(self, prompt: str, max_retries: int = 3) -> str:
        """
        Base text generation method without soft retry logic.
        """
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                api_key, client = self._select_client_for_request()
                self._pace_requests_if_needed(api_key)

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._build_generation_config(None),
                )
                # Prefer direct text if present (property or callable)
                response_text = None
                if response and hasattr(response, 'text'):
                    try:
                        response_text = response.text() if callable(response.text) else response.text
                    except Exception:
                        response_text = None

                # Fallback: assemble from candidates/parts
                if not response_text:
                    try:
                        parts = response.candidates[0].content.parts
                        response_text = ''.join(getattr(p, 'text', '') for p in parts)
                    except Exception:
                        response_text = None

                if response_text:
                    self._emit_usage_event(response)
                    return str(response_text).strip()

                # Safety block detection
                if response and hasattr(response, 'prompt_feedback') and getattr(response.prompt_feedback, 'block_reason', None):
                    block_reason = response.prompt_feedback.block_reason
                    # This is a non-retriable error - raise ProhibitedException
                    raise ProhibitedException(
                        message=f"Prompt blocked by safety settings. Reason: {block_reason}",
                        prompt=prompt,
                        api_response=str(response.prompt_feedback) if hasattr(response, 'prompt_feedback') else None,
                        api_call_type="text_generation"
                    )

                # Otherwise, treat as invalid/empty response
                raise ValueError("API returned an empty or invalid response.")

            except ProhibitedException:
                raise

            except API_ERROR_TYPES as e:
                last_error = e
                # Safety signals should route to the sanitizer (do not rotate keys)
                if _looks_like_safety_block(e):
                    raise ProhibitedException(
                        message=_error_message(e),
                        prompt=prompt,
                        api_call_type="text_generation",
                    )

                if _is_invalid_argument_error(e) or _is_not_found_error(e):
                    print(f"\nNon-retriable API error: {e}")
                    raise e

                if _is_permission_denied_error(e):
                    rotated = self._rotate_or_disable_key(self._active_api_key())
                    if rotated and attempt < max_retries - 1:
                        continue
                    print(f"\nPermission denied API error: {e}")
                    raise e

                if _is_rate_limited_error(e):
                    retry_after = _retry_delay_seconds(e)
                    delay = retry_after if retry_after is not None else self._compute_backoff_seconds(attempt, base=2.0, cap=30.0)
                    rotated = self._rotate_or_disable_key(self._active_api_key(), cooldown_seconds=delay)
                    if rotated and attempt < max_retries - 1:
                        continue
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    raise Exception(f"All {max_retries} API call attempts failed. Last error: {e}") from e

                # Transient/unknown API errors: retry with backoff
                delay = _retry_delay_seconds(e)
                if delay is None:
                    delay = self._compute_backoff_seconds(attempt, base=1.0, cap=15.0)
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                raise Exception(f"All {max_retries} API call attempts failed. Last error: {e}") from e

            except Exception as e:
                last_error = e
                if isinstance(e, ValueError) and "No usable API keys" in str(e):
                    raise
                if attempt < max_retries - 1:
                    delay = self._compute_backoff_seconds(attempt, base=1.0, cap=10.0)
                    time.sleep(delay)
                    continue
                raise Exception(f"All {max_retries} API call attempts failed. Last error: {e}") from e

        raise Exception(f"All {max_retries} API call attempts failed. Last error: {last_error}") from last_error

    @retry_with_softer_prompt(max_retries=3, delay=2.0)
    def _generate_text_with_soft_retry(self, prompt: str, max_retries: int = 3) -> str:
        """
        Text generation with soft retry logic for ProhibitedException.
        The decorator will automatically retry with softer prompts.
        """
        return self._generate_text_base(prompt, max_retries)

    # --------------------
    # Structured Output
    # --------------------
    def generate_structured(self, prompt: str, response_schema, max_retries: int = 3):
        """
        Generates structured output using Gemini. 
        
        Args:
            prompt: The prompt text
            response_schema: Either a dict (JSON schema) or a Pydantic model class
            max_retries: Number of retries on failure
            
        Returns:
            If response_schema is a dict: Returns a Python dict
            If response_schema is a Pydantic model: Returns an instance of that model
        """
        # Check if response_schema is a Pydantic model
        from pydantic import BaseModel
        is_pydantic = False
        if not isinstance(response_schema, dict):
            # Check if it's a Pydantic model class or a type annotation
            try:
                if issubclass(response_schema, BaseModel):
                    is_pydantic = True
            except TypeError:
                # Could be a list[Model] or other type annotation
                is_pydantic = True
        
        # We do not use soft retry here by default, because schema prompts are minimal.
        # If desired, we could add a similar decorator later.
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                # Note: For structured output, passing schema either via generation_config
                # or constructor works; we pass here to avoid global state on the model.
                api_key, client = self._select_client_for_request()
                self._pace_requests_if_needed(api_key)

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._build_generation_config({
                        "response_mime_type": "application/json",
                        "response_schema": response_schema,
                    }),
                )

                # Safety block detection (route to sanitizer; do not rotate keys)
                if response and hasattr(response, "prompt_feedback") and getattr(response.prompt_feedback, "block_reason", None):
                    block_reason = response.prompt_feedback.block_reason
                    raise ProhibitedException(
                        message=f"Prompt blocked by safety settings. Reason: {block_reason}",
                        prompt=prompt,
                        api_response=str(response.prompt_feedback),
                        api_call_type="structured_output",
                    )
                
                # If using Pydantic models, use the parsed response
                if is_pydantic:
                    if hasattr(response, 'parsed') and response.parsed is not None:
                        self._emit_usage_event(response)
                        return response.parsed
                    else:
                        # For Pydantic models, parsed response is required
                        raise ValueError("Structured output failed: No parsed response available. This may indicate the response was truncated or malformed.")

                # Only for dict schemas (backward compatibility)
                import json as _json
                response_text = None

                if response and hasattr(response, 'text'):
                    if callable(response.text):
                        response_text = response.text()
                    else:
                        response_text = response.text

                # If no text directly available, try to extract from candidates
                if not response_text:
                    try:
                        parts = response.candidates[0].content.parts
                        response_text = ''.join(getattr(p, 'text', '') for p in parts)
                    except Exception:
                        pass

                parsed_response = None
                parse_error = None
                cleaned_text = None

                if response_text:
                    cleaned_text = self._clean_json_text(response_text)
                    try:
                        parsed_response = _json.loads(cleaned_text)
                    except _json.JSONDecodeError as e:
                        self._log_json_parse_error(cleaned_text, e)
                        parse_error = e

                if parsed_response is None:
                    parsed_response = self._extract_structured_payload(response, cleaned_text)

                if parsed_response is None and parse_error is None:
                    parsed_response = {}

                if parsed_response is not None:
                    self._emit_usage_event(response)
                    return parsed_response

                if parse_error is not None:
                    raise ValueError(f"Failed to parse JSON response: {parse_error}")

                raise ValueError("Structured API returned an empty response.")

            except API_ERROR_TYPES as e:
                last_error = e
                if _looks_like_safety_block(e):
                    raise ProhibitedException(
                        message=_error_message(e),
                        prompt=prompt,
                        api_call_type="structured_output",
                    )
                if _is_invalid_argument_error(e) or _is_not_found_error(e):
                    print(f"\nNon-retriable structured API error: {e}")
                    raise e
                if _is_permission_denied_error(e):
                    rotated = self._rotate_or_disable_key(self._active_api_key())
                    if rotated and attempt < max_retries - 1:
                        continue
                    print(f"\nPermission denied structured API error: {e}")
                    raise e
                if _is_rate_limited_error(e):
                    retry_after = _retry_delay_seconds(e)
                    delay = retry_after if retry_after is not None else self._compute_backoff_seconds(attempt, base=2.0, cap=30.0)
                    rotated = self._rotate_or_disable_key(self._active_api_key(), cooldown_seconds=delay)
                    if rotated and attempt < max_retries - 1:
                        continue
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    raise Exception(f"All {max_retries} structured API call attempts failed. Last error: {e}") from e

                delay = _retry_delay_seconds(e)
                if delay is None:
                    delay = self._compute_backoff_seconds(attempt, base=1.0, cap=15.0)
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                raise Exception(f"All {max_retries} structured API call attempts failed. Last error: {e}") from e
            except Exception as e:
                last_error = e
                if isinstance(e, ProhibitedException):
                    raise
                if isinstance(e, ValueError) and "No usable API keys" in str(e):
                    raise
                if attempt < max_retries - 1:
                    delay = self._compute_backoff_seconds(attempt, base=1.0, cap=10.0)
                    time.sleep(delay)
                    continue
                raise Exception(f"All {max_retries} structured API call attempts failed. Last error: {e}") from e

        raise Exception(f"All {max_retries} structured API call attempts failed. Last error: {last_error}") from last_error

    @staticmethod
    def _clean_json_text(raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _log_json_parse_error(self, text: str, exc) -> None:
        try:
            length = len(text) if isinstance(text, str) else 0
            print(f"JSON parsing error: {exc}")
            print(f"Response text length: {length}")

            # Show error position context when available
            pos = getattr(exc, 'pos', None)
            if isinstance(pos, int) and 0 <= pos <= length:
                start = max(0, pos - 120)
                end = min(length, pos + 120)
                snippet = text[start:end]
                marker_relative = pos - start
                print(f"Error context [{start}:{end}] (pos={pos}):")
                print(snippet)
                print(" " * marker_relative + "^")

            # Head/Tail snippets for quick inspection
            head = text[:200] if length > 0 else ""
            tail = text[-200:] if length > 200 else ""
            if head:
                print("Response head (200):")
                print(head)
            if tail:
                print("Response tail (200):")
                print(tail)

            # Structural hinting: brace/bracket balance
            open_braces = text.count('{') - text.count('}') if isinstance(text, str) else 0
            open_brackets = text.count('[') - text.count(']') if isinstance(text, str) else 0
            print(f"Brace balance: braces={open_braces}, brackets={open_brackets}")

        except Exception as log_exc:  # Best-effort logging; never raise from logger
            print(f"[parse-debug] Failed to log JSON parse details: {log_exc}")

    def _extract_structured_payload(self, response, fallback_text: str | None = None):
        if response is None:
            return None

        parsed = getattr(response, 'parsed', None)
        coerced = self._coerce_structured_payload(parsed)
        if coerced is not None:
            return coerced

        parts = getattr(response, 'parts', None)
        if not parts:
            candidates = getattr(response, 'candidates', None) or []
            for candidate in candidates:
                content = getattr(candidate, 'content', None)
                if content and getattr(content, 'parts', None):
                    parts = content.parts
                    break

        if parts:
            for part in parts:
                fc = getattr(part, 'function_call', None)
                if fc is None:
                    continue
                payload = self._coerce_structured_payload(getattr(fc, 'args', None))
                if payload is not None:
                    return payload

            for part in parts:
                fr = getattr(part, 'function_response', None)
                if fr is None:
                    continue
                payload = self._coerce_structured_payload(getattr(fr, 'response', None))
                if payload is not None:
                    return payload

            for part in parts:
                payload = self._coerce_structured_payload(getattr(part, 'text', None))
                if payload is not None:
                    return payload

        if fallback_text:
            return self._coerce_structured_payload(fallback_text)

        return None

    @staticmethod
    def _coerce_structured_payload(payload):
        if payload is None:
            return None

        try:
            from pydantic import BaseModel  # Local import to avoid eager dependency costs
        except Exception:  # pragma: no cover - pydantic should exist but guard anyway
            BaseModel = None

        if BaseModel and isinstance(payload, BaseModel):
            return payload.model_dump()

        if isinstance(payload, (dict, list)):
            return payload

        if isinstance(payload, str):
            cleaned = GeminiModel._clean_json_text(payload)
            if not cleaned:
                return None
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return None

        return None
