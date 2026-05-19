# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Lightweight web dashboard for real-time observability — Phase 5.

DashboardServer serves a single HTML page on ``localhost:8081`` that
displays live agent metrics with auto-refresh every 5 seconds.

Shows:
- Active sessions
- Recent tool calls with latencies
- Latency chart (tool latencies over time)
- Error rate
- Token usage breakdown
- Audit log viewer with filtering

All rendering is client-side. No JavaScript framework needed — just
vanilla HTML/CSS/JS.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .metrics import MetricsCollector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
AUDIT_DB_PATH = XAVANI_HOME / "data" / "oag_audit.db"
METRICS_FILE = XAVANI_HOME / "logs" / "metrics.json"

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8081


# ---------------------------------------------------------------------------
# Dashboard HTTP Handler
# ---------------------------------------------------------------------------


class DashboardHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard server.

    Serves:
    - ``GET /`` → HTML page
    - ``GET /api/metrics`` → JSON metrics snapshot
    - ``GET /api/audit?limit=N&user=X&tool=Y&errors=1`` → JSON audit entries
    - ``GET /api/traces?limit=N`` → JSON trace entries
    """

    # Shared references set by the server
    metrics_collector: Optional[MetricsCollector] = None

    def do_GET(self) -> None:
        """Route incoming GET requests."""
        try:
            if self.path == "/" or self.path == "/index.html":
                self._serve_html()
            elif self.path.startswith("/api/metrics"):
                self._serve_metrics()
            elif self.path.startswith("/api/audit"):
                self._serve_audit()
            elif self.path.startswith("/api/traces"):
                self._serve_traces()
            else:
                self._send_json(404, {"error": "Not found"})
        except Exception as exc:
            logger.error("Dashboard handler error: %s", exc)
            self._send_json(500, {"error": str(exc)})

    # ── Route Handlers ───────────────────────────────────────────────

    def _serve_html(self) -> None:
        """Serve the main dashboard HTML page."""
        html = _DASHBOARD_HTML
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_metrics(self) -> None:
        """Return current metrics as JSON."""
        if self.metrics_collector is None:
            data: Dict[str, Any] = {"status": "no_collector"}
        else:
            data = self.metrics_collector.get_summary()
        self._send_json(200, data)

    def _serve_audit(self) -> None:
        """Return audit log entries as JSON with optional filters."""
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        limit = int(params.get("limit", ["50"])[0])
        user_filter = params.get("user", [None])[0]
        tool_filter = params.get("tool", [None])[0]
        errors_only = params.get("errors", ["0"])[0] in ("1", "true")

        entries = self._query_audit(
            limit=limit,
            user_id=user_filter,
            tool_name=tool_filter,
            errors_only=errors_only,
        )
        self._send_json(200, {"entries": entries, "count": len(entries)})

    def _serve_traces(self) -> None:
        """Return recent trace entries as JSON."""
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        limit = int(params.get("limit", ["50"])[0])

        traces = self._read_traces(limit=limit)
        self._send_json(200, {"traces": traces, "count": len(traces)})

    # ── Data Access ──────────────────────────────────────────────────

    def _query_audit(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        errors_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Query the SQLite audit log with filters."""
        try:
            if not AUDIT_DB_PATH.exists():
                return []

            conn = sqlite3.connect(str(AUDIT_DB_PATH))
            conn.row_factory = sqlite3.Row

            where_clauses: List[str] = []
            params: List[Any] = []

            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)
            if tool_name:
                where_clauses.append("tool_name = ?")
                params.append(tool_name)
            if errors_only:
                where_clauses.append("allowed = 0")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            rows = conn.execute(
                f"SELECT * FROM audit_log WHERE {where_sql} "
                f"ORDER BY id DESC LIMIT ?",
                params + [limit],
            ).fetchall()

            conn.close()
            return [dict(r) for r in rows]

        except (sqlite3.Error, OSError) as exc:
            logger.debug("Audit query failed: %s", exc)
            return []

    def _read_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Read recent traces from the traces JSONL file."""
        traces_path = XAVANI_HOME / "logs" / "traces.jsonl"
        try:
            if not traces_path.exists():
                return []

            traces: List[Dict[str, Any]] = []
            with open(traces_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        traces.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            traces.reverse()
            return traces[:limit]

        except OSError as exc:
            logger.debug("Failed to read traces: %s", exc)
            return []

    # ── Response Helpers ─────────────────────────────────────────────

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        """Send a JSON response."""
        body = json.dumps(data, default=str, indent=2)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet logging — suppress default HTTP server logs."""
        logger.debug("Dashboard HTTP: %s", format % args)


