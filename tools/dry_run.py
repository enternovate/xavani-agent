# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Session-scoped dry-run mode.

When enabled, mutating tools (terminal, write_file, patch) report the
action they would take and change nothing. State lives in a ContextVar so
gateway worker threads stay isolated.
"""

import contextvars

_enabled: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "xavani_dry_run", default=False,
)


def enabled() -> bool:
    return _enabled.get()


def set_enabled(value: bool) -> None:
    _enabled.set(bool(value))


def toggle() -> bool:
    new_value = not _enabled.get()
    _enabled.set(new_value)
    return new_value
