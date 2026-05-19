#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""
Xavani Agent — The open-source AI agent gateway.
Built by Enternovate. Provided as open source for the community.

A fully local, private, cross-platform AI agent CLI with MCP gateway,
skills management, and multi-provider support.

Pronounced: shahr-vaa-nee

Usage:
    python xavani.py                          # Interactive mode
    python xavani.py --message "do X"         # Single query
    python xavani.py --gateway                # Start gateway server
    python xavani.py --install postgres       # Install MCP server
    python xavani.py --migrate-from-agent    # Import settings from another agent
    python xavani.py --migrate-from-openclaw  # Migrate from OpenClaw
"""

import os
import sys
import logging

# ── Bootstrap ──────────────────────────────────────────────────────
# Force Xavani home directory BEFORE any other imports
_XAVANI_HOME = os.path.expanduser("~/.xavani")
os.environ.setdefault("XAVANI_HOME", _XAVANI_HOME)
os.environ.setdefault("XAVANI_HOME", _XAVANI_HOME)  # Xavani compat
os.environ["XAVANI_QUIET"] = "1"
os.environ["XAVANI_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"

# Create Xavani directories
for d in ["", "logs", "skills", "policies", "installed", "data"]:
    os.makedirs(os.path.join(_XAVANI_HOME, d), exist_ok=True)

# ── Imports ────────────────────────────────────────────────────────

# Set skin before any CLI components initialize
from xavani_cli.skin_engine import set_active_skin, get_active_skin
set_active_skin("xavani-darkblue")

from cli import XavaniCLI, main as xavani_main
from xavani_cli.oag_commands import OAG_COMMAND_DEFS, OAG_COMMAND_HANDLERS, register_oag_commands
from xavani_cli.commands import COMMAND_REGISTRY
from xavani_cli.config import cfg_get
from agent.display import KawaiiSpinner
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table

logger = logging.getLogger(__name__)

# ── Buffalo Logo ────────────────────────────────────────────────────

BUFFALO_LOGO = """
                          ╔══════════════════════════════╗
                          ║   XAVANI AGENT              ║
                          ║   by Enternovate             ║
                          ╚══════════════════════════════╝

                 ,_   _  ,_,_   _,  ___ ___  ,  ,_
                 |_) / \\ | | | (/_   |   |  |  |_)
                 |  \\_/  | | | ,_)   |   |  |  | \\\\
                ════════════════════════════════════════
                Open-source AI agent gateway. Local only.
