"""ASGI app for the Xavani Omera API surface."""
from __future__ import annotations

import hmac
import json
import time
import uuid

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from xavani_omera import inference
from xavani_omera.capabilities import omera_service_payload, research_capabilities
from xavani_omera.chat_research import research_system_block
from xavani_omera.config import Settings

MAX_BODY_BYTES = 262_144
MAX_MESSAGES = 40
MAX_MESSAGE_CHARS = 8000
MAX_TOTAL_CHARS = 32_000
ROOT_KEYS = {"model", "messages", "stream", "xavani_research"}

app = FastAPI(title="Xavani Omera API", docs_url=None, redoc_url=None, openapi_url=None)
router = APIRouter()


def _error(message: str, status: int, kind: str = "invalid_request_error") -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": kind}}, status_code=status)


def _authorized(request: Request, settings: Settings) -> bool:
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        return False
    supplied = header[7:]
    for candidate in (settings.api_key, settings.api_key_previous):
        if candidate and hmac.compare_digest(supplied, candidate):
            return True
    return False


def _parse(body: dict) -> tuple[str | None, list[dict], str, bool, bool]:
    """Return (system prompt, conversation, last user text, stream, research)."""
    if set(body) - ROOT_KEYS:
        raise ValueError("UNKNOWN_ROOT_FIELD")
    messages = body.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError("INVALID_MESSAGES")

    system_parts: list[str] = []
    conversation: list[dict] = []
    total = 0
    for item in messages:
        if not isinstance(item, dict) or set(item) != {"role", "content"}:
            raise ValueError("INVALID_MESSAGE")
        role = item["role"]
        content = item["content"]
        if role not in {"system", "user", "assistant"}:
            raise ValueError("INVALID_ROLE")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("INVALID_CONTENT")
        if len(content) > MAX_MESSAGE_CHARS:
            raise ValueError("MESSAGE_TOO_LONG")
        total += len(content)
        if role == "system":
            system_parts.append(content)
        else:
            conversation.append({"role": role, "content": content})

    if total > MAX_TOTAL_CHARS or not conversation:
        raise ValueError("INVALID_CONVERSATION")
    if conversation[-1]["role"] != "user":
        raise ValueError("LAST_MESSAGE_MUST_BE_USER")

    stream = bool(body.get("stream", False))
    research = body.get("xavani_research", True)
    if not isinstance(research, bool):
        raise ValueError("INVALID_RESEARCH_FLAG")
    return "\n".join(system_parts) or None, conversation, conversation[-1]["content"], stream, research


@router.get("/health")
async def health():
    settings = Settings.from_env()
    return {
        "status": "ok" if settings.configured else "unconfigured",
        "service": "xavani-omera",
        "research": research_capabilities(),
        "inference": bool(settings.inference_api_key and settings.inference_model),
        "model": settings.model_name,
    }


@router.get("/v1/capabilities")
async def capabilities(request: Request):
    settings = Settings.from_env()
    if not settings.api_key or not _authorized(request, settings):
        return _error("Unauthorized.", 401, "authentication_error")
    payload = omera_service_payload(settings.model_name)
    return {
        "object": "xavani.api_server.capabilities",
        **payload,
        "features": {
            "chat_completions": True,
            "chat_completions_streaming": True,
            "responses_api": False,
            "run_submission": False,
            "profiles_api": False,
            "skills_api": False,
            "session_continuity_header": None,
            "session_key_header": None,
        },
    }


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    settings = Settings.from_env()
    try:
        settings.validate()
    except ValueError:
        return _error("Service is not configured.", 503, "service_unavailable")
    if not _authorized(request, settings):
        return _error("Unauthorized.", 401, "authentication_error")

    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return _error("Request body too large.", 413)
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("INVALID_BODY")
        system_prompt, conversation, user_message, stream, research = _parse(body)
    except (json.JSONDecodeError, ValueError):
        return _error("Invalid request.", 400)

    if research:
        block = await research_system_block(user_message)
        if block:
            system_prompt = f"{system_prompt}\n\n{block}" if system_prompt else block

    upstream = (
        [{"role": "system", "content": system_prompt}] if system_prompt else []
    ) + conversation
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    created = int(time.time())

    if not stream:
        try:
            content = await inference.complete(upstream, settings)
        except Exception:
            return _error("Model is unavailable.", 502, "upstream_error")
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": settings.model_name,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "xavani": {"completed": True, "partial": False, "failed": False},
        }

    iterator = inference.stream(upstream, settings)
    try:
        first = await iterator.__anext__()
    except StopAsyncIteration:
        return _error("Model returned no content.", 502, "upstream_error")
    except Exception:
        return _error("Model is unavailable.", 502, "upstream_error")

    async def frames():
        try:
            yield _chunk(completion_id, created, settings.model_name, first)
            async for token in iterator:
                yield _chunk(completion_id, created, settings.model_name, token)
        except Exception:
            yield _final(completion_id, created, settings.model_name, "error")
            yield "data: [DONE]\n\n"
            return
        yield _final(completion_id, created, settings.model_name, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(frames(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


def _chunk(completion_id, created, model, token) -> str:
    return "data: " + json.dumps({
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
    }) + "\n\n"


def _final(completion_id, created, model, reason) -> str:
    return "data: " + json.dumps({
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": reason}],
    }) + "\n\n"


app.include_router(router)
app.include_router(router, prefix="/api/index")
