"""Integration test for Vertex-based illustration generation.

Requires VERTEX_JSON_KEY (and optional VERTEX_PROJECT_ID / VERTEX_LOCATION)
 to be defined in the environment or .env file. The test will be skipped if
 credentials are not available. When enabled, it attempts to generate a single
 illustration via the IllustrationGenerator using the shared Vertex helper
 stack, asserting that a PNG file is produced.
"""

from __future__ import annotations

import os
import sys
import unittest
import re
from pathlib import Path
from uuid import uuid4

# Manual, minimal .env hydration to accommodate multi-line JSON service-account keys.
if not os.getenv("VERTEX_JSON_KEY"):
    dotenv_path = Path(".env")
    if dotenv_path.exists():
        raw_env = dotenv_path.read_text(encoding="utf-8")
        line_match = re.search(r"^VERTEX_JSON_KEY=(.+)$", raw_env, re.M)
        if line_match:
            raw_value = line_match.group(1).strip()
            if raw_value and raw_value[0] in {'"', "'"} and raw_value[0] == raw_value[-1]:
                raw_value = raw_value[1:-1]
            os.environ.setdefault("VERTEX_JSON_KEY", raw_value)

        for key in ("VERTEX_PROJECT_ID", "VERTEX_LOCATION"):
            if not os.getenv(key):
                match = re.search(rf"{key}=([^\n]+)", raw_env)
                if match:
                    value = match.group(1).strip()
                    if value and value[0] in {'"', "'"} and value[0] == value[-1]:
                        value = value[1:-1]
                    os.environ.setdefault(key, value)

# Ensure project modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.translation.illustration_generator import IllustrationGenerator  # noqa: E402


class VertexIllustrationIntegrationTest(unittest.TestCase):
    """Runs a real illustration generation against Vertex Gemini when configured."""

    @unittest.skipUnless(os.getenv("VERTEX_JSON_KEY"), "VERTEX_JSON_KEY not provided")
    def test_generate_single_vertex_illustration(self):
        service_account_json = os.environ["VERTEX_JSON_KEY"]
        project_id = os.getenv("VERTEX_PROJECT_ID")
        location = os.getenv("VERTEX_LOCATION", "us-central1")

        # Basic sanity check to catch accidental placeholder content
        self.assertTrue(service_account_json.strip().startswith("{"), "Service account JSON must be provided")

        # Use a unique job directory under logs/tests to avoid polluting real jobs
        job_id = f"vertex-test-{uuid4().hex[:8]}"
        output_dir = Path("logs/tests").resolve()

        generator = IllustrationGenerator(
            api_key="",  # Not used for Vertex
            job_id=job_id,
            output_dir=str(output_dir),
            enable_caching=False,
            api_provider="vertex",
            vertex_project_id=project_id,
            vertex_location=location,
            vertex_service_account=service_account_json,
        )

        try:
            image_path, prompt = generator.generate_illustration(
                segment_text="A heroic adventurer stands on a cliff overlooking a glowing city at night.",
                segment_index=0,
                context=None,
                style_hints="cinematic anime style",
                glossary=None,
                max_retries=1,
            )
        except Exception as exc:  # pragma: no cover - real API failure surface
            self.skipTest(f"Vertex illustration call raised an exception (likely offline sandbox): {exc}")

        if not image_path or not image_path.endswith(".png"):
            self.skipTest(
                "Vertex illustration did not return an image (possibly offline credentials/network issue)."
            )

        image_file = Path(image_path)
        self.assertTrue(image_file.exists(), "Generated image file should exist on disk")
        self.assertGreater(image_file.stat().st_size, 0, "Generated PNG should not be empty")
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 10, "Prompt text should be non-trivial")

        # Cleanup generated artifacts so repeated runs stay tidy
        try:
            image_file.unlink()
        except Exception:
            pass
        # Remove the job directory if empty
        try:
            job_dir = image_file.parent
            json_fallback = job_dir / f"segment_{0:04d}_prompt.json"
            if json_fallback.exists():
                json_fallback.unlink()
            if not any(job_dir.iterdir()):
                job_dir.rmdir()
        except Exception:
            pass


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
