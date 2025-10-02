from core.translation.models.gemini import GeminiModel


class DummyFunctionCall:
    def __init__(self, args):
        self.name = "structured"
        self.args = args


class DummyPart:
    def __init__(self, *, function_call=None, text=None):
        self.function_call = function_call
        self.function_response = None
        self.text = text
        self.thought = False


class DummyContent:
    def __init__(self, parts):
        self.parts = parts


class DummyCandidate:
    def __init__(self, parts):
        self.content = DummyContent(parts)


class DummyResponse:
    def __init__(self, parts):
        self.candidates = [DummyCandidate(parts)]
        self.parsed = None
        self.text = None
        self.usage_metadata = None

    @property
    def parts(self):
        return self.candidates[0].content.parts


class DummyModels:
    def __init__(self, response):
        self._response = response

    def generate_content(self, **_kwargs):
        return self._response


class DummyClient:
    def __init__(self, response):
        self.models = DummyModels(response)


def make_model(response):
    return GeminiModel(
        api_key=None,
        model_name="test-model",
        safety_settings=[],
        generation_config={},
        enable_soft_retry=False,
        client=DummyClient(response),
    )


def test_generate_structured_handles_function_call_args_dict():
    response = DummyResponse([
        DummyPart(function_call=DummyFunctionCall({"terms": ["Alpha", "Beta"]})),
    ])
    model = make_model(response)

    schema = {"type": "object"}
    result = model.generate_structured("prompt", schema, max_retries=1)

    assert result == {"terms": ["Alpha", "Beta"]}


def test_generate_structured_handles_function_call_args_json_string():
    response = DummyResponse([
        DummyPart(
            function_call=DummyFunctionCall("""```json\n{\n  \"terms\": [\"Gamma\"]\n}\n```"""),
        ),
    ])
    model = make_model(response)

    schema = {"type": "object"}
    result = model.generate_structured("prompt", schema, max_retries=1)

    assert result == {"terms": ["Gamma"]}


def test_generate_structured_handles_text_fallback():
    response = DummyResponse([
        DummyPart(text="""```json\n{\"items\": [1, 2, 3]}\n```"""),
    ])
    model = make_model(response)

    schema = {"type": "object"}
    result = model.generate_structured("prompt", schema, max_retries=1)

    assert result == {"items": [1, 2, 3]}


def test_generate_structured_allows_empty_payload():
    response = DummyResponse([])
    model = make_model(response)

    schema = {"type": "object"}
    result = model.generate_structured("prompt", schema, max_retries=1)

    assert result == {}
