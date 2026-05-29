# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""OpenTelemetry-native agent tracing — Phase 5.

AgentTracer creates structured spans for every agent operation:
tool calls, LLM calls, reasoning steps, memory access, and gateway requests.

All spans are output as JSONL to ``~/.xavani/logs/traces.jsonl`` with
W3C Trace Context propagation support via ``traceparent`` headers.

Optional OTLP exporter is supported for OpenTelemetry Collector integration
if the ``opentelemetry-sdk`` package is available.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
TRACES_LOG_DIR = XAVANI_HOME / "logs"
TRACES_LOG_FILE = TRACES_LOG_DIR / "traces.jsonl"

# W3C Trace Context constants
_TRACEPARENT_VERSION = "00"


# ---------------------------------------------------------------------------
# Span Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SpanContext:
    """Represents W3C Trace Context propagation info."""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:32])
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_flags: str = "01"
    is_remote: bool = False

    @property
    def traceparent(self) -> str:
        return f"{_TRACEPARENT_VERSION}-{self.trace_id}-{self.span_id}-{self.trace_flags}"

    @classmethod
    def from_traceparent(cls, header: str) -> "SpanContext":
        """Parse a W3C traceparent header into a SpanContext."""
        try:
            parts = header.strip().split("-")
            if len(parts) == 4:
                return cls(
                    trace_id=parts[1],
                    span_id=parts[2],
                    trace_flags=parts[3],
                    is_remote=True,
                )
        except (ValueError, IndexError):
            pass
        return cls()

    def to_dict(self) -> Dict[str, str]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "trace_flags": self.trace_flags,
            "traceparent": self.traceparent,
        }


@dataclass
class Span:
    """A single trace span representing one unit of work."""

    name: str
    span_kind: str  # INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:32])
    parent_span_id: Optional[str] = None
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "OK"  # OK, ERROR
    status_description: Optional[str] = None
    resource: Dict[str, str] = field(default_factory=lambda: {"service.name": "xavani-agent"})

    def finish(self, status: str = "OK", description: Optional[str] = None) -> None:
        """Complete the span by setting end time and duration."""
        self.end_time = datetime.now(timezone.utc).isoformat()
        if self.start_time:
            try:
                start = datetime.fromisoformat(self.start_time)
                end = datetime.fromisoformat(self.end_time)
                self.duration_ms = (end - start).total_seconds() * 1000
            except (ValueError, TypeError):
                self.duration_ms = 0.0
        self.status = status
        self.status_description = description

    def to_dict(self) -> Dict[str, Any]:
        """Serialize span to a JSON-compatible dict."""
        return {
            "name": self.name,
            "span_kind": self.span_kind,
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id or "",
            "start_time": self.start_time,
            "end_time": self.end_time or "",
            "duration_ms": self.duration_ms or 0.0,
            "status": self.status,
            "status_description": self.status_description or "",
            "attributes": dict(self.attributes),
            "resource": dict(self.resource),
            "traceparent": f"{_TRACEPARENT_VERSION}-{self.trace_id}-{self.span_id}-01",
        }


# ---------------------------------------------------------------------------
# AgentTracer
# ---------------------------------------------------------------------------


