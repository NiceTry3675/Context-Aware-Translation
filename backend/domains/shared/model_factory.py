"""
Model API Factory

Centralized factory for creating model API instances.
Eliminates duplication across all services.

Refactored from backend/services/base/model_factory.py
"""

from typing import Union, Any, Optional

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.translation.models.vertex import VertexGeminiModel
from core.translation.models.vertex_utils import build_vertex_model_path


def _looks_like_service_account(raw: Optional[str]) -> bool:
    """Quick check to see if a string appears to be a service account JSON blob."""
    if not raw:
        return False
    stripped = raw.strip()
    return (
        stripped.startswith('{')
        and '"type"' in stripped
        and '"project_id"' in stripped
        and '"private_key"' in stripped
    )


class ModelValidationError(Exception):
    """Raised when API credentials or model selection fail validation."""
    pass


class ModelAPIFactory:
    """Factory class for creating model API instances."""

    @staticmethod
    def create(
        api_key: str,
        model_name: str,
        config: dict = None,
        api_provider: Optional[str] = None,
        vertex_project_id: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_service_account: Optional[str] = None
    ) -> Union[GeminiModel, OpenRouterModel, VertexGeminiModel]:
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
            
        provider = api_provider
        if provider is None:
            if api_key and api_key.startswith("sk-or-"):
                provider = 'openrouter'
            elif api_key and (api_key.startswith("AIza") or len(api_key) == 39):
                provider = 'gemini'
            elif vertex_service_account or _looks_like_service_account(api_key):
                provider = 'vertex'
                if not vertex_service_account:
                    vertex_service_account = api_key
            else:
                provider = 'gemini'

        if provider == 'openrouter':
            print(f"--- [API] Using OpenRouter model: {model_name} ---")
            return OpenRouterModel(
                api_key=api_key,
                model_name=model_name,
                enable_soft_retry=config.get('enable_soft_retry', True)
            )
        elif provider == 'vertex':
            service_account_json = vertex_service_account or api_key
            normalized_model_name = build_vertex_model_path(
                model_name,
                vertex_project_id,
                vertex_location,
            )
            print(
                f"--- [API] Using Vertex Gemini model: {normalized_model_name} "
                f"(project={vertex_project_id}, location={vertex_location}) ---"
            )
            return VertexGeminiModel(
                service_account_json=service_account_json,
                project_id=vertex_project_id or '',
                location=vertex_location,
                model_name=normalized_model_name,
                safety_settings=config['safety_settings'],
                generation_config=config['generation_config'],
                enable_soft_retry=config.get('enable_soft_retry', True)
            )
        elif provider == 'gemini':
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
    def validate_api_key(
        api_key: str,
        model_name: str,
        api_provider: Optional[str] = None,
        vertex_project_id: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_service_account: Optional[str] = None
    ) -> bool:
        """
        Validates the API key based on its format and model compatibility.

        Args:
            api_key: API key to validate
            model_name: Model name to validate against

        Returns:
            True if valid. Raises ModelValidationError if validation fails.
        """
        provider = api_provider
        if provider is None:
            if api_key and api_key.startswith("sk-or-"):
                provider = 'openrouter'
            elif api_key and (api_key.startswith("AIza") or len(api_key) == 39):
                provider = 'gemini'
            elif vertex_service_account or _looks_like_service_account(api_key):
                provider = 'vertex'
                if not vertex_service_account:
                    vertex_service_account = api_key
            else:
                provider = 'gemini'

        try:
            if provider == 'openrouter':
                if OpenRouterModel.validate_api_key(api_key, model_name):
                    return True
                raise ModelValidationError("OpenRouter API key is invalid or lacks access to the selected model.")
            if provider == 'vertex':
                service_account_json = vertex_service_account or api_key
                normalized_model_name = build_vertex_model_path(
                    model_name,
                    vertex_project_id,
                    vertex_location,
                )
                VertexGeminiModel.validate_credentials(
                    service_account_json,
                    vertex_project_id or '',
                    vertex_location,
                    normalized_model_name
                )
                return True
            if provider == 'gemini':
                if GeminiModel.validate_api_key(api_key, model_name):
                    return True
                raise ModelValidationError("Gemini API key is invalid or lacks access to the selected model.")
            raise ModelValidationError("Unsupported API provider specified.")
        except VertexGeminiModel.VertexCredentialError as exc:
            raise ModelValidationError(str(exc)) from exc
        except ModelValidationError:
            raise
        except Exception as exc:
            raise ModelValidationError(f"Failed to validate model credentials: {exc}") from exc
    
    @staticmethod
    def is_openrouter_key(api_key: str) -> bool:
        """Check if API key is for OpenRouter."""
        return api_key.startswith("sk-or-")
    
    @staticmethod
    def is_gemini_key(api_key: str) -> bool:
        """Check if API key is for Gemini."""
        return api_key.startswith("AIza") or len(api_key) == 39
