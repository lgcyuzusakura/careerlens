"""15-minute defence demo: one X-Trace-Id across Vue -> BFF -> Java -> Python.

Synthetic data only. No key, no real resume/JD, no material bodies printed or saved.

    python scripts/demo_chain.py
    python scripts/demo_chain.py --jd-file tests/fixtures/jd-synthetic.txt
    python scripts/demo_chain.py --no-logs
    python scripts/demo_chain.py --include-degradation --trace 0b3d5f70-9c2e-4a61-8d47-6e1f2a3b4c5d

--include-degradation sends useExternalModel=true. Use it ONLY when the running
stack has no real model key configured; otherwise synthetic material would be
sent to a real provider. By default no external call is made.

--trace only sets the header sent by the client. BFF always mints its own trace,
so the on-screen chain trace is the one printed in [2/6]; direct Java and Python
calls reuse that generated trace.

Only localhost targets are accepted. Every printed claim is backed by an
assertion; a skipped log check is reported as skipped, never as PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "demo"
MAX_RESPONSE_BYTES = 1_048_576
MAX_JD_BYTES = 65_536
MAX_JD_CODEPOINTS = 12_000
RESUME = "项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。"
JD = "必须掌握 Java、Spring Boot；Docker 经验优先。"
NO_SKILL_JD = "请积极主动，拥有良好的沟通能力和团队合作精神。"
LOG_SERVICES = {"bff", "domain-api", "ai-service"}

SERVICES = {
    "web": ("http://localhost:3000", "/"),
    "bff": ("http://localhost:8081", "/healthz"),
    "domain-api": ("http://localhost:8080", "/actuator/health/readiness"),
    "ai-service": ("http://localhost:8082", "/healthz"),
}


def call(method: str, url: str, body=None, trace: str | None = None, timeout: int = 26):
    """One bounded HTTP call; connection/timeout failures become a result, not a crash."""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if trace:
        headers["X-Trace-Id"] = trace
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    except (urllib.error.URLError, OSError) as error:
        return {"status": 0, "trace": None, "payload": None, "error": type(error).__name__}
    try:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return {"status": response.status, "trace": response.headers.get("X-Trace-Id"),
                    "payload": None, "error": "RESPONSE_TOO_LARGE"}
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError, OSError):
        payload = None
    return {"status": response.status, "trace": response.headers.get("X-Trace-Id"),
            "payload": payload if isinstance(payload, dict) else None}


def find_docker() -> str | None:
    found = shutil.which("docker")
    if found:
        return found
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe",
        Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def show_logs(trace: str) -> tuple[set[str], int]:
    """Return service names only; never persist raw log lines."""
    docker = find_docker()
    if not docker:
        print("  [跳过] 未找到 docker CLI，同一 trace 的日志断言未执行")
        return set(), 0
    try:
        result = subprocess.run(
            [docker, "compose", "logs", "--since", "15m", "--no-color"],
            cwd=ROOT, capture_output=True, text=True, timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"  [跳过] 读取容器日志失败：{type(error).__name__}")
        return set(), 0
    services: set[str] = set()
    count = 0
    for line in (result.stdout or "").splitlines():
        if trace not in line or '"traceId"' not in line:
            continue
        for candidate in LOG_SERVICES:
            if candidate in line.split("|", 1)[0]:
                services.add(candidate)
                break
        count += 1
        if count <= 12:
            print(f"    {line.strip()[:220]}")
    if not services:
        print("  [注意] 未检索到该 trace 的结构化日志行；请确认容器日志未被清理")
    print(f"  日志命中服务：{', '.join(sorted(services)) or '无'}（{count} 行）")
    return services, count


def brief(result: dict) -> str:
    payload = result.get("payload") or {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    score = data.get("score")
    if isinstance(score, dict):
        return f"score={score.get('value')} matched={score.get('matchedWeight')}/{score.get('totalWeight')}"
    return "score=(Python 不产生分数)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", help="客户端携带的 UUID v4；BFF 会重新生成，链路 trace 以 [2/6] 打印值为准")
    parser.add_argument("--jd-file", type=Path, help="合成 JD 文本；默认使用确定性短 JD")
    parser.add_argument("--no-logs", action="store_true", help="跳过 docker 日志断言（结论会标记为未验证）")
    parser.add_argument("--include-degradation", action="store_true",
                        help="仅在确认未配置真实模型 key 时使用；会发送 useExternalModel=true")
    parser.add_argument("--web", default="http://localhost:3000", help="仅允许 localhost 的前端地址")
    args = parser.parse_args()

    parsed_web = urllib.parse.urlparse(args.web)
    if parsed_web.scheme not in {"http", "https"} or parsed_web.hostname not in {"localhost", "127.0.0.1", "::1"}:
        print("FAIL: --web 只允许 http(s) 且主机为 localhost / 127.0.0.1")
        return 1

    jd_text = JD
    if args.jd_file:
        try:
            raw = args.jd_file.read_bytes()
        except OSError as error:
            print(f"FAIL: 无法读取 JD 文件：{type(error).__name__}")
            return 1
        if len(raw) > MAX_JD_BYTES:
            print("FAIL: JD 文件超过 64 KiB")
            return 1
        try:
            jd_text = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            print("FAIL: JD 文件不是 UTF-8")
            return 1
        if not jd_text or len(jd_text) > MAX_JD_CODEPOINTS:
            print(f"FAIL: JD 为空或超过 {MAX_JD_CODEPOINTS} 个码点")
            return 1

    body = {"resumeText": RESUME, "jdText": jd_text, "options": {"useExternalModel": False}}
    client_trace = args.trace or str(uuid.uuid4())
    report: dict = {"at": datetime.now(timezone.utc).isoformat(), "clientTrace": client_trace,
                    "layers": {}, "errors": {}, "health": {}, "checks": {}}
    failures: list[str] = []

    print("=" * 78)
    print("CareerLens 请求链演示 · 只用合成材料 · 不输出材料正文")
    print("=" * 78)
    print(f"客户端携带的 trace：{client_trace}")
    print("说明：BFF 不接受客户端伪造的 trace，会重新生成；Java / Python 复用上游 trace。\n")

    print("[1/6] 四层健康探针")
    for service, (base, path) in SERVICES.items():
        result = call("GET", base + path, timeout=8)
        ok = result["status"] == 200
        report["health"][service] = result["status"]
        print(f"  {service:11s} {base + path:52s} HTTP {result['status']} {'OK' if ok else 'FAIL'}")
        if not ok:
            failures.append(f"health {service}")

    print("\n[2/6] 浏览器入口：POST /api/v1/analyses（Vue -> BFF -> Java -> Python）")
    analysis = call("POST", args.web + "/api/v1/analyses", body, trace=client_trace)
    trace = analysis["trace"]
    payload = analysis.get("payload") or {}
    envelope_ok = set(payload) == {"code", "msg", "data"}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    print(f"  HTTP {analysis['status']}  code={payload.get('code')}  envelope={envelope_ok}")
    print(f"  链路 trace = {trace}")
    print(f"  mode={data.get('mode')}  {brief(analysis)}")
    print(f"  matches={[m.get('skillId') for m in data.get('matches', [])]}")
    print(f"  gaps={[g.get('skillId') for g in data.get('gaps', [])]}")
    print(f"  evidence={len(data.get('evidence', []))} 条；warnings={[w.get('code') for w in data.get('warnings', [])]}")
    for gap in data.get("gaps", [])[:3]:
        print(f"  缺口措辞示例：{gap.get('reason')}")
    if analysis["status"] != 200 or payload.get("code") != "OK" or not envelope_ok or not trace:
        failures.append("browser analysis")
    if not isinstance(data.get("score"), dict):
        failures.append("browser score missing")
    report["chainTrace"] = trace
    report["layers"]["browser"] = {"status": analysis["status"], "code": payload.get("code"),
                                   "mode": data.get("mode"), "score": (data.get("score") or {}).get("value")}

    print("\n[3/6] 同一 trace 在三个后端服务日志中的证据")
    if args.no_logs or not trace:
        print("  [跳过] --no-logs 或无 trace；同一 trace 日志断言未执行")
        report["checks"]["crossLayerLogs"] = "SKIPPED"
    else:
        services, line_count = show_logs(trace)
        report["logServices"] = sorted(services)
        report["logLineCount"] = line_count
        if len(services) >= 3:
            report["checks"]["crossLayerLogs"] = "PASS"
            print("  断言通过：bff / domain-api / ai-service 三个服务均出现该 trace")
        else:
            report["checks"]["crossLayerLogs"] = "FAIL"
            failures.append("cross-layer trace logs")

    print("\n[4/6] 逐层直连（调试端口，展示每层契约与评分归属）")
    direct = [
        ("BFF", "http://localhost:8081", "/api/v1/analyses", body, True),
        ("Java", "http://localhost:8080", "/api/v1/matches", body, True),
        ("Python", "http://localhost:8082", "/internal/v1/extractions",
         {**body, "contractVersion": "analysis-v1", "skillDictionaryVersion": "skills-v1"}, False),
    ]
    for name, base, path, layer_body, expect_score in direct:
        result = call("POST", base + path, layer_body, trace=trace)
        layer_payload = result.get("payload") or {}
        layer_data = layer_payload.get("data") if isinstance(layer_payload.get("data"), dict) else {}
        has_score = isinstance(layer_data.get("score"), dict)
        print(f"  {name:7s} {base + path:48s} HTTP {result['status']:3d} "
              f"code={str(layer_payload.get('code')):12s} trace={result['trace']} "
              f"score={'有' if has_score else '无'} matches={len(layer_data.get('matches', []))} "
              f"requirements={len(layer_data.get('requirements', []))}")
        if result["status"] != 200 or layer_payload.get("code") != "OK":
            failures.append(f"direct {name}")
        if has_score != expect_score:
            failures.append(f"score ownership {name}")
        if name == "Python" and not layer_data.get("requirements"):
            failures.append("python requirements missing")
        report["layers"][name] = {"status": result["status"], "code": layer_payload.get("code"),
                                  "responseTrace": result["trace"], "hasScore": has_score}
    print("  读法：Python 只返回结构化提取与证据，没有 matches / gaps / score；分数由 Java 计算。")
    print("  读法：BFF 每次生成自己的 trace，直连时响应头与本次链路 trace 不同是预期行为。")

    print("\n[5/6] 边界与错误映射")
    errors = [
        ("空白简历", {**body, "resumeText": " "}, 400, "INVALID_INPUT"),
        ("未知字段", {**body, "unknown": True}, 400, "INVALID_INPUT"),
        ("超大请求", {**body, "resumeText": "a" * 170000}, 413, "PAYLOAD_TOO_LARGE"),
    ]
    for label, error_body, expected_status, expected_code in errors:
        result = call("POST", args.web + "/api/v1/analyses", error_body, trace=client_trace, timeout=40)
        code = (result.get("payload") or {}).get("code")
        print(f"  {label:8s} HTTP {result['status']:3d} code={code}")
        if result["status"] != expected_status or code != expected_code:
            failures.append(f"error {label}")
        report["errors"][label] = {"status": result["status"], "code": code}
    no_skill = call("POST", args.web + "/api/v1/analyses", {**body, "jdText": NO_SKILL_JD})
    no_skill_payload = no_skill.get("payload") or {}
    no_skill_data = no_skill_payload.get("data") if isinstance(no_skill_payload.get("data"), dict) else {}
    no_skill_score = no_skill_data.get("score") or {}
    print(f"  无可识别要求：score.value={no_skill_score.get('value')} "
          f"reason={no_skill_score.get('reason')}")
    if (no_skill["status"] != 200 or no_skill_payload.get("code") != "OK"
            or no_skill_score.get("value") is not None):
        failures.append("null score")
    report["errors"]["noRecognizedRequirements"] = {"score": no_skill_score.get("value"),
                                                    "reason": no_skill_score.get("reason")}

    if args.include_degradation:
        print("  警告：--include-degradation 会发送 useExternalModel=true；"
              "仅在确认运行时未配置真实模型 key 时使用")
        degraded = call("POST", args.web + "/api/v1/analyses",
                        {**body, "options": {"useExternalModel": True}})
        degraded_payload = degraded.get("payload") or {}
        degraded_data = degraded_payload.get("data") if isinstance(degraded_payload.get("data"), dict) else {}
        mode = degraded_data.get("mode")
        print(f"  外部模型请求结果：HTTP {degraded['status']} code={degraded_payload.get('code')} "
              f"mode={mode} warnings={[w.get('code') for w in degraded_data.get('warnings', [])]}")
        if mode == "llm":
            print("  注意：检测到真实模型响应；本次合成材料已发往配置的模型网关")
        if degraded["status"] != 200 or degraded_payload.get("code") != "OK" or mode not in {"rules", "degraded", "llm"}:
            failures.append("degradation")
        report["errors"]["degradation"] = {"mode": mode, "realModelUsed": mode == "llm"}
    else:
        print("  降级演示：未启用（默认不外发；加 --include-degradation 且确认无真实 key 后再演示）")
        report["checks"]["degradation"] = "SKIPPED"

    print("\n[6/6] 汇总")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"chain-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  报告（只含状态码/trace/计数/服务名，不含材料与日志正文）：{target.relative_to(ROOT)}")
    if failures:
        print(f"  FAIL: {', '.join(failures)}")
        return 1
    log_note = "同一 trace 日志已断言" if report["checks"].get("crossLayerLogs") == "PASS" else "同一 trace 日志断言已跳过"
    print(f"  PASS: 四层健康、一次真实链路、逐层契约与评分归属、错误映射；{log_note}；trace={trace}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
