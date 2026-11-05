"""Exercise SSE through a real local TCP gateway with synthetic materials only."""
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from app.extraction import make_evidence
from app.provider import model_extract
from tests.model_gateway import Handler


@pytest.mark.parametrize("style", ["chat", "responses"])
async def test_real_http_streaming_gateway(monkeypatch, style):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic-fixture")
    monkeypatch.setenv("OPENAI_API_STYLE", style)
    monkeypatch.setenv("ALLOW_HTTP_MODEL", "true")
    try:
        evidence = make_evidence("项目经历\n虚构课程平台使用 Java 和 Spring Boot，实现 REST API。", "必须掌握 Java，Docker 经验优先。")
        result = await model_extract(evidence)
        assert {skill.skillId for skill in result.structuredResume.skills} >= {"java", "spring-boot"}
        assert {item.skillId for item in result.requirements} == {"java", "docker"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
