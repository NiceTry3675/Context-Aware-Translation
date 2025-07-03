import time
import google.generativeai as genai

class GeminiModel:
    """
    A wrapper class for the Google Gemini API to handle text generation,
    including configuration, API calls, and retry logic.
    """
    def __init__(self, api_key: str, model_name: str, safety_settings: list, generation_config: dict):
        """
        Initializes the Gemini model client.
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            safety_settings=safety_settings,
            generation_config=generation_config
        )
        print(f"GeminiModel initialized with model: {model_name}")

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generates text using the Gemini API, with a built-in retry mechanism.

        Args:
            prompt (str): The full prompt to send to the model.
            max_retries (int): The maximum number of times to retry on failure.

        Returns:
            str: The generated text from the model.
        
        Raises:
            Exception: If all retry attempts fail.
        """
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
                else:
                    # This handles cases where the API returns a valid but empty response
                    raise ValueError("API returned an empty or invalid response.")
            except Exception as e:
                print(f"\nAPI call failed on attempt {attempt + 1}/{max_retries}. Error: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    # After all retries, re-raise the last exception
                    raise Exception(f"All {max_retries} API call attempts failed.") from e
        
        # This line should not be reachable if max_retries > 0
        return ""
