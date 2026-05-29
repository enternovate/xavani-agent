# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Safe-logging helpers that redact sensitive patterns from log output.

The module exposes two collaborating pieces:

* :class:`SafeLogFilter` — a :class:`logging.Filter` that rewrites the formatted
  message of every record passing through it. Install once on the root logger
  and every descendant emitter (handlers, libraries, third-party loggers)
  inherits the redaction.
* :class:`SafeFormatter` — a :class:`logging.Formatter` wrapper that sanitises
  the **fully formatted** record, including ``exc_info`` tracebacks and
  ``stack_info`` output. Plain filters can only touch ``msg``/``args`` and
  therefore miss secrets that appear in exception strings, so production
  handlers should wrap their formatter with this class as well.

The redaction list is conservative — patterns are anchored by recognisable
prefixes wherever possible to keep false-positive rate low, with optional
broad fallbacks for opaque high-entropy strings. Custom patterns can be
added at runtime via :func:`add_pattern` to cover provider-specific secrets
without monkey-patching the module.
"""

from __future__ import annotations

import logging
import re
import sys
import threading
import traceback
from typing import Final, Iterable, List, Optional, Pattern, Tuple

__all__ = [
    "REDACTION",
    "SafeLogFilter",
    "SafeFormatter",
    "DEFAULT_PATTERNS",
    "add_pattern",
    "remove_pattern",
    "redact",
    "install",
    "is_installed",
]

# ---------------------------------------------------------------------------
# Redaction marker
# ---------------------------------------------------------------------------

REDACTION: Final[str] = "[REDACTED]"

# ---------------------------------------------------------------------------
# Default sensitive-pattern catalogue
# ---------------------------------------------------------------------------
#
# Patterns are written to match the *whole secret* so the entire token is
# replaced rather than truncated. Each entry is documented with its rough
# origin so we can keep the list maintainable as upstream secret shapes
# change. Anchor with `\b` whenever the prefix is alphanumeric — bare
# substring matches would otherwise nibble into longer identifiers like
# ``my-sk-key`` and produce confusing redactions in unrelated text.
#
# Where a provider uses a stable prefix we ALWAYS prefer the prefixed form
# over the broad high-entropy fallback at the bottom: prefixed patterns
# have negligible false-positive rate.

_PROVIDER_PREFIX_PATTERNS: Tuple[Pattern[str], ...] = (
    # OpenAI / Anthropic / providers using `sk-` prefix (including sk-ant-, sk-or-, …)
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    # OpenAI project / org keys
    re.compile(r"\bsk-proj-[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\bsk-org-[A-Za-z0-9_\-]{20,}\b"),
    # OpenAI legacy session keys
    re.compile(r"\bsess-[A-Za-z0-9]{20,}\b"),
    # xAI Grok
    re.compile(r"\bxai-[A-Za-z0-9_\-]{20,}\b"),
    # Groq
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),
    # Stripe (live + test)
    re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b"),
    # GitHub tokens (PAT classic, fine-grained, OAuth, etc.)
    re.compile(r"\bgh[ousrp]_[A-Za-z0-9]{30,}\b"),
    # GitHub Apps installation tokens (legacy)
    re.compile(r"\bv1\.[A-Fa-f0-9]{40}\b"),
    # Slack bot/user/refresh tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b"),
    # Slack webhook URLs
    re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+"),
    # AWS Access Key ID (the secret key alone is undetectable; pair-detection is impractical)
    re.compile(r"\b(?:AKIA|ASIA|AROA)[A-Z0-9]{16}\b"),
    # Google / Firebase API keys
    re.compile(r"\bAIza[A-Za-z0-9_\-]{32,}\b"),
    # Discord bot tokens
    re.compile(r"\b[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27,}\b"),
    # Telegram bot tokens
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b"),
    # Anthropic-style suffix tokens occasionally used in OAuth flows
    re.compile(r"\b(?:claude|anthropic)[_\-][A-Za-z0-9_\-]{20,}\b", re.IGNORECASE),
    # Xavani-internal session/refresh tokens (xavani_ prefix)
    re.compile(r"\bxavani_[A-Za-z0-9_\-]{16,}\b", re.IGNORECASE),
    # Generic JWT (header.payload.signature) — anchored by the canonical eyJ prefix
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"),
)

_TRANSPORT_PATTERNS: Tuple[Pattern[str], ...] = (
    # `Authorization: Bearer …`
    re.compile(r"(?<![A-Za-z0-9])Bearer\s+[A-Za-z0-9_\-\.=]{20,}", re.IGNORECASE),
    # `Authorization: Basic …`
    re.compile(r"(?<![A-Za-z0-9])Basic\s+[A-Za-z0-9+/=]{16,}", re.IGNORECASE),
    # URLs embedding credentials: scheme://user:pass@host
    re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)[^/\s:]+:[^/\s@]+@"),
    # PKCE / OAuth user codes
    re.compile(r"\buser_code=[A-Z0-9\-]{4,}\b", re.IGNORECASE),
    # OAuth code / state / refresh params on a URL
    re.compile(r"\b(?:access_token|refresh_token|id_token|code|state)=[A-Za-z0-9_\-\.]{12,}\b"),
)

_BLOCK_PATTERNS: Tuple[Pattern[str], ...] = (
    # PEM-style private keys (single line redaction; multi-line PEMs are
    # caught by the start-marker since logging is line-oriented).
    re.compile(r"-----BEGIN(?:\s+[A-Z0-9 ]+)?\s+PRIVATE\s+KEY-----[^-]+-----END(?:\s+[A-Z0-9 ]+)?\s+PRIVATE\s+KEY-----"),
    re.compile(r"-----BEGIN(?:\s+[A-Z0-9 ]+)?\s+PRIVATE\s+KEY-----"),
)

# Broad fallbacks. These run LAST so prefix-based patterns above always win.
# Tuned to minimise false positives:
#   * Hex strings of >=48 chars (covers most secret-shaped values without
#     hitting common 32-char UUIDs and 40-char git SHAs).
#   * Base64-shaped strings of >=64 chars (covers session blobs without
#     matching short message-IDs).
_BROAD_PATTERNS: Tuple[Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-z0-9])[a-f0-9]{48,}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9+/]{64,}={0,2}(?![A-Za-z0-9])"),
)

DEFAULT_PATTERNS: Tuple[Pattern[str], ...] = (
    *_BLOCK_PATTERNS,
    *_PROVIDER_PREFIX_PATTERNS,
    *_TRANSPORT_PATTERNS,
    *_BROAD_PATTERNS,
)

# Runtime-mutable pattern list. A lock protects it so add/remove never race
# against an in-flight redaction. Reads grab a snapshot tuple to avoid
# holding the lock for the full pattern sweep.
_pattern_lock = threading.RLock()
_active_patterns: List[Pattern[str]] = list(DEFAULT_PATTERNS)


def _snapshot_patterns() -> Tuple[Pattern[str], ...]:
    """Return an immutable snapshot of the active pattern list."""
    with _pattern_lock:
        return tuple(_active_patterns)


def add_pattern(pattern: "str | Pattern[str]", *, flags: int = 0) -> Pattern[str]:
    """Register an additional redaction pattern.

    The pattern fires alongside :data:`DEFAULT_PATTERNS` on every record.
    String inputs are compiled once and the compiled object is returned so
    callers can later pass it to :func:`remove_pattern`.
    """
    compiled = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
    with _pattern_lock:
        _active_patterns.append(compiled)
    return compiled


def remove_pattern(pattern: Pattern[str]) -> bool:
    """Remove a previously-registered pattern.

    Returns ``True`` if the pattern was found and removed, ``False`` if it
    was never registered or has already been removed. Default patterns can
    be removed but most call sites should leave them in place; if you find
    yourself stripping defaults regularly the right move is usually to
    refine the pattern upstream instead.
    """
    with _pattern_lock:
        try:
            _active_patterns.remove(pattern)
            return True
        except ValueError:
            return False


def redact(text: str, patterns: Optional[Iterable[Pattern[str]]] = None) -> str:
    """Apply every active redaction pattern to ``text`` and return the result.

    Useful for ad-hoc sanitisation outside the logging path (e.g. when
    persisting state to disk or echoing a debug payload to the terminal).
    """
    if not text:
        return text
    if patterns is None:
        patterns = _snapshot_patterns()
    out = text
    for pat in patterns:
        out = pat.sub(REDACTION, out)
    return out


# ---------------------------------------------------------------------------
# Logging filter
# ---------------------------------------------------------------------------


class SafeLogFilter(logging.Filter):
    """Logging filter that scrubs sensitive substrings from every record.

    The filter rewrites both the message body and the formatter-cached
    exception text. ``record.args`` is cleared after substitution because
    the standard logging formatter would otherwise re-interpolate them and
    resurrect the raw values.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 (interface)
        patterns = _snapshot_patterns()
        try:
            message = record.getMessage()
        except Exception:
            # Defensive: a misuse of %-args shouldn't suppress the record,
            # but we also can't safely format args here. Fall back to str().
            message = str(record.msg)
        record.msg = redact(message, patterns)
        record.args = ()
        if record.exc_info and record.exc_text is None:
            # Render the traceback now (the formatter would otherwise do
            # this lazily without going through our redactor).
            record.exc_text = "".join(traceback.format_exception(*record.exc_info))
        if record.exc_text:
            record.exc_text = redact(record.exc_text, patterns)
        if record.stack_info:
            record.stack_info = redact(record.stack_info, patterns)
        return True


