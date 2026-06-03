# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Sandbox hardening for local execution (v0.4.0 roadmap U42).

Two layers:
  * **Cross-platform, tested:** OS resource caps (address space / CPU time / open
    files) via the stdlib ``resource`` module, plus availability detection for the
    kernel mechanisms below. Pairs with ``tools/egress_policy.py`` (network egress).
  * **Linux-only, platform-gated:** seccomp syscall filtering and Landlock
    filesystem confinement. These require Linux + an optional binding; on any other
    host (or without the binding) they degrade gracefully to a clear status instead
    of shipping unrunnable code.

The actual ``setrlimit`` call is injectable so unit tests verify the mapping logic
without mutating the test process.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class SandboxResult:
    """Outcome of applying one hardening mechanism."""

    applied: bool
    mechanism: str
    detail: str


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_unix() -> bool:
    return sys.platform != "win32"


def kernel_sandbox_status() -> Dict[str, Dict[str, object]]:
    """Report availability of the Linux-only kernel mechanisms (no application)."""

    def _probe(module_name: str) -> Dict[str, object]:
        if not is_linux():
            return {"available": False, "reason": f"{module_name} is Linux-only; host is {sys.platform}"}
        try:  # pragma: no cover - Linux-only path
            __import__(module_name)
            return {"available": True, "reason": f"{module_name} binding importable"}
        except ImportError:  # pragma: no cover - Linux-only path
            return {"available": False, "reason": f"install a '{module_name}' binding to enable"}

    return {"seccomp": _probe("seccomp"), "landlock": _probe("landlock")}


def apply_resource_limits(
    *,
    memory_mb: Optional[int] = None,
    cpu_seconds: Optional[int] = None,
    open_files: Optional[int] = None,
    setter: Optional[Callable] = None,
    getter: Optional[Callable] = None,
) -> SandboxResult:
    """Apply soft resource limits to the current process (or via injected ``setter``).

    Only limits whose ``RLIMIT_*`` constant exists on the platform are applied
    (e.g. ``RLIMIT_AS`` is Linux-only); others are reported as skipped. A limit is
    never raised above the existing hard cap.
    """
    try:
        import resource
    except ImportError:
        return SandboxResult(False, "resource_limits", "resource module unavailable (non-Unix host)")

    set_limit = setter or resource.setrlimit
    get_limit = getter or resource.getrlimit

    plan = []
    if memory_mb is not None:
        plan.append(("RLIMIT_AS", int(memory_mb) * 1024 * 1024))
    if cpu_seconds is not None:
        plan.append(("RLIMIT_CPU", int(cpu_seconds)))
    if open_files is not None:
        plan.append(("RLIMIT_NOFILE", int(open_files)))

    applied: List[str] = []
    skipped: List[str] = []
    for const_name, soft_value in plan:
        const = getattr(resource, const_name, None)
        if const is None:
            skipped.append(f"{const_name} (unsupported on {sys.platform})")
            continue
        _, hard = get_limit(const)
        if hard != resource.RLIM_INFINITY and soft_value > hard:
            soft_value = hard
        set_limit(const, (soft_value, hard))
        applied.append(const_name)

    detail = f"applied={applied}"
    if skipped:
        detail += f" skipped={skipped}"
    return SandboxResult(bool(applied), "resource_limits", detail)


def harden(
    *,
    memory_mb: int = 512,
    cpu_seconds: int = 120,
    open_files: int = 256,
) -> List[SandboxResult]:
    """Apply the full hardening profile to the current process; return per-mechanism results.

    Resource caps are applied immediately; the Linux kernel mechanisms are reported
    via their availability status (their application is environment-specific and is
    performed by the Linux runtime backend, not here).
    """
    results = [
        apply_resource_limits(memory_mb=memory_mb, cpu_seconds=cpu_seconds, open_files=open_files)
    ]
    for mechanism, status in kernel_sandbox_status().items():
        results.append(
            SandboxResult(bool(status["available"]), mechanism, str(status["reason"]))
        )
    return results


__all__ = [
    "SandboxResult",
    "is_linux",
    "is_unix",
    "kernel_sandbox_status",
    "apply_resource_limits",
    "harden",
]
