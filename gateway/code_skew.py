"""Detect when the gateway is running stale code after a hot ``git pull`` (A08).

The gateway is a single long-lived process; its ``sys.modules`` is frozen at
boot. If the checkout is updated underneath it (a manual ``git pull``, or the
window before ``xavani update``'s graceful restart fires), new code paths can
resolve freshly-pulled consumer modules against stale cached dependencies ->
cryptic ImportErrors.

We snapshot the checkout revision at gateway startup and compare on demand, so
the running gateway can warn with a clear "restart the gateway" message instead
of crashing on an import error. If the revision can't be read (non-git
install, IO error), the boot snapshot stays ``None`` and skew detection no-ops
— it never produces a false positive.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_boot_fingerprint: str | None = None
_skew_warned: bool = False


def _git(args: list[str]) -> str:
    """Run a git command in the project root; return stdout or empty."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ""
        return (result.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _fingerprint() -> str | None:
    """Current checkout fingerprint ``git:<ref>:<sha>``, or None."""
    sha = _git(["rev-parse", "HEAD"])
    if not sha:
        return None
    ref = _git(["symbolic-ref", "--short", "HEAD"])
    return f"git:{ref or 'detached'}:{sha}"


def record_boot_fingerprint() -> None:
    """Snapshot the checkout revision at gateway startup (idempotent)."""
    global _boot_fingerprint
    if _boot_fingerprint is None:
        _boot_fingerprint = _fingerprint()


def _short(fingerprint: str) -> str:
    """Render a ``git:<ref>:<sha>`` fingerprint as a compact label."""
    sha = fingerprint.rsplit(":", 1)[-1]
    if sha and sha != "unresolved" and len(sha) > 10:
        return sha[:10]
    return sha or fingerprint


def detect_code_skew() -> tuple[str, str] | None:
    """Return ``(boot_rev, disk_rev)`` short labels if the checkout drifted
    since boot, else ``None``."""
    if _boot_fingerprint is None:
        return None
    disk = _fingerprint()
    if disk is None or disk == _boot_fingerprint:
        return None
    return (_short(_boot_fingerprint), _short(disk))


def warn_if_code_skew() -> bool:
    """Log a warning once when the checkout drifted since boot.

    Returns True when skew was detected (and newly reported). Repeated
    calls stay silent until the process restarts — one warning per boot.
    """
    global _skew_warned
    if _skew_warned:
        return False
    skew = detect_code_skew()
    if skew is None:
        return False
    _skew_warned = True
    boot, disk = skew
    logger.warning(
        "CODE SKEW: gateway running code from %s but the checkout is now %s. "
        "Restart the gateway (xavani gateway restart) to pick up the new code.",
        boot,
        disk,
    )
    return True


__all__ = [
    "record_boot_fingerprint",
    "detect_code_skew",
    "warn_if_code_skew",
]