# ---------------------------------------------------------------------------
# Logging formatter wrapper
# ---------------------------------------------------------------------------


class SafeFormatter(logging.Formatter):
    """Formatter wrapper that redacts the **final** formatted output.

    Use this when a handler emits records through paths the filter can't
    intercept — e.g. structured-logging libraries that build their own
    output string from ``record.__dict__`` rather than calling
    :meth:`logging.LogRecord.getMessage`.
    """

    def __init__(
        self,
        inner: Optional[logging.Formatter] = None,
        *,
        patterns: Optional[Iterable[Pattern[str]]] = None,
    ) -> None:
        super().__init__()
        self._inner = inner or logging.Formatter()
        self._patterns = tuple(patterns) if patterns is not None else None

    def format(self, record: logging.LogRecord) -> str:
        formatted = self._inner.format(record)
        return redact(formatted, self._patterns or _snapshot_patterns())

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:  # noqa: N802 (stdlib)
        return self._inner.formatTime(record, datefmt)


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

_install_lock = threading.Lock()
_installed_filter: Optional[SafeLogFilter] = None


def is_installed() -> bool:
    """Return ``True`` when :func:`install` has already attached the filter."""
    with _install_lock:
        return _installed_filter is not None


def install(logger: Optional[logging.Logger] = None) -> SafeLogFilter:
    """Attach :class:`SafeLogFilter` to ``logger`` (root logger by default).

    Idempotent — repeated calls return the same filter instance and never
    attach it twice. Returns the installed filter so callers can wire it
    into additional loggers manually if they need to.
    """
    global _installed_filter
    with _install_lock:
        if _installed_filter is None:
            _installed_filter = SafeLogFilter()
        target = logger or logging.getLogger()
        if _installed_filter not in target.filters:
            target.addFilter(_installed_filter)
        return _installed_filter


# Best-effort: wire the filter into uncaught-exception output so a crash
# doesn't bypass redaction. Only runs when the module is imported directly;
# downstream code can opt out by restoring ``sys.excepthook`` after import.
def _safe_excepthook(exc_type, exc_value, exc_tb) -> None:  # pragma: no cover - exit path
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sys.stderr.write(redact(text))


sys.excepthook = _safe_excepthook
