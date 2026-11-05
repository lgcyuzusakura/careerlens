"""Consume bounded OpenAI-compatible SSE with explicit completion checks."""
import json

import httpx
from httpx_sse import EventSource


MAX_OUTPUT_BYTES = 262144
MAX_STREAM_BYTES = 1048576
MAX_EVENTS = 4096


class StreamFailure(Exception):
    def __init__(self, code="LLM_INVALID_OUTPUT"):
        self.code = code


class BoundedStream(httpx.AsyncByteStream):
    def __init__(self, response, limit):
        self.response, self.limit = response, limit

    async def __aiter__(self):
        size = 0
        async for chunk in self.response.aiter_bytes():
            size += len(chunk)
            if size > self.limit:
                raise StreamFailure()
            yield chunk


def response_text(data):
    return data.get("output_text") or "".join(
        part.get("text", "")
        for item in data.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )


def checked_text(text):
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise StreamFailure()
    return text


async def read_model_response(response, style):
    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "text/event-stream":
        # Some compatible gateways ignore stream=true and return a complete JSON body.
        data = bytearray()
        async for chunk in BoundedStream(response, MAX_OUTPUT_BYTES):
            data.extend(chunk)
        decoded = json.loads(data)
        if style == "responses":
            if decoded.get("status") in {"failed", "incomplete", "cancelled"}:
                raise StreamFailure()
            return checked_text(response_text(decoded))
        choice = decoded["choices"][0]
        if choice.get("finish_reason") in {"length", "content_filter", "tool_calls"}:
            raise StreamFailure()
        return checked_text(choice["message"]["content"])

    bounded = httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=BoundedStream(response, MAX_STREAM_BYTES))
    fragments, size, events, stopped = [], 0, 0, False
    async for event in EventSource(bounded).aiter_sse():
        events += 1
        if events > MAX_EVENTS:
            raise StreamFailure()
        if not event.data:
            continue
        if event.data == "[DONE]":
            if style != "responses" and stopped:
                return checked_text("".join(fragments))
            raise StreamFailure()
        data = json.loads(event.data)
        if not isinstance(data, dict):
            raise StreamFailure()
        kind = data.get("type", event.event)
        if kind in {"error", "response.failed"} or data.get("error"):
            raise StreamFailure("LLM_UNAVAILABLE")
        if kind in {"response.incomplete", "response.cancelled"}:
            raise StreamFailure()
        delta = None
        if style == "responses":
            if kind == "response.output_text.delta":
                delta = data.get("delta")
            elif kind == "response.completed":
                completed = data.get("response", {})
                if completed.get("status", "completed") != "completed":
                    raise StreamFailure()
                text = "".join(fragments)
                final = response_text(completed)
                if final and text and final != text:
                    raise StreamFailure()
                return checked_text(final or text)
        else:
            choices = data.get("choices", [])
            if not choices:
                continue
            choice = choices[0]
            if choice.get("index", 0) != 0:
                raise StreamFailure()
            reason = choice.get("finish_reason")
            if reason is not None:
                if reason != "stop":
                    raise StreamFailure()
                stopped = True
            delta = choice.get("delta", {}).get("content")
        if delta is not None:
            if not isinstance(delta, str):
                raise StreamFailure()
            size += len(delta.encode("utf-8"))
            if size > MAX_OUTPUT_BYTES:
                raise StreamFailure()
            fragments.append(delta)
    # EOF without a terminal event must never turn a partial answer into a result.
    raise StreamFailure()
