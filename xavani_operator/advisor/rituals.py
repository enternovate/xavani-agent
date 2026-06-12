# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Advisor rituals — daily brief, 8pm error log, tomorrow plan, hourly nudge (v1.0.0 ③).

These render the messages the Companion sends and persist the **error log** — the
user's explicit ask: *not a feelings journal, but a daily error log* (what did I
predict that didn't happen, what did I believe that turned out off, where did I
waste effort on a wrong assumption) plus tomorrow's plan. Storage is a JSONL file
under ``<xavani-home>/advisor/``; delivery is via an injected ``sender`` so tests
never touch the network. Pure Python, zero-LLM in this module (R10).

ErrorLogEntry fields: ``date`` ("YYYY-MM-DD"), ``predictions_missed`` [{predicted,
actual}], ``beliefs_revised`` [{believed, corrected}], ``wasted_effort``
[{assumption, cost}], ``tomorrow_plan`` [{task, why, est}], ``created_at`` (epoch).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

# The 8pm questions — phrased exactly to the user's vision: an error log, not a diary.
EVENING_QUESTIONS: tuple[str, ...] = (
    "What did you predict today that didn't happen?",
    "What did you believe yesterday that turned out to be off?",
    "Where did you waste effort because an assumption was wrong?",
    "What's your plan for tomorrow — the tasks you want done?",
)


@dataclass
class ErrorLogEntry:
    """One day's error log + tomorrow's plan (the 8pm ritual's output)."""

    date: str = ""  # YYYY-MM-DD
    predictions_missed: list[dict] = field(default_factory=list)  # {predicted, actual}
    beliefs_revised: list[dict] = field(default_factory=list)  # {believed, corrected}
    wasted_effort: list[dict] = field(default_factory=list)  # {assumption, cost}
    tomorrow_plan: list[dict] = field(default_factory=list)  # {task, why, est}
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.date:
            self.date = datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ErrorLogEntry":
        fields = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in fields})


def _xavani_home() -> Path:
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home()
    except Exception:  # pragma: no cover - fallback only
        import os

        return Path(os.path.expanduser("~/.xavani"))


def advisor_dir() -> Path:
    return _xavani_home() / "advisor"


def errorlog_path() -> Path:
    return advisor_dir() / "error_log.jsonl"


# --------------------------------------------------------------------------- #
# Rendering (deterministic)
# --------------------------------------------------------------------------- #
def render_evening_prompt(questions: tuple[str, ...] = EVENING_QUESTIONS) -> str:
    """The 8pm message asking the user to fill the day's error log."""
    lines = [
        "🌙 8pm — the daily error log (not a diary; a debugging log for your judgment).",
        "Answer what applies; one line each is fine:",
        "",
    ]
    lines += [f"  {i}. {q}" for i, q in enumerate(questions, 1)]
    lines += ["", "Reply and I'll log it and line up tomorrow's tasks."]
    return "\n".join(lines)


def render_brief(
    *,
    date: str | None = None,
    perceptions: list[str] | None = None,
    goals: list[str] | None = None,
    wisdom_verdict: str | None = None,
    quantum_decision: str | None = None,
    recommendations: list[str] | None = None,
) -> str:
    """Render the morning brief from the engines' outputs. Deterministic skeleton.

    (The LLM may elaborate the prose elsewhere; the structure + content selection
    is pure Python so the brief is always grounded and never fabricated.)
    """
    date = date or datetime.now().strftime("%Y-%m-%d")
    out = [f"☀️ Daily brief — {date}", ""]
    if perceptions:
        out += ["What I'm seeing:"] + [f"  • {p}" for p in perceptions] + [""]
    if goals:
        out += ["Your open goals:"] + [f"  • {g}" for g in goals] + [""]
    if quantum_decision:
        out += [f"Today's best move (quantum decision): {quantum_decision}", ""]
    if wisdom_verdict:
        out += [f"Counsel (the Oracle): {wisdom_verdict}", ""]
    if recommendations:
        out += ["Recommendations:"] + [f"  → {r}" for r in recommendations] + [""]
    if len(out) <= 2:
        out.append("Quiet day — no signals worth your attention yet.")
    return "\n".join(out).rstrip()


def render_hourly_nudge(open_tasks: list[str]) -> str | None:
    """Render the hourly task-chase nudge; ``None`` when there is nothing to chase."""
    if not open_tasks:
        return None
    lines = ["⏰ Task check — still open from today's plan:"]
    lines += [f"  ☐ {t}" for t in open_tasks]
    lines.append("Reply 'done <n>' as you finish, or tell me what's blocking you.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def save_error_log(entry: ErrorLogEntry, path: str | Path | None = None) -> Path:
    """Append an error-log entry as one JSON line. Returns the file path."""
    p = Path(path) if path is not None else errorlog_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
    return p


def load_error_log(path: str | Path | None = None) -> list[ErrorLogEntry]:
    """Load all error-log entries (most recent last)."""
    p = Path(path) if path is not None else errorlog_path()
    if not p.exists():
        return []
    entries: list[ErrorLogEntry] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(ErrorLogEntry.from_dict(json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue
    return entries


# --------------------------------------------------------------------------- #
# Delivery (injected sender — Telegram in prod, list.append in tests)
# --------------------------------------------------------------------------- #
def deliver(message: str | None, sender: Callable[[str], object] | None = None) -> bool:
    """Send ``message`` via ``sender``; return whether anything was sent."""
    if not message or sender is None:
        return False
    sender(message)
    return True
