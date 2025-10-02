import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.celery_tasks.illustrations import _resolve_prompt_model_name


def test_resolve_prompt_model_name_uses_override():
    result = _resolve_prompt_model_name("custom-model", {"gemini_model_name": "default-model"})
    assert result == "custom-model"


def test_resolve_prompt_model_name_falls_back_to_default():
    result = _resolve_prompt_model_name(None, {"gemini_model_name": "fallback-model"})
    assert result == "fallback-model"


def test_resolve_prompt_model_name_uses_global_default_when_missing():
    result = _resolve_prompt_model_name(None, None)
    assert result == "gemini-flash-latest"
