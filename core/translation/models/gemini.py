import json
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
        else:
            if not api_key:
                raise ValueError("API key or Vertex credentials required.")
            # google-genai client (unified Gemini API)
            self.client = genai.Client(api_key=api_key)
            self.api_key = api_key
        self.model_name = model_name
        self.safety_settings = safety_settings
        self.generation_config = generation_config
        self.enable_soft_retry = enable_soft_retry
        self.usage_callback = usage_callback
        self.last_usage: UsageEvent | None = None
        print(f"GeminiModel initialized with model: {model_name}, soft_retry: {enable_soft_retry}")

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
        print(f"\nRetriable {label} failed on attempt {attempt + 1}/{max_retries}. Error: {error}")
        if attempt < max_retries - 1:
            print("Retrying in 5 seconds...")
            time.sleep(5)
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
        except API_ERROR_TYPES:
            # Permission or invalid argument for bad keys, NotFound for invalid models.
            return False
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
        except API_ERROR_TYPES:
            return False
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
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
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
                if _is_permission_denied_error(e) or _is_invalid_argument_error(e):
                    if _looks_like_safety_block(e):
                        raise ProhibitedException(
                            message=_error_message(e),
                            prompt=prompt,
                            api_call_type="text_generation"
                        )
                    print(f"\nNon-retriable API error: {e}")
                    raise e
                self._retry_or_raise(e, attempt, max_retries, "API call")

            except Exception as e:
                self._retry_or_raise(e, attempt, max_retries, "API call")
        
        return ""  # Should not be reached
    
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
        for attempt in range(max_retries):
            try:
                # Note: For structured output, passing schema either via generation_config
                # or constructor works; we pass here to avoid global state on the model.
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._build_generation_config({
                        "response_mime_type": "application/json",
                        "response_schema": response_schema,
                    }),
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
                if _is_permission_denied_error(e) or _is_invalid_argument_error(e):
                    print(f"\nNon-retriable structured API error: {e}")
                    raise e
                self._retry_or_raise(e, attempt, max_retries, "structured API call")
            except Exception as e:
                self._retry_or_raise(e, attempt, max_retries, "structured API call")

        return {} if not is_pydantic else None

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
