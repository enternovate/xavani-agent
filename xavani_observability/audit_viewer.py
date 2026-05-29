# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""CLI audit viewer — Phase 5.

AuditViewer provides CLI inspection of the gateway audit log with
Rich tables, filtering, and export capabilities.

Reads from the SQLite audit database at ``~/.xavani/data/oag_audit.db``.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

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
AUDIT_DB_PATH = XAVANI_HOME / "data" / "oag_audit.db"


# ---------------------------------------------------------------------------
# AuditViewer
# ---------------------------------------------------------------------------


class AuditViewer:
    """CLI audit log inspector.

    Reads from the gateway's SQLite audit database and displays entries
    in formatted Rich tables. Supports filtering by user, tool, and
    error status, plus JSON export.

    Usage::
        av = AuditViewer()
        av.show_recent(limit=20)
        av.show_by_user("alice")
        av.show_by_tool("read_file")
        av.show_errors()
        av.export(format="json")
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or AUDIT_DB_PATH
        self._console = Console()

    # ── Public Display Methods ───────────────────────────────────────

    def show_recent(self, limit: int = 20) -> None:
        """Show the most recent audit log entries.

        Args:
            limit: Maximum number of entries to display.
        """
        records = self._query(limit=limit)
        if not records:
            self._console.print("[yellow]No audit entries found.[/yellow]")
            return
        self._print_table(records, title=f"Recent Audit Entries (last {len(records)})")

    def show_by_user(self, user: str, limit: int = 20) -> None:
        """Show audit entries filtered by user.

        Args:
            user: User ID to filter by.
            limit: Maximum number of entries to display.
        """
        records = self._query(user_id=user, limit=limit)
        if not records:
            self._console.print(f"[yellow]No audit entries for user '{user}'.[/yellow]")
            return
        self._print_table(records, title=f"Audit Entries for User: {user} ({len(records)})")

    def show_by_tool(self, tool: str, limit: int = 20) -> None:
        """Show audit entries filtered by tool name.

        Args:
            tool: Tool name to filter by.
            limit: Maximum number of entries to display.
        """
        records = self._query(tool_name=tool, limit=limit)
        if not records:
            self._console.print(f"[yellow]No audit entries for tool '{tool}'.[/yellow]")
            return
        self._print_table(records, title=f"Audit Entries for Tool: {tool} ({len(records)})")

    def show_errors(self, limit: int = 20) -> None:
        """Show only failed or denied requests.

        Args:
            limit: Maximum number of entries to display.
        """
        records = self._query(errors_only=True, limit=limit)
        if not records:
            self._console.print("[green]No denied/failed audit entries found.[/green]")
            return
        total_denied = self._count_errors()
        self._print_table(
            records,
            title=f"Denied/Failed Requests ({len(records)} shown, {total_denied} total)",
            style="error",
        )

    # ── Export ───────────────────────────────────────────────────────

    def export(self, format: str = "json") -> str:
        """Export all audit data to a file.

        Args:
            format: Export format (currently only ``json`` is supported).

        Returns:
            Path to the exported file as a string.
        """
        records = self._query(limit=10000)
        export_dir = XAVANI_HOME / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if format == "json":
            export_path = export_dir / f"audit_export_{timestamp}.json"
            data = {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_entries": len(records),
                "entries": records,
            }
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self._console.print(f"[green]Exported {len(records)} entries to {export_path}[/green]")
            return str(export_path)
        else:
            self._console.print(f"[red]Unsupported export format: {format} (use 'json')[/red]")
            return ""

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Print and return aggregate audit statistics."""
        stats = self._get_stats()
        self._console.print("\n[bold]Audit Statistics[/bold]")
        self._console.print(f"  Total requests:  {stats['total_requests']}")
        self._console.print(f"  Denied requests: {stats['denied_requests']}")
        self._console.print(f"  Unique users:    {stats['unique_users']}")
        self._console.print(f"  Unique tools:    {stats['unique_tools']}")
        self._console.print(f"  Database path:   {self._db_path}")
        return stats

    # ── Internal Query Methods ───────────────────────────────────────

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Get a connection to the audit database."""
        if not self._db_path.exists():
            self._console.print(f"[yellow]Audit database not found at {self._db_path}[/yellow]")
            self._console.print("[yellow]Start the gateway to create the database.[/yellow]")
            return None
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as exc:
            self._console.print(f"[red]Failed to open audit database: {exc}[/red]")
            return None

    def _query(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        errors_only: bool = False,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query the audit database with optional filters."""
        conn = self._get_connection()
        if conn is None:
            return []

        try:
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
                f"ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

            return [dict(r) for r in rows]

        except sqlite3.Error as exc:
            logger.debug("Audit query failed: %s", exc)
            return []
        finally:
            conn.close()

    def _count_errors(self) -> int:
        """Count total denied/failed entries."""
        conn = self._get_connection()
        if conn is None:
            return 0
        try:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM audit_log WHERE allowed = 0"
            ).fetchone()
            return row["c"] if row else 0
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def _get_stats(self) -> Dict[str, Any]:
        """Get aggregate audit statistics."""
        conn = self._get_connection()
        if conn is None:
            return {"total_requests": 0, "denied_requests": 0, "unique_users": 0, "unique_tools": 0}

        try:
            total = conn.execute(
                "SELECT COUNT(*) as c FROM audit_log"
            ).fetchone()["c"]
            denied = conn.execute(
                "SELECT COUNT(*) as c FROM audit_log WHERE allowed = 0"
            ).fetchone()["c"]
            unique_users = conn.execute(
                "SELECT COUNT(DISTINCT user_id) as c FROM audit_log"
            ).fetchone()["c"]
            unique_tools = conn.execute(
                "SELECT COUNT(DISTINCT tool_name) as c FROM audit_log"
            ).fetchone()["c"]
            return {
                "total_requests": total,
                "denied_requests": denied,
                "unique_users": unique_users,
                "unique_tools": unique_tools,
            }
        except sqlite3.Error:
            return {"total_requests": 0, "denied_requests": 0, "unique_users": 0, "unique_tools": 0}
        finally:
            conn.close()

    # ── Rich Table Rendering ─────────────────────────────────────────

    def _print_table(
        self,
        records: List[Dict[str, Any]],
        title: str = "Audit Entries",
        style: str = "info",
    ) -> None:
        """Print audit entries in a formatted Rich table.

        Args:
            records: List of audit entry dicts.
            title: Table title.
            style: Row style hint ("error" or "info").
        """
        if not records:
            self._console.print("[yellow]No records to display.[/yellow]")
            return

        table = Table(
            title=title,
            title_style="bold",
            header_style="bold cyan",
            border_style="blue",
            show_lines=False,
        )

        table.add_column("ID", style="dim", width=6)
        table.add_column("Timestamp", width=22)
        table.add_column("User", width=16)
        table.add_column("Tool", width=20)
        table.add_column("Server", width=16)
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Status", width=10)
        table.add_column("Reason", width=20)

        for rec in records:
            rec_id = str(rec.get("id", ""))
            timestamp = self._format_timestamp(rec.get("timestamp", ""))
            user_id = rec.get("user_id", "") or ""
            tool_name = rec.get("tool_name", "") or ""
            server_name = rec.get("server_name", "") or ""
            duration = f"{rec.get('duration_ms', 0):.1f}ms" if rec.get("duration_ms") else "-"

            allowed = rec.get("allowed", 0)
            if allowed:
                status_text = Text("ALLOWED", style="green")
            else:
                status_text = Text("DENIED", style="red bold")

            reason = rec.get("denied_reason", "") or ""

            row_style = "red" if not allowed else ""
            table.add_row(
                rec_id,
                timestamp,
                user_id,
                tool_name,
                server_name,
                duration,
                status_text,
                reason,
                style=row_style,
            )

        self._console.print("")
        self._console.print(table)
        self._console.print("")

    @staticmethod
    def _format_timestamp(iso_timestamp: str) -> str:
        """Format an ISO timestamp for display.

        Args:
            iso_timestamp: ISO 8601 timestamp string.

        Returns:
            Formatted timestamp string like ``2026-05-19 14:30:00``.
        """
        if not iso_timestamp:
            return "-"
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return iso_timestamp[:19] if len(iso_timestamp) >= 19 else iso_timestamp
