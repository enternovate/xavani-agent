"""Xavani Agent - slash command definitions and handlers.

Implements the Xavani Agent gateway commands that extend the base Hermes CLI:
  /install <name>       - Install MCP server from registry
  /gateway-up           - Start the MCP proxy gateway on localhost:8080
  /gateway-down         - Stop the gateway
  /registry-status      - Show installed servers and gateway status
  /policy-add <file>    - Add a policy rule
  /audit [--since 24h]  - Show audit log

Each command handler follows the pattern used by ``hermes_cli/commands.py``:
a canonical ``CommandDef`` in a local registry and a handler function.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hermes_cli.commands import CommandDef
from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAG Command Definitions
# ---------------------------------------------------------------------------
# These are registered into the dispatcher at OAG startup (see oag_cli.py).
# The naming convention uses a "oag_" prefix to avoid collisions with
# built-in Hermes commands.

OAG_COMMAND_DEFS: List[CommandDef] = [
    CommandDef(
        name="install",
        description="Install an MCP server from the registry",
        category="OAG Gateway",
        args_hint="<name>",
        cli_only=True,
    ),
    CommandDef(
        name="gateway-up",
        description="Start the MCP proxy gateway on localhost:8080",
        category="OAG Gateway",
        cli_only=True,
    ),
    CommandDef(
        name="gateway-down",
        description="Stop the running OAG gateway",
        category="OAG Gateway",
        cli_only=True,
    ),
    CommandDef(
        name="registry-status",
        description="Show installed MCP servers and gateway status",
        category="OAG Gateway",
        aliases=("status",),
        cli_only=True,
    ),
    CommandDef(
        name="policy-add",
        description="Add a policy rule from a YAML/JSON file",
        category="OAG Gateway",
        args_hint="<policy.yaml>",
        cli_only=True,
    ),
    CommandDef(
        name="audit",
        description="Show the OAG audit log",
        category="OAG Gateway",
        args_hint="[--since 24h]",
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
# Helpers
# ---------------------------------------------------------------------------

def _oag_home() -> Path:
    """Return the OAG home directory (default: ~/.oag)."""
    env = os.environ.get("OAG_HOME", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".oag"


def _oag_config_path() -> Path:
    """Return path to OAG config file."""
    return _oag_home() / "config.yaml"


def _oag_installed_path() -> Path:
    """Return path to installed MCP servers index."""
    return _oag_home() / "installed_servers.json"


def _oag_policy_dir() -> Path:
    """Return path to policy rules directory."""
    return _oag_home() / "policies"


def _oag_audit_log_path() -> Path:
    """Return path to the audit log file."""
    return _oag_home() / "audit.log"


def _oag_gateway_pid_path() -> Path:
    """Return path to the OAG gateway PID file."""
    return _oag_home() / "gateway.pid"


def _ensure_oag_dirs() -> None:
    """Create OAG home directories if they do not exist."""
    _oag_home().mkdir(parents=True, exist_ok=True)
    _oag_policy_dir().mkdir(parents=True, exist_ok=True)
    if not _oag_installed_path().exists():
        _oag_installed_path().write_text("[]", encoding="utf-8")
    if not _oag_audit_log_path().exists():
        _oag_audit_log_path().write_text("", encoding="utf-8")


def _append_audit(entry: str) -> None:
    """Append a timestamped audit log entry."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with _oag_audit_log_path().open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {entry}\n")
    except OSError as e:
        logger.warning("Failed to write audit log: %s", e)


def _get_installed_servers() -> List[Dict[str, Any]]:
    """Return the list of installed MCP servers."""
    path = _oag_installed_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_installed_servers(servers: List[Dict[str, Any]]) -> None:
    """Write the installed MCP servers list."""
    _oag_installed_path().write_text(
        json.dumps(servers, indent=2, default=str), encoding="utf-8"
    )


