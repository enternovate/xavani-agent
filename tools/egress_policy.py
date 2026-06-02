# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Network egress allowlist (v0.4.0 roadmap U42 — sandbox hardening, testable core).

A deterministic, pure-Python outbound-network policy: restrict which hosts the
agent (or a sandboxed task) may reach. This is the *egress* counterpart to
``tools/url_safety.py`` (which blocks malicious/SSRF URLs) — here the concern is
"only these hosts are permitted to leave the box".

Configuration (env, read by :func:`from_env`):
  * ``XAVANI_EGRESS_ALLOWLIST``    — comma/space separated hosts (``api.example.com``,
                                     ``example.org``; subdomains of an entry are allowed).
  * ``XAVANI_EGRESS_DEFAULT_DENY`` — ``1/true/yes/on`` to deny anything not allowlisted.

The kernel-level pieces of sandbox hardening (seccomp/landlock syscall filters)
are platform-gated and intentionally out of this module; this allowlist is the
cross-platform, unit-testable layer the runtime backends can enforce.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping, Sequence, Tuple
from urllib.parse import urlparse


class EgressBlocked(RuntimeError):
    """Raised when an outbound host is not permitted by the policy."""


def _normalize_host(entry: str) -> str:
    return entry.strip().lower().lstrip("*").lstrip(".").rstrip("/")


@dataclass(frozen=True)
class EgressPolicy:
    """An immutable host allowlist with an optional default-deny stance."""

    allow: Tuple[str, ...] = ()
    default_deny: bool = False

    @classmethod
    def create(cls, allow: Sequence[str] = (), default_deny: bool = False) -> "EgressPolicy":
        return cls(tuple(_normalize_host(h) for h in allow if h and h.strip()), bool(default_deny))

    @staticmethod
    def host_of(url: str) -> str:
        """Extract a lowercase hostname from a URL or a bare host string."""
        candidate = url if "://" in url else "//" + url
        netloc = urlparse(candidate).netloc
        # strip userinfo and port
        host = netloc.split("@")[-1].split(":")[0]
        return host.lower()

    def is_allowed(self, url: str) -> Tuple[bool, str]:
        """Return ``(allowed, reason)`` for ``url`` (deterministic, no I/O)."""
        host = self.host_of(url)
        if not host:
            return (False, "no host in URL")
        for allowed in self.allow:
            if host == allowed or host.endswith("." + allowed):
                return (True, f"allowlisted: {allowed}")
        if self.default_deny:
            return (False, f"host {host!r} not in egress allowlist")
        return (True, "default-allow (no allowlist match; default_deny is off)")

    def check(self, url: str) -> bool:
        """Raise :class:`EgressBlocked` if ``url`` is not permitted; else return True."""
        ok, reason = self.is_allowed(url)
        if not ok:
            raise EgressBlocked(reason)
        return True


def from_env(env: Mapping[str, str] | None = None) -> EgressPolicy:
    """Build an :class:`EgressPolicy` from environment variables."""
    env = env if env is not None else os.environ
    raw = env.get("XAVANI_EGRESS_ALLOWLIST", "") or ""
    allow = [tok for tok in re.split(r"[,\s]+", raw) if tok]
    default_deny = str(env.get("XAVANI_EGRESS_DEFAULT_DENY", "")).strip().lower() in (
        "1", "true", "yes", "on",
    )
    return EgressPolicy.create(allow=allow, default_deny=default_deny)


__all__ = ["EgressPolicy", "EgressBlocked", "from_env"]
