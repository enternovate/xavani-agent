# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A16: preflight gate for long-running operations.

Before any operation that takes >5s (backtest, long install, complex
analysis), verify the environment: state files writable, disk space
available, no stale locks, network reachability. Fail fast with the
resource name — prevent a 20-minute job dying at minute 19 because the
session DB was locked.

Usage::

    from tools.long_running import preflight, PreflightError

    try:
        preflight(disk_min_mb=500, lock_paths=[session_db_path])
    except PreflightError as exc:
        return tool_error(str(exc))
"""

from __future__ import annotations

import logging
import os
import shutil
import socket
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DISK_MIN_MB = 500
DEFAULT_URL_TIMEOUT = 5.0


class PreflightError(RuntimeError):
    """Raised when a preflight check fails. Message names the resource."""


def check_writable(paths: Iterable[Path]) -> List[str]:
    """Return problems for paths that are not writable."""
    problems: List[str] = []
    for path in paths:
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            probe = path.parent / f".xavani_preflight_{os.getpid()}"
            with open(probe, "wb") as f:
                f.write(b"probe")
            probe.unlink()
        except OSError as exc:
            problems.append(f"{path} is not writable: {exc}")
    return problems


def check_disk_space(path: Path, min_free_mb: int) -> List[str]:
    """Return problems when the filesystem hosting path is too full."""
    try:
        usage = shutil.disk_usage(path)
        free_mb = usage.free // (1024 * 1024)
        if free_mb < min_free_mb:
            return [
                f"{path} has {free_mb} MB free; minimum {min_free_mb} MB "
                f"required for this operation"
            ]
    except OSError as exc:
        return [f"cannot stat disk for {path}: {exc}"]
    return []


def check_stale_locks(lock_paths: Iterable[Path], stale_after_s: float = 300.0) -> List[str]:
    """Return problems when a lock file is held by a live process.

    A lock file older than ``stale_after_s`` whose PID is not running is
    considered stale (safe to ignore). A lock held by a LIVE pid blocks
    the operation.
    """
    import errno

    problems: List[str] = []
    now = time.time()
    for lock_path in lock_paths:
        lock_path = Path(lock_path)
        if not lock_path.exists():
            continue
        try:
            raw = lock_path.read_text(encoding="utf-8").strip()
            pid = int(raw) if raw.isdigit() else None
        except OSError:
            pid = None
        try:
            age = now - lock_path.stat().st_mtime
        except OSError:
            age = 0.0
        if pid is not None and age < stale_after_s:
            # PID may be a live process holding the lock.
            try:
                # windows-footgun: ok — psutil.pid_exists is cross-platform;
                # os.kill(pid, 0) would send CTRL_C_EVENT on Windows (bpo-14484).
                import psutil

                if psutil.pid_exists(pid):
                    problems.append(f"lock {lock_path} held by live pid {pid}")
                    continue
            except OSError:
                pass
            # pid dead (or uncheckable) — stale lock, safe
            continue
        if pid is None and age < stale_after_s:
            problems.append(f"lock {lock_path} is fresh but has no pid")
    return problems


def check_network(host: str = "api.anthropic.com", port: int = 443,
                  timeout: float = DEFAULT_URL_TIMEOUT) -> List[str]:
    """Return problems when the host is unreachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return []
    except OSError as exc:
        return [f"network unreachable ({host}:{port}): {exc}"]


def preflight(
    *,
    writable_paths: Optional[Iterable[Path]] = None,
    disk_path: Optional[Path] = None,
    disk_min_mb: int = DEFAULT_DISK_MIN_MB,
    lock_paths: Optional[Iterable[Path]] = None,
    check_network_host: Optional[str] = None,
    check_network_port: int = 443,
) -> Dict[str, List[str]]:
    """Run all preflight checks. Returns {check_name: [problems]}.

    Never raises for a failed check — returns the problems so the caller
    decides. Use :func:`raise_if_problems` for the fail-fast variant.
    """
    results: Dict[str, List[str]] = {}
    if writable_paths:
        problems = check_writable(writable_paths)
        if problems:
            results["writable"] = problems
    if disk_path is not None:
        problems = check_disk_space(disk_path, disk_min_mb)
        if problems:
            results["disk"] = problems
    if lock_paths:
        problems = check_stale_locks(lock_paths)
        if problems:
            results["locks"] = problems
    if check_network_host:
        problems = check_network(check_network_host, check_network_port)
        if problems:
            results["network"] = problems
    return results


def raise_if_problems(results: Dict[str, List[str]]) -> None:
    """Raise PreflightError naming every failing resource."""
    if not results:
        return
    lines = ["Preflight failed:"]
    for check, problems in results.items():
        for problem in problems:
            lines.append(f"  [{check}] {problem}")
    raise PreflightError("\n".join(lines))