def _is_gateway_running() -> bool:
    """Check whether the OAG gateway process is alive."""
    pid_path = _oag_gateway_pid_path()
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)  # Signal 0 = existence probe
        return True
    except (OSError, ValueError, ValueError):
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

    Looks up the server definition in the OAG registry and configures it
    as an MCP server in ``~/.oag/config.yaml``.
    """
    name = args.strip()
    if not name:
        return (
            "  [bold #FF3366]Usage: /install <name>[/]\n"
            "  [dim]Install an MCP server from the OAG registry.[/]"
        )

    _ensure_oag_dirs()

    # ---- In-memory registry of known OAG MCP servers ----
    # In production this would query a remote registry; for now we
    # ship a small built-in catalogue.
    BUILTIN_REGISTRY: Dict[str, Dict[str, Any]] = {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "description": "Secure filesystem access (read, write, move, search)",
        },
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "description": "GitHub API integration (repos, issues, PRs, search)",
        },
        "postgres": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "description": "PostgreSQL database exploration and querying",
        },
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", str(_oag_home() / "data" / "oag.db")],
            "description": "Local SQLite database management via MCP",
        },
        "brave-search": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "description": "Web search via Brave Search API",
        },
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"],
            "description": "HTTP content fetching and web scraping",
        },
        "puppeteer": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            "description": "Browser automation with headless Chrome",
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "description": "Knowledge graph memory with persistent embeddings",
        },
    }

    name_lower = name.lower()
    entry = BUILTIN_REGISTRY.get(name_lower)
    if not entry:
        available = ", ".join(sorted(BUILTIN_REGISTRY.keys()))
        return (
            f"  [bold #FF3366]Unknown MCP server: {name}[/]\n"
            f"  [dim]Available servers: {available}[/]\n"
            f"  [dim]Usage: /install <name>[/]"
        )

    # Load existing installed servers
    servers = _get_installed_servers()

    # Check if already installed
    if any(s.get("name") == name_lower for s in servers):
        return f"  [bold #00E676]✓ {name} is already installed.[/]"

    # Add to installed list
    server_entry = {
        "name": name_lower,
        "command": entry["command"],
        "args": entry["args"],
        "description": entry.get("description", ""),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    servers.append(server_entry)
    _save_installed_servers(servers)
    _append_audit(f"install server '{name_lower}'")

    # Write to MCP config so the agent auto-discovers it on next reload
    try:
        from hermes_cli.config import load_config, save_config
        cfg = load_config()
        mcp_servers = cfg.setdefault("mcp_servers", {})
        mcp_servers[name_lower] = {
            "command": entry["command"],
            "args": list(entry["args"]),
        }
        save_config(cfg)
    except Exception as exc:
        logger.warning("Could not write MCP server to config: %s", exc)

    return (
        f"  [bold #00E676]✓ Installed MCP server: {name}[/]\n"
        f"  [dim]  {entry.get('description', '')}[/]\n"
        f"  [dim]  Command: {entry['command']} {' '.join(entry['args'])}[/]\n"
        f"  [dim]  Use /reload-mcp to activate it in the current session.[/]"
    )


@_register_handler("gateway-up")
def oag_gateway_up(args: str, cli=None) -> str:
    """Start the OAG MCP proxy gateway on localhost:8080.

    Launches the Hermes gateway in the background with OAG-specific
    configuration overrides.
    """
    if _is_gateway_running():
        pid = _gateway_pid()
        return (
            f"  [bold #FFB300]⚠ Gateway is already running (PID {pid})[/]\n"
            f"  [dim]Use /gateway-down to stop it first.[/]"
        )

    _ensure_oag_dirs()

    # Determine the project root
    project_root = Path(__file__).resolve().parent.parent

    # Set OAG environment overrides
    env = os.environ.copy()
    env.setdefault("OAG_HOME", str(_oag_home()))
    env.setdefault("HERMES_HOME", str(_oag_home()))
    env.setdefault("OAG_GATEWAY_PORT", "8080")
    env.setdefault("OAG_GATEWAY_HOST", "127.0.0.1")

    # Launch the gateway subprocess (non-blocking)
    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gateway.run",
                "--port", "8080",
                "--host", "127.0.0.1",
            ],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Write PID file
        _oag_gateway_pid_path().write_text(str(proc.pid), encoding="utf-8")
        _append_audit(f"gateway up (PID {proc.pid})")

        return (
            f"  [bold #00E676]✓ Gateway started (PID {proc.pid})[/]\n"
            f"  [dim]  Listening on http://127.0.0.1:8080[/]\n"
            f"  [dim]  Use /gateway-down to stop it.[/]"
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
        # Stale PID file
        _oag_gateway_pid_path().unlink(missing_ok=True)
        return "  [bold #FFB300]⚠ Gateway was not running (stale PID cleaned up).[/]"

    try:
        os.kill(pid, 15)  # SIGTERM
        # Wait briefly for graceful shutdown
        for _ in range(50):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # Force kill if still alive
            try:
                os.kill(pid, 9)
            except OSError:
                pass
    except OSError as e:
        return f"  [bold #FF3366]✗ Failed to stop gateway: {e}[/]"
    finally:
        _oag_gateway_pid_path().unlink(missing_ok=True)

    _append_audit("gateway down")
    return f"  [bold #00E676]✓ Gateway stopped (PID {pid})[/]"


@_register_handler("registry-status")
def oag_registry_status(args: str, cli=None) -> str:
    """Show installed MCP servers and gateway status."""
    _ensure_oag_dirs()

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
    servers = _get_installed_servers()
    if servers:
        lines.append(f"  [bold #00F5FF]Installed MCP Servers:[/]")
        for srv in servers:
            name = srv.get("name", "?")
            desc = srv.get("description", "")
            installed = srv.get("installed_at", "")[:10] if srv.get("installed_at") else ""
            desc_str = f" — {desc}" if desc else ""
            date_str = f" [dim]({installed})[/]" if installed else ""
            lines.append(f"    [bold #E0E8FF]⚡ {name}[/]{desc_str}{date_str}")
    else:
        lines.append(f"  [bold #FFB300]⚠ No MCP servers installed yet.[/]")
        lines.append(f"  [dim]  Use /install <name> to add one.[/]")
        lines.append(f"  [dim]  Available: filesystem, github, postgres, sqlite, brave-search, fetch, puppeteer, memory[/]")

    lines.append("")

    # ---- OAG home path ----
    lines.append(f"  [dim]OAG home: {_oag_home()}[/]")

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

    # Validate basic structure
    try:
        import yaml
        data = yaml.safe_load(content)
    except Exception as e:
        return f"  [bold #FF3366]✗ Failed to parse YAML/JSON: {e}[/]"

    if not isinstance(data, dict):
        return "  [bold #FF3366]✗ Policy file must contain a top-level dictionary.[/]"

    policy_name = data.get("name") or data.get("rule") or policy_path.stem
    policy_name = str(policy_name).replace(" ", "-")

    _ensure_oag_dirs()
    dest = _oag_policy_dir() / f"{policy_name}.yaml"
    try:
        import yaml as yaml_out
        with dest.open("w", encoding="utf-8") as f:
            yaml_out.dump(data, f, default_flow_style=False, allow_unicode=True)
    except OSError as e:
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
    _ensure_oag_dirs()

    # Parse --since argument
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

    # Parse duration
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

    log_path = _oag_audit_log_path()
    if not log_path.exists() or log_path.stat().st_size == 0:
        return "  [dim]Audit log is empty.[/]"

    try:
        log_lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    except OSError as e:
        return f"  [bold #FF3366]✗ Failed to read audit log: {e}[/]"

    # Filter by cutoff
    matching: List[str] = []
    for line in log_lines:
        line = line.strip()
        if not line:
            continue
        # Lines are formatted: [2025-01-01T00:00:00Z] message
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
    for entry in matching:
        result.append(f"    {entry}")

    return "\n".join(result)


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
