import json

import httpx
import pytest

from app.extraction import make_evidence, rules
from app.models import ModelOutput
from app.provider import ModelFailure, model_extract


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://model.example.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic")
    original = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr("app.provider.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))

    return install


EVIDENCE = make_evidence("项目经历\n使用 Java 和 Spring Boot 开发合成管理平台。", "必须掌握 Java，Docker 经验优先。")


async def test_valid_protocol_and_grounded_output(gateway):
    extracted = rules(EVIDENCE)
    output = ModelOutput(structuredResume=extracted.structuredResume, requirements=extracted.requirements)

    def respond(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-test-only"
        body = json.loads(request.content)
        assert body["model"] == "synthetic" and body["temperature"] == 0
        return httpx.Response(200, json={"choices": [{"message": {"content": output.model_dump_json()}}]})

    gateway(respond)
    result = await model_extract(EVIDENCE)
    assert result.structuredResume.skills[0].skillId == "java"


@pytest.mark.parametrize("status,code", [(429, "LLM_RATE_LIMITED"), (500, "LLM_UNAVAILABLE"), (302, "LLM_UNAVAILABLE")])
async def test_http_failures_are_bounded_and_mapped(gateway, status, code):
    gateway(lambda request: httpx.Response(status, text="internal details"))
    with pytest.raises(ModelFailure) as failure:
        await model_extract(EVIDENCE)
    assert failure.value.code == code


async def test_timeout_maps_without_leaking_transport_details(gateway):
    def timeout(request):
        raise httpx.ReadTimeout("private endpoint information")
    gateway(timeout)
    with pytest.raises(ModelFailure) as failure:
        await model_extract(EVIDENCE)
    assert failure.value.code == "LLM_TIMEOUT"


@pytest.mark.parametrize("content", ["not json", '{"choices":[]}', "x" * 262145], ids=["invalid-json", "missing-choice", "oversized"])
async def test_malformed_or_oversized_output_is_rejected(gateway, content):
    gateway(lambda request: httpx.Response(200, content=content))
    with pytest.raises(ModelFailure) as failure:
        await model_extract(EVIDENCE)
    assert failure.value.code == "LLM_INVALID_OUTPUT"


async def test_fabricated_evidence_is_rejected(gateway):
    extracted = rules(EVIDENCE)
    extracted.structuredResume.skills[0].evidenceIds = ["R999"]
    output = ModelOutput(structuredResume=extracted.structuredResume, requirements=extracted.requirements)
    gateway(lambda request: httpx.Response(200, json={"choices": [{"message": {"content": output.model_dump_json()}}]}))
    with pytest.raises(ModelFailure) as failure:
        await model_extract(EVIDENCE)
    assert failure.value.code == "LLM_INVALID_OUTPUT"
