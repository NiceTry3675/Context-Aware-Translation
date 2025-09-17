"""Unit tests for Vertex configuration helpers."""

import json
import sys
from pathlib import Path
from unittest import TestCase, mock

# Ensure project modules are importable when running via pytest/python -m
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.translation.models.vertex import VertexGeminiModel
from core.translation.models.vertex_utils import (
    VertexClientConfig,
    VertexConfigurationError,
    build_vertex_client,
    build_vertex_model_path,
    create_vertex_client_config,
    normalize_vertex_model_name,
)
from backend.domains.shared.model_factory import ModelAPIFactory


SERVICE_ACCOUNT_TEMPLATE = {
    "type": "service_account",
    "project_id": "demo-project",
    "private_key_id": "abc123",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIBVwIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEAu\n-----END PRIVATE KEY-----\n",
    "client_email": "demo@demo-project.iam.gserviceaccount.com",
    "client_id": "1234567890",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/demo%40demo-project.iam.gserviceaccount.com",
}


class TestVertexClientConfig(TestCase):
    """Behavioural coverage for helper utilities."""

    def setUp(self) -> None:
        self.service_account_json = json.dumps(SERVICE_ACCOUNT_TEMPLATE)

    @mock.patch("core.translation.models.vertex_utils.service_account.Credentials.from_service_account_info")
    def test_create_config_uses_json_defaults(self, mock_from_info):
        mock_from_info.return_value = mock.sentinel.credentials

        config = create_vertex_client_config(
            self.service_account_json,
            project_id=None,
            location=None,
        )

        self.assertEqual(config.project_id, "demo-project")
        self.assertEqual(config.location, "us-central1")
        self.assertIs(config.credentials, mock.sentinel.credentials)
        mock_from_info.assert_called_once()

    @mock.patch("core.translation.models.vertex_utils.service_account.Credentials.from_service_account_info")
    def test_create_config_respects_overrides(self, mock_from_info):
        mock_from_info.return_value = mock.sentinel.credentials

        config = create_vertex_client_config(
            self.service_account_json,
            project_id="override-project",
            location="asia-northeast3",
        )

        self.assertEqual(config.project_id, "override-project")
        self.assertEqual(config.location, "asia-northeast3")

    def test_create_config_rejects_invalid_json(self):
        with self.assertRaises(VertexConfigurationError):
            create_vertex_client_config("not-json", project_id="demo", location=None)

    def test_create_config_requires_project(self):
        payload = SERVICE_ACCOUNT_TEMPLATE.copy()
        payload.pop("project_id")
        with self.assertRaises(VertexConfigurationError):
            create_vertex_client_config(
                json.dumps(payload),
                project_id=None,
                location=None,
            )

    def test_build_vertex_client_sets_vertexai_flag(self):
        with mock.patch("core.translation.models.vertex_utils.genai.Client") as mock_client:
            config = VertexClientConfig(
                project_id="demo",
                location="us-central1",
                credentials_info={},
                credentials=mock.sentinel.credentials,
            )

            build_vertex_client(config, http_options=mock.sentinel.http)

            mock_client.assert_called_once_with(
                vertexai=True,
                credentials=mock.sentinel.credentials,
                project="demo",
                location="us-central1",
                http_options=mock.sentinel.http,
            )

    def test_normalize_vertex_model_name(self):
        self.assertEqual(
            normalize_vertex_model_name("gemini-2.5-flash-lite"),
            "publishers/google/models/gemini-2.5-flash-lite",
        )
        self.assertEqual(
            normalize_vertex_model_name("models/gemini-2.5-flash-lite"),
            "publishers/google/models/gemini-2.5-flash-lite",
        )
        self.assertEqual(
            normalize_vertex_model_name("publishers/google/models/gemini-2.5-flash-lite"),
            "publishers/google/models/gemini-2.5-flash-lite",
        )


class TestVertexGeminiModel(TestCase):
    """Ensure model wrapper delegates to the helper utilities."""

    @mock.patch("core.translation.models.vertex.build_vertex_client")
    @mock.patch("core.translation.models.vertex.create_vertex_client_config")
    def test_validate_credentials_success(self, mock_create_config, mock_build_client):
        client_mock = mock.Mock()
        client_mock.models.get.side_effect = Exception("metadata failure")
        client_mock.models.generate_content.return_value = mock.Mock()
        mock_build_client.return_value = client_mock

        config_mock = mock.Mock()
        config_mock.project_id = "demo-project"
        config_mock.location = "europe-west4"
        mock_create_config.return_value = config_mock

        result = VertexGeminiModel.validate_credentials(
            "{}",
            project_id="custom",
            location="us-central1",
            model_name="models/gemini-2.5-flash-lite",
        )

        self.assertTrue(result)
        mock_create_config.assert_called_once()
        expected_model_path = build_vertex_model_path(
            "models/gemini-2.5-flash-lite",
            "demo-project",
            "europe-west4",
        )
        client_mock.models.generate_content.assert_called_once_with(
            model=expected_model_path,
            contents="ping",
        )

    @mock.patch("core.translation.models.vertex.create_vertex_client_config")
    def test_validate_credentials_wraps_config_errors(self, mock_create_config):
        mock_create_config.side_effect = VertexConfigurationError("bad config")

        with self.assertRaises(VertexGeminiModel.VertexCredentialError) as exc:
            VertexGeminiModel.validate_credentials(
                "{}",
                project_id="demo",
                location="us-central1",
                model_name="models/gemini",
            )

        self.assertIn("bad config", str(exc.exception))


class TestModelAPIFactoryVertexDetection(TestCase):
    """Verify JSON credentials are treated as Vertex inputs."""

    @mock.patch("core.translation.models.vertex.build_vertex_client")
    @mock.patch("core.translation.models.vertex.create_vertex_client_config")
    def test_create_with_json_api_key_infers_vertex(self, mock_create_config, mock_build_client):
        mock_client_config = mock.Mock()
        mock_client_config.project_id = "demo"
        mock_client_config.location = "us-central1"
        mock_create_config.return_value = mock_client_config
        mock_build_client.return_value = mock.Mock()

        config = {
            'safety_settings': [],
            'generation_config': {},
        }

        ModelAPIFactory.create(
            api_key=json.dumps(SERVICE_ACCOUNT_TEMPLATE),
            model_name="models/gemini-1.5-pro",
            config=config,
        )

        mock_create_config.assert_called_once()
        mock_build_client.assert_called_once()
