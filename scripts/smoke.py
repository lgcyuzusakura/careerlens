"""Exercise the real four-service HTTP chain with synthetic data only."""
import json
import os
import urllib.error
import urllib.request


BASE = os.getenv("WEB_BASE_URL", "http://localhost:3000")
BODY = {"resumeText": "项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。", "jdText": "必须掌握 Java、Spring Boot；Docker 经验优先。", "options": {"useExternalModel": False}}


def call(path, body=None, status=200, base=BASE):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(request, timeout=26)
    except urllib.error.HTTPError as error:
        response = error
    assert response.status == status, (path, response.status, response.read().decode())
    trace = response.headers.get("X-Trace-Id")
    result = json.loads(response.read())
    assert set(result) == {"code", "msg", "data"}
    assert trace and len(trace) == 36
    return result, trace


def main():
    templates, _ = call("/api/v1/job-templates")
    assert len(templates["data"]["items"]) >= 2
    result, trace = call("/api/v1/analyses", BODY)
    data = result["data"]
    assert data["score"] == {"value": 86, "matchedWeight": 6, "totalWeight": 7, "reason": "WEIGHTED_SKILL_COVERAGE"}, data["score"]
    assert {item["skillId"] for item in data["matches"]} == {"java", "spring-boot"}
    assert {item["skillId"] for item in data["gaps"]} == {"docker"}
    assert data["mode"] == "rules"
    for port, path, payload in [(8081,"/api/v1/analyses",BODY),(8080,"/api/v1/matches",BODY),(8082,"/internal/v1/extractions",{**BODY,"contractVersion":"analysis-v1","skillDictionaryVersion":"skills-v1"})]:
        direct, _ = call(path,payload,base=f"http://localhost:{port}")
        assert direct["code"] == "OK"
    call("/api/v1/analyses", {**BODY, "resumeText": " "}, 400)
    call("/api/v1/analyses", {**BODY, "unknown": True}, 400)
    call("/api/v1/analyses", {**BODY, "resumeText": "a" * 170000}, 413)
    unicode_result, _ = call("/api/v1/analyses", {**BODY, "resumeText": "😀" * 15000 + " Java"})
    assert len(unicode_result["data"]["evidence"][0]["text"]) == 15005
    no_requirements, _ = call("/api/v1/analyses", {**BODY, "jdText": "请积极主动，拥有良好的沟通能力和团队合作精神。"})
    assert no_requirements["data"]["score"]["value"] is None
    result, _ = call("/api/v1/analyses", {**BODY, "options": {"useExternalModel": True}})
    expected = os.getenv("EXPECTED_EXTERNAL_MODE", "degraded")
    assert result["data"]["mode"] == expected, result["data"]["mode"]
    print(f"PASS four-service HTTP smoke; 86/100, gaps, direct REST, 400, null score, external={expected}; traceId={trace}")


if __name__ == "__main__":
    main()
