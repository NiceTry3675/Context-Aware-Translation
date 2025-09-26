"""
Model API Factory

Centralized factory for creating model API instances.
Eliminates duplication across all services.

Refactored from backend/services/base/model_factory.py
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple, Union

from google import genai
from google.genai import errors as genai_errors

try:  # Backwards-compat for legacy google-api-core errors in tests.
    from google.api_core import exceptions as google_api_exceptions
except ImportError:  # pragma: no cover - optional dependency in minimal envs.
    google_api_exceptions = None

KNOWN_VERTEX_MODELS: Tuple[str, ...] = (
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)

API_ERROR_TYPES: Tuple[type[BaseException], ...] = (genai_errors.APIError,)
if google_api_exceptions is not None:  # pragma: no branch - simple tuple concat
    API_ERROR_TYPES = API_ERROR_TYPES + (google_api_exceptions.GoogleAPIError,)


def _error_code(exc: Exception) -> Optional[int]:
    code = getattr(exc, "code", None)
    try:
        return int(code) if code is not None else None
    except (TypeError, ValueError):
        return None


def _error_status(exc: Exception) -> str:
    for attr in ("status", "reason"):
        value = getattr(exc, attr, None)
        if isinstance(value, str):
            return value.upper()
    return ""


def _error_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    return message if isinstance(message, str) and message else str(exc)


def _is_not_found_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(exc, google_api_exceptions.NotFound):
        return True
    code = _error_code(exc)
    if code == 404:
        return True
    return "NOT_FOUND" in _error_status(exc)


def _is_permission_denied_error(exc: Exception) -> bool:
    if google_api_exceptions and isinstance(exc, google_api_exceptions.PermissionDenied):
        return True
    code = _error_code(exc)
    if code == 403:
        return True
    return "PERMISSION_DENIED" in _error_status(exc)

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.translation.usage_tracker import UsageEvent
from backend.domains.shared.provider_context import (
    ProviderContext,
    build_vertex_client,
    vertex_model_resource_name,
)


class ModelAPIFactory:
    """Factory class for creating model API instances."""
    
    @staticmethod
    def create(
        api_key: str | None,
        model_name: str,
        config: dict | None = None,
        provider_context: ProviderContext | None = None,
        usage_callback: Callable[[UsageEvent], None] | None = None,
    ) -> Union[GeminiModel, OpenRouterModel]:
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

        if provider_context and provider_context.name == "vertex":
            client, resolved_model = ModelAPIFactory._create_vertex_client_and_model(provider_context, model_name)
            print(f"--- [API] Using Vertex Gemini model: {resolved_model} ---")
            return GeminiModel(
                api_key=None,
                client=client,
                model_name=resolved_model,
                safety_settings=config['safety_settings'],
                generation_config=config['generation_config'],
                enable_soft_retry=config.get('enable_soft_retry', True),
                usage_callback=usage_callback,
            )

        if not api_key:
            raise ValueError("API key is required for the selected provider.")

        if api_key.startswith("sk-or-") or (provider_context and provider_context.name == "openrouter"):
            print(f"--- [API] Using OpenRouter model: {model_name} ---")
            return OpenRouterModel(
                api_key=api_key,
                model_name=model_name,
                generation_config=config.get('generation_config', {}),
                enable_soft_retry=config.get('enable_soft_retry', True),
                usage_callback=usage_callback,
            )
        elif api_key.startswith("AIza") or len(api_key) == 39 or (provider_context and provider_context.name == "gemini"):
            print(f"--- [API] Using Gemini model: {model_name} ---")
            return GeminiModel(
                api_key=api_key,
                model_name=model_name,
                safety_settings=config['safety_settings'],
                generation_config=config['generation_config'],
                enable_soft_retry=config.get('enable_soft_retry', True),
                usage_callback=usage_callback,
            )
        else:
            raise ValueError(f"Unsupported API key format: {api_key[:10]}...")
    
    @staticmethod
    def validate_api_key(
        api_key: str | None,
        model_name: str,
        provider_context: ProviderContext | None = None,
    ) -> bool:
        """
        Validates the API key based on its format and model compatibility.
        
        Args:
            api_key: API key to validate
            model_name: Model name to validate against
            
        Returns:
            True if API key is valid for the model, False otherwise
        """
        try:
            if provider_context and provider_context.name == "vertex":
                return ModelAPIFactory._validate_vertex_credentials(provider_context, model_name)

            if not api_key:
                return False

            if api_key.startswith("sk-or-") or (provider_context and provider_context.name == "openrouter"):
                return OpenRouterModel.validate_api_key(api_key, model_name)
            elif api_key.startswith("AIza") or len(api_key) == 39 or (provider_context and provider_context.name == "gemini"):
                return GeminiModel.validate_api_key(api_key, model_name)
            else:
                return False
        except API_ERROR_TYPES as exc:  # Normalise google-genai APIError surface
            raise ValueError(f"Vertex API error: {_error_message(exc)}") from exc
        except Exception as exc:
            raise ValueError(str(exc)) from exc

    @staticmethod
    def _create_vertex_client_and_model(
        context: ProviderContext,
        model_name: str,
    ) -> Tuple[genai.Client, str]:
        if not context.credentials:
            raise ValueError("Vertex provider context missing credentials.")
        if not context.project_id or not context.location:
            raise ValueError("Vertex provider context missing project metadata.")

        client = build_vertex_client(context)
        resolved_model = vertex_model_resource_name(model_name, context)
        return client, resolved_model

    @staticmethod
    def _validate_vertex_credentials(
        context: ProviderContext,
        model_name: str,
    ) -> bool:
        client, resolved_model = ModelAPIFactory._create_vertex_client_and_model(context, model_name)
        short_name = _short_model_name(resolved_model)
        candidate_models = []
        # Try full resource path first
        candidate_models.append(resolved_model)
        # Fallback to publisher-scoped and short identifiers, as the SDK historically accepted both
        publisher_scoped = f"publishers/google/models/{short_name}"
        if publisher_scoped not in candidate_models:
            candidate_models.append(publisher_scoped)
        if short_name not in candidate_models:
            candidate_models.append(short_name)

        last_error: Exception | None = None
        try:
            for candidate in candidate_models:
                try:
                    client.models.get(model=candidate)
                    return True
                except API_ERROR_TYPES as exc:
                    last_error = exc
                    if _is_permission_denied_error(exc):
                        raise ValueError(
                            "Permission denied accessing Vertex AI. Check your service account credentials and permissions."
                        ) from exc
                    continue
            # If we reach here, every candidate failed
            if isinstance(last_error, API_ERROR_TYPES) and _is_not_found_error(last_error):
                available = _collect_vertex_model_names(client)
                suggestion_list = ", ".join(sorted(set(available)))
                raise ValueError(
                    f"Vertex AI model '{model_name}' not found. Available models: {suggestion_list}"
                ) from last_error
            if isinstance(last_error, API_ERROR_TYPES):
                raise ValueError(f"Vertex API error: {_error_message(last_error)}") from last_error
            if last_error:
                raise last_error
            raise ValueError("Vertex model validation failed for an unknown reason.")
        except Exception as exc:
            raise ValueError(f"Failed to validate Vertex credentials: {exc}") from exc
def _short_model_name(model_name: str) -> str:
    return model_name.split("/")[-1]


def _collect_vertex_model_names(client: genai.Client) -> Tuple[str, ...]:
    discovered: set[str] = set(KNOWN_VERTEX_MODELS)
    try:
        for model in client.models.list():
            name = getattr(model, "name", None)
            if isinstance(name, str) and name:
                discovered.add(_short_model_name(name))
            base_model_id = getattr(model, "base_model_id", None)
            if isinstance(base_model_id, str) and base_model_id:
                discovered.add(base_model_id)
    except API_ERROR_TYPES:
        # Listing requires the same permissions as usage; ignore failures and fall back to static list.
        pass
    except Exception:
        pass
    return tuple(sorted(discovered))
