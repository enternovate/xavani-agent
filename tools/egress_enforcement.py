"""Egress enforcement at the httpx transport layer (D03).

``tools/egress_policy.py`` defines the policy (allowlist + default-deny).
This module enforces it where the agent actually sends bytes: the httpx
transport. Wrapping ``httpx.HTTPTransport`` means every request through a
client built with this transport is checked against the policy BEFORE a
socket opens — the agent physically cannot exfiltrate to a host outside
the allowlist when ``XAVANI_EGRESS_DEFAULT_DENY=1``.

Enforcement is OFF by default (policy default-allow), so existing behavior
is unchanged unless an operator sets the allowlist + default-deny.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from tools.egress_policy import EgressPolicy, EgressBlocked, from_env

logger = logging.getLogger(__name__)


class EgressEnforcingTransport(httpx.BaseTransport):
    """Wrap an httpx transport and block requests to non-allowlisted hosts.

    ``handle_request`` is the single entry point httpx uses for both sync
    and async paths; the async variant delegates to the sync transport, so
    one check covers both.
    """

    def __init__(
        self,
        *,
        policy: Optional[EgressPolicy] = None,
        inner: Optional[httpx.BaseTransport] = None,
        transport_kwargs: Optional[dict] = None,
    ) -> None:
        self._policy = policy if policy is not None else from_env()
        if inner is not None:
            self._inner = inner
        else:
            self._inner = httpx.HTTPTransport(**(transport_kwargs or {}))

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        try:
            self._policy.check(url)
        except EgressBlocked as exc:
            logger.warning("EGRESS BLOCKED: %s (%s)", url, exc)
            raise
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


def build_egress_client(
    base_url: str = "",
    *,
    policy: Optional[EgressPolicy] = None,
    **client_kwargs,
) -> httpx.Client:
    """Build an httpx.Client whose transport enforces the egress policy."""
    kwargs = dict(client_kwargs)
    if base_url:
        kwargs["base_url"] = base_url
    return httpx.Client(
        transport=EgressEnforcingTransport(policy=policy),
        **kwargs,
    )


def maybe_enforce(base_url: str = "", **client_kwargs) -> Optional[httpx.Client]:
    """Return an enforcing client ONLY when default-deny is active.

    When the operator has NOT enabled default-deny, return ``None`` so the
    caller keeps its existing client construction (zero behavior change).
    When default-deny IS active, return an enforcing client so every
    request is checked.
    """
    policy = from_env()
    if not policy.default_deny:
        return None
    return build_egress_client(base_url=base_url, policy=policy, **client_kwargs)


__all__ = [
    "EgressEnforcingTransport",
    "build_egress_client",
    "maybe_enforce",
]
