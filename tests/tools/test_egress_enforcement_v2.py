# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Round-2 D03: egress enforcement at the client-factory layer.

Covers the async transport and the ``client_or_enforced`` /
``async_client_or_enforced`` helpers used by the agent's HTTP client
factories (adapters, metadata, usage, OAuth manager). Enforcement is
active only when the policy says default-deny.
"""

import httpx
import pytest

from tools.egress_enforcement import (
    EgressEnforcingAsyncTransport,
    EgressEnforcingTransport,
    async_client_or_enforced,
    build_egress_async_client,
    build_egress_client,
    client_or_enforced,
)
from tools.egress_policy import EgressBlocked, EgressPolicy


def _deny_policy(*allow):
    return EgressPolicy.create(allow=allow, default_deny=True)


def _fake_response():
    return httpx.Response(200, request=httpx.Request("GET", "https://allowed.example/x"))


class _FakeTransport(httpx.BaseTransport):
    """Records the request and returns a canned response without I/O."""

    def __init__(self):
        self.requests = []

    def handle_request(self, request):
        self.requests.append(str(request.url))
        return _fake_response()


class _FakeAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.requests = []

    async def handle_async_request(self, request):
        self.requests.append(str(request.url))
        return _fake_response()

    async def aclose(self):
        pass


def test_sync_transport_blocks_non_allowlisted():
    inner = _FakeTransport()
    transport = EgressEnforcingTransport(
        policy=_deny_policy("allowed.example"), inner=inner
    )
    request = httpx.Request("GET", "https://evil.example/x")
    with pytest.raises(EgressBlocked):
        transport.handle_request(request)
    assert inner.requests == []  # the socket never opened


def test_sync_transport_passes_allowlisted():
    inner = _FakeTransport()
    transport = EgressEnforcingTransport(
        policy=_deny_policy("allowed.example"), inner=inner
    )
    request = httpx.Request("GET", "https://allowed.example/x")
    transport.handle_request(request)
    assert inner.requests == ["https://allowed.example/x"]


@pytest.mark.asyncio
async def test_async_transport_blocks_non_allowlisted():
    inner = _FakeAsyncTransport()
    transport = EgressEnforcingAsyncTransport(
        policy=_deny_policy("allowed.example"), inner=inner
    )
    request = httpx.Request("GET", "https://evil.example/x")
    with pytest.raises(EgressBlocked):
        await transport.handle_async_request(request)
    assert inner.requests == []
    await transport.aclose()


@pytest.mark.asyncio
async def test_async_transport_passes_allowlisted():
    inner = _FakeAsyncTransport()
    transport = EgressEnforcingAsyncTransport(
        policy=_deny_policy("allowed.example"), inner=inner
    )
    request = httpx.Request("GET", "https://allowed.example/x")
    await transport.handle_async_request(request)
    assert inner.requests == ["https://allowed.example/x"]
    await transport.aclose()


def test_build_egress_client_blocks_via_real_client_pipeline(monkeypatch):
    """A real client built with the enforcing transport blocks before I/O."""
    policy = _deny_policy("allowed.example")
    client = build_egress_client(policy=policy)
    with pytest.raises(EgressBlocked):
        client.get("https://evil.example/x")
    client.close()


def test_build_egress_async_client_blocks(monkeypatch):
    async def _run():
        policy = _deny_policy("allowed.example")
        async with build_egress_async_client(policy=policy) as client:
            with pytest.raises(EgressBlocked):
                await client.get("https://evil.example/x")

    import asyncio

    asyncio.run(_run())


def test_client_or_enforced_returns_plain_when_not_denying(monkeypatch):
    monkeypatch.delenv("XAVANI_EGRESS_DEFAULT_DENY", raising=False)
    monkeypatch.delenv("XAVANI_EGRESS_ALLOWLIST", raising=False)
    client = client_or_enforced(timeout=5.0)
    assert isinstance(client, httpx.Client)
    assert not isinstance(client._transport, EgressEnforcingTransport)
    client.close()


def test_client_or_enforced_returns_enforcing_when_denying(monkeypatch):
    monkeypatch.setenv("XAVANI_EGRESS_DEFAULT_DENY", "1")
    monkeypatch.setenv("XAVANI_EGRESS_ALLOWLIST", "allowed.example")
    client = client_or_enforced(timeout=5.0)
    assert isinstance(client._transport, EgressEnforcingTransport)
    with pytest.raises(EgressBlocked):
        client.get("https://evil.example/x")
    client.close()


def test_async_client_or_enforced_returns_enforcing_when_denying(monkeypatch):
    monkeypatch.setenv("XAVANI_EGRESS_DEFAULT_DENY", "1")
    monkeypatch.setenv("XAVANI_EGRESS_ALLOWLIST", "allowed.example")

    async def _run():
        client = async_client_or_enforced(timeout=5.0)
        assert isinstance(client._transport, EgressEnforcingAsyncTransport)
        with pytest.raises(EgressBlocked):
            await client.get("https://evil.example/x")
        await client.aclose()

    import asyncio

    asyncio.run(_run())
