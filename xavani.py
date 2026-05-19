#!/usr/bin/env python3
"""
Xavani Agent — The open-source AI agent gateway.
Built by Entornovate. Provided as open source for the community.

A fully local, private, cross-platform AI agent CLI with MCP gateway,
skills management, and multi-provider support.

Usage:
    python xavani.py                          # Interactive mode
    python xavani.py --message "do X"         # Single query
    python xavani.py --gateway                # Start gateway server
    python xavani.py --install postgres       # Install MCP server
"""

import os
import sys
import logging

# ── Bootstrap ──────────────────────────────────────────────────────
# Force Xavani home directory BEFORE any other imports
_XAVANI_HOME = os.path.expanduser("~/.xavani")
os.environ.setdefault("XAVANI_HOME", _XAVANI_HOME)
os.environ.setdefault("HERMES_HOME", _XAVANI_HOME)  # Hermes compat
os.environ["HERMES_QUIET"] = "1"
os.environ["HERMES_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"

# Create Xavani directories
for d in ["", "logs", "skills", "policies", "installed", "data"]:
    os.makedirs(os.path.join(_XAVANI_HOME, d), exist_ok=True)

# ── Imports ────────────────────────────────────────────────────────

# Set skin before any CLI components initialize
from hermes_cli.skin_engine import set_active_skin, get_active_skin
set_active_skin("xavani-darkblue")

from cli import HermesCLI, main as hermes_main
from hermes_cli.oag_commands import OAG_COMMAND_DEFS, OAG_COMMAND_HANDLERS, register_oag_commands
from hermes_cli.commands import COMMAND_REGISTRY
from hermes_cli.config import cfg_get
from agent.display import KawaiiSpinner
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

# ── Buffalo Logo ────────────────────────────────────────────────────

BUFFALO_LOGO = """
                          ╔══════════════════════════════╗
                          ║   XAVANI AGENT              ║
                          ║   by Entornovate             ║
                          ╚══════════════════════════════╝

                 ,_   _  ,_,_   _,  ___ ___  ,  ,_
                 |_) / \ | | | (/_   |   |  |  |_)
                 |  \_/  | | | ,_)   |   |  |  | \\
                ════════════════════════════════════════
                Open-source AI agent gateway. Local only.
"""


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
            f"[bold {colors['banner_title']}]XAVANI AGENT[/bold {colors['banner_title']}]\n"
            f"[{colors['banner_accent']}]Open-Source AI Agent Gateway[/{colors['banner_accent']}]\n"
            f"\n"
            f"[{colors['banner_text']}]Built by [bold]Entornovate[/bold][/{colors['banner_text']}]\n"
            f"[{colors['banner_text']}]Provided as Open Source[/{colors['banner_text']}]\n"
            f"\n"
            f"[{colors['banner_dim']}]⟡ Fully local — no telemetry, no cloud[/{colors['banner_dim']}]\n"
            f"[{colors['banner_dim']}]⟡ 169+ built-in skills[/{colors['banner_dim']}]\n"
            f"[{colors['banner_dim']}]⟡ MCP gateway on localhost:8080[/{colors['banner_dim']}]\n"
            f"[{colors['banner_dim']}]⟡ Multi-provider: OpenAI, Claude, Gemini, Ollama[/{colors['banner_dim']}]\n"
            f"[{colors['banner_dim']}]⟡ Cross-platform: macOS, Windows, Linux[/{colors['banner_dim']}]\n"
            f"\n"
            f"Type [bold {colors['ui_accent']}]/help[/bold {colors['ui_accent']}] for commands or start typing.\n"
        ),
        border_style=colors["banner_border"],
        title=Text(" ⚡ Xavani Agent ", style=f"bold {colors['banner_title']}"),
        subtitle=Text("v0.1.0 — Entornovate", style=colors["banner_dim"]),
        padding=(1, 2),
    )
    console.print(banner)


# ── Xavani CLI Class ──────────────────────────────────────────────

class XavaniCLI(HermesCLI):
    """Xavani Agent CLI — extending Hermes with OAG gateway commands."""

    def __init__(self, *args, **kwargs):
        # Register OAG commands before init
        register_oag_commands()
        super().__init__(*args, **kwargs)

    def show_banner(self):
        """Override banner with Xavani branding."""
        show_xavani_banner(self.console)

    def process_command(self, cmd_name: str, args: str = "") -> bool:
        """Handle Xavani-specific commands, then fall through to Hermes."""
        handler = OAG_COMMAND_HANDLERS.get(cmd_name)
        if handler:
            handler(args, cli=self)
            return True
        return super().process_command(cmd_name, args)


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
):
    """Xavani Agent — Open-source AI agent gateway by Entornovate.

    Args:
        message: Single query mode (non-interactive)
        gateway: Start MCP gateway server
        install: Install an MCP server from registry
        skills: Comma-separated skills to load
        toolsets: Comma-separated toolsets to enable
        list_tools: List available tools and exit
        version: Show version and exit
        tui: Start TUI mode
    """
    if version:
        print("Xavani Agent v0.1.0")
        print("Built by Entornovate — Open Source")
        return

    if install:
        from hermes_cli.oag_commands import oag_install
        oag_install(install)
        return

    # Set active skin
    set_active_skin("xavani-darkblue")

    if gateway:
        os.environ["OAG_GATEWAY"] = "1"
        from gateway.run import start_gateway
        import asyncio
        print(f"{BUFFALO_LOGO}")
        print("Starting Xavani Gateway on http://localhost:8080 ...")
        asyncio.run(start_gateway())
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

    # Interactive mode
    show_xavani_banner()
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