# ---------------------------------------------------------------------------
# DashboardServer
# ---------------------------------------------------------------------------


class DashboardServer:
    """Lightweight web dashboard for real-time agent observability.

    Serves a single HTML page on ``localhost:8081`` with live metrics,
    audit log viewer, and trace inspection.

    Usage::
        ds = DashboardServer(metrics_collector=mc)
        ds.start()  # runs in background thread
        # ... agent runs ...
        ds.stop()
    """

    def __init__(
        self,
        host: str = DASHBOARD_HOST,
        port: int = DASHBOARD_PORT,
        metrics_collector: Optional[MetricsCollector] = None,
    ) -> None:
        self._host = host
        self._port = port
        self._metrics_collector = metrics_collector
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> bool:
        """Start the dashboard server in a background thread.

        Returns:
            True if started successfully, False if the port is in use.
        """
        if self._running:
            logger.info("Dashboard already running on %s:%d", self._host, self._port)
            return True

        try:
            # Create server with our handler
            self._server = HTTPServer(
                (self._host, self._port),
                DashboardHTTPHandler,
            )
            # Attach shared references
            DashboardHTTPHandler.metrics_collector = self._metrics_collector

            self._running = True
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="dashboard-server",
            )
            self._thread.start()
            logger.info(
                "Dashboard started on http://%s:%d",
                self._host,
                self._port,
            )
            return True

        except OSError as exc:
            if "Address already in use" in str(exc):
                logger.warning(
                    "Dashboard port %d is already in use. "
                    "Is another dashboard already running?",
                    self._port,
                )
                return False
            logger.error("Failed to start dashboard: %s", exc)
            return False

    def stop(self) -> None:
        """Stop the dashboard server gracefully."""
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("Dashboard stopped")

    @property
    def is_running(self) -> bool:
        """Check if the dashboard server is running."""
        return self._running

    @property
    def url(self) -> str:
        """Return the dashboard URL."""
        return f"http://{self._host}:{self._port}"


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Xavani Agent Dashboard</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --success: #3fb950;
    --warning: #d29922;
    --danger: #f85149;
    --info: #79c0ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 20px;
  }
  h1 { font-size: 1.5rem; margin-bottom: 16px; }
  h1 small { font-size: 0.8rem; color: var(--text-muted); font-weight: normal; }
  h2 { font-size: 1rem; margin-bottom: 8px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
  h3 { font-size: 0.85rem; margin-bottom: 4px; color: var(--text-muted); }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 20px;
  }
  .header .info { font-size: 0.8rem; color: var(--text-muted); }
  .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
  .status-dot.ok { background: var(--success); }
  .status-dot.warn { background: var(--warning); }
  .status-dot.err { background: var(--danger); }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px; margin-bottom: 20px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px;
  }
  .card h2 { margin-bottom: 12px; }
  .stat-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.85rem; }
  .stat-row .label { color: var(--text-muted); }
  .stat-row .value { font-weight: 600; }
  .stat-row .value.success { color: var(--success); }
  .stat-row .value.danger { color: var(--danger); }
  .stat-row .value.warning { color: var(--warning); }
  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }
  .stat-card { text-align: center; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 6px; }
  .stat-card .num { font-size: 1.5rem; font-weight: 700; }
  .stat-card .lbl { font-size: 0.7rem; color: var(--text-muted); margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
  th { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border); color: var(--text-muted); font-weight: 500; }
  td { padding: 6px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: rgba(88,166,255,0.05); }
  .badge {
    display: inline-block; padding: 1px 6px; border-radius: 12px;
    font-size: 0.7rem; font-weight: 500;
  }
  .badge.ok { background: rgba(63,185,80,0.15); color: var(--success); }
  .badge.err { background: rgba(248,81,73,0.15); color: var(--danger); }
  .badge.info { background: rgba(121,192,255,0.15); color: var(--info); }
  .filters { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .filters input, .filters select {
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    padding: 6px 10px; border-radius: 6px; font-size: 0.8rem;
  }
  .filters button {
    background: var(--accent); color: #fff; border: none;
    padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
  }
  .filters button:hover { opacity: 0.85; }
  .chart-container { width: 100%; height: 200px; margin-top: 8px; position: relative; }
  .chart-bar { display: flex; align-items: flex-end; gap: 4px; height: 160px; padding-top: 8px; }
  .chart-bar .bar {
    flex: 1; background: var(--accent); border-radius: 3px 3px 0 0;
    min-height: 2px; position: relative; transition: height 0.3s;
  }
  .chart-bar .bar:hover { opacity: 0.8; }
  .chart-labels { display: flex; gap: 4px; font-size: 0.6rem; color: var(--text-muted); }
  .chart-labels span { flex: 1; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tabs { display: flex; gap: 4px; margin-bottom: 12px; }
  .tab {
    padding: 6px 14px; border-radius: 6px 6px 0 0; cursor: pointer;
    background: var(--bg); border: 1px solid var(--border); border-bottom: none;
    font-size: 0.8rem; color: var(--text-muted);
  }
  .tab.active { background: var(--surface); color: var(--text); border-color: var(--border); }
  .tab:hover { background: var(--surface); }
  .panel { display: none; }
  .panel.active { display: block; }
  .empty-state { text-align: center; padding: 24px; color: var(--text-muted); font-size: 0.85rem; }
  .error-list { max-height: 300px; overflow-y: auto; }
  @media (max-width: 640px) {
    .grid { grid-template-columns: 1fr; }
    .stat-grid { grid-template-columns: 1fr 1fr; }
  }
</style>
</head>
<body>
<div class="header">
  <h1>&#x1F50D; Xavani Dashboard <small>v0.1</small></h1>
  <div class="info">
    <span class="status-dot ok" id="statusDot"></span>
    <span id="statusText">Live</span>
    &middot;
    <span id="refreshInfo">updating in 5s</span>
    &middot;
    <a href="/api/metrics" style="color:var(--text-muted);">API</a>
  </div>
</div>

<div class="grid" id="summaryCards">
  <div class="card"><h2>Sessions</h2><div class="stat-grid">
    <div class="stat-card"><div class="num" id="activeSessions">0</div><div class="lbl">Active</div></div>
    <div class="stat-card"><div class="num" id="totalCalls">0</div><div class="lbl">Total Calls</div></div>
  </div></div>
  <div class="card"><h2>Latency</h2><div class="stat-grid">
    <div class="stat-card"><div class="num" id="avgLatency">0</div><div class="lbl">Avg (ms)</div></div>
    <div class="stat-card"><div class="num" id="p95Latency">0</div><div class="lbl">P95 (ms)</div></div>
  </div></div>
  <div class="card"><h2>Errors</h2><div class="stat-grid">
    <div class="stat-card"><div class="num" id="totalErrors">0</div><div class="lbl">Total</div></div>
    <div class="stat-card"><div class="num" id="errorRate">0%</div><div class="lbl">Rate</div></div>
  </div></div>
  <div class="card"><h2>Tokens</h2><div class="stat-grid">
    <div class="stat-card"><div class="num" id="inputTokens">0</div><div class="lbl">Input</div></div>
    <div class="stat-card"><div class="num" id="outputTokens">0</div><div class="lbl">Output</div></div>
  </div></div>
</div>

<div class="grid">
  <div class="card" style="grid-column: span 2;">
    <h2>Top Tools</h2>
    <div id="topToolsChart" class="chart-container">
      <div class="chart-bar" id="toolChart"></div>
      <div class="chart-labels" id="toolLabels"></div>
    </div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" data-tab="tools" onclick="switchTab('tools')">Tool Calls</div>
  <div class="tab" data-tab="audit" onclick="switchTab('audit')">Audit Log</div>
  <div class="tab" data-tab="traces" onclick="switchTab('traces')">Traces</div>
  <div class="tab" data-tab="errors" onclick="switchTab('errors')">Errors</div>
</div>

<div class="panel active" id="panel-tools">
  <div class="card">
    <h2>Recent Tool Calls</h2>
    <table><thead><tr><th>Tool</th><th>Count</th><th>Avg (ms)</th><th>Errors</th></tr></thead>
    <tbody id="toolTableBody"></tbody></table>
  </div>
</div>

<div class="panel" id="panel-audit">
  <div class="card">
    <h2>Audit Log</h2>
    <div class="filters">
      <input type="text" id="auditUser" placeholder="Filter by user..." oninput="loadAudit()">
      <input type="text" id="auditTool" placeholder="Filter by tool..." oninput="loadAudit()">
      <label style="font-size:0.8rem;color:var(--text-muted);display:flex;align-items:center;gap:4px;">
        <input type="checkbox" id="auditErrorsOnly" onchange="loadAudit()"> Errors only
      </label>
    </div>
    <table><thead><tr><th>Time</th><th>User</th><th>Tool</th><th>Server</th><th>Duration</th><th>Status</th></tr></thead>
    <tbody id="auditTableBody"></tbody></table>
  </div>
</div>

<div class="panel" id="panel-traces">
  <div class="card">
    <h2>Recent Traces</h2>
    <table><thead><tr><th>Name</th><th>Kind</th><th>Duration</th><th>Status</th><th>Trace ID</th></tr></thead>
    <tbody id="tracesTableBody"></tbody></table>
  </div>
</div>

<div class="panel" id="panel-errors">
  <div class="card">
    <h2>Error Details</h2>
    <div id="errorList" class="error-list"><div class="empty-state">No errors recorded</div></div>
  </div>
</div>

<script>
let refreshInterval = null;
const REFRESH_MS = 5000;

function $(id) { return document.getElementById(id); }

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${name}"]`).classList.add('active');
  $(`panel-${name}`).classList.add('active');
}

// ── Formatting ──

function fmtMs(ms) { return ms != null ? ms.toFixed(1) : '-'; }

function fmtTime(iso) {
  if (!iso) return '-';
  try { return new Date(iso).toLocaleTimeString(); } catch(e) { return iso; }
}

function statBar(val, max, color) {
  const pct = max > 0 ? (val / max * 100) : 0;
  return `<div class="bar" style="height:${pct}%;background:${color||'var(--accent)'}" title="${val}"></div>`;
}

// ── Data Loading ──

async function fetchJSON(url) {
  try { const r = await fetch(url); return await r.json(); }
  catch(e) { console.error('fetch failed', url, e); return null; }
}

async function loadMetrics() {
  const data = await fetchJSON('/api/metrics');
  if (!data) return;

  // Summary cards
  $('activeSessions').textContent = data.active_sessions || 0;
  $('totalCalls').textContent = (data.total_tool_calls || 0) + (data.total_llm_calls || 0);
  $('totalErrors').textContent = data.total_errors || 0;
  $('errorRate').textContent = (data.overall_error_rate || 0) + '%';

  // Token usage
  let inTok = 0, outTok = 0;
  if (data.token_usage) {
    Object.values(data.token_usage).forEach(u => {
      inTok += u.input_tokens || 0;
      outTok += u.output_tokens || 0;
    });
  }
  $('inputTokens').textContent = inTok.toLocaleString();
  $('outputTokens').textContent = outTok.toLocaleString();

  // Latency averages
  let totalAvg = 0, totalP95 = 0, count = 0;
  if (data.tools) {
    Object.values(data.tools).forEach(t => {
      if (t.avg_ms != null) { totalAvg += t.avg_ms * t.call_count; count += t.call_count; }
      if (t.p95_ms != null && t.p95_ms > totalP95) totalP95 = t.p95_ms;
    });
  }
  if (data.llms) {
    Object.values(data.llms).forEach(l => {
      if (l.avg_ms != null) { totalAvg += l.avg_ms * l.call_count; count += l.call_count; }
      if (l.p95_ms != null && l.p95_ms > totalP95) totalP95 = l.p95_ms;
    });
  }
  $('avgLatency').textContent = count > 0 ? fmtMs(totalAvg / count) : '0';
  $('p95Latency').textContent = fmtMs(totalP95);

  // Status dot
  const dot = $('statusDot');
  if (data.overall_error_rate > 10) { dot.className = 'status-dot err'; }
  else if (data.overall_error_rate > 5) { dot.className = 'status-dot warn'; }
  else { dot.className = 'status-dot ok'; }

  // Top tools chart
  renderToolChart(data);

  // Tool calls table
  renderToolTable(data);

  // Error list
  renderErrors(data);
}

function renderToolChart(data) {
  const chart = $('toolChart');
  const labels = $('toolLabels');
  chart.innerHTML = '';
  labels.innerHTML = '';

  if (!data.tools) return;
  const tools = Object.entries(data.tools)
    .sort((a, b) => (b[1].call_count || 0) - (a[1].call_count || 0))
    .slice(0, 10);
  if (tools.length === 0) return;

  const maxCall = Math.max(...tools.map(t => t[1].call_count));
  tools.forEach(([name, stats]) => {
    chart.innerHTML += statBar(stats.call_count, maxCall, 'var(--accent)');
    labels.innerHTML += `<span>${name}</span>`;
  });
}

function renderToolTable(data) {
  const tbody = $('toolTableBody');
  tbody.innerHTML = '';
  if (!data.tools) { tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state">No tool calls yet</div></td></tr>'; return; }

  const sorted = Object.entries(data.tools).sort((a, b) => (b[1].call_count||0) - (a[1].call_count||0));
  sorted.forEach(([name, stats]) => {
    const errCount = (data.error_rates && data.error_rates[name]) ? data.error_rates[name].total || 0 : 0;
    const errBadge = errCount > 0 ? `<span class="badge err">${errCount}</span>` : '<span class="badge ok">0</span>';
    tbody.innerHTML += `<tr><td>${name}</td><td>${stats.call_count}</td><td>${fmtMs(stats.avg_ms)}</td><td>${errBadge}</td></tr>`;
  });
}

function renderErrors(data) {
  const el = $('errorList');
  if (!data.error_rates || Object.keys(data.error_rates).length === 0) {
    el.innerHTML = '<div class="empty-state">No errors recorded</div>';
    return;
  }
  let html = '<table><thead><tr><th>Tool</th><th>Error Type</th><th>Count</th><th>Rate</th></tr></thead><tbody>';
  Object.entries(data.error_rates).forEach(([tool, info]) => {
    const errTypes = Object.entries(info).filter(([k]) => k !== 'total' && k !== 'error_rate_pct');
    errTypes.forEach(([etype, count]) => {
      html += `<tr><td>${tool}</td><td><span class="badge err">${etype}</span></td><td>${count}</td><td>${info.error_rate_pct || 0}%</td></tr>`;
    });
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

async function loadAudit() {
  const tbody = $('auditTableBody');
  const user = $('auditUser').value;
  const tool = $('auditTool').value;
  const errorsOnly = $('auditErrorsOnly').checked ? 1 : 0;
  let url = `/api/audit?limit=50&user=${encodeURIComponent(user)}&tool=${encodeURIComponent(tool)}&errors=${errorsOnly}`;
  const data = await fetchJSON(url);
  if (!data || !data.entries) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state">No audit entries</div></td></tr>'; return; }
  if (data.entries.length === 0) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state">No matching entries</div></td></tr>'; return; }

  tbody.innerHTML = '';
  data.entries.forEach(e => {
    const status = e.allowed ? '<span class="badge ok">Allowed</span>' : '<span class="badge err">Denied</span>';
    tbody.innerHTML += `<tr>
      <td>${fmtTime(e.timestamp)}</td>
      <td>${e.user_id || '-'}</td>
      <td>${e.tool_name || '-'}</td>
      <td>${e.server_name || '-'}</td>
      <td>${e.duration_ms != null ? fmtMs(e.duration_ms) + 'ms' : '-'}</td>
      <td>${status}</td>
    </tr>`;
  });
}

async function loadTraces() {
  const tbody = $('tracesTableBody');
  const data = await fetchJSON('/api/traces?limit=50');
  if (!data || !data.traces) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state">No traces yet</div></td></tr>'; return; }
  if (data.traces.length === 0) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state">No traces yet</div></td></tr>'; return; }

  tbody.innerHTML = '';
  data.traces.forEach(t => {
    const statusClass = t.status === 'OK' ? 'ok' : 'err';
    const traceShort = t.trace_id ? t.trace_id.substring(0, 8) + '...' : '-';
    tbody.innerHTML += `<tr>
      <td>${t.name || '-'}</td>
      <td><span class="badge info">${t.span_kind || '-'}</span></td>
      <td>${t.duration_ms != null ? fmtMs(t.duration_ms) + 'ms' : '-'}</td>
      <td><span class="badge ${statusClass}">${t.status || '-'}</span></td>
      <td style="font-family:monospace;font-size:0.7rem;">${traceShort}</td>
    </tr>`;
  });
}

// ── Refresh Loop ──

async function refresh() {
  await loadMetrics();
  loadAudit();
  loadTraces();
}

function startRefresh() {
  refresh();
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(refresh, REFRESH_MS);
}

startRefresh();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


def run_dashboard(
    host: str = DASHBOARD_HOST,
    port: int = DASHBOARD_PORT,
) -> DashboardServer:
    """Run the dashboard server independently (for CLI use)."""
    mc = MetricsCollector()
    ds = DashboardServer(host=host, port=port, metrics_collector=mc)
    ds.start()
    print(f"\n  Dashboard: {ds.url}")
    print("  Press Ctrl+C to stop.\n")
    try:
        while ds.is_running:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    ds.stop()
    return ds


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dashboard()
