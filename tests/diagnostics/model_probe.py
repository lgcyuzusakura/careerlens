"""Probe the running Python container using a synthetic prompt; print metadata only."""
import argparse
import subprocess


PROBE = r'''
import asyncio, inspect, json, os, time
import httpx
from app import provider

async def main():
    style = os.environ.get("PROBE_STYLE", "responses")
    key, base, model = (os.getenv(name, "") for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"))
    print(json.dumps({"configured": bool(key and base and model), "runtimeStyle": os.getenv("OPENAI_API_STYLE", "chat"), "responsesSupported": "/responses" in inspect.getsource(provider), "probeStyle": style}), flush=True)
    if not key or not base or not model:
        return
    if os.getenv("PROBE_EXTRACTION") == "true":
        from unittest.mock import patch
        from app.extraction import make_evidence
        original_client, original_timeout = httpx.AsyncClient, asyncio.timeout
        def client_with_budget(**kwargs):
            kwargs["timeout"] = httpx.Timeout(40, connect=5, pool=1)
            return original_client(**kwargs)
        evidence=make_evidence("虚构课程平台使用 Java 和 Spring Boot 编写 API，使用 Docker 部署。", "必须掌握 Java 和 Spring Boot，Docker 经验优先。")
        started=time.monotonic()
        with patch.object(provider.httpx, "AsyncClient", client_with_budget), patch.object(provider.asyncio, "timeout", lambda seconds: original_timeout(45)):
            try:
                result=await provider.model_extract(evidence)
                print(json.dumps({"stage": "full-extraction", "schemaAndEvidenceValid": True, "elapsedMs": round((time.monotonic()-started)*1000), "skillCount": len(result.structuredResume.skills)}), flush=True)
            except provider.ModelFailure as error:
                print(json.dumps({"stage": "full-extraction", "schemaAndEvidenceValid": False, "failureCode": error.code, "elapsedMs": round((time.monotonic()-started)*1000)}), flush=True)
        return
    payload = {"model": model, "input": "Return this JSON object exactly: {\"synthetic\":true}", "max_output_tokens": 128, "store": False} if style == "responses" else {"model": model, "messages": [{"role": "user", "content": "Return this JSON object exactly: {\"synthetic\":true}"}], "max_tokens": 128}
    endpoint = "/responses" if style == "responses" else "/chat/completions"
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(40, connect=5), follow_redirects=False, trust_env=False) as client:
            async with client.stream("POST", base.rstrip("/")+endpoint, json=payload, headers={"Authorization": "Bearer "+key}) as response:
                print(json.dumps({"stage": "headers", "status": response.status_code, "elapsedMs": round((time.monotonic()-started)*1000), "contentType": response.headers.get("content-type", "").split(";")[0]}), flush=True)
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 262144:
                        print(json.dumps({"stage": "body", "tooLarge": True}), flush=True)
                        return
                try:
                    data=json.loads(content)
                    output=data.get("output_text") or "".join(part.get("text", "") for item in data.get("output", []) for part in item.get("content", []) if part.get("type")=="output_text")
                    if style!="responses":
                        output=(data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                    print(json.dumps({"stage": "body", "elapsedMs": round((time.monotonic()-started)*1000), "json": True, "hasModelOutput": bool(output), "bytes": len(content), "hasError": bool(data.get("error"))}), flush=True)
                except (ValueError, TypeError, AttributeError):
                    print(json.dumps({"stage": "body", "elapsedMs": round((time.monotonic()-started)*1000), "json": False, "bytes": len(content)}), flush=True)
    except Exception as error:
        print(json.dumps({"stage": "transport", "exception": type(error).__name__, "elapsedMs": round((time.monotonic()-started)*1000)}), flush=True)

asyncio.run(main())
'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=["responses", "chat"], default="responses")
    parser.add_argument("--full-extraction", action="store_true", help="Run the current extractor with a temporary 45-second budget in a separate process")
    args = parser.parse_args()
    subprocess.run(["docker", "compose", "exec", "-T", "-e", f"PROBE_STYLE={args.style}", "-e", f"PROBE_EXTRACTION={str(args.full_extraction).lower()}", "ai-service", "python", "-c", PROBE], check=True)
