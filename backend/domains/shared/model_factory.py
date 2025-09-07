"""
Model API Factory

Centralized factory for creating model API instances.
Eliminates duplication across all services.

Refactored from backend/services/base/model_factory.py
"""

from typing import Union, Any
from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel


class ModelAPIFactory:
    """Factory class for creating model API instances."""
    
    @staticmethod
    def create(api_key: str, model_name: str, config: dict = None) -> Union[GeminiModel, OpenRouterModel]:
        """
        Factory method to create the correct model API instance.
        
        Args:
            api_key: API key for the model service
            model_name: Name of the model to use
            config: Optional configuration dict. If not provided, loads from config loader.
            
        Returns:
            Model API instance (GeminiModel or OpenRouterModel)
            
        Raises:
            ValueError: If API key format is invalid
        """
        if config is None:
            config = load_config()
            
        if api_key.startswith("sk-or-"):
            print(f"--- [API] Using OpenRouter model: {model_name} ---")
            return OpenRouterModel(
                api_key=api_key,
                model_name=model_name,
                enable_soft_retry=config.get('enable_soft_retry', True)
            )
        elif api_key.startswith("AIza") or len(api_key) == 39:  # Gemini API key patterns
            print(f"--- [API] Using Gemini model: {model_name} ---")
            return GeminiModel(
                api_key=api_key,
                model_name=model_name,
                safety_settings=config['safety_settings'],
                generation_config=config['generation_config'],
                enable_soft_retry=config.get('enable_soft_retry', True)
            )
        else:
            raise ValueError(f"Unsupported API key format: {api_key[:10]}...")
    
    @staticmethod
    def create_model(api_key: str, model_name: str, config: dict = None) -> Union[GeminiModel, OpenRouterModel]:
        """
        Factory method to create the correct model API instance.
        Kept for backward compatibility. Use create() instead.
        
        Args:
            api_key: API key for the model service
            model_name: Name of the model to use
            config: Optional configuration dict. If not provided, loads from config loader.
            
        Returns:
            Model API instance (GeminiModel or OpenRouterModel)
        """
        return ModelAPIFactory.create(api_key, model_name, config)
    
    @staticmethod
    def validate_api_key(api_key: str, model_name: str) -> bool:
        """
        Validates the API key based on its format and model compatibility.
        
        Args:
            api_key: API key to validate
            model_name: Model name to validate against
            
        Returns:
            True if API key is valid for the model, False otherwise
        """
        try:
            if api_key.startswith("sk-or-"):
                return OpenRouterModel.validate_api_key(api_key, model_name)
            elif api_key.startswith("AIza") or len(api_key) == 39:  # Gemini API key patterns
                return GeminiModel.validate_api_key(api_key, model_name)
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    def get_supported_models(api_key: str) -> list[str]:
        """
        Get list of supported models for the given API key type.
        
        Args:
            api_key: API key to determine provider
            
        Returns:
            List of supported model names
        """
        if api_key.startswith("sk-or-"):
            return [
                "google/gemini-2.0-flash-exp",
                "google/gemini-2.0-flash",
                "google/gemini-pro-002",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "anthropic/claude-3.5-sonnet",
                "x-ai/grok-beta",
                "deepseek/deepseek-r1"
            ]
        else:
            return [
                "gemini-2.0-flash-exp",
                "gemini-2.0-flash", 
                "gemini-pro-002"
            ]
    
    @staticmethod
    def is_openrouter_key(api_key: str) -> bool:
        """Check if API key is for OpenRouter."""
        return api_key.startswith("sk-or-")
    
    @staticmethod
    def is_gemini_key(api_key: str) -> bool:
        """Check if API key is for Gemini."""
        return api_key.startswith("AIza") or len(api_key) == 39