# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Advisor reviewer role: a second model reviews each turn.

When enabled (/advisor enable), every AIAgent.chat() reply goes to the
advisor model — its own context and its own model, resolved from
model_router role ``advisor``. The advisor returns severity-tagged notes
that are appended inline to the reply. Advisor failures never break the
main turn: they degrade to silence.
"""

import logging
import re
from typing import Any, Dict, List, Optional

MAX_NOTES = 5
DEFAULT_TIMEOUT_S = 60

_SEVERITIES = ("high", "medium", "low")
_NOTE_RE = re.compile(
    r"^\s*\[(?P<severity>high|medium|low)\]\s*(?P<note>.+)$",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = (
    "You are a silent senior reviewer. You see one user request and the "
    "assistant's reply. List only real problems: factual errors, missed "
    "requirements, unsafe actions, broken code, wrong file paths. "
    "Output at most "
    f"{MAX_NOTES} lines, each exactly '[high] ...' or '[medium] ...' or "
    "'[low] ...'. high = must fix now, medium = should fix, low = nice to "
    "fix. Output NOTHING else — no preamble, no praise. If there is "
    "nothing to flag, output an empty response."
)


def resolve_advisor_model() -> Optional[Dict[str, Optional[str]]]:
    """Resolve the advisor model via the model-router advisor role."""
    try:
        from model_router import resolve_role

        choice = resolve_role("advisor")
    except Exception:
        return None
    if not choice:
        return None
    return {"provider": getattr(choice, "provider", None),
            "model": getattr(choice, "model", None)}


def parse_notes(response: str) -> List[Dict[str, str]]:
    """Parse '[severity] note' lines; cap at MAX_NOTES."""
    notes: List[Dict[str, str]] = []
    if not response:
        return notes
    for raw in response.splitlines():
        match = _NOTE_RE.match(raw)
        if not match:
            continue
        severity = match.group("severity").lower()
        note = match.group("note").strip()
        if severity in _SEVERITIES and note:
            notes.append({"severity": severity, "note": note})
        if len(notes) >= MAX_NOTES:
            break
    return notes


def review_turn(
    user_message: str,
    assistant_reply: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> Optional[List[Dict[str, str]]]:
    """Ask the advisor model to review one turn.

    Returns parsed notes, an empty list when the advisor flags nothing,
    or None when no advisor model is available.
    """
    resolved = resolve_advisor_model()
    target_provider = provider or (resolved or {}).get("provider")
    target_model = model or (resolved or {}).get("model")
    if not target_model:
        return None

    transcript = (
        f"<user_request>\n{user_message[:8000]}\n</user_request>\n\n"
        f"<assistant_reply>\n{assistant_reply[:12000]}\n</assistant_reply>"
    )
    try:
        from agent.auxiliary_client import call_llm

        response = call_llm(
            provider=target_provider,
            model=target_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0.0,
            max_tokens=500,
            timeout=timeout,
        )
    except Exception as exc:
        logging.debug("advisor review failed: %s", exc)
        return None
    return parse_notes(_response_text(response))


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        text = getattr(message, "content", None)
        if isinstance(text, str):
            return text
    return ""


def format_notes_block(notes: List[Dict[str, str]]) -> str:
    """Render notes as the inline block appended to the reply."""
    lines = ["", "---", "[advisor notes]"]
    for entry in notes:
        lines.append(f"[{entry['severity']}] {entry['note']}")
    return "\n".join(lines)


def maybe_review(agent: Any, user_message: str, reply: str) -> str:
    """Chat-hook wrapper: review when enabled, append notes inline.

    Never raises — an advisor failure degrades to the plain reply.
    """
    if not getattr(agent, "advisor_enabled", False):
        return reply
    if not reply or not reply.strip():
        return reply
    try:
        notes = review_turn(user_message, reply)
    except Exception as exc:
        logging.debug("advisor review crashed: %s", exc)
        return reply
    if not notes:
        return reply
    return reply + format_notes_block(notes)
