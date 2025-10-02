import importlib.util
import sys
import types
import unittest
from pathlib import Path

# Provide a minimal FastAPI stub so provider_context can import HTTPException without the dependency.
fastapi_stub = types.ModuleType("fastapi")


class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _install_fastapi_stub():
    fastapi_stub.HTTPException = _HTTPException
    sys.modules.setdefault("fastapi", fastapi_stub)


_install_fastapi_stub()


def _install_google_stub():
    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

    genai_module.Client = DummyClient
    genai_module.types = types.SimpleNamespace()

    oauth2_module = types.ModuleType("google.oauth2")
    service_account_module = types.ModuleType("google.oauth2.service_account")

    class DummyCredentials:
        @classmethod
        def from_service_account_info(cls, info):
            return cls()

    service_account_module.Credentials = DummyCredentials

    sys.modules.setdefault("google", google_module)
    sys.modules.setdefault("google.genai", genai_module)
    sys.modules.setdefault("google.oauth2", oauth2_module)
    sys.modules.setdefault("google.oauth2.service_account", service_account_module)

    google_module.genai = genai_module
    oauth2_module.service_account = service_account_module


_install_google_stub()

MODULE_PATH = Path(__file__).resolve().parents[1] / "backend" / "domains" / "shared" / "provider_context.py"
SPEC = importlib.util.spec_from_file_location("provider_context", MODULE_PATH)
provider_context = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules.setdefault("provider_context", provider_context)
SPEC.loader.exec_module(provider_context)

ProviderContext = provider_context.ProviderContext
parse_provider_context = provider_context.parse_provider_context
DEFAULT_VERTEX_LOCATION = provider_context.DEFAULT_VERTEX_LOCATION
HTTPException = provider_context.HTTPException
provider_context_to_payload = provider_context.provider_context_to_payload
provider_context_from_payload = provider_context.provider_context_from_payload
vertex_model_resource_name = provider_context.vertex_model_resource_name


def _service_account(**overrides):
    data = {
        "type": "service_account",
        "project_id": "demo-project",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nABC\n-----END PRIVATE KEY-----\n",
        "client_email": "vertex@example.iam.gserviceaccount.com",
        "client_id": "1234567890",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/vertex%40example.iam.gserviceaccount.com",
    }
    data.update(overrides)
    return data


class ProviderContextParsingTests(unittest.TestCase):
    def test_parse_vertex_wrapped_configuration(self):
        payload = {
            "project_id": "demo-project",
            "location": "asia-northeast3",
            "default_model": "gemini-flash-latest",
            "service_account": _service_account(project_id="demo-project"),
        }

        context = parse_provider_context("vertex", payload)

        self.assertIsInstance(context, ProviderContext)
        self.assertEqual(context.name, "vertex")
        self.assertEqual(context.project_id, "demo-project")
        self.assertEqual(context.location, "asia-northeast3")
        self.assertEqual(context.default_model, "gemini-flash-latest")
        self.assertIsNotNone(context.credentials)
        self.assertEqual(context.credentials["client_email"], "vertex@example.iam.gserviceaccount.com")

    def test_parse_vertex_raw_configuration_defaults(self):
        payload = _service_account()

        context = parse_provider_context("vertex", payload)

        self.assertEqual(context.project_id, "demo-project")
        self.assertEqual(context.location, DEFAULT_VERTEX_LOCATION)
        self.assertIsNotNone(context.credentials)
        self.assertEqual(context.credentials["token_uri"], "https://oauth2.googleapis.com/token")

    def test_parse_vertex_raw_configuration_with_location_override(self):
        payload = {
            **_service_account(),
            "location": "europe-west4",
        }

        context = parse_provider_context("vertex", payload)

        self.assertEqual(context.location, "europe-west4")

    def test_parse_vertex_configuration_missing_fields(self):
        payload = _service_account()
        payload.pop("private_key")

        with self.assertRaises(HTTPException) as ctx:
            parse_provider_context("vertex", payload)

        self.assertIn("private_key", ctx.exception.detail)

    def test_parse_vertex_configuration_malformed_json(self):
        with self.assertRaises(HTTPException) as ctx:
            parse_provider_context("vertex", "{")

        self.assertIn("Malformed JSON", ctx.exception.detail)

    def test_parse_with_non_vertex_provider(self):
        context = parse_provider_context("gemini", None)

        self.assertEqual(context.name, "gemini")
        self.assertIsNone(context.project_id)

    def test_provider_context_serialization_roundtrip(self):
        context = parse_provider_context(
            "vertex",
            {
                "location": "asia-northeast1",
                "project_id": "demo-project",
                "private_key": "-----BEGIN PRIVATE KEY-----\nABC\n-----END PRIVATE KEY-----\n",
                "client_email": "vertex@example.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            },
        )

        payload = provider_context_to_payload(context)
        restored = provider_context_from_payload(payload)

        self.assertIsNotNone(restored)
        self.assertEqual(restored.name, "vertex")
        self.assertEqual(restored.project_id, "demo-project")
        self.assertIn("private_key", restored.credentials)

    def test_vertex_model_resource_name(self):
        context = ProviderContext(
            name="vertex",
            project_id="demo-project",
            location="asia-northeast1",
            credentials=_service_account(),
        )

        resource = vertex_model_resource_name("gemini-flash-latest", context)

        self.assertTrue(resource.startswith("projects/demo-project/"))


if __name__ == "__main__":
    unittest.main()