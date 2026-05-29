# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""No-op stub kept after the Nous Portal provider was removed.

Existing call sites still import these helpers to short-circuit retries when
the upstream provider was rate-limited. Since Xavani no longer ships a Nous
Portal integration, the guard always reports "no limit recorded" and
``clear_nous_rate_limit`` is a no-op. Keeps the import contract stable
without performing any cross-session bookkeeping.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def nous_rate_limit_remaining() -> Optional[float]:
    return None


def clear_nous_rate_limit() -> None:
    return None


def record_nous_rate_limit(*_args: Any, **_kwargs: Any) -> None:
    return None


def get_nous_rate_limit_state() -> Mapping[str, Any]:
    return {}


def is_genuine_nous_rate_limit(*_args: Any, **_kwargs: Any) -> bool:
    """No-op stub — Nous Portal is no longer integrated, so genuine
    rate-limit detection is irrelevant. Returns False so callers fall
    through to the normal retry/backoff path."""
    return False
