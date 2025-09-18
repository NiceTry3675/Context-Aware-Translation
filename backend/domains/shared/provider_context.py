from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal, Optional, Union

from google import genai
from google.oauth2 import service_account

try:  # FastAPI is available in production, but tests may run without the dependency installed.
    from fastapi import HTTPException  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

DEFAULT_VERTEX_LOCATION = "us-central1"
SUPPORTED_PROVIDERS: tuple[str, ...] = ("gemini", "vertex", "openrouter")
REQUIRED_SERVICE_ACCOUNT_FIELDS = {"client_email", "private_key", "token_uri"}


@dataclass(slots=True)
class ProviderContext:
    """Normalized provider context shared across services."""

    name: Literal["gemini", "vertex", "openrouter"]
    project_id: Optional[str] = None
    location: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    default_model: Optional[str] = None


Payload = Optional[Union[str, bytes, Dict[str, Any]]]


def parse_provider_context(provider: str, payload: Payload) -> ProviderContext:
    """Create a provider context from the incoming payload."""

    if not provider:
        raise HTTPException(status_code=422, detail="Missing provider selection.")

    provider_name = provider.lower()
    if provider_name not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unsupported provider '{provider}'.")

    if provider_name != "vertex":
        return ProviderContext(name=provider_name)

    data = _load_payload(payload)
    return _parse_vertex_payload(data)


def _load_payload(payload: Payload) -> Dict[str, Any]:
    if payload is None:
        raise HTTPException(status_code=422, detail="Vertex provider requires JSON payload.")

    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"Malformed JSON payload: {exc.msg}.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Vertex provider payload must be a JSON object.")

    return payload


def _parse_vertex_payload(data: Dict[str, Any]) -> ProviderContext:
    if "service_account" in data:
        service_account = data.get("service_account")
        if not isinstance(service_account, dict):
            raise HTTPException(status_code=422, detail="`service_account` must be an object.")

        project_id = data.get("project_id") or service_account.get("project_id")
        if not project_id:
            raise HTTPException(status_code=422, detail="Missing `project_id` in wrapped Vertex configuration.")
        if not isinstance(project_id, str):
            raise HTTPException(status_code=422, detail="Vertex `project_id` must be a string.")

        location = data.get("location")
        if not location:
            raise HTTPException(status_code=422, detail="Missing `location` in wrapped Vertex configuration.")
        if not isinstance(location, str):
            raise HTTPException(status_code=422, detail="Vertex `location` must be a string.")

        default_model = data.get("default_model")
        if default_model is not None and not isinstance(default_model, str):
            raise HTTPException(status_code=422, detail="Vertex `default_model` must be a string when provided.")
        credentials = dict(service_account)
    else:
        credentials = dict(data)
        default_model = credentials.pop("default_model", None)
        if default_model is not None and not isinstance(default_model, str):
            raise HTTPException(status_code=422, detail="Vertex `default_model` must be a string when provided.")
        location = credentials.pop("location", DEFAULT_VERTEX_LOCATION)
        if not isinstance(location, str):
            raise HTTPException(status_code=422, detail="Vertex `location` must be a string.")
        project_id = credentials.get("project_id")
        if not project_id:
            raise HTTPException(status_code=422, detail="Vertex service account JSON missing `project_id`.")
        if not isinstance(project_id, str):
            raise HTTPException(status_code=422, detail="Vertex `project_id` must be a string.")

    _validate_service_account(credentials)

    return ProviderContext(
        name="vertex",
        project_id=project_id,
        location=location,
        credentials=credentials,
        default_model=default_model,
    )


def _validate_service_account(credentials: Dict[str, Any]) -> None:
    missing = [
        field
        for field in REQUIRED_SERVICE_ACCOUNT_FIELDS
        if not isinstance(credentials.get(field), str) or not credentials.get(field).strip()
    ]
    if missing:
        joined = ", ".join(sorted(missing))
        raise HTTPException(
            status_code=422,
            detail=f"Vertex service account JSON missing required fields: {joined}.",
        )

    if not isinstance(credentials.get("private_key"), str) or "BEGIN PRIVATE KEY" not in credentials["private_key"]:
        raise HTTPException(status_code=422, detail="Vertex private key is not in the expected PEM format.")


def provider_context_to_payload(context: ProviderContext) -> Dict[str, Any]:
    """Serialize a provider context into a JSON-safe payload."""

    if context is None:
        return {}

    data = {
        key: value
        for key, value in asdict(context).items()
        if value is not None
    }
    return data


def provider_context_from_payload(data: Optional[Dict[str, Any]]) -> Optional[ProviderContext]:
    """Reconstruct a ProviderContext from a serialized payload."""

    if not data:
        return None

    # Defensive copy to avoid mutating caller structures
    payload = dict(data)
    credentials = payload.get("credentials")
    if credentials is not None and not isinstance(credentials, dict):
        raise ValueError("Provider context credentials payload must be a dictionary.")

    return ProviderContext(
        name=payload.get("name", "gemini"),
        project_id=payload.get("project_id"),
        location=payload.get("location"),
        credentials=credentials,
        default_model=payload.get("default_model"),
    )


def build_vertex_client(context: ProviderContext) -> genai.Client:
    """Instantiate a google-genai client configured for Vertex AI."""

    if not context.credentials:
        raise ValueError("Vertex provider context requires credentials.")
    if not context.project_id or not context.location:
        raise ValueError("Vertex provider context requires project_id and location.")

    credentials = service_account.Credentials.from_service_account_info(context.credentials)
    if credentials.requires_scopes:
        credentials = credentials.with_scopes([
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/generative-language"
        ])
    client_kwargs = {
        "vertexai": True,
        "project": context.project_id,
        "location": context.location,
        "credentials": credentials,
    }

    return genai.Client(**client_kwargs)


def vertex_model_resource_name(model_name: str, context: ProviderContext) -> str:
    """Resolve a short Gemini model ID to the Vertex resource name."""

    if model_name.startswith("projects/"):
        return model_name

    short_name = model_name.split("/")[-1]
    return (
        f"projects/{context.project_id}/locations/{context.location}/publishers/google/models/{short_name}"
    )
