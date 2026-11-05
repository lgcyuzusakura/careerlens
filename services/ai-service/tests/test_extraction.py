import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models import ModelOutput
from app.extraction import clean, make_evidence, rules, validate_model


BODY = {"resumeText": "项目经历\n使用 Java 和 Spring Boot 开发合成管理 API，使用 JUnit 测试。", "jdText": "必须熟悉 Java、Spring Boot；Docker 经验优先。", "options": {"useExternalModel": False}, "contractVersion": "analysis-v1", "skillDictionaryVersion": "skills-v1"}


def test_cleaning_normalizes_and_redacts():
    assert clean("Ｊａｖａ\r\n  示例  文本\u200b") == ["Java", "示例 文本"]
    assert "@" not in clean("联系：synthetic@example.invalid，13800000000")[0]
    assert "13800000000" not in clean("联系：synthetic@example.invalid，13800000000")[0]


def test_boundaries_and_negation():
    data = rules(make_evidence("技能：JavaScript，C++，未使用过 Redis，熟悉 Vue 3。", "必须掌握 Java 和 C；Redis 经验优先。"))
    ids = {item.skillId for item in data.structuredResume.skills}
    assert "javascript" in ids and "cpp" in ids and "vue3" in ids
    assert not ids.intersection({"java", "c", "redis"})


def test_priority_and_exact_evidence():
    result = rules(make_evidence(BODY["resumeText"], BODY["jdText"]))
    priorities = {item.skillId: item.priority for item in result.requirements}
    assert priorities == {"java": "required", "spring-boot": "required", "docker": "preferred"}
    output = ModelOutput(structuredResume=result.structuredResume, requirements=result.requirements)
    output.structuredResume.skills[0].evidenceIds = ["J1"]
    with pytest.raises(ValueError):
        validate_model(output, result.evidence)


async def test_endpoint_rules_and_trace(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "auto")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/internal/v1/extractions", json=BODY)
        assert response.status_code == 200
        assert set(response.json()) == {"code", "msg", "data"}
        assert response.json()["data"]["mode"] == "rules"
        assert response.headers["X-Trace-Id"]


async def test_invalid_input_and_extra_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for data in [{**BODY, "resumeText": " " * 30}, {**BODY, "extra": True}, {**BODY, "options": {"useExternalModel": "false"}}]:
            response = await client.post("/internal/v1/extractions", json=data)
            assert response.status_code == 400
            assert "input" not in response.json().get("data", {})


async def test_missing_key_is_explicit_degradation(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "auto")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/internal/v1/extractions", json={**BODY, "options": {"useExternalModel": True}})
        assert response.json()["data"]["mode"] == "degraded"
        assert response.json()["data"]["warnings"][0]["code"] == "LLM_NOT_CONFIGURED"


async def test_required_never_sends_without_consent(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "required")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/internal/v1/extractions", json=BODY)).status_code == 400


async def test_model_failure_falls_back(monkeypatch):
    from app.provider import ModelFailure
    async def failed(evidence):
        raise ModelFailure("LLM_TIMEOUT")
    monkeypatch.setattr("app.main.model_extract", failed)
    monkeypatch.setenv("LLM_MODE", "auto")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/internal/v1/extractions", json={**BODY, "options": {"useExternalModel": True}})
        assert response.status_code == 200
        assert response.json()["data"]["warnings"][0]["code"] == "LLM_TIMEOUT"
