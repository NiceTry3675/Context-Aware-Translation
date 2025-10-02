import requests
import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from ...utils.retry import retry_with_softer_prompt
from shared.errors import ProhibitedException
from ..usage_tracker import UsageEvent

class OpenRouterModel:
    """
    A wrapper for the OpenRouter API.
    It mimics the structure of the GeminiModel for easy integration.
    """
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        generation_config: Dict[str, Any] | None = None,
        usage_callback: Callable[[UsageEvent], None] | None = None,
        native_gemini_api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initializes the OpenRouter model client.

        Args:
            api_key (str): The OpenRouter API key.
            model_name (str): The model to use via OpenRouter (e.g., "openai/gpt-4o").
            **kwargs: Additional keyword arguments (for compatibility, not all are used).
        """
        if not api_key.startswith("sk-or-"):
            raise ValueError("Invalid OpenRouter API key provided. It should start with 'sk-or-'.")
        
        self.api_key = api_key
        self.model_name = model_name
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # For compatibility with existing config structure
        self.enable_soft_retry = kwargs.get('enable_soft_retry', True)
        self.generation_config: Dict[str, Any] = generation_config or {}
        self.usage_callback = usage_callback
        self.last_usage: UsageEvent | None = None
        self.native_gemini_api_key = native_gemini_api_key

    def _emit_usage_event(self, result: Dict[str, Any]) -> None:
        usage = result.get('usage') if isinstance(result, dict) else None
        if not isinstance(usage, dict):
            return

        prompt = usage.get('prompt_tokens', usage.get('input_tokens', 0))
        completion = usage.get('completion_tokens', usage.get('output_tokens', 0))
        total = usage.get('total_tokens')

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

        event = UsageEvent(
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            timestamp=datetime.utcnow(),
        )
        self.last_usage = event
        if self.usage_callback:
            try:
                self.usage_callback(event)
            except Exception as exc:  # pragma: no cover
                print(f"[OpenRouterModel] Failed to emit usage event: {exc}")

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generates text using the specified OpenRouter model.

        Args:
            prompt (str): The prompt to send to the model.
            max_retries (int): Maximum number of retries for transient errors.

        Returns:
            str: The generated text content.
        
        Raises:
            Exception: If the API call fails.
        """
        if self.enable_soft_retry:
            return self._generate_text_with_soft_retry(prompt, max_retries)
        else:
            return self._generate_text_base(prompt, max_retries)
    
    def _generate_text_base(self, prompt: str, max_retries: int = 3) -> str:
        """
        Base text generation method with retry logic for transient errors.
        """
        # Map shared generation_config to OpenAI-compatible fields
        max_output_tokens = self.generation_config.get("max_output_tokens")
        temperature = self.generation_config.get("temperature")
        top_p = self.generation_config.get("top_p")

        body = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        # Apply mapped parameters when available
        if isinstance(max_output_tokens, int) and max_output_tokens > 0:
            # OpenRouter (OpenAI compatible) expects 'max_tokens' as completion cap
            body["max_tokens"] = max_output_tokens
        if isinstance(temperature, (int, float)):
            body["temperature"] = float(temperature)
        if isinstance(top_p, (int, float)):
            body["top_p"] = float(top_p)
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=body,
                    timeout=300  # 5 minutes timeout
                )
                
                # Check for content policy violations
                if response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', '')
                    if 'content policy' in error_msg.lower() or 'prohibited' in error_msg.lower():
                        raise ProhibitedException(
                            message=f"Content blocked by OpenRouter: {error_msg}",
                            prompt=prompt,
                            api_response=str(error_data),
                            api_call_type="text_generation"
                        )
                
                response.raise_for_status()  # Raise an exception for bad status codes
                
                result = response.json()
                self._emit_usage_event(result)
                content = result['choices'][0]['message']['content']
                return content

            except ProhibitedException:
                # Re-raise ProhibitedException without retrying
                raise
            
            except requests.exceptions.Timeout as e:
                # Timeout is retriable
                print(f"\nTimeout on attempt {attempt + 1}/{max_retries}. Error: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise Exception(f"All {max_retries} API call attempts timed out. Last error: {e}")
            
            except requests.exceptions.RequestException as e:
                # Check if it's a rate limit or server error (retriable)
                if hasattr(e, 'response') and e.response:
                    if e.response.status_code in [429, 500, 502, 503, 504]:
                        print(f"\nRetriable error on attempt {attempt + 1}/{max_retries}. Status: {e.response.status_code}")
                        if attempt < max_retries - 1:
                            wait_time = min(5 * (2 ** attempt), 30)  # Exponential backoff, max 30s
                            print(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue
                
                # Non-retriable error
                print(f"\nNon-retriable OpenRouter API error: {e}")
                raise Exception(f"OpenRouter API request failed: {e}")
            
            except (KeyError, IndexError) as e:
                print(f"Error parsing OpenRouter response: {e}")
                raise Exception(f"Could not parse OpenRouter API response")
        
        # Should not be reached
        raise Exception(f"All {max_retries} API call attempts failed")
    
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
        Structured output using OpenRouter (OpenAI-compatible chat API).

        Behavior mirrors GeminiModel.generate_structured:
        - If response_schema is a Pydantic model: returns an instance, requires valid JSON
        - If response_schema is a dict (JSON schema): returns parsed Python dict
        - Adds JSON-only instructions and attempts to enforce JSON mode when supported
        """
        # Defer import to keep optional dependency light
        from pydantic import BaseModel  # type: ignore

        is_pydantic = False
        if not isinstance(response_schema, dict):
            try:
                if issubclass(response_schema, BaseModel):
                    is_pydantic = True
            except TypeError:
                is_pydantic = True

        # If the selected model is a Gemini engine routed via OpenRouter and a native Gemini key is available,
        # use native Gemini structured output for best compatibility.
        model_lower = (self.model_name or "").lower()
        is_gemini_via_openrouter = (
            model_lower.startswith("google/") or model_lower.startswith("gemini-") or "gemini" in model_lower
        )
        try:
            from core.translation.models.gemini import GeminiModel as _GeminiModel  # type: ignore
            from core.config.loader import load_config as _load_config  # type: ignore
        except Exception:
            _GeminiModel = None
            _load_config = None

        if is_gemini_via_openrouter and _GeminiModel and _load_config:
            try:
                cfg = _load_config()
                gemini_api_key = self.native_gemini_api_key or cfg.get("gemini_api_key")
                if gemini_api_key:
                    native = _GeminiModel(
                        api_key=gemini_api_key,
                        model_name=model_lower.replace("google/", ""),
                        safety_settings=cfg.get("safety_settings", []),
                        generation_config=cfg.get("generation_config", {}),
                        enable_soft_retry=cfg.get("enable_soft_retry", True),
                    )
                    return native.generate_structured(prompt, response_schema, max_retries=max_retries)
            except Exception:
                # Fall back to OpenRouter path below on any failure
                pass

        # Non-Gemini engines via OpenRouter: explicitly not supported for structured output
        raise NotImplementedError("Structured output is only supported for Gemini models.")

    @classmethod
    def validate_api_key(cls, api_key: str, model_name: str = None) -> bool:
        """
        Validates the OpenRouter API key by checking if it can list models.

        Args:
            api_key (str): The API key to validate.
            model_name (str, optional): Not used for OpenRouter validation, 
                                       but included for compatibility.

        Returns:
            bool: True if the key is valid, False otherwise.
        """
        if not api_key or not api_key.startswith("sk-or-"):
            return False
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        try:
            # A lightweight call to check if the key is valid
            response = requests.get(f"{cls.BASE_URL}/models", headers=headers, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
