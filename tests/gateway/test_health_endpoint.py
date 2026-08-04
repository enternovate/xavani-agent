# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A10/E01: gateway health + readiness endpoint tests.

health_status reports liveness; readiness_status reports whether the
gateway can take inbound traffic (>=1 messaging platform connected).
The status endpoint serves /health, /ready and /metrics on a configured
port (gated via XAVANI_PROMETHEUS_PORT / observability.prometheus_port).
"""

import json
import threading

import pytest

from gateway import health
from xavani_observability.prometheus import (
    PrometheusEndpoint,
    get_prometheus_port,
    render_metrics_text,
)


@pytest.fixture(autouse=True)
def _reset_health(monkeypatch):
    monkeypatch.setattr(health, "_state_provider", None)
    yield


def test_health_status_without_provider():
    payload = health.health_status()
    assert payload["status"] == "ok"
    assert payload["running"] is True


def test_health_status_with_provider():
    health.set_state_provider(
        lambda: {
            "version": "0.1.0",
            "running": True,
            "platforms_connected": 2,
            "platforms": ["discord", "telegram"],
        }
    )
    payload = health.health_status()
    assert payload["version"] == "0.1.0"
    assert payload["platforms_connected"] == 2
    assert payload["platforms"] == ["discord", "telegram"]


def test_readiness_not_ready_without_platforms():
    health.set_state_provider(lambda: {"running": True, "platforms_connected": 0})
    payload = health.readiness_status()
    assert payload["ready"] is False
    assert "no messaging platform" in payload["reason"]


def test_readiness_ready_with_platforms():
    health.set_state_provider(
        lambda: {"running": True, "platforms_connected": 1, "platforms": ["telegram"]}
    )
    payload = health.readiness_status()
    assert payload["ready"] is True
    assert payload["reason"] == "ok"


def test_readiness_not_ready_when_gateway_stopped():
    health.set_state_provider(lambda: {"running": False, "platforms_connected": 2})
    assert health.readiness_status()["ready"] is False


def test_provider_exception_fails_safe():
    def _boom():
        raise RuntimeError("boom")

    health.set_state_provider(_boom)
    assert health.health_status()["status"] == "ok"
    assert health.readiness_status()["ready"] is False


def test_prometheus_port_from_env(monkeypatch):
    monkeypatch.setenv("XAVANI_PROMETHEUS_PORT", "9101")
    assert get_prometheus_port() == 9101


def test_prometheus_port_defaults_zero(monkeypatch):
    monkeypatch.delenv("XAVANI_PROMETHEUS_PORT", raising=False)
    assert get_prometheus_port() == 0


def test_render_metrics_text_shape():
    summary = {
        "tools": {"read_file": {"call_count": 3, "p50_ms": 1.0, "p95_ms": 2.0, "p99_ms": 3.0}},
        "error_rates": {},
        "total_tool_calls": 3,
        "total_llm_calls": 1,
        "total_errors": 0,
        "overall_error_rate": 0.0,
    }
    text = render_metrics_text(summary)
    assert 'xavani_tool_calls_total{tool="read_file"} 3' in text
    assert 'xavani_tool_latency_ms{tool="read_file",quantile="0.95"} 2.0' in text
    assert "xavani_total_tool_calls 3" in text


def test_endpoint_serves_health_and_ready(monkeypatch):
    health.set_state_provider(
        lambda: {"running": True, "platforms_connected": 1, "platforms": ["telegram"]}
    )
    endpoint = PrometheusEndpoint(port=0)  # disabled — not used here
    del endpoint

    # Spin a real server on an ephemeral port.
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = PrometheusEndpoint(port=port)
    assert server.start() is True
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
            assert r.status == 200
            payload = json.loads(r.read())
            assert payload["status"] == "ok"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=5) as r:
            assert r.status == 200
            payload = json.loads(r.read())
            assert payload["ready"] is True
    finally:
        server.stop()
