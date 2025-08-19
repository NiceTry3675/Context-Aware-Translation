import os
import requests
import json
import time
from typing import Dict, Any, List
from ...utils.retry import retry_with_softer_prompt
from ...errors import ProhibitedException

class OpenRouterModel:
    """
    A wrapper for the OpenRouter API.
    It mimics the structure of the GeminiModel for easy integration.
    """
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model_name: str, **kwargs):
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
        body = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
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
