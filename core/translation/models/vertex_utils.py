"""Shared helpers for configuring Vertex AI clients via google-genai."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from google import genai
from google.auth import exceptions as auth_exceptions
from google.oauth2 import service_account

VERTEX_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
DEFAULT_VERTEX_LOCATION = "us-central1"


class VertexConfigurationError(Exception):
    """Raised when Vertex client configuration fails."""


@dataclass(frozen=True)
class VertexClientConfig:
    """Normalized configuration needed to talk to Vertex AI generative models."""

    project_id: str
    location: str
    credentials_info: Dict[str, Any]
    credentials: service_account.Credentials

    def as_client_kwargs(self) -> Dict[str, Any]:
        """Return keyword arguments accepted by ``genai.Client`` for Vertex AI."""
        return {
            "vertexai": True,
            "credentials": self.credentials,
            "project": self.project_id,
            "location": self.location,
        }


def build_vertex_client(
    config: VertexClientConfig,
    *,
    http_options: Optional[Any] = None,
) -> genai.Client:
    """Instantiate a google-genai client configured for Vertex AI."""
    client_kwargs = config.as_client_kwargs()
    if http_options is not None:
        client_kwargs["http_options"] = http_options
    return genai.Client(**client_kwargs)


def create_vertex_client_config(
    service_account_json: str,
    *,
    project_id: Optional[str],
    location: Optional[str],
) -> VertexClientConfig:
    """Parse credentials JSON and construct a Vertex client configuration.

    Args:
        service_account_json: Raw service account credentials JSON string.
        project_id: Optional explicit project override.
        location: Optional location override; defaults to ``us-central1``.

    Returns:
        VertexClientConfig ready for ``genai.Client`` construction.

    Raises:
        VertexConfigurationError: If parsing or credential creation fails.
    """
    if not service_account_json:
        raise VertexConfigurationError("Vertex service account JSON is required.")

    try:
        credentials_info: Dict[str, Any] = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise VertexConfigurationError("Vertex service account JSON is invalid.") from exc

    derived_project_id = (project_id or credentials_info.get("project_id") or "").strip()
    if not derived_project_id:
        raise VertexConfigurationError("Vertex project ID is required.")

    normalized_location = (location or DEFAULT_VERTEX_LOCATION).strip() or DEFAULT_VERTEX_LOCATION

    try:
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=[VERTEX_SCOPE],
        )
    except (ValueError, auth_exceptions.GoogleAuthError) as exc:
        raise VertexConfigurationError(
            f"Failed to load Vertex service account credentials: {exc}"
        ) from exc

    return VertexClientConfig(
        project_id=derived_project_id,
        location=normalized_location,
        credentials_info=credentials_info,
        credentials=credentials,
    )


def normalize_vertex_model_name(model_name: str) -> str:
    """Ensure a model identifier is in the format Vertex expects."""
    if not model_name:
        return model_name

    normalized = model_name.strip()

    if normalized.startswith("projects/"):
        return normalized

    if normalized.startswith("publishers/"):
        return normalized

    if normalized.startswith("models/"):
        normalized = normalized[len("models/") :]

    return f"publishers/google/models/{normalized}"


def build_vertex_model_path(
    model_name: str,
    project_id: Optional[str],
    location: Optional[str],
) -> str:
    """Construct a model resource path valid for Vertex AI requests."""
    normalized = normalize_vertex_model_name(model_name)

    if normalized.startswith("projects/"):
        return normalized

    project = (project_id or "").strip()
    loc = (location or DEFAULT_VERTEX_LOCATION).strip() or DEFAULT_VERTEX_LOCATION

    if not project:
        return normalized

    return f"projects/{project}/locations/{loc}/{normalized}"
