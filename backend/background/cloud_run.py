"""Minimal Cloud Run Jobs REST client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from google.auth import default as google_auth_default
from google.auth.transport.requests import AuthorizedSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CloudRunExecutionRef:
    operation_name: Optional[str]
    execution_name: Optional[str]
    response: dict[str, Any]


class CloudRunJobClient:
    """Run and cancel Cloud Run Jobs with container environment overrides."""

    def __init__(self, project_id: str, region: str, job_name: str):
        if not project_id:
            raise ValueError("Google Cloud project id is required")
        if not region:
            raise ValueError("Google Cloud region is required")
        if not job_name:
            raise ValueError("Cloud Run background job name is required")

        self.project_id = project_id
        self.region = region
        self.job_name = job_name
        credentials, _ = google_auth_default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.session = AuthorizedSession(credentials)

    def run_with_env(
        self,
        env: dict[str, str],
        *,
        task_count: int = 1,
        timeout: str = "86400s",
    ) -> CloudRunExecutionRef:
        url = (
            "https://run.googleapis.com/v2/"
            f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}:run"
        )
        body = {
            "overrides": {
                "containerOverrides": [
                    {
                        "env": [
                            {"name": name, "value": value}
                            for name, value in sorted(env.items())
                            if value is not None
                        ]
                    }
                ],
                "taskCount": task_count,
                "timeout": timeout,
            }
        }

        response = self.session.post(url, json=body, timeout=30)
        response.raise_for_status()
        payload = response.json()
        operation_name = payload.get("name")
        execution_name = self._extract_execution_name(payload)
        logger.info(
            "Started Cloud Run job %s operation=%s execution=%s",
            self.job_name,
            operation_name,
            execution_name,
        )
        return CloudRunExecutionRef(
            operation_name=operation_name,
            execution_name=execution_name,
            response=payload,
        )

    def cancel_execution(self, execution_name: str) -> dict[str, Any]:
        if not execution_name:
            raise ValueError("Cloud Run execution name is required")

        full_execution_name = self._normalize_execution_name(execution_name)
        url = f"https://run.googleapis.com/v2/{full_execution_name}:cancel"
        response = self.session.post(url, json={}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        logger.info("Cancelled Cloud Run execution %s", full_execution_name)
        return payload

    def execution_from_operation(self, operation_name: str) -> Optional[str]:
        if not operation_name:
            return None
        url = f"https://run.googleapis.com/v2/{operation_name}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return self._extract_execution_name(response.json())

    def _normalize_execution_name(self, execution_name: str) -> str:
        if execution_name.startswith("projects/"):
            return execution_name
        return (
            f"projects/{self.project_id}/locations/{self.region}/jobs/"
            f"{self.job_name}/executions/{execution_name}"
        )

    @staticmethod
    def _extract_execution_name(payload: dict[str, Any]) -> Optional[str]:
        metadata = payload.get("metadata") or {}
        for key in ("target", "name"):
            value = metadata.get(key)
            if isinstance(value, str) and "/executions/" in value:
                return value
        response = payload.get("response") or {}
        name = response.get("name")
        if isinstance(name, str) and "/executions/" in name:
            return name
        return None
