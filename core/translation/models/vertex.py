from typing import Optional

from google.api_core import exceptions as google_exceptions

from .gemini import GeminiModel
from .vertex_utils import (
    VertexConfigurationError,
    build_vertex_client,
    build_vertex_model_path,
    create_vertex_client_config,
)


class VertexGeminiModel(GeminiModel):
    """Gemini model wrapper for Vertex AI deployments using service account credentials."""

    class VertexCredentialError(Exception):
        """Raised when Vertex credential validation fails."""
        pass

    def __init__(
        self,
        service_account_json: str,
        project_id: str,
        location: Optional[str],
        model_name: str,
        safety_settings: list,
        generation_config: dict,
        enable_soft_retry: bool = True
    ):
        if not service_account_json:
            raise ValueError("Vertex service account JSON cannot be empty.")

        try:
            client_config = create_vertex_client_config(
                service_account_json,
                project_id=project_id,
                location=location,
            )
        except VertexConfigurationError as exc:
            raise VertexGeminiModel.VertexCredentialError(str(exc)) from exc

        client = build_vertex_client(client_config)
        normalized_model_name = build_vertex_model_path(
            model_name,
            client_config.project_id,
            client_config.location,
        )

        super().__init__(
            api_key=None,
            model_name=normalized_model_name,
            safety_settings=safety_settings,
            generation_config=generation_config,
            enable_soft_retry=enable_soft_retry,
            client=client
        )

        self._credentials_info = client_config.credentials_info
        self.project_id = client_config.project_id
        self.location = client_config.location
        self._model_resource = normalized_model_name

    @staticmethod
    def _format_vertex_error(
        error: Exception,
        model_name: str,
        project_id: str,
        location: str
    ) -> str:
        """Build a helpful error message for Vertex credential failures."""
        friendly_model = model_name.split("/")[-1] if model_name else model_name
        base = getattr(error, "message", "") or getattr(error, "details", "") or str(error)

        if isinstance(error, google_exceptions.PermissionDenied):
            reason = "The service account lacks permission to access the Vertex model."
        elif isinstance(error, google_exceptions.InvalidArgument):
            reason = "The requested model name is invalid or not available in the project."
        elif isinstance(error, google_exceptions.NotFound):
            reason = "The requested model could not be found in the project."
        else:
            reason = "Vertex API returned an error while validating the model."

        context = (
            f"Vertex validation failed for model '{friendly_model}' "
            f"in project '{project_id}' (location '{location}')."
        )
        if base:
            return f"{context} {reason} (Vertex error: {base})"
        return f"{context} {reason}"

    @staticmethod
    def validate_credentials(
        service_account_json: str,
        project_id: str,
        location: Optional[str],
        model_name: str
    ) -> bool:
        """Validate credentials by attempting to access the model metadata."""
        if not service_account_json:
            raise VertexGeminiModel.VertexCredentialError("Vertex service account JSON is required.")

        try:
            client_config = create_vertex_client_config(
                service_account_json,
                project_id=project_id,
                location=location,
            )
        except VertexConfigurationError as exc:
            raise VertexGeminiModel.VertexCredentialError(str(exc)) from exc

        try:
            client = build_vertex_client(client_config)
            model_resource = build_vertex_model_path(
                model_name,
                client_config.project_id,
                client_config.location,
            )
        except Exception as exc:  # pragma: no cover - defensive, build is deterministic today
            raise VertexGeminiModel.VertexCredentialError(
                f"Failed to initialize Vertex AI client: {exc}"
            ) from exc

        try:
            client.models.get(model=model_resource)
            return True
        except Exception as metadata_error:  # Attempt a lightweight generate call before failing
            try:
                client.models.generate_content(model=model_resource, contents="ping")
                return True
            except Exception as generate_error:
                error_to_report = generate_error or metadata_error
                message = VertexGeminiModel._format_vertex_error(
                    error_to_report,
                    model_resource,
                    client_config.project_id,
                    client_config.location,
                )
                raise VertexGeminiModel.VertexCredentialError(message) from error_to_report
