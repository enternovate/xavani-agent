# MIT License
#
# Copyright (c) 2025-2026 Enternovate
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ============================================================================
# Xavani Agent — Weixin (WeCom) stub module
# ============================================================================

"""Stub for the Weixin (WeCom) platform adapter.

The full Weixin integration was stripped from this fork. This module keeps the
public surface importable so that:

* `xavani_cli.gateway` and `tools.send_message_tool` still load without
  crashing when their lazy imports run.
* The test module collects, but its tests skip at runtime via `pytestmark`.

Calls that actually try to use the adapter raise `RuntimeError` with a clear
message instructing users to enable the platform externally.
"""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional, Tuple


AIOHTTP_AVAILABLE = False
try:  # pragma: no cover - opportunistic
    import aiohttp  # type: ignore  # noqa: F401
    AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore[assignment]


_UNAVAILABLE_MESSAGE = (
    "The Weixin (WeCom) platform adapter is not available in this build. "
    "Re-install the full xavani-agent package or use a different platform."
)


class ContextTokenStore:
    """In-memory stub token store.

    The real implementation persists access/JS tickets to disk so that they
    can be reused across processes. The stub keeps them in memory so that
    unit tests can construct it without touching the filesystem.
    """

    def __init__(self, directory: Optional[str] = None) -> None:
        self.directory = directory
        self._tokens: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[dict[str, Any]]:
        entry = self._tokens.get(key)
        if entry is None:
            return None
        if entry.get("expires_at", 0) <= time.time():
            self._tokens.pop(key, None)
            return None
        return dict(entry)

    def set(self, key: str, value: Mapping[str, Any], ttl_seconds: int = 0) -> None:
        record = dict(value)
        if ttl_seconds:
            record["expires_at"] = time.time() + ttl_seconds
        self._tokens[key] = record

    def clear(self) -> None:
        self._tokens.clear()


class WeixinAdapter:
    """Stub adapter.

    Constructing the adapter is allowed (tests do it), but any real method
    that would have made an API call raises `RuntimeError`. The error is
    informative so callers can present a clean message to operators.
    """

    name = "weixin"

    def __init__(self, config: Any) -> None:
        self.config = config

    def is_available(self) -> bool:
        return False

    async def send(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(_UNAVAILABLE_MESSAGE)

    async def receive(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(_UNAVAILABLE_MESSAGE)


def check_weixin_requirements() -> Tuple[bool, str]:
    """Report whether the Weixin adapter can be used.

    Returns ``(ok, message)``. The stub always reports ``False`` with an
    explanatory message so callers can surface it to the user.
    """
    return False, _UNAVAILABLE_MESSAGE


def qr_login(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError(_UNAVAILABLE_MESSAGE)


def send_weixin_direct(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError(_UNAVAILABLE_MESSAGE)


async def _api_get(*_args: Any, **_kwargs: Any) -> dict[str, Any]:  # pragma: no cover
    raise RuntimeError(_UNAVAILABLE_MESSAGE)


async def _api_post(*_args: Any, **_kwargs: Any) -> dict[str, Any]:  # pragma: no cover
    raise RuntimeError(_UNAVAILABLE_MESSAGE)


async def _send_message(*_args: Any, **_kwargs: Any) -> dict[str, Any]:  # pragma: no cover
    raise RuntimeError(_UNAVAILABLE_MESSAGE)


async def _get_upload_url(*_args: Any, **_kwargs: Any) -> dict[str, Any]:  # pragma: no cover
    raise RuntimeError(_UNAVAILABLE_MESSAGE)


__all__ = [
    "ContextTokenStore",
    "WeixinAdapter",
    "check_weixin_requirements",
    "qr_login",
    "send_weixin_direct",
    "AIOHTTP_AVAILABLE",
]
