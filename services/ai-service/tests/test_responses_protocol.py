"""Responses compatibility is verified with an HTTP transport fixture, never a paid key."""
import json

import httpx
import pytest

from app.extraction import make_evidence, rules
from app.models import ModelOutput
from app.provider import ModelFailure, model_extract


EVIDENCE = make_evidence("项目经历\n虚构平台使用 Java 和 Spring Boot 编写 API。", "必须掌握 Java，Docker 经验优先。")


@pytest.fixture
def responses_gateway(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.example.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic-model")
    monkeypatch.setenv("OPENAI_API_STYLE", "responses")
    original = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr("app.provider.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))

    return install


@pytest.mark.parametrize("shape", ["output-text", "message-parts"])
async def test_responses_request_and_grounded_result(responses_gateway, shape):
    extracted = rules(EVIDENCE)
    content = ModelOutput(structuredResume=extracted.structuredResume, requirements=extracted.requirements).model_dump_json()

    def respond(request):
        assert request.url.path == "/v1/responses"
        assert request.headers["Authorization"] == "Bearer synthetic-test-only"
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["model"] == "synthetic-model"
        assert body["text"]["format"]["type"] == "json_object"
        assert body["input"][0]["role"] == "system"
        assert body["input"][1]["role"] == "user"
        assert "messages" not in body and "temperature" not in body
        payload = {"output_text": content} if shape == "output-text" else {"output": [{"type": "message", "content": [{"type": "output_text", "text": content}]}]}
        return httpx.Response(200, json=payload)

    responses_gateway(respond)
    result = await model_extract(EVIDENCE)
    assert {s.skillId for s in result.structuredResume.skills} == {"java", "spring-boot"}


@pytest.mark.parametrize("payload", [{"output": []}, {"output": [{"content": [{"type": "refusal", "refusal": "no"}]}]}, {"output_text": "not JSON"}], ids=["empty", "refusal", "malformed"])
async def test_responses_invalid_output_is_rejected(responses_gateway, payload):
    responses_gateway(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ModelFailure) as error:
        await model_extract(EVIDENCE)
    assert error.value.code == "LLM_INVALID_OUTPUT"


async def test_responses_rejects_fabricated_evidence(responses_gateway):
    extracted = rules(EVIDENCE)
    extracted.structuredResume.skills[0].evidenceIds = ["R999"]
    output = ModelOutput(structuredResume=extracted.structuredResume, requirements=extracted.requirements)
    responses_gateway(lambda request: httpx.Response(200, json={"output_text": output.model_dump_json()}))
    with pytest.raises(ModelFailure) as error:
        await model_extract(EVIDENCE)
    assert error.value.code == "LLM_INVALID_OUTPUT"
