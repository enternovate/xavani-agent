#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Open Agent Gateway (OAG) CLI — Interactive Gateway Interface.

A cyberpunk-themed interactive CLI that wraps the Xavani Agent AI framework
with OAG-specific branding, commands, and gateway management capabilities.

Usage:
    python oag_cli.py                        # Start interactive mode
    python oag_cli.py -q "message"           # Single query mode
    python oag_cli.py --gateway              # Start gateway mode
    python oag_cli.py --install <name>       # Install an MCP server
"""

# Force the OAG home directory early, before any Xavani imports resolve.
import os as _os
import sys as _sys
from pathlib import Path as _Path

_OAG_HOME = _os.environ.get("OAG_HOME", "").strip()
if not _OAG_HOME:
    _OAG_HOME = str(_Path.home() / ".oag")
    _os.environ.setdefault("OAG_HOME", _OAG_HOME)

# Set XAVANI_HOME to OAG_HOME so all Xavani internals use .oag/ instead of .xavani/
_os.environ.setdefault("XAVANI_HOME", _OAG_HOME)

# Ensure OAG home directory exists
_Path(_OAG_HOME).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Now it is safe to import Xavani modules
# ---------------------------------------------------------------------------

import logging
import signal as _signal
import sys
from pathlib import Path
from typing import List, Optional

# Configure minimal logging before anything else
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(message)s",
)

import atexit

# Setup OAG telemetry opt-out before any import that might read it
_os.environ["XAVANI_DISABLE_TELEMETRY"] = "1"
_os.environ["DO_NOT_TRACK"] = "1"

# ---------------------------------------------------------------------------
# Pre-init: set the OAG skin before XavaniCLI is constructed
# ---------------------------------------------------------------------------
try:
    from xavani_cli.skin_engine import set_active_skin
    set_active_skin("oag-default")
except Exception:
    pass  # Skin engine unavailable; default skin will be used

import fire

from cli import XavaniCLI, CLI_CONFIG, load_cli_config
from cli import (
    _build_compact_banner,
    _parse_skills_argument,
    build_preloaded_skills_prompt,
    get_tool_definitions,
)
from xavani_cli.banner import build_welcome_banner
from xavani_cli.commands import (
    COMMAND_REGISTRY,
    _COMMAND_LOOKUP,
    _build_command_lookup,
    resolve_command,
)

# Import OAG command definitions and handlers
from xavani_cli.oag_commands import (
    OAG_COMMAND_DEFS,
    OAG_COMMAND_HANDLERS,
    register_oag_commands,
    _ensure_oag_dirs,
    _append_audit,
    _oag_home,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAG Cyberpunk Banner
# ---------------------------------------------------------------------------

OAG_STARTUP_BANNER = r"""[bold #00E5FF]  ██████╗  █████╗  ██████╗      ██████╗██╗     ██╗
[bold #00D4FF] ██╔═══██╗██╔══██╗██╔════╝    ██╔════╝██║     ██║
[bold #00C4FF] ██║   ██║███████║██║         ██║     ██║     ██║
[bold #00B4FF] ██║   ██║██╔══██║██║         ██║     ██║     ██║
[bold #00A4FF] ╚██████╔╝██║  ██║╚██████╗    ╚██████╗███████╗██║
[bold #0094FF]  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝     ╚═════╝╚══════╝╚═╝[/]

[dim #4A5580]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
[bold #00F5FF] Open Agent Gateway[/] [dim #4A5580]— AI Agent Gateway Framework[/]
[dim #4A5580]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]

[bold #4488FF]⚡  Gateway Services:[/]    [dim]MCP proxy  •  Plugin host  •  Audit log[/]
[bold #4488FF]⚡  Commands:[/]            [dim]/install  /gateway-up  /gateway-down[/]
[bold #4488FF]                         [/] [dim]/registry-status  /policy-add  /audit[/]
[bold #4488FF]⚡  Home:[/]               [dim]{oag_home}[/]
[dim #4A5580]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]
"""


# ---------------------------------------------------------------------------
# OAGCLI — extended XavaniCLI with OAG-specific overrides
# ---------------------------------------------------------------------------

class OAGCLI(XavaniCLI):
    """OAG-branded CLI that extends XavaniCLI with gateway management commands."""

    def __init__(self, *args, **kwargs):
        # Register OAG commands before base init so they are available
        # during command dispatch setup.
        register_oag_commands()
        _ensure_oag_dirs()
        _append_audit("CLI session started")

        super().__init__(*args, **kwargs)

        # Force OAG home in environment for child processes
        _os.environ["XAVANI_HOME"] = str(_oag_home())
        _os.environ["OAG_HOME"] = str(_oag_home())

        # Disable telemetry
        _os.environ["XAVANI_DISABLE_TELEMETRY"] = "1"
        _os.environ["DO_NOT_TRACK"] = "1"

    def show_banner(self):
        """Display the OAG cyberpunk-themed startup banner."""
        self.console.clear()

        # Print the OAG ASCII art banner
        term_width = _min_term_width()
        if term_width >= 60:
            self.console.print(OAG_STARTUP_BANNER.format(oag_home=str(_oag_home())))
        else:
            compact = _build_compact_banner()
            if compact:
                self.console.print(compact)
            self.console.print(
                f"\n[bold #00F5FF]Open Agent Gateway[/] [dim]— v0.1[/]"
            )

        # Show session info
        accent = "#00E5FF"
        self._console_print(
            f"[dim {accent}]━━━ Session ━━━[/]"
        )
        self._console_print(
            f"  [bold #E0E8FF]Model:[/]  {getattr(self, 'model', 'auto') or 'auto'}"
        )
        self._console_print(
            f"  [bold #E0E8FF]Session:[/] {self.session_id}"
        )
        if self.enabled_toolsets:
            toolsets_str = ", ".join(sorted(self.enabled_toolsets)) if self.enabled_toolsets else "all"
            self._console_print(
                f"  [bold #E0E8FF]Toolsets:[/] {toolsets_str}"
            )
        self._console_print(
            f"  [bold #E0E8FF]OAG Home:[/] {_oag_home()}"
        )
        self._console_print(
            f"[dim {accent}]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )

        # Warn about tools if there are issues
        self._show_tool_availability_warnings()

        # Show security advisories
        try:
            self._show_security_advisories()
        except Exception:
            pass

        self._console_print()

    def process_command(self, command: str) -> bool:
        """Process a slash command, including OAG-specific ones.

        Extends the base process_command to handle OAG gateway commands
        before falling through to the Xavani dispatcher.
        """
        cmd_stripped = command.strip()
        if not cmd_stripped:
            return True

        cmd_lower = cmd_stripped.lower()
        base_word = cmd_lower.split()[0].lstrip("/")
        args = cmd_stripped.split(maxsplit=1)[1] if " " in cmd_stripped else ""

        # Check OAG command handlers first
        handler = OAG_COMMAND_HANDLERS.get(base_word)
        if handler is not None:
            try:
                result = handler(args, cli=self)
                if result:
                    from rich.markup import escape as _escape
                    self.console.print(result)
                _append_audit(f"command /{base_word} {' '.join(args.split()[:3])}")
            except Exception as exc:
                logger.exception("OAG command /%s failed", base_word)
                self._console_print(
                    f"  [bold #FF3366]✗ Command /{base_word} failed: {exc}[/]"
                )
            return True

        # Fall through to the built-in Xavani dispatch
        return super().process_command(command)

    def _console_print(self, *args, **kwargs):
        """Thread-safe console print using the Rich console or ChatConsole."""
        safe_kwargs = dict(kwargs)
        if self._app:
            from xavani_cli.cli_output import ChatConsole
            cc = ChatConsole()
            cc.print(*args, **safe_kwargs)
        else:
            self.console.print(*args, **safe_kwargs)

    def _show_security_advisories(self):
        """Override to suppress Xavani-specific security banners that
        reference .xavani/ paths or assume Xavani branding."""
        pass  # OAG does not use Xavani security advisory banners by default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _min_term_width() -> int:
    """Return terminal width, with a safe minimum."""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def _get_platform_tools(config: dict) -> list:
    """Return the platform toolset list for the CLI."""
    try:
        from xavani_cli.tools_config import _get_platform_tools
        return sorted(_get_platform_tools(config, "cli"))
    except Exception:
        return ["xavani-cli"]


# ---------------------------------------------------------------------------
# Signal handler for clean shutdown
# ---------------------------------------------------------------------------

def _oag_signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    logger.debug("OAG CLI received signal %d", signum)
    _append_audit(f"CLI received signal {signum}")
    raise KeyboardInterrupt()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def oag_main(
    query: str = None,
    q: str = None,
    image: str = None,
    toolsets: str = None,
    skills: str | List[str] | tuple = None,
    model: str = None,
    provider: str = None,
    api_key: str = None,
    base_url: str = None,
    max_turns: int = None,
    verbose: bool = False,
    quiet: bool = False,
    compact: bool = False,
    list_tools: bool = False,
    list_toolsets: bool = False,
    gateway: bool = False,
    resume: str = None,
    worktree: bool = False,
    w: bool = False,
    checkpoints: bool = False,
    pass_session_id: bool = False,
    ignore_user_config: bool = False,
    ignore_rules: bool = False,
    install: str = None,
):
    """
    Open Agent Gateway CLI — Interactive AI Gateway Interface.

    Args:
        query: Single query to execute (then exit). Alias: -q
        q: Shorthand for --query
        image: Optional local image path to attach to a single query
        toolsets: Comma-separated list of toolsets to enable
        skills: Comma-separated or repeated list of skills to preload
        model: Model to use
        provider: Inference provider
        api_key: API key for authentication
        base_url: Base URL for the API
        max_turns: Maximum tool-calling iterations (default: 90)
        verbose: Enable verbose logging
        compact: Use compact display mode
        list_tools: List available tools and exit
        list_toolsets: List available toolsets and exit
        gateway: Run as messaging gateway
        resume: Resume a previous session by ID
        worktree: Run in an isolated git worktree
        w: Shorthand for --worktree
        install: Install an MCP server from the OAG registry and exit

    Examples:
        python oag_cli.py                              # Start interactive mode
        python oag_cli.py -q "List my files"            # Single query
        python oag_cli.py --install filesystem           # Install MCP server
        python oag_cli.py --gateway                      # Run gateway
        python oag_cli.py --toolsets web,terminal        # Specific toolsets
        python oag_cli.py --list-tools                   # Show available tools
    """
    # Handle --install flag (non-interactive MCP server install)
    if install:
        from xavani_cli.oag_commands import oag_install
        result = oag_install(install)
        _append_audit(f"CLI install '{install}'")
        print(result)
        return

    # Handle gateway mode
    if gateway:
        import asyncio
        try:
            from gateway.run import start_gateway
        except ImportError:
            print(
                "[ERROR] Gateway module not available. "
                "Make sure xavani-agent is properly installed.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("Starting Open Agent Gateway (messaging platforms)...")
        asyncio.run(start_gateway())
        return

    # Force UTF-8 stdio on Windows
    try:
        from xavani_cli.stdio import configure_windows_stdio
        configure_windows_stdio()
    except Exception:
        pass

    _os.environ["XAVANI_INTERACTIVE"] = "1"

    # Install signal handlers
    try:
        _signal.signal(_signal.SIGTERM, _oag_signal_handler)
        if hasattr(_signal, "SIGHUP"):
            _signal.signal(_signal.SIGHUP, _oag_signal_handler)
    except Exception:
        pass

    # Parse toolsets
    toolsets_list = None
    if toolsets:
        if isinstance(toolsets, str):
            toolsets_list = [t.strip() for t in toolsets.split(",")]
        elif isinstance(toolsets, (list, tuple)):
            toolsets_list = []
            for t in toolsets:
                if isinstance(t, str):
                    toolsets_list.extend([x.strip() for x in t.split(",")])
                else:
                    toolsets_list.append(str(t))
    else:
        toolsets_list = _get_platform_tools(CLI_CONFIG)

    parsed_skills = _parse_skills_argument(skills)

    # Create OAG CLI instance
    cli = OAGCLI(
        model=model,
        toolsets=toolsets_list,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        max_turns=max_turns,
        verbose=verbose,
        compact=compact,
        resume=resume,
        checkpoints=checkpoints,
        pass_session_id=pass_session_id,
        ignore_rules=ignore_rules,
    )

    if parsed_skills:
        skills_prompt, loaded_skills, missing_skills = build_preloaded_skills_prompt(
            parsed_skills,
            task_id=cli.session_id,
        )
        if missing_skills:
            missing_display = ", ".join(missing_skills)
            print(f"[ERROR] Unknown skill(s): {missing_display}", file=sys.stderr)
            sys.exit(1)
        if skills_prompt:
            cli.system_prompt = "\n\n".join(
                part for part in (cli.system_prompt, skills_prompt) if part
            ).strip()
            cli.preloaded_skills = loaded_skills

    # Handle list commands
    if list_tools:
        cli.show_banner()
        cli.show_tools()
        sys.exit(0)

    if list_toolsets:
        cli.show_banner()
        cli.show_toolsets()
        sys.exit(0)

    atexit.register(_oag_cleanup)

    # Handle single query mode
    if query or q or image:
        _query = query or q or ""
        cli.chat(_query, images=Path(image) if image else None)
        try:
            cli._print_exit_summary()
        except Exception:
            pass
        _append_audit("CLI single-query concluded")
        return

    # Run interactive mode
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n[OAG] Interrupted. Shutting down...")
    except Exception as exc:
        logger.exception("Fatal error in OAG CLI")
        print(f"\n[OAG] Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        _append_audit("CLI session ended")
        _oag_cleanup()


def _oag_cleanup():
    """Run OAG-specific cleanup on exit."""
    try:
        from cli import _run_cleanup
        _run_cleanup()
    except Exception:
        pass
    # Remove stale gateway PID if we own it and it's not running
    try:
        from xavani_cli.oag_commands import _oag_gateway_pid_path, _is_gateway_running
        pid_path = _oag_gateway_pid_path()
        if pid_path.exists() and not _is_gateway_running():
            pid_path.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI entry via Fire
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Regenerate command lookup tables for OAG commands on import
    register_oag_commands()

    fire.Fire(oag_main)
