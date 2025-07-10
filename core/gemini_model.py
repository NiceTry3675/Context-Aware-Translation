import time
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

class GeminiModel:
    """
    A wrapper class for the Google Gemini API to handle text generation,
    including configuration, API calls, and retry logic.
    """
    def __init__(self, api_key: str, model_name: str, safety_settings: list, generation_config: dict):
        """
        Initializes the Gemini model client.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            safety_settings=safety_settings,
            generation_config=generation_config
        )
        print(f"GeminiModel initialized with model: {model_name}")

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validates the provided API key by making a lightweight call to the Gemini API.
        Returns True if valid, False otherwise.
        """
        if not api_key:
            return False
        try:
            genai.configure(api_key=api_key)
            # A lightweight, inexpensive call to list models
            genai.list_models()
            return True
        except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument):
            return False
        except Exception:
            # For other potential issues like network errors, we can be lenient
            # or decide to return False. For now, we assume the key is invalid.
            return False

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generates text using the Gemini API, with a built-in retry mechanism
        that distinguishes between retriable and non-retriable errors.
        """
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
                else:
                    if response and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                        block_reason = response.prompt_feedback.block_reason
                        # This is a non-retriable error
                        raise google_exceptions.InvalidArgument(f"Prompt blocked by safety settings. Reason: {block_reason}")
                    else:
                        raise ValueError("API returned an empty or invalid response.")

            except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument) as e:
                # Non-retriable errors: Invalid API key, bad request, safety blocks.
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
                    # After all retries, re-raise the last exception
                    raise Exception(f"All {max_retries} API call attempts failed.") from e
        
        return "" # Should not be reached
