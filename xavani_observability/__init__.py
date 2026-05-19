# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Observability — Phase 5.

OpenTelemetry-native tracing, metrics collection, dashboard, and audit viewer
for the Xavani Agent Gateway.

Everything stores data under ``~/.xavani/``. Zero telemetry, zero external
dependencies beyond the Python standard library and rich.
"""

from __future__ import annotations

from .tracer import AgentTracer
from .metrics import MetricsCollector
from .dashboard import DashboardServer
from .audit_viewer import AuditViewer

__all__ = [
    "AgentTracer",
    "MetricsCollector",
    "DashboardServer",
    "AuditViewer",
]
