import os
import sys
from pathlib import Path

os.environ.setdefault("CLERK_SECRET_KEY", "test-clerk-secret")
os.environ.setdefault("ADMIN_SECRET_KEY", "test-admin-secret")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.background.cloud_run import CloudRunJobClient
from backend.background.job_runner import payload_from_env
from backend.background.tasks import RUN_MAINTENANCE_TASK


def test_extract_execution_name_from_run_operation_metadata():
    operation = {
        "name": "projects/demo/locations/asia-northeast3/operations/op-1",
        "metadata": {
            "target": (
                "projects/demo/locations/asia-northeast3/jobs/"
                "trans-background-job/executions/trans-background-job-abc12"
            )
        },
    }

    assert CloudRunJobClient._extract_execution_name(operation).endswith(
        "/executions/trans-background-job-abc12"
    )


def test_payload_from_scheduler_env(monkeypatch):
    monkeypatch.delenv("BACKGROUND_TASK_PAYLOAD", raising=False)
    monkeypatch.delenv("TASK_EXECUTION_ID", raising=False)
    monkeypatch.setenv("BACKGROUND_TASK_NAME", RUN_MAINTENANCE_TASK)
    monkeypatch.setenv("BACKGROUND_TASK_KIND", "maintenance")

    payload = payload_from_env()

    assert payload["task_name"] == RUN_MAINTENANCE_TASK
    assert payload["task_kind"] == "maintenance"
    assert payload["kwargs"] == {}
    assert payload["task_id"]
