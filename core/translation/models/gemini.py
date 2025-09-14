import time
from google import genai
from google.api_core import exceptions as google_exceptions
from shared.errors import ProhibitedException
from ...utils.retry import retry_with_softer_prompt
try:
    # Prefer typed helpers from the new google-genai package
    from google.genai import types as genai_types
except Exception:  # pragma: no cover
    genai_types = None

class GeminiModel:
    """
    A wrapper class for the Google Gemini API to handle text generation,
    including configuration, API calls, and retry logic.
    """
    def __init__(self, api_key: str, model_name: str, safety_settings: list, generation_config: dict, enable_soft_retry: bool = True):
        """
        Initializes the Gemini model client.
        
        Args:
            api_key: The API key for Gemini
            model_name: The model name to use
            safety_settings: Safety settings for the model
            generation_config: Generation configuration
            enable_soft_retry: Whether to enable retry with softer prompts for ProhibitedException
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        # google-genai client (unified Gemini API)
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.safety_settings = safety_settings
        self.generation_config = generation_config
        self.enable_soft_retry = enable_soft_retry
        print(f"GeminiModel initialized with model: {model_name}, soft_retry: {enable_soft_retry}")
    
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

    @staticmethod
    def validate_api_key(api_key: str, model_name: str = "gemini-2.5-flash-lite") -> bool:
        """
        Validates the provided API key by checking if the specified model can be accessed.
        Returns True if valid, False otherwise.
        """
        if not api_key:
            return False
        try:
            client = genai.Client(api_key=api_key)
            # Try a metadata fetch first (no content generation)
            try:
                # google-genai supports models.get(); param name may vary across versions,
                # but this call will raise if unauthorized/unknown.
                client.models.get(model=model_name)
                return True
            except Exception:
                # Fallback to a minimal generate call to validate access
                client.models.generate_content(model=model_name, contents="ping")
                return True
        except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument, google_exceptions.NotFound):
            # PermissionDenied/InvalidArgument for bad keys, NotFound for invalid model names
            return False
        except Exception:
            # Conservatively return False on other errors
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
                # Re-raise ProhibitedException without retrying
                raise
                
            except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument) as e:
                # Check if this is actually a content safety block
                error_str = str(e).upper()
                if "PROHIBITED" in error_str or "SAFETY" in error_str or "BLOCKED" in error_str:
                    raise ProhibitedException(
                        message=str(e),
                        prompt=prompt,
                        api_call_type="text_generation"
                    )
                # Other non-retriable errors: Invalid API key, bad request.
                # We should not retry these.
                print(f"\nNon-retriable API error: {e}")
                raise e # Re-raise the exception to be caught by the translation engine

            except Exception as e:
                # Retriable errors: Server errors, network issues, etc.
                print(f"\nRetriable API call failed on attempt {attempt + 1}/{max_retries}. Error: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    # After all retries, re-raise the last exception with more context
                    raise Exception(f"All {max_retries} API call attempts failed. Last error: {e}") from e
        
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
                if is_pydantic and hasattr(response, 'parsed') and response.parsed is not None:
                    return response.parsed
                
                # Otherwise, parse JSON as before (backward compatibility)
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
                
                if response_text:
                    # Strip markdown code block formatting if present
                    cleaned_text = response_text.strip()
                    if cleaned_text.startswith('```json'):
                        cleaned_text = cleaned_text[7:]  # Remove ```json prefix
                    elif cleaned_text.startswith('```'):
                        cleaned_text = cleaned_text[3:]  # Remove ``` prefix
                    if cleaned_text.endswith('```'):
                        cleaned_text = cleaned_text[:-3]  # Remove ``` suffix
                    cleaned_text = cleaned_text.strip()
                    
                    try:
                        return _json.loads(cleaned_text)
                    except _json.JSONDecodeError as e:
                        # Log the problematic JSON for debugging
                        print(f"JSON parsing error: {e}")
                        print(f"Response text length: {len(cleaned_text)}")
                        
                        # Check if this looks like a truncation issue
                        if "Unterminated string" in str(e) and cleaned_text.strip()[-1] not in ['}', ']']:
                            print("Warning: Response appears to be truncated. Attempting to repair...")
                            # Try to repair truncated JSON
                            repaired = self._attempt_json_repair(cleaned_text)
                            if repaired:
                                try:
                                    return _json.loads(repaired)
                                except _json.JSONDecodeError:
                                    print("Failed to repair truncated JSON")
                        
                        # Log problematic section for other errors
                        if hasattr(e, 'pos'):
                            start = max(0, e.pos - 100)
                            end = min(len(cleaned_text), e.pos + 100)
                            print(f"Problematic section around position {e.pos}:")
                            print(repr(cleaned_text[start:end]))
                        raise ValueError(f"Failed to parse JSON response: {e}")
                
                raise ValueError("Structured API returned an empty or unparseable response.")

            except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument) as e:
                # Bad key/arguments are not retriable
                print(f"\nNon-retriable structured API error: {e}")
                raise e
            except Exception as e:
                print(f"\nRetriable structured API call failed on attempt {attempt + 1}/{max_retries}. Error: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise Exception(f"All {max_retries} structured API call attempts failed. Last error: {e}") from e

        return {} if not is_pydantic else None