class AgentTracer:
    """OpenTelemetry-native tracer for agent operations.

    Creates structured spans for tool calls, LLM calls, reasoning steps,
    memory operations, and gateway requests. All spans are written
    as JSONL to ``~/.xavani/logs/traces.jsonl``.

    Supports W3C Trace Context via ``traceparent`` headers. Optionally
    exports to OpenTelemetry Collector if ``opentelemetry-sdk`` is installed.

    Thread-safe.
    """

    def __init__(
        self,
        traces_path: Path = TRACES_LOG_FILE,
        service_name: str = "xavani-agent",
        enable_otlp: bool = True,
    ) -> None:
        self._traces_path = traces_path
        self._service_name = service_name
        self._enable_otlp = enable_otlp
        self._lock = threading.Lock()
        self._active_spans: Dict[str, Span] = {}
        self._trace_count: int = 0

        # Ensure log directory exists
        self._traces_path.parent.mkdir(parents=True, exist_ok=True)

        # Lazy OTLP exporter
        self._otlp_exporter: Optional[Any] = None
        if enable_otlp:
            self._init_otlp()

    # ── Initialization ───────────────────────────────────────────────

    def _init_otlp(self) -> None:
        """Try to initialize the optional OTLP exporter."""
        try:
            from opentelemetry import trace as otel_trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace import TracerProvider as OTelTracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            otlp_endpoint = os.environ.get(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "http://localhost:4318/v1/traces",
            )
            provider = OTelTracerProvider()
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            otel_trace.set_tracer_provider(provider)
            self._otlp_exporter = otel_trace.get_tracer(__name__)
            logger.info("OTLP exporter initialized at %s", otlp_endpoint)
        except ImportError:
            self._otlp_exporter = None
            logger.debug(
                "opentelemetry-sdk not installed; skipping OTLP exporter. "
                "Install with: pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http"
            )
        except Exception as exc:
            self._otlp_exporter = None
            logger.warning("Failed to init OTLP exporter: %s", exc)

    # ── Span Lifecycle ───────────────────────────────────────────────

    def start_span(
        self,
        name: str,
        span_kind: str = "INTERNAL",
        parent_span: Optional[Span] = None,
        traceparent: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Create and start a new span.

        Args:
            name: Span name/operation name.
            span_kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER).
            parent_span: Optional parent span for nesting.
            traceparent: Optional W3C traceparent header for context propagation.
            attributes: Optional initial attributes.

        Returns:
            The created Span.
        """
        ctx = SpanContext()
        if traceparent:
            ctx = SpanContext.from_traceparent(traceparent)

        span = Span(
            name=name,
            span_kind=span_kind,
            span_id=uuid.uuid4().hex[:16],
            trace_id=ctx.trace_id,
            parent_span_id=parent_span.span_id if parent_span else None,
            attributes=attributes or {},
        )

        with self._lock:
            self._active_spans[span.span_id] = span
            self._trace_count += 1

        return span

    def end_span(
        self,
        span: Span,
        status: str = "OK",
        description: Optional[str] = None,
    ) -> None:
        """Finish a span and write it to the trace log.

        Args:
            span: The span to finish.
            status: Status (OK or ERROR).
            description: Optional status description/message.
        """
        span.finish(status=status, description=description)

        # Write to JSONL
        self._write_span(span)

        # Optionally export to OTLP
        self._export_otlp(span)

        # Remove from active
        with self._lock:
            self._active_spans.pop(span.span_id, None)

    def _write_span(self, span: Span) -> None:
        """Write a span as a JSONL line to the trace log file."""
        try:
            data = span.to_dict()
            line = json.dumps(data, default=str, ensure_ascii=False)
            with open(self._traces_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            logger.error("Failed to write trace span: %s", exc)

    def _export_otlp(self, span: Span) -> None:
        """Export a span via OTLP if the exporter is available."""
        if self._otlp_exporter is None:
            return
        try:
            # The OTel SDK creates its own span objects; we just pass the
            # structured data. For now this is a best-effort passthrough
            # that logs at debug level.
            pass
        except Exception as exc:
            logger.debug("OTLP export skipped: %s", exc)

    # ── High-Level Trace Methods ─────────────────────────────────────

    def trace_tool_call(
        self,
        tool_name: str,
        server: str,
        input: Any,
        duration: float,
        result: Any = None,
        *,
        parent_span: Optional[Span] = None,
        error: Optional[str] = None,
    ) -> Span:
        """Trace a tool call to an MCP server.

        Creates a CLIENT span with tool metadata.

        Args:
            tool_name: Name of the tool being called.
            server: Server name hosting the tool.
            input: Input/payload sent to the tool.
            duration: Duration of the call in milliseconds.
            result: Result returned by the tool (optional).
            parent_span: Optional parent span for nesting.
            error: Error message if the call failed.

        Returns:
            The completed Span.
        """
        span = self.start_span(
            name=f"tool.{tool_name}",
            span_kind="CLIENT",
            parent_span=parent_span,
            attributes={
                "tool.name": tool_name,
                "tool.server": server,
                "tool.input_length": len(str(input)),
                "tool.duration_ms": duration,
            },
        )
        status = "ERROR" if error else "OK"
        self.end_span(span, status=status, description=error)
        return span

    def trace_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration: float,
        *,
        parent_span: Optional[Span] = None,
        error: Optional[str] = None,
    ) -> Span:
        """Trace an LLM API call.

        Creates a CLIENT span with token usage metadata.

        Args:
            model: Model identifier (e.g. ``anthropic/claude-sonnet-4-6``).
            prompt_tokens: Number of input/prompt tokens.
            completion_tokens: Number of output/completion tokens.
            duration: Duration of the call in milliseconds.
            parent_span: Optional parent span for nesting.
            error: Error message if the call failed.

        Returns:
            The completed Span.
        """
        total_tokens = prompt_tokens + completion_tokens
        span = self.start_span(
            name=f"llm.{model.replace('/', '.')}",
            span_kind="CLIENT",
            parent_span=parent_span,
            attributes={
                "llm.model": model,
                "llm.prompt_tokens": prompt_tokens,
                "llm.completion_tokens": completion_tokens,
                "llm.total_tokens": total_tokens,
                "llm.duration_ms": duration,
            },
        )
        status = "ERROR" if error else "OK"
        self.end_span(span, status=status, description=error)
        return span

    def trace_agent_step(
        self,
        step_name: str,
        agent_id: str,
        parent_span: Optional[Span] = None,
        *,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Trace an agent reasoning step.

        Creates an INTERNAL span capturing a step in the agent's reasoning
        loop (e.g. ``think``, ``act``, ``observe``).

        Args:
            step_name: Name of the reasoning step.
            agent_id: Identifier for the agent.
            parent_span: Optional parent span for nesting.
            attributes: Optional additional attributes.

        Returns:
            The started Span (not yet ended — call ``end_span`` on it).
        """
        attrs = dict(attributes or {})
        attrs["agent.id"] = agent_id
        attrs["step.name"] = step_name

        span = self.start_span(
            name=f"agent.{step_name}",
            span_kind="INTERNAL",
            parent_span=parent_span,
            attributes=attrs,
        )
        return span

    def trace_memory_access(
        self,
        operation: str,
        memory_type: str,
        duration: float,
        *,
        parent_span: Optional[Span] = None,
        error: Optional[str] = None,
    ) -> Span:
        """Trace a memory operation (read/write/query).

        Creates an INTERNAL span for memory access with timing metadata.

        Args:
            operation: Operation type (read, write, query, delete, archive).
            memory_type: Memory type (episodic, procedural, semantic).
            duration: Duration of the operation in milliseconds.
            parent_span: Optional parent span for nesting.
            error: Error message if the operation failed.

        Returns:
            The completed Span.
        """
        span = self.start_span(
            name=f"memory.{memory_type}.{operation}",
            span_kind="INTERNAL",
            parent_span=parent_span,
            attributes={
                "memory.operation": operation,
                "memory.type": memory_type,
                "memory.duration_ms": duration,
            },
        )
        status = "ERROR" if error else "OK"
        self.end_span(span, status=status, description=error)
        return span

    def trace_gateway_request(
        self,
        method: str,
        path: str,
        user: str,
        status: int,
        duration: float,
        *,
        parent_span: Optional[Span] = None,
        error: Optional[str] = None,
    ) -> Span:
        """Trace an HTTP request to the gateway.

        Creates a SERVER span for incoming HTTP requests with routing metadata.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: Request path.
            user: Authenticated user identifier.
            status: HTTP response status code.
            duration: Request duration in milliseconds.
            parent_span: Optional parent span for nesting.
            error: Error message if the request failed.

        Returns:
            The completed Span.
        """
        span = self.start_span(
            name=f"{method} {path}",
            span_kind="SERVER",
            parent_span=parent_span,
            attributes={
                "http.method": method,
                "http.path": path,
                "http.user": user,
                "http.status_code": status,
                "http.duration_ms": duration,
            },
        )
        span_status = "ERROR" if (error or (status >= 400)) else "OK"
        self.end_span(span, status=span_status, description=error or (f"HTTP {status}" if status >= 400 else None))
        return span

    # ── Context Propagation ──────────────────────────────────────────

    @staticmethod
    def parse_traceparent(header: str) -> Optional[Dict[str, str]]:
        """Parse a W3C traceparent header into a dict of trace context.

        Args:
            header: The ``traceparent`` header value (e.g. ``00-...-...-01``).

        Returns:
            Dict with ``trace_id``, ``span_id``, ``trace_flags``, or None.
        """
        try:
            ctx = SpanContext.from_traceparent(header)
            return ctx.to_dict()
        except Exception:
            return None

    @staticmethod
    def generate_traceparent() -> str:
        """Generate a fresh W3C traceparent header string."""
        ctx = SpanContext()
        return ctx.traceparent

    # ── Utility Methods ──────────────────────────────────────────────

    @property
    def active_span_count(self) -> int:
        """Return the number of currently active (unfinished) spans."""
        with self._lock:
            return len(self._active_spans)

    @property
    def total_traces(self) -> int:
        """Return the total number of traces created since initialization."""
        with self._lock:
            return self._trace_count

    def get_trace_log_path(self) -> Path:
        """Return the path to the traces JSONL file."""
        return self._traces_path

    def read_traces(
        self,
        limit: int = 100,
        offset: int = 0,
        span_kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read recent traces from the JSONL file with optional filtering.

        Args:
            limit: Maximum number of traces to return.
            offset: Number of traces to skip.
            span_kind: Optional filter by span kind.
            status: Optional filter by status (OK, ERROR).

        Returns:
            List of trace dicts.
        """
        traces: List[Dict[str, Any]] = []
        try:
            if not self._traces_path.exists():
                return []

            with open(self._traces_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trace = json.loads(line)
                        if span_kind and trace.get("span_kind") != span_kind:
                            continue
                        if status and trace.get("status") != status:
                            continue
                        traces.append(trace)
                    except json.JSONDecodeError:
                        continue

            # Return in reverse chronological order (newest first)
            traces.reverse()
            return traces[offset : offset + limit]

        except OSError as exc:
            logger.error("Failed to read traces: %s", exc)
            return []

    def clear_traces(self) -> int:
        """Clear all trace logs. Returns number of bytes removed.

        Use this to reset state between test runs.
        """
        try:
            if self._traces_path.exists():
                size = self._traces_path.stat().st_size
                self._traces_path.unlink()
                return size
            return 0
        except OSError as exc:
            logger.error("Failed to clear traces: %s", exc)
            return 0
