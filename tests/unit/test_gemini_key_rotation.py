import os
import sys

import pytest

from google.api_core import exceptions as google_exceptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.translation.models.gemini import GeminiModel
from shared.errors import ProhibitedException


class DummyPromptFeedback:
    def __init__(self, block_reason: str):
        self.block_reason = block_reason


class DummyResponse:
    def __init__(self, *, text: str | None = None, prompt_feedback: DummyPromptFeedback | None = None):
        self.text = text
        self.prompt_feedback = prompt_feedback
        self.candidates = []
        self.usage_metadata = None


class DummyModels:
    def __init__(self, fn):
        self._fn = fn

    def generate_content(self, **kwargs):
        return self._fn(**kwargs)


class DummyClient:
    def __init__(self, fn):
        self.models = DummyModels(fn)


def make_model(*, plan_by_key: dict[str, list[object]], **kwargs) -> tuple[GeminiModel, dict[str, int]]:
    calls: dict[str, int] = {}

    def client_factory(api_key: str):
        calls.setdefault(api_key, 0)

        def behavior(**_kwargs):
            calls[api_key] += 1
            actions = plan_by_key.get(api_key) or []
            if not actions:
                raise RuntimeError(f"No planned action for key={api_key}")
            action = actions.pop(0)
            if isinstance(action, BaseException):
                raise action
            return action

        return DummyClient(behavior)

    model = GeminiModel(
        api_key="key_primary",
        model_name="test-model",
        safety_settings=[],
        generation_config={},
        enable_soft_retry=False,
        backup_api_keys=["key_backup"],
        client_factory=client_factory,
        **kwargs,
    )
    return model, calls


def test_rotates_on_permission_denied():
    model, calls = make_model(
        plan_by_key={
            "key_primary": [google_exceptions.PermissionDenied("PERMISSION_DENIED")],
            "key_backup": [DummyResponse(text="ok")],
        }
    )

    result = model.generate_text("prompt", max_retries=2)

    assert result == "ok"
    assert calls["key_primary"] == 1
    assert calls["key_backup"] == 1


def test_does_not_rotate_on_safety_block():
    model, calls = make_model(
        plan_by_key={
            "key_primary": [DummyResponse(prompt_feedback=DummyPromptFeedback("SAFETY"))],
            "key_backup": [DummyResponse(text="ok")],
        }
    )

    with pytest.raises(ProhibitedException):
        model.generate_text("prompt", max_retries=2)

    assert calls["key_primary"] == 1
    assert calls.get("key_backup", 0) == 0


def test_rotates_on_rate_limit_without_sleep(monkeypatch):
    slept: list[float] = []

    def fake_sleep(seconds: float):
        slept.append(seconds)

    # Patch module-level sleep used by GeminiModel
    import core.translation.models.gemini as gemini_module

    monkeypatch.setattr(gemini_module.time, "sleep", fake_sleep)

    model, calls = make_model(
        plan_by_key={
            "key_primary": [google_exceptions.ResourceExhausted("RESOURCE_EXHAUSTED")],
            "key_backup": [DummyResponse(text="ok")],
        }
    )

    result = model.generate_text("prompt", max_retries=2)

    assert result == "ok"
    assert calls["key_primary"] == 1
    assert calls["key_backup"] == 1
    # When a backup key is available, we rotate instead of sleeping on 429.
    assert slept == []
