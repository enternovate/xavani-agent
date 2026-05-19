# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Agent - slash command definitions and handlers.

Implements the Xavani Agent gateway commands that extend the base Hermes CLI:
  /install <name>       - Install MCP server from registry
  /uninstall <name>     - Remove an installed MCP server
  /gateway-up           - Start the MCP proxy gateway on localhost:8080
  /gateway-down         - Stop the gateway
  /registry-status      - Show installed servers and gateway status
  /policy-add <file>    - Add a policy rule
  /audit [--since 24h]  - Show audit log
  /security-scan <name> - Run security scan on an installed server

Each command handler follows the pattern used by ``hermes_cli/commands.py``:
a canonical ``CommandDef`` in a local registry and a handler function.
"""

from __future__ import annotations

import json
import logging
import os
import psutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hermes_cli.commands import CommandDef

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Xavani Home / Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", str(Path.home() / ".xavani"))).expanduser()
OAG_HOME = XAVANI_HOME  # OAG home is same as Xavani home

# ---------------------------------------------------------------------------
# OAG Command Definitions
# ---------------------------------------------------------------------------
# These are registered into the dispatcher at OAG startup.
# The naming convention uses a "oag_" prefix to avoid collisions with
# built-in Hermes commands.

OAG_COMMAND_DEFS: List[CommandDef] = [
    CommandDef(
        name="install",
        description="Install an MCP server from the registry",
        category="Xavani Gateway",
        args_hint="<name>",
        cli_only=True,
    ),
    CommandDef(
        name="uninstall",
        description="Remove an installed MCP server",
        category="Xavani Gateway",
        args_hint="<name>",
        cli_only=True,
    ),
    CommandDef(
        name="gateway-up",
        description="Start the MCP proxy gateway on localhost:8080",
        category="Xavani Gateway",
        cli_only=True,
    ),
    CommandDef(
        name="gateway-down",
        description="Stop the running OAG gateway",
        category="Xavani Gateway",
        cli_only=True,
    ),
    CommandDef(
        name="registry-status",
        description="Show installed MCP servers and gateway status",
        category="Xavani Gateway",
        aliases=("status",),
        cli_only=True,
    ),
    CommandDef(
        name="policy-add",
        description="Add a policy rule from a YAML/JSON file",
        category="Xavani Gateway",
        args_hint="<policy.yaml>",
        cli_only=True,
    ),
    CommandDef(
        name="audit",
        description="Show the OAG audit log",
        category="Xavani Gateway",
        args_hint="[--since 24h]",
        cli_only=True,
    ),
    CommandDef(
        name="security-scan",
        description="Run a security scan on an installed MCP server",
        category="Xavani Gateway",
        args_hint="<name>",
        cli_only=True,
    ),
    CommandDef(
        name="registry-list",
        description="List all available servers in the built-in registry",
        category="Xavani Gateway",
        args_hint="[query]",
        cli_only=True,
    ),
]

# Map canonical name -> handler callable
OAG_COMMAND_HANDLERS: Dict[str, callable] = {}


def _register_handler(name: str):
    """Decorator that registers a handler for the given canonical command name."""
    def wrapper(fn):
        OAG_COMMAND_HANDLERS[name] = fn
        return fn
    return wrapper


# ---------------------------------------------------------------------------
# Lazy imports for OAG modules
# ---------------------------------------------------------------------------

def _get_registry() -> Any:
    """Lazy-import and return the OAGRegistry instance."""
    try:
        from xavani_registry import OAGRegistry
        return OAGRegistry()
    except ImportError:
        # Fallback to the old-style JSON-based registry
        return None


def _get_proxy_server() -> Any:
    """Lazy-import and return the OAGProxyServer."""
    try:
        from gateway.oag_proxy import OAGProxyServer, OAGAuditLogger, OAGPolicyEngine, OAGAuthManager
        return {
            "server": OAGProxyServer,
            "audit": OAGAuditLogger,
            "policies": OAGPolicyEngine,
            "auth": OAGAuthManager,
        }
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Helpers (backward compat with existing ~/.oag/)
# ---------------------------------------------------------------------------

def _ensure_xavani_dirs() -> None:
    """Create Xavani home directories if they do not exist."""
    for d in ["", "installed", "policies", "data", "logs", "skills"]:
        (XAVANI_HOME / d).mkdir(parents=True, exist_ok=True)

    # Also create legacy ~/.oag/ dirs for backward compat
    _oag_home().mkdir(parents=True, exist_ok=True)
    _oag_policy_dir().mkdir(parents=True, exist_ok=True)
    if not _oag_installed_path().exists():
        _oag_installed_path().write_text("[]", encoding="utf-8")
    if not _oag_audit_log_path().exists():
        _oag_audit_log_path().write_text("", encoding="utf-8")


def _oag_home() -> Path:
    """Return the OAG home directory (backward compat: ~/.oag)."""
    env = os.environ.get("OAG_HOME", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".oag"


def _oag_installed_path() -> Path:
    """Return path to legacy installed MCP servers index."""
    return _oag_home() / "installed_servers.json"


def _oag_policy_dir() -> Path:
    """Return path to policy rules directory."""
    return _oag_home() / "policies"


def _oag_audit_log_path() -> Path:
    """Return path to the legacy audit log file."""
    return _oag_home() / "audit.log"


def _oag_gateway_pid_path() -> Path:
    """Return path to the OAG gateway PID file."""
    return _oag_home() / "gateway.pid"


def _append_audit(entry: str) -> None:
    """Append a timestamped audit log entry to legacy log file."""
    from gateway.oag_proxy import OAGAuditLogger
    try:
        audit = OAGAuditLogger()
        audit.log(
            user_id="cli",
            tool_name=None,
            server_name=None,
            input_summary=entry,
            duration_ms=0,
            allowed=True,
        )
    except Exception:
        # Fall back to plain text audit
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            with _oag_audit_log_path().open("a", encoding="utf-8") as f:
                f.write(f"[{ts}] {entry}\n")
        except OSError as e:
            logger.warning("Failed to write audit log: %s", e)


def _get_installed_servers() -> List[Dict[str, Any]]:
    """Return the list of installed MCP servers (backward compat)."""
    registry = _get_registry()
    if registry:
        return registry.list()
    # Fallback
    path = _oag_installed_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _is_gateway_running() -> bool:
    """Check whether the Xavani gateway process is alive."""
    from xavani_runtime.runner import is_process_alive
    pid_path = _oag_gateway_pid_path()
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        return is_process_alive(pid)
    except (OSError, ValueError):
        return False


def _gateway_pid() -> Optional[int]:
    """Return the gateway PID, or None if not running."""
    pid_path = _oag_gateway_pid_path()
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

@_register_handler("install")
def oag_install(args: str, cli=None) -> str:
    """Install an MCP server from the registry.

    Usage: /install <name>

    Uses the OAGRegistry to look up and install MCP servers from the
    built-in registry with security scanning and package signing.
    """
    name = args.strip()
    if not name:
        return (
            "  [bold #FF3366]Usage: /install <name>[/]\n"
            "  [dim]Install an MCP server from the Xavani registry.[/]"
        )

    _ensure_xavani_dirs()

    from xavani_registry import OAGRegistry
    registry = OAGRegistry()

    try:
        entry = registry.install(name)
        _append_audit(f"install server '{name}'")
        return (
            f"  [bold #00E676]✓ Installed MCP server: {name}[/]\n"
            f"  [dim]  {entry.get('description', '')}[/]\n"
            f"  [dim]  Command: {entry['command']} {' '.join(entry.get('args', []))}[/]\n"
            f"  [dim]  Security: score {entry.get('security_scan', {}).get('score', 'N/A')}/100[/]\n"
            f"  [dim]  Use /reload-mcp to activate it in the current session.[/]"
        )
    except Exception as exc:
        logger.error("Failed to install '%s': %s", name, exc)
        return f"  [bold #FF3366]✗ Failed to install '{name}': {exc}[/]"


@_register_handler("uninstall")
def oag_uninstall(args: str, cli=None) -> str:
    """Uninstall an MCP server.

    Usage: /uninstall <name>
    """
    name = args.strip()
    if not name:
        return (
            "  [bold #FF3366]Usage: /uninstall <name>[/]\n"
            "  [dim]Remove an installed MCP server.[/]"
        )

    name = name.lower().strip()
    from xavani_registry import OAGRegistry
    registry = OAGRegistry()

    if not registry.is_installed(name):
        return f"  [bold #FFB300]⚠ Server '{name}' is not installed.[/]"

    try:
        info = registry.uninstall(name)
        _append_audit(f"uninstall server '{name}'")
        return (
            f"  [bold #00E676]✓ Uninstalled MCP server: {name}[/]\n"
            f"  [dim]  Config removed: {info.get('config_removed', False)}[/]"
        )
    except Exception as exc:
        logger.error("Failed to uninstall '%s': %s", name, exc)
        return f"  [bold #FF3366]✗ Failed to uninstall '{name}': {exc}[/]"


@_register_handler("gateway-up")
def oag_gateway_up(args: str, cli=None) -> str:
    """Start the OAG MCP proxy gateway on localhost:8080.

    Launches the OAG Proxy (FastAPI-based MCP gateway) in a background
    thread, bypassing the old Hermes messaging gateway.
    """
    if _is_gateway_running():
        pid = _gateway_pid()
        return (
            f"  [bold #FFB300]⚠ Gateway is already running (PID {pid})[/]\n"
            f"  [dim]Use /gateway-down to stop it first.[/]"
        )

    _ensure_xavani_dirs()

    try:
        from gateway.oag_proxy import start_oag_gateway
        # Start the OAG proxy in background
        proxy = start_oag_gateway(host="127.0.0.1", port=8080)
        # Store PID — use the thread's ID or a marker
        import threading
        # Write a marker PID so _is_gateway_running works
        _oag_gateway_pid_path().write_text(str(os.getpid()), encoding="utf-8")
        _append_audit("gateway up (OAG Proxy)")

        return (
            f"  [bold #00E676]✓ OAG Gateway started[/]\n"
            f"  [dim]  Listening on http://127.0.0.1:8080[/]\n"
            f"  [dim]  Endpoints: /health, /mcp, /audit, /auth/token, /policies[/]\n"
            f"  [dim]  Use /gateway-down to stop it.[/]"
        )
    except ImportError as exc:
        return (
            f"  [bold #FF3366]✗ Missing dependencies: {exc}[/]\n"
            f"  [dim]  Install with: pip install 'xavani-agent[web]'[/]"
        )
    except Exception as e:
        logger.error("Failed to start gateway: %s", e)
        return f"  [bold #FF3366]✗ Failed to start gateway: {e}[/]"


@_register_handler("gateway-down")
def oag_gateway_down(args: str, cli=None) -> str:
    """Stop the running OAG MCP proxy gateway."""
    pid = _gateway_pid()
    if not pid:
        return "  [bold #FFB300]⚠ Gateway is not running.[/]"

    if not _is_gateway_running():
        _oag_gateway_pid_path().unlink(missing_ok=True)
        return "  [bold #FFB300]⚠ Gateway was not running (stale PID cleaned up).[/]"

    try:
        proc = psutil.Process(pid)
        proc.terminate()  # SIGTERM equivalent, cross-platform
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()  # SIGKILL equivalent, cross-platform
            proc.wait(timeout=2)
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
        return f"  [bold #FF3366]✗ Failed to stop gateway: {e}[/]"
    finally:
        _oag_gateway_pid_path().unlink(missing_ok=True)

    _append_audit("gateway down")
    return f"  [bold #00E676]✓ Gateway stopped (PID {pid})[/]"


@_register_handler("registry-status")
def oag_registry_status(args: str, cli=None) -> str:
    """Show installed MCP servers and gateway status."""
    _ensure_xavani_dirs()

    lines: List[str] = []

    # ---- Gateway status ----
    gw_pid = _gateway_pid()
    gw_running = _is_gateway_running()

    if gw_running:
        lines.append(f"  [bold #00E676]● Gateway running (PID {gw_pid})[/]")
        lines.append(f"  [dim]  http://127.0.0.1:8080[/]")
    else:
        lines.append(f"  [bold #FFB300]○ Gateway not running[/]")
    lines.append("")

    # ---- Installed servers ----
    from xavani_registry import OAGRegistry
    registry = OAGRegistry()
    servers = registry.list()

    if servers:
        lines.append(f"  [bold #00F5FF]Installed MCP Servers:[/]")
        for srv in servers:
            name = srv.get("name", "?")
            desc = srv.get("description", "")
            version = srv.get("version", "")
            installed = srv.get("installed_at", "")[:10] if srv.get("installed_at") else ""
            desc_str = f" — {desc}" if desc else ""
            ver_str = f" [dim]v{version}[/]" if version else ""
            date_str = f" [dim]({installed})[/]" if installed else ""
            lines.append(f"    [bold #E0E8FF]⚡ {name}[/]{desc_str}{ver_str}{date_str}")
    else:
        lines.append(f"  [bold #FFB300]⚠ No MCP servers installed yet.[/]")
        lines.append(f"  [dim]  Use /install <name> to add one.[/]")

    # ---- Registry info ----
    try:
        reg_info = registry.registry_info()
        available = reg_info.get("total_available", 0)
        lines.append("")
        lines.append(f"  [dim]Registry: {available} servers available[/]")
    except Exception:
        pass

    lines.append("")

    # ---- Xavani home path ----
    lines.append(f"  [dim]Xavani home: {XAVANI_HOME}[/]")

    return "\n".join(lines)


@_register_handler("policy-add")
def oag_policy_add(args: str, cli=None) -> str:
    """Add a policy rule from a YAML or JSON file.

    Usage: /policy-add <path>
    """
    path_raw = args.strip()
    if not path_raw:
        return (
            "  [bold #FF3366]Usage: /policy-add <policy.yaml>[/]\n"
            "  [dim]Add a policy rule from a YAML or JSON file.[/]"
        )

    policy_path = Path(path_raw).expanduser().resolve()
    if not policy_path.exists():
        return f"  [bold #FF3366]✗ File not found: {policy_path}[/]"

    try:
        content = policy_path.read_text(encoding="utf-8")
    except OSError as e:
        return f"  [bold #FF3366]✗ Failed to read file: {e}[/]"

    try:
        import yaml
        data = yaml.safe_load(content)
    except Exception as e:
        return f"  [bold #FF3366]✗ Failed to parse YAML/JSON: {e}[/]"

    if not isinstance(data, dict):
        return "  [bold #FF3366]✗ Policy file must contain a top-level dictionary.[/]"

    policy_name = data.get("name") or data.get("rule") or policy_path.stem
    policy_name = str(policy_name).replace(" ", "-")

    try:
        from gateway.oag_proxy import OAGPolicyEngine
        engine = OAGPolicyEngine()
        dest = engine.add_policy_from_dict(policy_name, data)
    except Exception as e:
        return f"  [bold #FF3366]✗ Failed to write policy: {e}[/]"

    _append_audit(f"policy add '{policy_name}' from {policy_path}")

    rule_count = len(data.get("rules", data.get("allow", data.get("deny", []))))
    return (
        f"  [bold #00E676]✓ Policy added: {policy_name}[/]\n"
        f"  [dim]  Source: {policy_path}[/]\n"
        f"  [dim]  Stored: {dest}[/]\n"
        f"  [dim]  Rules:  {rule_count}[/]"
    )


@_register_handler("audit")
def oag_audit(args: str, cli=None) -> str:
    """Show the OAG audit log.

    Usage: /audit [--since 24h]

    Options:
      --since <duration>  Show entries from the last N hours (default: 24h).
                          Examples: 1h, 48h, 7d
    """
    _ensure_xavani_dirs()

    since_duration = "24h"
    rest = args.strip()
    if rest.startswith("--since"):
        parts = rest.split(None, 1)
        if len(parts) > 1:
            since_duration = parts[1].strip()
        else:
            return (
                "  [bold #FF3366]Usage: /audit [--since 24h][/]\n"
                "  [dim]--since requires a duration value like 24h, 2d, 48h[/]"
            )

    try:
        if since_duration.endswith("h"):
            hours = int(since_duration[:-1])
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        elif since_duration.endswith("d"):
            days = int(since_duration[:-1])
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        else:
            return (
                "  [bold #FF3366]Invalid duration format.[/]\n"
                "  [dim]Use e.g. --since 24h, --since 7d[/]"
            )
    except (ValueError, IndexError):
        return (
            "  [bold #FF3366]Invalid duration format.[/]\n"
            "  [dim]Use e.g. --since 24h, --since 7d[/]"
        )

    try:
        from gateway.oag_proxy import OAGAuditLogger
        audit = OAGAuditLogger()
        entries = audit.query(since=cutoff, limit=500)

        if not entries:
            return f"  [dim]No audit entries since {since_duration} ago.[/]"

        lines = [f"  [bold #00F5FF]OAG Audit Log (last {since_duration}):[/]"]
        for e in entries:
            ts = e.get("timestamp", "")[:19] if e.get("timestamp") else ""
            user = e.get("user_id", "")
            tool = e.get("tool_name", "")
            allowed = "✓" if e.get("allowed") else "✗"
            summary = (e.get("input_summary") or "")[:60]
            server = e.get("server_name", "") or ""
            lines.append(
                f"    [{ts}] {user} | {tool} | {server} | {allowed} | {summary}"
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.warning("Failed to query SQLite audit: %s", exc)
        # Fall back to legacy text log
        log_path = _oag_audit_log_path()
        if not log_path.exists() or log_path.stat().st_size == 0:
            return "  [dim]Audit log is empty.[/]"

        try:
            log_lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        except OSError as e:
            return f"  [bold #FF3366]✗ Failed to read audit log: {e}[/]"

        matching = []
        for line in log_lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and "]" in line:
                ts_str = line[1:].split("]")[0]
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        matching.append(line)
                except ValueError:
                    continue
            else:
                matching.append(line)

        if not matching:
            return f"  [dim]No audit entries since {since_duration} ago.[/]"

        result = [f"  [bold #00F5FF]OAG Audit Log (last {since_duration}):[/]"]
        for entry_line in matching:
            result.append(f"    {entry_line}")
        return "\n".join(result)


@_register_handler("security-scan")
def oag_security_scan(args: str, cli=None) -> str:
    """Run a security scan on an installed MCP server.

    Usage: /security-scan <name>
    """
    name = args.strip()
    if not name:
        return (
            "  [bold #FF3366]Usage: /security-scan <name>[/]\n"
            "  [dim]Run a security scan on an installed MCP server.[/]"
        )

    name = name.lower().strip()
    from xavani_registry import OAGRegistry
    registry = OAGRegistry()

    if not registry.is_installed(name):
        return f"  [bold #FFB300]⚠ Server '{name}' is not installed.[/]"

    try:
        scan = registry.security_scan(name)
        lines: List[str] = []

        if scan["passed"]:
            lines.append(f"  [bold #00E676]✓ Security scan passed: {name}[/]")
        else:
            lines.append(f"  [bold #FF3366]✗ Security scan failed: {name}[/]")

        lines.append(f"  [dim]  Score: {scan['score']}/100[/]")
        lines.append(f"  [dim]  High severity: {scan['high_severity_count']}[/]")
        lines.append(f"  [dim]  Medium severity: {scan['medium_severity_count']}[/]")

        if scan["findings"]:
            lines.append("")
            lines.append(f"  [bold #FFB300]Findings:[/]")
            for f in scan["findings"][:10]:
                severity_label = {1: "LOW", 2: "MED", 3: "HIGH"}.get(f["severity"], "?")
                lines.append(
                    f"    [{severity_label}] {f['pattern']}: {f['match'][:80]}"
                )

        return "\n".join(lines)
    except Exception as exc:
        return f"  [bold #FF3366]✗ Security scan failed: {exc}[/]"


@_register_handler("registry-list")
def oag_registry_list(args: str, cli=None) -> str:
    """List all available servers in the built-in registry.

    Usage: /registry-list [query]
    """
    query = args.strip()
    from xavani_registry import OAGRegistry
    registry = OAGRegistry()

    if query:
        results = registry.search(query)
        if not results:
            return f"  [dim]No servers found matching '{query}'.[/]"
        lines = [f"  [bold #00F5FF]Servers matching '{query}':[/]"]
    else:
        reg_info = registry.registry_info()
        available = reg_info.get("total_available", 0)
        servers = reg_info.get("servers", [])
        if not servers:
            return "  [dim]No servers available in registry.[/]"
        lines = [f"  [bold #00F5FF]Available Servers ({available} total):[/]"]
        results = []
        for name in servers:
            srv = registry.get(name)
            if srv:
                results.append(srv)

    for srv in results:
        name = srv.get("name", "?")
        desc = srv.get("description", "")
        installed = srv.get("installed", False)
        tags = srv.get("tags", [])
        tag_str = f" [dim][{'/'.join(tags[:3])}][/]" if tags else ""
        installed_mark = " [bold #00E676]● installed[/]" if installed else ""
        desc_str = f" — {desc[:100]}" if desc else ""
        lines.append(f"    [bold #E0E8FF]⚡ {name}[/]{desc_str}{tag_str}{installed_mark}")

    if not query:
        lines.append("")
        lines.append(f"  [dim]Use /install <name> to install a server.[/]")
        lines.append(f"  [dim]Use /registry-list <query> to search.[/]")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plugin-style registration helper (used by oag_cli.py)
# ---------------------------------------------------------------------------

def register_oag_commands() -> None:
    """Ensure OAG command handlers are registered into the shared plugin
    command namespace so the HermesCLI dispatcher can resolve them.

    This mimics how plugins register slash commands via
    ``PluginContext.register_command()``.
    """
    try:
        from hermes_cli.plugins import get_plugin_manager
        pm = get_plugin_manager()
        for cmd_def in OAG_COMMAND_DEFS:
            handler = OAG_COMMAND_HANDLERS.get(cmd_def.name)
            if handler is None:
                logger.warning("No handler registered for OAG command '%s'", cmd_def.name)
                continue
            # Re-register will be a no-op if already present; skip conflicts.
            if cmd_def.name in pm._plugin_commands:
                continue
            pm._plugin_commands[cmd_def.name] = {
                "handler": handler,
                "description": cmd_def.description,
                "plugin": "__oag__",
            }
    except Exception as exc:
        logger.debug("Could not register OAG commands via plugin manager: %s", exc)
        # Fallback: register directly into the global command registry lookups
        # so resolve_command() still finds them.
        _register_into_hermes_commands()


def _register_into_hermes_commands() -> None:
    """Fallback registration that injects OAG commands directly into the
    Hermes commands structures so they are discoverable.
    """
    try:
        from hermes_cli.commands import COMMAND_REGISTRY, _COMMAND_LOOKUP, _build_command_lookup

        # Check which OAG commands are not already present
        existing_names = {c.name for c in COMMAND_REGISTRY}
        for cmd_def in OAG_COMMAND_DEFS:
            if cmd_def.name not in existing_names:
                COMMAND_REGISTRY.append(cmd_def)

        # Rebuild lookup tables
        _COMMAND_LOOKUP.clear()
        _COMMAND_LOOKUP.update(_build_command_lookup())
    except Exception as exc:
        logger.warning("Failed to register OAG commands into Hermes dispatch: %s", exc)
