# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Smart notification routing (G07).

A single entry point, :func:`smart_notify`, that always prints to the
console and additionally appends to the gateway log file when the gateway
is running (``XAVANI_GATEWAY_RUNNING=1``).  Kept deliberately small so it
is trivially testable and safe to call from any thread.
"""

from __future__ import annotations

import os
import time
from typing import Optional


def _gateway_log_path():
    """Resolve ``<XAVANI_HOME>/logs/gateway.log`` (lazy import)."""
    from xavani_constants import get_xavani_home

    return get_xavani_home() / "logs" / "gateway.log"


def gateway_running() -> bool:
    """True when the gateway process has signalled it is live."""
    return os.environ.get("XAVANI_GATEWAY_RUNNING") == "1"


def smart_notify(title: str, body: str, *, level: str = "info") -> None:
    """Route a notification to the best available channel.

    - Always prints ``[level] title: body`` to the console.
    - When the gateway is running (``XAVANI_GATEWAY_RUNNING=1``), also
      appends a timestamped line to ``<XAVANI_HOME>/logs/gateway.log``.

    Log failures are swallowed — a notification must never crash the
    caller.
    """
    print(f"[{level}] {title}: {body}")
    if gateway_running():
        _append_gateway_log(title, body, level)


def _append_gateway_log(title: str, body: str, level: str) -> None:
    try:
        path = _gateway_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} [{level}] {title}: {body}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
