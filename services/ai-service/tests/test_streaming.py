import json

import httpx
import pytest

from app.extraction import make_evidence, rules
from app.models import ModelOutput
from app.provider import ModelFailure, model_extract
from app.streaming import MAX_STREAM_BYTES, StreamFailure, read_model_response


def event(data, name=None):
    prefix = f"event: {name}\n" if name else ""
    return (prefix + "data: " + (data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)) + "\n\n").encode("utf-8")


class Chunks(httpx.AsyncByteStream):
    def __init__(self, body, size=7, timeout=False):
        self.body, self.size, self.timeout = body, size, timeout

    async def __aiter__(self):
        for start in range(0, len(self.body), self.size):
            yield self.body[start:start+self.size]
        if self.timeout:
            raise httpx.ReadTimeout("synthetic-private-transport-canary")


def response(body, size=7, timeout=False):
    return httpx.Response(200, headers={"content-type": "text/event-stream; charset=utf-8"}, stream=Chunks(body, size, timeout))


def chat_stream(text, done=True, reason="stop"):
    body = b": heartbeat\n\n" + event({"choices": [{"index": 0, "delta": {"role": "assistant"}}]})
    for start in range(0, len(text), 17):
        body += event({"choices": [{"index": 0, "delta": {"content": text[start:start+17]}}]})
    body += event({"choices": [{"index": 0, "delta": {}, "finish_reason": reason}]})
    return body + (event("[DONE]") if done else b"")


def responses_stream(text, done=True):
    body = event({"type": "response.created"}, "response.created")
    for start in range(0, len(text), 17):
        body += event({"type": "response.output_text.delta", "delta": text[start:start+17]}, "response.output_text.delta")
    body += event({"type": "response.output_text.done", "text": text}, "response.output_text.done")
    if done:
        body += event({"type": "response.completed", "response": {"status": "completed", "output": [{"content": [{"type": "output_text", "text": text}]}]}}, "response.completed")
    return body


@pytest.mark.parametrize("style", ["chat", "responses"])
@pytest.mark.parametrize("chunk_size", [1, 7, 256])
async def test_sse_reassembles_utf8_split_across_network_chunks(style, chunk_size):
    text = json.dumps({"synthetic": "虚构简历与技能：Java，Python", "note": "multi\nline"}, ensure_ascii=False)
    body = chat_stream(text) if style == "chat" else responses_stream(text)
    assert await read_model_response(response(body, chunk_size), style) == text


@pytest.mark.parametrize("style", ["chat", "responses"])
async def test_stream_eof_without_terminal_event_is_not_success(style):
    body = chat_stream('{"synthetic":true}', done=False) if style == "chat" else responses_stream('{"synthetic":true}', done=False)
    with pytest.raises(StreamFailure):
        await read_model_response(response(body), style)


@pytest.mark.parametrize("reason", ["length", "content_filter", "tool_calls"])
async def test_chat_refuses_truncated_filtered_or_tool_output(reason):
    with pytest.raises(StreamFailure):
        await read_model_response(response(chat_stream('{"synthetic":true}', reason=reason)), "chat")


@pytest.mark.parametrize("kind,code", [("error", "LLM_UNAVAILABLE"), ("response.failed", "LLM_UNAVAILABLE"), ("response.incomplete", "LLM_INVALID_OUTPUT")])
async def test_responses_terminal_errors_are_classified(kind, code):
    with pytest.raises(StreamFailure) as error:
        await read_model_response(response(event({"type": kind})), "responses")
    assert error.value.code == code


async def test_completed_response_cannot_replace_streamed_text():
    body = event({"type": "response.output_text.delta", "delta": '{"synthetic":true}'})
    body += event({"type": "response.completed", "response": {"status": "completed", "output_text": '{"different":true}'}})
    with pytest.raises(StreamFailure):
        await read_model_response(response(body), "responses")


@pytest.mark.parametrize("body", [b"data: invalid-json\n\n", event("[DONE]"), event({"choices": [{"delta": {"content": {"invalid": True}}}]})], ids=["invalid-json", "done-without-content", "non-text-delta"])
async def test_malformed_stream_never_becomes_a_result(body):
    with pytest.raises((StreamFailure, ValueError)):
        await read_model_response(response(body), "chat")


async def test_stream_wire_budget_applies_before_newline_and_json_decoding():
    with pytest.raises(StreamFailure):
        await read_model_response(response(b"data: " + b"x" * MAX_STREAM_BYTES, 65536), "chat")


async def test_output_and_event_budgets_are_bounded():
    for body in [event({"choices": [{"delta": {"content": "x" * 262145}}]}), event({}) * 4097]:
        with pytest.raises(StreamFailure):
            await read_model_response(response(body, 65536), "chat")


@pytest.mark.parametrize("style", ["chat", "responses"])
async def test_provider_requests_stream_and_validates_complete_evidence(monkeypatch, style):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.example.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic")
    monkeypatch.setenv("OPENAI_API_STYLE", style)
    evidence = make_evidence("项目经历\n虚构平台使用 Java 和 Docker 部署接口。", "必须掌握 Java，Docker 经验优先。")
    extracted = rules(evidence)
    text = ModelOutput(structuredResume=extracted.structuredResume, requirements=extracted.requirements).model_dump_json()
    original = httpx.AsyncClient

    def handler(request):
        body = json.loads(request.content)
        assert body["stream"] is True
        assert request.headers["Accept"] == "text/event-stream"
        assert request.url.path == ("/v1/responses" if style == "responses" else "/v1/chat/completions")
        return response(responses_stream(text) if style == "responses" else chat_stream(text))

    monkeypatch.setattr("app.provider.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = await model_extract(evidence)
    assert {skill.skillId for skill in result.structuredResume.skills} == {"java", "docker"}


async def test_stream_read_timeout_maps_to_safe_failure(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.example.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic")
    monkeypatch.setenv("OPENAI_API_STYLE", "chat")
    original = httpx.AsyncClient
    monkeypatch.setattr("app.provider.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(lambda request: response(event({"choices": [{"delta": {"content": "{"}}]}), timeout=True)), **kwargs))
    with pytest.raises(ModelFailure) as error:
        await model_extract(make_evidence("Synthetic Java project with tests", "Java and Docker required"))
    assert error.value.code == "LLM_TIMEOUT"
