# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Optional Prometheus metrics endpoint for Xavani Agent.

Exposes agent metrics in Prometheus format over HTTP. Disabled by default.
Enable via env: ``XAVANI_PROMETHEUS_PORT=9100`` or config:
``observability.prometheus_port: 9100``.

Only starts when explicitly enabled — zero overhead when off.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


class _MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves Prometheus-format metrics."""

    def do_GET(self):
        if self.path == "/metrics":
            metrics = self.server._get_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(metrics.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


class PrometheusEndpoint:
    """Optional Prometheus metrics endpoint.

    Only starts when a port is configured. Zero overhead when disabled.
    """

    def __init__(self, port: int = 0):
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._metrics_fn = None

    def set_metrics_provider(self, fn):
        """Set a callable that returns Prometheus-format metrics string."""
        self._metrics_fn = fn

    def start(self) -> bool:
        """Start the Prometheus endpoint. Returns True if started."""
        if self._port <= 0:
            return False

        try:
            self._server = HTTPServer(("0.0.0.0", self._port), _MetricsHandler)
            self._server._get_metrics = self._get_metrics
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            logger.info("Prometheus endpoint started on port %d", self._port)
            return True
        except Exception as exc:
            logger.warning("Failed to start Prometheus endpoint: %s", exc)
            return False

    def stop(self):
        """Stop the Prometheus endpoint."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _get_metrics(self) -> str:
        """Return Prometheus-format metrics."""
        if self._metrics_fn:
            return self._metrics_fn()
        return "# No metrics provider configured\n"


def get_prometheus_port() -> int:
    """Get the configured Prometheus port from env or config."""
    # Env var takes precedence
    port_str = os.environ.get("XAVANI_PROMETHEUS_PORT", "")
    if port_str:
        try:
            return int(port_str)
        except ValueError:
            return 0

    # Config fallback
    try:
        from xavani_cli.config import load_config
        cfg = load_config()
        obs = cfg.get("observability", {})
        return int(obs.get("prometheus_port", 0))
    except Exception:
        return 0
