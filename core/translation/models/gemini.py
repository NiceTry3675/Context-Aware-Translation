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
        self.model = genai.GenerativeModel(
            model_name,
            safety_settings=safety_settings,
            generation_config=generation_config
        )
        self.enable_soft_retry = enable_soft_retry
        print(f"GeminiModel initialized with model: {model_name}, soft_retry: {enable_soft_retry}")

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
