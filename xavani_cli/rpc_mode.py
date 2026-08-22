# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""NDJSON-over-stdio RPC mode for embedders.

One JSON frame per line. Every request carries ``id`` and ``method``;
every response echoes ``id``. Tool calls surface as answerable cards:
the embedder receives a ``tool_request`` result and answers with a
``tool_response`` frame carrying ``approve`` or ``deny``.

Entry point: ``python3 -m xavani_cli.rpc_mode``.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import uuid
from typing import Any, Callable, TextIO


class RpcSession:
    """Protocol core: frames in, frames out, no I/O of its own."""

    def __init__(
        self,
        chat_fn: Callable[[str], str],
        tools_fn: Callable[[], list[dict]],
    ):
        self._chat_fn = chat_fn
        self._tools_fn = tools_fn
        self._pending_cards: dict[str, dict[str, Any]] = {}
        self._resolved_cards: dict[str, dict[str, Any]] = {}

    def resolved_cards(self) -> dict[str, dict[str, Any]]:
        return dict(self._resolved_cards)

    def handle_frame(self, frame: dict[str, Any]) -> dict[str, Any]:
        """Dispatch one decoded request frame to its response."""
        frame_id = frame.get("id")
        method = frame.get("method")
        if not isinstance(frame_id, (str, int)) or not isinstance(method, str):
            return {"id": frame.get("id"), "error": "frame must have id and method"}
        handler = getattr(self, f"_rpc_{method.replace('/', '_')}", None)
        if handler is None or method.startswith("_"):
            return {"id": frame_id, "error": f"unknown method: {method}"}
        return handler(frame_id, frame.get("params") or {})

    def handle_line(self, line: str) -> str:
        """Decode one input line into one response line."""
        if not line.strip():
            return ""
        try:
            frame = json.loads(line)
        except json.JSONDecodeError as exc:
            response: dict[str, Any] = {"id": None, "error": f"invalid json: {exc}"}
            return json.dumps(response, ensure_ascii=False) + "\n"
        if not isinstance(frame, dict):
            response = {"id": None, "error": "frame must be a JSON object"}
            return json.dumps(response, ensure_ascii=False) + "\n"
        response = self.handle_frame(frame)
        return json.dumps(response, ensure_ascii=False) + "\n"

    def _rpc_ping(self, frame_id: Any, _params: dict) -> dict[str, Any]:
        return {"id": frame_id, "result": {"pong": True, "version": get_version()}}

    def _rpc_chat(self, frame_id: Any, params: dict) -> dict[str, Any]:
        message = params.get("message")
        if not isinstance(message, str) or not message.strip():
            return {
                "id": frame_id,
                "error": "params.message must be a non-empty string",
            }
        return {"id": frame_id, "result": {"reply": self._chat_fn(message)}}

    def _rpc_tools_list(self, frame_id: Any, _params: dict) -> dict[str, Any]:
        return {"id": frame_id, "result": {"tools": self._tools_fn()}}

    def _rpc_tool_request(self, frame_id: Any, params: dict) -> dict[str, Any]:
        tool = params.get("tool")
        args = params.get("args")
        if not isinstance(tool, str) or not tool.strip():
            return {"id": frame_id, "error": "params.tool must be a non-empty string"}
        if not isinstance(args, dict):
            args = {}
        card_id = uuid.uuid4().hex[:12]
        card = {"card_id": card_id, "tool": tool, "args": args}
        self._pending_cards[card_id] = card
        return {
            "id": frame_id,
            "result": {
                **card,
                "status": "awaiting_response",
                "question": (
                    f"Approve tool {tool}? Reply with a tool_response frame."
                ),
            },
        }

    def _rpc_tool_response(self, frame_id: Any, params: dict) -> dict[str, Any]:
        card_id = params.get("card_id")
        decision = params.get("decision")
        if not isinstance(card_id, str):
            return {"id": frame_id, "error": "params.card_id must be a string"}
        if decision not in ("approve", "deny"):
            return {
                "id": frame_id,
                "error": "params.decision must be 'approve' or 'deny'",
            }
        card = self._pending_cards.pop(card_id, None)
        if card is None:
            return {"id": frame_id, "error": "unknown card_id"}
        resolved = {**card, "status": "approved" if decision == "approve" else "denied"}
        self._resolved_cards[card_id] = resolved
        return {"id": frame_id, "result": resolved}


def get_version() -> str:
    """Distribution version, or 'unknown' outside an installed checkout."""
    try:
        from importlib.metadata import version

        return version("xavani-agent")
    except Exception:
        return "unknown"


def serve(input_stream: TextIO, output_stream: TextIO, session: RpcSession) -> None:
    """Read NDJSON frames until EOF; write one response line per frame."""
    for line in input_stream:
        out = session.handle_line(line.rstrip("\n"))
        if out:
            output_stream.write(out)
            output_stream.flush()


def main(argv: list[str] | None = None) -> int:
    """Run the stdio loop with real oneshot-backed chat."""
    from xavani_cli.oneshot import run_oneshot

    def chat_fn(prompt: str) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            run_oneshot(prompt)
        return buffer.getvalue()

    def tools_fn() -> list[dict]:
        return []

    serve(sys.stdin, sys.stdout, RpcSession(chat_fn, tools_fn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
