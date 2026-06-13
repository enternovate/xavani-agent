# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""The Always-On Companion's advisor rituals (v1.0.0 major ③).

The daily-advisor surface: a morning **brief**, the **8pm error-log** ritual, the
**tomorrow-plan** capture, and **hourly task-chasing** — all rendered
deterministically and delivered through an *injected sender* (Telegram in
production, a list in tests), mirroring ``xavani_operator/notify.py``.

The LLM is allowed only to *write* the brief's prose; everything here — what to
ask, what to store, when to nudge — is pure Python (R10).
"""

from __future__ import annotations

from xavani_operator.advisor.rituals import (
    EVENING_QUESTIONS,
    ErrorLogEntry,
    deliver,
    load_error_log,
    render_brief,
    render_evening_prompt,
    render_hourly_nudge,
    save_error_log,
)
from xavani_operator.advisor.schedule import advisor_jobs

__all__ = [
    "EVENING_QUESTIONS",
    "ErrorLogEntry",
    "render_evening_prompt",
    "render_brief",
    "render_hourly_nudge",
    "save_error_log",
    "load_error_log",
    "deliver",
    "advisor_jobs",
]
