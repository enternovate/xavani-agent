# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C20: error recovery map — error category to actionable fix.

When an error occurs, look up its category and suggest the remediation
instead of a bare traceback. The map covers the failure classes Xavani
users actually hit: config problems, credential issues, network/timeout
failures, sandbox unavailability, and common misconfigurations.

Usage::

    from xavani_cli.error_recovery import suggest_recovery

    suggestion = suggest_recovery(str(exc))
    if suggestion:
        print(suggestion["action"])
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# (regex, category, action, hint) — ordered; first match wins.
_RECOVERY_PATTERNS: list[Tuple[re.Pattern, str, str, str]] = [
    (
        re.compile(r"config.*(?:parse|invalid|malformed|yaml)", re.I),
        "config_invalid",
        "Run `xavani validate` to check config.yaml. Fix the YAML line named in the error, then restart.",
        "A typo in config.yaml silently disables every user override.",
    ),
    (
        re.compile(r"(?:api[\s_-]?key|token|credential|auth).*(?:invalid|missing|expired|401|403)", re.I),
        "credentials_invalid",
        "Run `xavani tools` to re-enter the provider API key, or check ~/.xavani/.env for the named variable.",
        "Provider keys live in ~/.xavani/.env and are never stored in config.yaml.",
    ),
    (
        re.compile(r"(?:timed? ?out|timeout|read.?timed.?out)", re.I),
        "timeout",
        "Retry once. If it persists, raise the timeout (terminal.timeout, or provider timeout in config.yaml) or switch providers.",
        "A single timeout is usually transient; repeated timeouts are a config or network issue.",
    ),
    (
        re.compile(r"(?:connection refused|connection reset|unreachable|ECONNREFUSED|name or service not known)", re.I),
        "network_unreachable",
        "Check network connectivity and the base_url in config.yaml. Corporate proxies may need a proxy setting.",
        "The endpoint could not be reached — verify the host and network.",
    ),
    (
        re.compile(r"(?:rate.?limit|429|too many requests)", re.I),
        "rate_limited",
        "Wait for the rate window, then retry with a delay. Lower concurrent tool calls or delegation fan-out.",
        "Providers enforce per-minute limits; back off before retrying.",
    ),
    (
        re.compile(r"(?:sandbox|execute_code).*(?:unavailable|not available|no such file|missing)", re.I),
        "sandbox_unavailable",
        "Check that the terminal backend is configured (xavani tools > Terminal). Use terminal_tool directly as a fallback.",
        "The execute_code sandbox needs a working local or remote backend.",
    ),
    (
        re.compile(r"(?:session.*(?:locked|corrupt|not available)|database.*(?:locked|corrupt))", re.I),
        "state_corrupt",
        "Close other xavani processes, then restart. If corruption persists, run `xavani validate` and inspect ~/.xavani/logs/.",
        "A stale lock or corrupt state.db usually clears on restart.",
    ),
    (
        re.compile(r"(?:module.?not.?found|no module named|import.*error)", re.I),
        "missing_dependency",
        "Install the missing dependency: `uv pip install -e '.[all,dev]'` in the repo, or pip install xavani-agent[extra] for the feature you used.",
        "Optional features ship as extras; install the extra for the missing module.",
    ),
    (
        re.compile(r"(?:permission denied|operation not permitted)", re.I),
        "permission_denied",
        "Fix file permissions on the path in the error, or run with the account that owns ~/.xavani.",
        "The process lacks write/execute permission on a required path.",
    ),
    (
        re.compile(r"(?:disk|space).*(?:full|insufficient)|no space left", re.I),
        "disk_full",
        "Free disk space, then retry. XAVANI_HOME needs at least 50 MB free (xavani home check).",
        "Session history and memory corrupt under disk pressure.",
    ),
]


def suggest_recovery(error_text: str) -> Optional[Dict[str, Any]]:
    """Map an error string to an actionable recovery suggestion.

    Returns None when no known pattern matches. The returned dict has
    ``category``, ``action``, and ``hint`` keys.
    """
    if not error_text:
        return None
    for pattern, category, action, hint in _RECOVERY_PATTERNS:
        if pattern.search(error_text):
            return {"category": category, "action": action, "hint": hint}
    return None


def format_recovery(error_text: str) -> str:
    """Return a human-readable recovery block, or \"\" when no match."""
    suggestion = suggest_recovery(error_text)
    if not suggestion:
        return ""
    lines = [
        "",
        "Recovery:",
        f"  {suggestion['action']}",
        f"  ({suggestion['hint']})",
        "",
    ]
    return "\n".join(lines)


def recovery_categories() -> list[str]:
    """All known recovery categories, for docs and tests."""
    return [category for _, category, _, _ in _RECOVERY_PATTERNS]
