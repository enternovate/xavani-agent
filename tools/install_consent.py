# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D06: install-time EULA/consent for auto-installs.

Auto-installed components (e.g. the tirith scanner binary) must have
explicit user consent. Consent is persisted per component so the user
is asked once, and every consent is logged for the audit trail.

Separate scopes: ``cli`` and ``gateway`` can be consented independently,
so a headless gateway never auto-installs something the CLI user
declined.

Usage::

    from tools.install_consent import require_consent, record_consent

    if require_consent("tirith", scope="cli"):
        # ask the user; on yes call record_consent(...)
    else:
        # already consented — proceed
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Components that require consent before auto-install.
CONSENT_REQUIRED = frozenset({"tirith"})


def _consent_path() -> Path:
    home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return home / "data" / "install_consents.json"


def _load() -> Dict[str, Dict[str, Any]]:
    path = _consent_path()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("install consent load failed: %s", exc)
    return {}


def _save(data: Dict[str, Dict[str, Any]]) -> None:
    try:
        path = _consent_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning("install consent save failed: %s", exc)


def _consent_key(component: str, scope: str) -> str:
    return f"{component}::{scope}"


def require_consent(component: str, scope: str) -> bool:
    """True when consent is required for this component+scope.

    False means: already consented (proceed), or the component is not
    in the consent-required set (no gate).
    """
    if component not in CONSENT_REQUIRED:
        return False
    data = _load()
    return _consent_key(component, scope) not in data


def record_consent(component: str, scope: str, *, version: str = "") -> bool:
    """Persist consent for a component+scope. Returns True when stored."""
    if component not in CONSENT_REQUIRED:
        return True  # not gated — nothing to record
    data = _load()
    data[_consent_key(component, scope)] = {
        "component": component,
        "scope": scope,
        "version": version,
        "ts": time.time(),
    }
    _save(data)
    logger.info("install consent recorded: %s (%s)", component, scope)
    return True


def revoke_consent(component: str, scope: str) -> bool:
    """Remove a recorded consent (user opt-out)."""
    data = _load()
    removed = data.pop(_consent_key(component, scope), None)
    if removed is not None:
        _save(data)
    return removed is not None


def consent_snapshot() -> Dict[str, Any]:
    """All recorded consents, for audit and reporting."""
    return _load()


def consent_log_entries() -> list[Dict[str, Any]]:
    """Consent entries as a list (audit-friendly)."""
    return sorted(
        consent_snapshot().values(),
        key=lambda e: e.get("ts", 0),
    )
