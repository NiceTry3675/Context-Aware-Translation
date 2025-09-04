import time
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from ...errors import ProhibitedException
from ...utils.retry import retry_with_softer_prompt

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
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.safety_settings = safety_settings
        self.generation_config = generation_config
        self.model = genai.GenerativeModel(
            model_name,
            safety_settings=safety_settings,
            generation_config=generation_config
        )
        self.enable_soft_retry = enable_soft_retry
        print(f"GeminiModel initialized with model: {model_name}, soft_retry: {enable_soft_retry}")
    
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
            genai.configure(api_key=api_key)
            # Check if the specific model is available and accessible with the key
            genai.get_model(f'models/{model_name}')
            return True
        except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument, google_exceptions.NotFound):
            # PermissionDenied/InvalidArgument for bad keys, NotFound for invalid model names
            return False
        except Exception:
            # For other potential issues like network errors, we can be lenient
            # or decide to return False. For now, we assume the key is invalid.
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
                response = self.model.generate_content(prompt)
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
                else:
                    if response and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                        block_reason = response.prompt_feedback.block_reason
                        # This is a non-retriable error - raise ProhibitedException
                        raise ProhibitedException(
                            message=f"Prompt blocked by safety settings. Reason: {block_reason}",
                            prompt=prompt,
                            api_response=str(response.prompt_feedback) if hasattr(response, 'prompt_feedback') else None,
                            api_call_type="text_generation"
                        )
                    else:
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
        
        return "" # Should not be reached
    
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
                response = self.model.generate_content(
                    contents=prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        # Keep temperature if provided; otherwise inherit a conservative default
                        temperature=self.generation_config.get('temperature', 0.7) if self.generation_config else 0.7,
                        # Add low top_p default for more deterministic structured output unless overridden
                        top_p=self.generation_config.get('top_p', 0.2) if self.generation_config else 0.2,
                        max_output_tokens=self.generation_config.get('max_output_tokens', 65536) if self.generation_config else 32768,  # Increased for structured output
                    ),
                    safety_settings=self.safety_settings,
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
