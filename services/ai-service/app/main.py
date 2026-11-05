import asyncio
import json
import os
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .models import Extraction, ExtractionInput
from .extraction import Unanalyzable, make_evidence, rules
from .provider import ModelFailure, model_extract


app = FastAPI(title="CareerLens AI extraction", version="0.1.0")
slots = asyncio.Semaphore(4)


def envelope(code, msg, data=None, status=200):
    return JSONResponse({"code": code, "msg": msg, "data": data}, status_code=status)


@app.middleware("http")
async def trace_and_limit(request: Request, call_next):
    trace = request.headers.get("X-Trace-Id", "")
    if not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}", trace):
        trace = str(uuid.uuid4())
    request.state.trace_id = trace
    started = time.monotonic()
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 163840:
            response = envelope("PAYLOAD_TOO_LARGE", "材料过大。", status=413)
            response.headers["X-Trace-Id"] = trace
            return response
    request._body = bytes(content)
    try:
        response = await call_next(request)
    except Exception:
        response = envelope("INTERNAL_ERROR", "提取服务暂不可用。", status=500)
    response.headers["X-Trace-Id"] = trace
    response.headers["Cache-Control"] = "no-store"
    if request.url.path.startswith("/internal/"):
        print(json.dumps({"service": "ai-service", "traceId": trace, "status": response.status_code, "durationMs": round((time.monotonic()-started)*1000)}), flush=True)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    return envelope("INVALID_INPUT", "请检查字段类型和文本长度。", {"errors": [{"field": str(item["loc"][-1]), "msg": "字段类型、长度或契约版本不符合要求。"} for item in error.errors()[:20]]}, 400)


@app.exception_handler(HTTPException)
async def http_error(request, error):
    return envelope("NOT_FOUND" if error.status_code == 404 else "INVALID_INPUT", "请求的资源或方法不支持。", status=error.status_code)


@app.get("/healthz")
async def health():
    return {"status": "UP"}


@app.get("/readyz")
async def ready():
    mode = os.getenv("LLM_MODE", "auto")
    configured = all(os.getenv(name) for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"))
    if mode not in {"auto", "rules", "required"} or mode == "required" and not configured:
        return JSONResponse({"status": "DOWN"}, status_code=503)
    return {"status": "UP"}


@app.post("/internal/v1/extractions")
async def extract(payload: ExtractionInput):
    mode = os.getenv("LLM_MODE", "auto")
    if mode not in {"auto", "rules", "required"}:
        return envelope("SERVICE_UNAVAILABLE", "提取模式未正确配置。", status=503)
    try:
        evidence = make_evidence(payload.resumeText, payload.jdText)
    except Unanalyzable:
        return envelope("UNANALYZABLE_INPUT", "请输入有效文本，每份材料最多 250 个非空行。", status=422)
    if mode == "required" and not payload.options.useExternalModel:
        return envelope("INVALID_INPUT", "当前服务要求明确同意使用外部模型。", status=400)
    try:
        await asyncio.wait_for(slots.acquire(), timeout=0.05)
    except TimeoutError:
        response = envelope("RATE_LIMITED", "分析繁忙，请稍后重试。", status=429)
        response.headers["Retry-After"] = "2"
        return response
    try:
        if mode == "rules" or not payload.options.useExternalModel:
            result = rules(evidence)
        else:
            try:
                output = await model_extract(evidence)
                result = Extraction(mode="llm", warnings=[], evidence=evidence, **output.model_dump())
            except ModelFailure as error:
                if mode == "required":
                    return envelope("UPSTREAM_TIMEOUT" if error.code == "LLM_TIMEOUT" else "SERVICE_UNAVAILABLE", "外部模型暂不可用。", status=504 if error.code == "LLM_TIMEOUT" else 503)
                result = rules(evidence, "degraded", error.code)
        return envelope("OK", "提取完成", result.model_dump())
    finally:
        slots.release()
