import os
import requests
import json
from typing import Dict, Any, List

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

    def generate_text(self, prompt: str) -> str:
        """
        Generates text using the specified OpenRouter model.

        Args:
            prompt (str): The prompt to send to the model.

        Returns:
            str: The generated text content.
        
        Raises:
            Exception: If the API call fails.
        """
        body = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=body,
                timeout=300  # 5 minutes timeout
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            return content

        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenRouter API: {e}")
            # In case of an error, re-raise it to be handled by the translation engine
            raise Exception(f"OpenRouter API request failed: {e}")
        except (KeyError, IndexError) as e:
            print(f"Error parsing OpenRouter response: {e}")
            raise Exception(f"Could not parse OpenRouter API response: {response.text}")

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
