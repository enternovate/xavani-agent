"""Safe logging utilities — redact sensitive patterns from log records."""

import logging
import re as _re

# Patterns that commonly indicate sensitive data in log messages
_SENSITIVE_PATTERNS = [
    # API keys (OpenAI, Anthropic, etc.)
    _re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    _re.compile(r"\b[xX][aA][vV][aA][nN][iI]_[a-zA-Z0-9_-]{10,}\b"),
    # Bearer tokens
    _re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]{20,}\b"),
    # Generic long hex/base64 strings that look like secrets
    _re.compile(r"\b[a-f0-9]{32,}\b"),
    _re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    # OAuth device/user codes
    _re.compile(r"\buser_code=[A-Z0-9\-]{4,}\b", _re.I),
    # URLs with embedded credentials
    _re.compile(r"[a-zA-Z]+://[^/\s:]*:[^/\s@]*@"),
]

_REDACTION = "[REDACTED]"


class SafeLogFilter(logging.Filter):
    """Logging filter that redacts sensitive patterns from every log record.

    Install once on the root logger and it sanitizes all descendant output::

        import logging
        from xavani_cli.safe_logging import SafeLogFilter
        logging.getLogger().addFilter(SafeLogFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in _SENSITIVE_PATTERNS:
            msg = pat.sub(_REDACTION, msg)
        record.msg = msg
        # Wipe args so %-formatting doesn't resurrect the raw data
        record.args = ()
        return True


def install() -> None:
    """Attach :class:`SafeLogFilter` to the root logger."""
    logging.getLogger().addFilter(SafeLogFilter())
