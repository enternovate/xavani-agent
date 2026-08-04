# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Debug-friendly state dumps (E05).

``state_dump()`` serializes the local ``~/.xavani`` config and session
state into a redacted JSON string: API keys, tokens and other secret-shaped
values are masked so the dump is safe to paste into a log or issue.

The dump is a snapshot, never a mutation: it only reads files under
``XAVANI_HOME`` and never touches the live agent state.
"""

import json
import os
import sys
from pathlib import Path

from tools.registry import registry

# Substrings that mark a config key as secret-shaped.  Values under these
# keys are masked in the dump.
_SECRET_KEY_PATTERNS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "auth",
    "key",
)
# Long opaque values (JWT-ish blobs) are masked even when the key name is
# generic (e.g. a base64 blob under ``encrypted``).
_MIN_SECRET_LENGTH = 24

_MAX_SESSION_FILES = 3
_MAX_SESSION_BYTES = 4000


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(pattern in lowered for pattern in _SECRET_KEY_PATTERNS)


def _mask(value) -> str:
    text = str(value)
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...***"


def redact(value: object, key: str = "") -> object:
    """Recursively mask secret-shaped values (E05).

    Dict keys matching a secret pattern (``api_key``, ``token``, ...) and
    long opaque strings anywhere in the tree are replaced with a masked
    form; the rest of the structure is preserved.
    """
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, (str, int, float, bool)) and (
        _is_secret_key(key) or (isinstance(value, str) and len(value) >= _MIN_SECRET_LENGTH)
    ):
        return _mask(value)
    return value


def _default_home() -> Path:
    env_home = os.environ.get("XAVANI_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".xavani"


def _load_config(home: Path) -> dict:
    """Load ~/.xavani/config.yaml (redacted), tolerating absence/corruption."""
    config_path = home / "config.yaml"
    if not config_path.is_file():
        return {}
    try:
        import yaml

        with open(config_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        result = redact(raw if isinstance(raw, dict) else {"_raw": raw})
        return result if isinstance(result, dict) else {}
    except Exception as exc:  # pragma: no cover - defensive
        return {"_error": f"could not parse config.yaml: {exc}"}


def _load_sessions(home: Path, max_files: int = _MAX_SESSION_FILES) -> list:
    """Load the most recent session files (redacted), newest first."""
    sessions_dir = home / "sessions"
    if not sessions_dir.is_dir():
        return []
    try:
        candidates = sorted(
            (p for p in sessions_dir.glob("*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:  # pragma: no cover - defensive
        return []
    sessions = []
    for path in candidates[:max_files]:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read(_MAX_SESSION_BYTES)
            payload = json.loads(content)
            sessions.append(
                {
                    "file": path.name,
                    "payload": redact(payload),
                }
            )
        except (json.JSONDecodeError, OSError):
            sessions.append({"file": path.name, "payload": {"_error": "unreadable"}})
    return sessions


def state_dump(xavani_home=None) -> str:
    """Serialize redacted ~/.xavani state to a JSON string (E05).

    ``xavani_home`` overrides the home directory (used by tests and by
    callers that want to dump a specific profile).  Returns valid JSON even
    when the home directory does not exist.
    """
    home = Path(xavani_home) if xavani_home is not None else _default_home()
    payload = {
        "xavani_home": str(home),
        "exists": home.exists(),
        "config": _load_config(home),
        "session_files": _load_sessions(home),
        "environment": {
            "XAVANI_HOME": os.environ.get("XAVANI_HOME"),
            "cwd": os.getcwd(),
            "python_version": sys.version.split()[0],
        },
    }
    return json.dumps(payload, indent=2, default=str)


# --- Registry ---------------------------------------------------------------
# Mirrors the small-tool pattern (see tools/clarify_tool.py): module-level
# ``registry.register`` with a JSON schema, handler and availability check.

_STATE_DUMP_SCHEMA = {
    "type": "function",
    "description": (
        "Dump the local ~/.xavani config and session state as a redacted JSON "
        "string (debugging aid, E05). API keys and tokens are masked."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


def check_state_dump_requirements() -> bool:
    """Always available — reading ~/.xavani needs no external services."""
    return True


registry.register(
    name="state_dump",
    toolset="debug",
    schema=_STATE_DUMP_SCHEMA,
    handler=lambda args, **kw: state_dump(),
    check_fn=check_state_dump_requirements,
    emoji="🩺",
)
