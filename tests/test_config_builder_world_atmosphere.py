from core.config.builder import DynamicConfigBuilder


class DummyModel:
    def __init__(self):
        self.calls = 0

    def generate_structured(self, prompt, schema):
        self.calls += 1
        return {}


def test_world_atmosphere_empty_payload_is_tolerated():
    model = DummyModel()
    builder = DynamicConfigBuilder(model, "Protagonist")

    result = builder._analyze_world_atmosphere(
        segment_text="Short heading",
        previous_context=None,
        glossary={},
        job_base_filename="test",
        segment_index=0,
    )

    assert result is None
    assert model.calls == 1
