"""Tests for egress enforcement at the transport layer (D03)."""

import os

import httpx
import pytest

from tools.egress_enforcement import (
    EgressEnforcingTransport,
    build_egress_client,
    maybe_enforce,
)
from tools.egress_policy import EgressBlocked, EgressPolicy

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clear_egress_env(monkeypatch):
    monkeypatch.delenv("XAVANI_EGRESS_ALLOWLIST", raising=False)
    monkeypatch.delenv("XAVANI_EGRESS_DEFAULT_DENY", raising=False)


class TestEgressEnforcingTransport:
    def test_blocks_non_allowlisted_host(self):
        policy = EgressPolicy.create(allow=["api.example.com"], default_deny=True)
        transport = EgressEnforcingTransport(policy=policy)
        request = httpx.Request("GET", "https://evil.com/data")
        with pytest.raises(EgressBlocked):
            transport.handle_request(request)
        transport.close()

    def test_allows_allowlisted_host(self):
        policy = EgressPolicy.create(allow=["api.example.com"], default_deny=True)
        inner = httpx.MockTransport(lambda req: httpx.Response(200, text="ok"))
        transport = EgressEnforcingTransport(policy=policy, inner=inner)
        request = httpx.Request("GET", "https://api.example.com/v1")
        response = transport.handle_request(request)
        assert response.status_code == 200
        transport.close()

    def test_default_allow_when_deny_off(self):
        policy = EgressPolicy.create(allow=[], default_deny=False)
        inner = httpx.MockTransport(lambda req: httpx.Response(200, text="ok"))
        transport = EgressEnforcingTransport(policy=policy, inner=inner)
        request = httpx.Request("GET", "https://anything.example.org/")
        assert transport.handle_request(request).status_code == 200
        transport.close()


class TestMaybeEnforce:
    def test_none_when_default_deny_off(self):
        assert maybe_enforce() is None

    def test_client_when_default_deny_on(self, monkeypatch):
        monkeypatch.setenv("XAVANI_EGRESS_ALLOWLIST", "api.example.com")
        monkeypatch.setenv("XAVANI_EGRESS_DEFAULT_DENY", "1")
        client = maybe_enforce("https://api.example.com/v1")
        assert client is not None
        assert isinstance(client._transport, EgressEnforcingTransport)
        client.close()


class TestBuildEgressClient:
    def test_client_blocks_forbidden_host(self):
        policy = EgressPolicy.create(allow=["api.example.com"], default_deny=True)
        client = build_egress_client(policy=policy)
        with pytest.raises(EgressBlocked):
            client.get("https://blocked.example.org/")
        client.close()

    def test_client_allows_allowlisted(self):
        policy = EgressPolicy.create(allow=["api.example.com"], default_deny=True)
        inner = httpx.MockTransport(lambda req: httpx.Response(200, text="ok"))
        client = httpx.Client(
            transport=EgressEnforcingTransport(policy=policy, inner=inner),
        )
        resp = client.get("https://api.example.com/v1")
        assert resp.status_code == 200
        client.close()