"""


# ── Startup Explanation ─────────────────────────────────────────────

def show_startup_explanation(console: Console = None):
    """Display detailed startup explanation with logo, features, and tips."""
    if console is None:
        console = Console()

    # Title panel
    title_panel = Panel(
        Text.from_markup(
            "\n"
            "[bold #e8b84b]⏺  XAVANI AGENT[/bold #e8b84b]\n"
            "[#88c0d0]Open-Source AI Agent Gateway[/#88c0d0]\n"
            "[#5e81ac]Built by Enternovate[/#5e81ac]\n"
            "\n"
            "[#81a1c1]Pronounced:[/#81a1c1] [italic]shahr-vaa-nee[/italic]\n"
            "[#81a1c1]Version:[/#81a1c1]  0.1.0\n"
            "[#81a1c1]License:[/#81a1c1]  MIT — Open source. Private. Local.\n"
        ),
        border_style="#4a9eff",
        title=Text(" ⚡ Xavani Agent ", style="bold #e8b84b"),
        subtitle=Text("Built by Enternovate — Open Source", style="#5e81ac"),
        padding=(1, 2),
    )
    console.print(title_panel)

    # Feature overview table
    feature_table = Table(show_header=False, box=None, padding=(0, 2))
    feature_table.add_column(style="#88c0d0", no_wrap=False)
    feature_table.add_column(style="#d8dee9", no_wrap=False)
    features = [
        ("Multi-Provider", "OpenAI, Claude, Gemini, Ollama, OpenRouter, xAI"),
        ("Built-in Skills", "169+ skills across 27 categories"),
        ("MCP Gateway", "localhost:8080 — MCP proxy for any app"),
        ("Fully Local", "Zero telemetry. Zero cloud dependency."),
        ("Cross-Platform", "macOS, Windows, Linux"),
        ("Dark Blue Theme", "Cyberpunk-styled TUI with buffalo logo"),
    ]
    for label, desc in features:
        feature_table.add_row(f"  [bold]{label}[/bold]", desc)
    console.print(Panel(feature_table, border_style="#4a9eff", title="Features", padding=(1, 2)))

    # Quick start tips
    tips_panel = Panel(
        Text.from_markup(
            "\n"
            "[bold #e8b84b]Quick Start Tips:[/bold #e8b84b]\n"
            "\n"
            "  [#88c0d0]⟡[/#88c0d0]  Just start [bold]typing[/bold] — the agent is ready to chat\n"
            "  [#88c0d0]⟡[/#88c0d0]  Type [bold]/help[/bold] to see all available commands\n"
            "  [#88c0d0]⟡[/#88c0d0]  Type [bold]/install <skill>[/bold] to install a skill\n"
            "  [#88c0d0]⟡[/#88c0d0]  Type [bold]/gateway-up[/bold] to start the MCP gateway\n"
            "  [#88c0d0]⟡[/#88c0d0]  Set env vars: [bold]XAVANI_PROVIDER[/bold], [bold]XAVANI_MODEL[/bold]\n"
            "  [#88c0d0]⟡[/#88c0d0]  Or run: [bold]xavani --message \"your task\"[/bold]\n"
            "\n"
            "[#5e81ac]  Migrating from another agent?[/#5e81ac]\n"
            "  [#88c0d0]⟡[/#88c0d0]  Run: [bold]xavani --migrate-from-xavani[/bold]\n"
            "  [#88c0d0]⟡[/#88c0d0]  Run: [bold]xavani --migrate-from-openclaw[/bold]\n"
            "\n"
            "[#81a1c1]  Buffalo out. ⚡[/#81a1c1]\n"
        ),
        border_style="#4a9eff",
        title="Getting Started",
        padding=(1, 2),
    )
    console.print(tips_panel)


# ── Xavani Banner ──────────────────────────────────────────────────

def show_xavani_banner(console: Console = None):
    """Display the Xavani Agent startup banner with buffalo art."""
    if console is None:
        console = Console()

    skin = get_active_skin()
    colors = skin.colors

    banner = Panel(
        Text.from_markup(
            f"\n"
            f"[bold {colors['banner_title']}]XAVANI AGENT[/bold {colors['banner_title']}]\\n"
            f"[{colors['banner_accent']}]Open-Source AI Agent Gateway[/{colors['banner_accent']}]\\n"
            f"\\n"
            f"[{colors['banner_text']}]Built by [bold]Enternovate[/bold][/{colors['banner_text']}]\\n"
            f"[{colors['banner_text']}]Provided as Open Source[/{colors['banner_text']}]\\n"
            f"\\n"
            f"[{colors['banner_dim']}]⟡ Fully local — no telemetry, no cloud[/{colors['banner_dim']}]\\n"
            f"[{colors['banner_dim']}]⟡ 169+ built-in skills[/{colors['banner_dim']}]\\n"
            f"[{colors['banner_dim']}]⟡ MCP gateway on localhost:8080[/{colors['banner_dim']}]\\n"
            f"[{colors['banner_dim']}]⟡ Multi-provider: OpenAI, Claude, Gemini, Ollama[/{colors['banner_dim']}]\\n"
            f"[{colors['banner_dim']}]⟡ Cross-platform: macOS, Windows, Linux[/{colors['banner_dim']}]\\n"
            f"\\n"
            f"Type [bold {colors['ui_accent']}]/help[/bold {colors['ui_accent']}] for commands or start typing.\\n"
        ),
        border_style=colors["banner_border"],
        title=Text(" ⚡ Xavani Agent ", style=f"bold {colors['banner_title']}"),
        subtitle=Text("v0.1.0 — Enternovate", style=colors["banner_dim"]),
        padding=(1, 2),
    )
    console.print(banner)


# ── Xavani CLI Class ──────────────────────────────────────────────

class XavaniCLI(XavaniCLI):
    """Xavani Agent CLI — the open-source AI agent gateway."""

    def __init__(self, *args, **kwargs):
        # Register OAG commands before init
        register_oag_commands()
        super().__init__(*args, **kwargs)

    def show_banner(self):
        """Override banner with Xavani branding."""
        show_xavani_banner(self.console)

    def process_command(self, cmd_name: str, args: str = "") -> bool:
        """Handle Xavani-specific commands, then fall through to standard dispatch."""
        handler = OAG_COMMAND_HANDLERS.get(cmd_name)
        if handler:
            handler(args, cli=self)
            return True
        return super().process_command(cmd_name, args)


# ── Migration helpers ──────────────────────────────────────────────

def _run_migrate_agent(dry_run: bool):
    """Run config migration from another agent."""
    try:
        from scripts.migrate_from_xavani import migrate_xavani
        migrate_xavani(dry_run=dry_run)
    except ImportError as e:
        print(f"Error: Could not load migration script: {e}")
        print("Make sure scripts/migrate_from_xavani.py exists.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)


def _run_migrate_openclaw(dry_run: bool):
    """Run OpenClaw → Xavani migration."""
    try:
        from scripts.migrate_from_openclaw import migrate_openclaw
        migrate_openclaw(dry_run=dry_run)
    except ImportError as e:
        print(f"Error: Could not load migration script: {e}")
        print("Make sure scripts/migrate_from_openclaw.py exists.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)


# ── Entry Point ────────────────────────────────────────────────────

def xavani_main(
    message: str = "",
    gateway: bool = False,
    install: str = "",
    skills: str = "",
    toolsets: str = "",
    list_tools: bool = False,
    version: bool = False,
    tui: bool = False,
    migrate_from_agent: str = "",
    migrate_from_openclaw: str = "",
):
    """Xavani Agent — Open-source AI agent gateway by Enternovate.

    Args:
        message: Single query mode (non-interactive)
        gateway: Start MCP gateway server
        install: Install an MCP server from registry
        skills: Comma-separated skills to load
        toolsets: Comma-separated toolsets to enable
        list_tools: List available tools and exit
        version: Show version and exit
        tui: Start TUI mode
        migrate_from_agent: Import settings from another agent (--dry-run or --apply)
        migrate_from_openclaw: Migrate from OpenClaw Agent (--dry-run or --apply)
    """
    if version:
        print("Xavani Agent v0.1.0")
        print("Pronounced: shahr-vaa-nee")
        print("Built by Enternovate — Open Source")
        print("MIT License — Free for any use.")
        return

    # Migration flags
    if migrate_from_agent:
        dry_run = migrate_from_agent.lower() in ("", "1", "true", "--dry-run", "dry-run")
        if migrate_from_agent.lower() in ("--apply", "apply", "1", "true"):
            dry_run = False
        _run_migrate_agent(dry_run=dry_run)
        return

    if migrate_from_openclaw:
        dry_run = migrate_from_openclaw.lower() in ("", "1", "true", "--dry-run", "dry-run")
        if migrate_from_openclaw.lower() in ("--apply", "apply", "1", "true"):
            dry_run = False
        _run_migrate_openclaw(dry_run=dry_run)
        return

    if install:
        from xavani_cli.oag_commands import oag_install
        oag_install(install)
        return

    # Set active skin
    set_active_skin("xavani-darkblue")

    if gateway:
        os.environ["OAG_GATEWAY"] = "1"
        try:
            from gateway.oag_proxy import create_oag_proxy
            print(f"{BUFFALO_LOGO}")
            print("Starting Xavani MCP Gateway Proxy on http://localhost:8080 ...")
            print("Endpoints: /health, /mcp, /audit, /auth/token, /policies")
            proxy = create_oag_proxy()
            proxy.run_forever()
        except ImportError as exc:
            print(f"Error: Missing dependencies for gateway mode: {exc}")
            print("Install with: pip install 'xavani-agent[web]'")
            sys.exit(1)
        return

    if message:
        # Single query mode
        show_xavani_banner()
        cli = XavaniCLI(
            message=message,
            enabled_toolsets=toolsets.split(",") if toolsets else None,
        )
        cli.run()
        return

    if list_tools:
        XavaniCLI().list_tools()
        return

    # Interactive mode — show detailed startup explanation
    console = Console()
    show_startup_explanation(console)
    cli = XavaniCLI(
        enabled_toolsets=toolsets.split(",") if toolsets else None,
    )
    cli.run()


# ── CLI Entry ──────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        import fire
        fire.Fire(xavani_main)
    except KeyboardInterrupt:
        print("\nXavani Agent shut down. Buffalo out. ⚡")
        sys.exit(0)
