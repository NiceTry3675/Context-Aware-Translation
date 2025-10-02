import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

google_module = sys.modules.setdefault('google', types.ModuleType('google'))
if not hasattr(google_module, 'genai'):
    google_module.genai = types.ModuleType('google.genai')
    sys.modules['google.genai'] = google_module.genai
if not hasattr(google_module.genai, 'errors'):
    google_module.genai.errors = types.SimpleNamespace()
if not hasattr(google_module.genai.errors, 'APIError'):
    google_module.genai.errors.APIError = Exception
if not hasattr(google_module.genai, 'Client'):
    class _FakeClient:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs):
            pass

    google_module.genai.Client = _FakeClient

from core.schemas.narrative_style import (
    AtmosphericQualities,
    CulturalContext,
    NarrativeElements,
    PhysicalWorld,
    VisualMood,
    WorldAtmosphereAnalysis,
)
from core.translation.illustration.world_atmosphere_provider import (
    WorldAtmosphereProvider,
    ensure_world_atmosphere_data,
    extract_world_atmosphere_dict,
)


@pytest.fixture
def sample_analysis() -> WorldAtmosphereAnalysis:
    return WorldAtmosphereAnalysis(
        segment_summary="The hero confronts a rival in a neon-lit alley during a rainstorm.",
        physical_world=PhysicalWorld(
            location="Neon alley",
            architecture_landscape="Rain-slick cobblestones",
            technology_period="Near-future",
            scale_spatial="Tight urban passage",
            material_culture=["holographic signs"],
        ),
        atmosphere=AtmosphericQualities(
            emotional_atmosphere="Tense showdown",
            tension_level="building",
            sensory_details=["rainfall", "distant sirens"],
            pacing_energy="Rapid exchanges",
            implicit_feelings="Mutual respect beneath rivalry",
        ),
        visual_mood=VisualMood(
            lighting_conditions="Neon reflections",
            color_palette=["electric blue", "magenta"],
            weather_environment="Cold rain",
            visual_texture="Glittering puddles",
            time_indicators="Midnight",
        ),
        cultural_context=CulturalContext(
            social_dynamics="Old rivals testing resolve",
            cultural_patterns=["formal dueling etiquette"],
            hierarchy_indicators="Underworld hierarchy",
            communication_style="Measured taunts",
            societal_norms=["honor before victory"],
        ),
        narrative_elements=NarrativeElements(
            point_of_focus="Hero locking eyes with rival",
            dramatic_weight="high",
            symbolic_elements=["flickering neon sign"],
            narrative_connections="Foreshadows imminent alliance",
            scene_role="Escalation before climax",
        ),
    )


@pytest.fixture
def sample_builder(sample_analysis: WorldAtmosphereAnalysis) -> MagicMock:
    builder = MagicMock()
    builder.analyze_world_atmosphere.return_value = sample_analysis
    return builder


def test_provider_reuses_existing_model_instance(sample_builder: MagicMock, sample_analysis: WorldAtmosphereAnalysis) -> None:
    provider = WorldAtmosphereProvider(sample_builder)
    segment = SimpleNamespace(world_atmosphere=sample_analysis)

    result = provider.ensure_world_atmosphere(segment, {}, None, 1, "job")

    assert result is sample_analysis
    sample_builder.analyze_world_atmosphere.assert_not_called()


def test_provider_populates_segment_with_dict(sample_builder: MagicMock, sample_analysis: WorldAtmosphereAnalysis) -> None:
    provider = WorldAtmosphereProvider(sample_builder)
    segment = {"source_text": "The hero darts forward."}

    result = provider.ensure_world_atmosphere(segment, {}, "previous line", 1, "job")

    sample_builder.analyze_world_atmosphere.assert_called_once()
    assert result == sample_analysis
    assert segment["world_atmosphere"]["segment_summary"] == sample_analysis.segment_summary
    assert provider.get_world_atmosphere_dict(segment)["segment_summary"] == sample_analysis.segment_summary


def test_provider_without_builder_returns_none(sample_analysis: WorldAtmosphereAnalysis) -> None:
    provider = WorldAtmosphereProvider(None)
    segment = {"source_text": "The hero catches a breath."}

    result = provider.ensure_world_atmosphere(segment, {}, None, 1, "job")

    assert result is None
    assert "world_atmosphere" not in segment


def test_extract_world_atmosphere_dict_handles_model(sample_analysis: WorldAtmosphereAnalysis) -> None:
    segment = SimpleNamespace(world_atmosphere=sample_analysis)

    extracted = extract_world_atmosphere_dict(segment)

    assert extracted["segment_summary"] == sample_analysis.segment_summary


def test_ensure_world_atmosphere_data_creates_and_reuses(sample_builder: MagicMock, sample_analysis: WorldAtmosphereAnalysis) -> None:
    provider = WorldAtmosphereProvider(sample_builder)
    segments = [{"source_text": "The hero darts forward."}]

    first_data, first_created = ensure_world_atmosphere_data(provider, segments, 0, {}, "job")
    assert first_created is True
    assert first_data["segment_summary"] == sample_analysis.segment_summary
    sample_builder.analyze_world_atmosphere.assert_called_once()

    second_data, second_created = ensure_world_atmosphere_data(provider, segments, 0, {}, "job")
    assert second_created is False
    assert second_data["segment_summary"] == sample_analysis.segment_summary
    sample_builder.analyze_world_atmosphere.assert_called_once()
