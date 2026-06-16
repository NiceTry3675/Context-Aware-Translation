import pytest

from backend.domains.shared.model_factory import (
    _apply_thinking_level,
    allowed_thinking_levels_for_model,
)


def test_flash_models_allow_all_text_thinking_levels():
    for model_name in (
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "google/gemini-3.5-flash",
    ):
        assert allowed_thinking_levels_for_model(model_name) == (
            "minimal",
            "low",
            "medium",
            "high",
        )
        assert _apply_thinking_level({}, model_name, "medium") == {
            "thinking_config": {"thinking_level": "medium"}
        }


def test_pro_models_allow_medium_but_not_minimal():
    for model_name in ("gemini-pro-latest", "gemini-3.1-pro-preview"):
        assert allowed_thinking_levels_for_model(model_name) == ("low", "medium", "high")
        assert _apply_thinking_level({}, model_name, "medium") == {
            "thinking_config": {"thinking_level": "medium"}
        }
        with pytest.raises(ValueError, match="Allowed: low, medium, high"):
            _apply_thinking_level({}, model_name, "minimal")


def test_image_models_expose_image_thinking_levels():
    assert allowed_thinking_levels_for_model("gemini-3.1-flash-image") == ("minimal", "high")
    assert allowed_thinking_levels_for_model("gemini-3-pro-image") == ("high",)

    assert _apply_thinking_level({}, "gemini-3.1-flash-image", "minimal") == {
        "thinking_config": {"thinking_level": "minimal"}
    }
    assert _apply_thinking_level({}, "gemini-3-pro-image", "high") == {
        "thinking_config": {"thinking_level": "high"}
    }
