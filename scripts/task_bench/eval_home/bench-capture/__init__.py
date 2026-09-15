"""bench-capture — provider response metadata recorder for model evaluations.

Appends one JSON line per API call to the file named by the
``XAVANI_BENCH_META`` environment variable. The line carries the
requested model, the provider response metadata (served model, usage,
finish reason, timing), and the session identifiers so an evaluation
report can attribute every call to a run.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _meta_path() -> str:
    path = os.getenv("XAVANI_BENCH_META", "").strip()
    if path:
        return path
    home = os.getenv("XAVANI_HOME", "").strip()
    if home:
        return os.path.join(home, "bench-meta.jsonl")
    return ""


def _record(**kwargs) -> None:
    path = _meta_path()
    if not path:
        return
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": kwargs.get("session_id"),
        "task_id": kwargs.get("task_id"),
        "model": kwargs.get("model"),
        "provider": kwargs.get("provider"),
        "base_url": kwargs.get("base_url"),
        "api_mode": kwargs.get("api_mode"),
        "api_call": kwargs.get("api_call_count"),
        "api_duration": kwargs.get("api_duration"),
        "finish_reason": kwargs.get("finish_reason"),
        "response_model": kwargs.get("response_model"),
        "usage": kwargs.get("usage"),
        "assistant_content_chars": kwargs.get("assistant_content_chars"),
        "assistant_tool_call_count": kwargs.get("assistant_tool_call_count"),
    }
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # A capture failure must never break an evaluation run.
        pass


def register(ctx) -> None:
    ctx.register_hook("post_api_request", _record)
