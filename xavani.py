#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Xavani Agent — the open-source AI agent gateway.

This module is the user-facing entry point. It sets up the ``~/.xavani``
home directory with restrictive permissions, configures the dark-blue
buffalo skin, registers the OAG slash-command handlers, and then dispatches
to one of several execution modes selected by Fire-parsed CLI flags:

* default — interactive REPL via :class:`XavaniCLI`
* ``--message`` — one-shot agent invocation
* ``--gateway`` — MCP proxy on ``localhost:8080``
* ``--install`` — register an MCP server
* ``--setup`` — first-run wizard
* ``--agents`` — list/inspect specialist personas
* ``--migrate-from-agent`` / ``--migrate-from-openclaw`` — config import

Pronounced: *shahr-vaa-nee*.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

# ---------------------------------------------------------------------------
# Bootstrap — runs *before* heavy imports
# ---------------------------------------------------------------------------
# Order matters: every downstream module reads ``XAVANI_HOME`` and the
# telemetry-off flags at import time, so we need them in ``os.environ``
# before any of those modules load. We also create the subdirectory tree
# with restrictive permissions because it stores OAuth tokens and API
# keys; a wide-open ``~/.xavani`` is a credential-exfil vector.

_XAVANI_HOME: Path = (
    Path(os.environ["XAVANI_HOME"]).expanduser()
    if os.environ.get("XAVANI_HOME")
    else Path.home() / ".xavani"
)
os.environ.setdefault("XAVANI_HOME", str(_XAVANI_HOME))
# Telemetry and quiet flags are forced even when already set elsewhere —
# Xavani is a zero-telemetry product by policy and we never want a stray
# upstream env var to opt the user back in.
os.environ["XAVANI_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"
# XAVANI_QUIET defers to the caller — they may have set it explicitly to
# allow debug output.
os.environ.setdefault("XAVANI_QUIET", "1")

_XAVANI_SUBDIRS: tuple[str, ...] = (
    "",            # ~/.xavani itself
    "logs",
    "skills",
    "policies",
    "installed",
    "data",
)

# Owner-only directory perms. The credentials in here (auth.json, .env)
# must not be world-readable.
_HOME_PERMS = 0o700

for sub in _XAVANI_SUBDIRS:
    target = _XAVANI_HOME / sub if sub else _XAVANI_HOME
    target.mkdir(mode=_HOME_PERMS, parents=True, exist_ok=True)
    # mkdir's mode arg is masked by the process umask, so reapply
    # explicitly. Best-effort: ignore the call on filesystems that don't
    # support chmod (e.g. some FUSE mounts).
    try:
        os.chmod(target, _HOME_PERMS)
    except OSError:
        pass

# ---------------------------------------------------------------------------
# Imports (must come after bootstrap)
# ---------------------------------------------------------------------------

from xavani_cli.skin_engine import set_active_skin, get_active_skin  # noqa: E402

set_active_skin("xavani-darkblue")

from cli import XavaniCLI as _BaseXavaniCLI  # noqa: E402
from cli import main as _cli_main  # noqa: E402,F401  pylint: disable=unused-import
from xavani_cli.oag_commands import (  # noqa: E402
    OAG_COMMAND_DEFS,
    OAG_COMMAND_HANDLERS,
    register_oag_commands,
)
from xavani_cli.commands import COMMAND_REGISTRY  # noqa: E402,F401  pylint: disable=unused-import
from xavani_cli.config import cfg_get  # noqa: E402,F401  pylint: disable=unused-import
from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION: str = "0.7.1"
PRONUNCIATION: str = "shahr-vaa-nee"
PRODUCT_NAME: str = "Xavani Agent"
VENDOR: str = "Enternovate"

BUFFALO_LOGO: str = """
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

# ---------------------------------------------------------------------------
# Banner rendering
# ---------------------------------------------------------------------------


def show_startup_explanation(console: Optional[Console] = None) -> None:
    """Display the detailed startup banner shown in interactive mode."""
    console = console or Console()

    title_panel = Panel(
        Text.from_markup(
            "\n"
            "[bold #e8b84b]⏺  XAVANI AGENT[/bold #e8b84b]\n"
            "[#88c0d0]Open-Source AI Agent Gateway[/#88c0d0]\n"
            f"[#5e81ac]Built by {VENDOR}[/#5e81ac]\n"
            "\n"
            f"[#81a1c1]Pronounced:[/#81a1c1] [italic]{PRONUNCIATION}[/italic]\n"
            f"[#81a1c1]Version:[/#81a1c1]  {VERSION}\n"
            "[#81a1c1]License:[/#81a1c1]  MIT — Open source. Private. Local.\n"
        ),
        border_style="#4a9eff",
        title=Text(" ⚡ Xavani Agent ", style="bold #e8b84b"),
        subtitle=Text(f"Built by {VENDOR} — Open Source", style="#5e81ac"),
        padding=(1, 2),
    )
    console.print(title_panel)

    feature_table = Table(show_header=False, box=None, padding=(0, 2))
    feature_table.add_column(style="#88c0d0", no_wrap=False)
    feature_table.add_column(style="#d8dee9", no_wrap=False)
    for label, desc in (
        ("Multi-Provider", "OpenAI, Claude, Gemini, Ollama, OpenRouter, xAI"),
        ("Built-in Skills", "169+ skills across 27 categories"),
        ("MCP Gateway", "localhost:8080 — MCP proxy for any app"),
    ):
        feature_table.add_row(f"  [bold]{label}[/bold]", desc)
    console.print(Panel(feature_table, border_style="#4a9eff", title="Features", padding=(1, 2)))

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
            "  [#88c0d0]⟡[/#88c0d0]  Run: [bold]xavani --migrate-from-agent --apply[/bold]\n"
            "  [#88c0d0]⟡[/#88c0d0]  Run: [bold]xavani --migrate-from-openclaw --apply[/bold]\n"
            "\n"
            "[#81a1c1]  Buffalo out. ⚡[/#81a1c1]\n"
        ),
        border_style="#4a9eff",
        title="Getting Started",
        padding=(1, 2),
    )
    console.print(tips_panel)


def show_xavani_banner(console: Optional[Console] = None) -> None:
    """Render the short banner used at the top of every interactive session.

    Newlines are emitted as literal ``\\n`` characters in the f-string —
    earlier versions of this function used ``\\\\n`` (escaped backslash)
    which baked the literal two-character sequence into the markup and
    surfaced as ``\\n`` in the rendered output. The Text.from_markup
    parser does not interpret those.
    """
    console = console or Console()
    skin = get_active_skin()
    colors = skin.colors

    body = Text.from_markup(
        f"\n"
        f"[bold {colors['banner_title']}]XAVANI AGENT[/bold {colors['banner_title']}]\n"
        f"[{colors['banner_accent']}]Open-Source AI Agent Gateway[/{colors['banner_accent']}]\n"
        f"\n"
        f"[{colors['banner_text']}]Built by [bold]{VENDOR}[/bold][/{colors['banner_text']}]\n"
        f"[{colors['banner_text']}]Provided as Open Source[/{colors['banner_text']}]\n"
        f"\n"
        f"[{colors['banner_dim']}]⟡ Fully local — no telemetry, no cloud[/{colors['banner_dim']}]\n"
        f"[{colors['banner_dim']}]⟡ 169+ built-in skills[/{colors['banner_dim']}]\n"
        f"[{colors['banner_dim']}]⟡ MCP gateway on localhost:8080[/{colors['banner_dim']}]\n"
        f"[{colors['banner_dim']}]⟡ Multi-provider: OpenAI, Claude, Gemini, Ollama[/{colors['banner_dim']}]\n"
        f"[{colors['banner_dim']}]⟡ Cross-platform: macOS, Windows, Linux[/{colors['banner_dim']}]\n"
        f"\n"
        f"Type [bold {colors['ui_accent']}]/help[/bold {colors['ui_accent']}] for commands or start typing.\n"
    )
    console.print(
        Panel(
            body,
            border_style=colors["banner_border"],
            title=Text(" ⚡ Xavani Agent ", style=f"bold {colors['banner_title']}"),
            subtitle=Text(f"v{VERSION} — {VENDOR}", style=colors["banner_dim"]),
            padding=(1, 2),
        )
    )


# ---------------------------------------------------------------------------
# CLI subclass
# ---------------------------------------------------------------------------


class XavaniCLI(_BaseXavaniCLI):  # type: ignore[misc, valid-type]
    """The Xavani CLI — extends the base CLI with the OAG slash commands."""

    def __init__(self, *args, **kwargs):
        register_oag_commands()
        super().__init__(*args, **kwargs)

    def show_banner(self) -> None:
        show_xavani_banner(self.console)

    def process_command(self, cmd_name: str, args: str = "") -> bool:
        handler = OAG_COMMAND_HANDLERS.get(cmd_name)
        if handler:
            handler(args, cli=self)
            return True
        return super().process_command(cmd_name, args)


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------


_DRY_RUN_TOKENS = frozenset({"", "1", "true", "yes", "dry", "dry-run", "--dry-run"})
_APPLY_TOKENS = frozenset({"--apply", "apply", "force"})


def _parse_dry_run(flag_value: str) -> bool:
    """Translate the CLI flag value into a dry-run boolean.

    The flag accepts a free-form string because Fire surfaces it that way;
    we recognise the common opt-in/opt-out spellings explicitly and treat
    anything else as dry-run for safety (better to make the user repeat
    the command with ``--apply`` than to silently mutate their home dir).
    """
    token = (flag_value or "").strip().lower()
    if token in _APPLY_TOKENS:
        return False
    if token in _DRY_RUN_TOKENS:
        return True
    return True  # Unknown token: default to dry-run.


def _run_migration(
    flag_value: str,
    module_name: str,
    func_name: str,
    pretty_source: str,
) -> None:
    """Locate ``module_name.func_name`` and run it with the parsed dry-run flag."""
    try:
        module = __import__(module_name, fromlist=[func_name])
        runner: Callable[..., None] = getattr(module, func_name)
    except (ImportError, AttributeError) as exc:
        logger.error("Could not load migration script for %s: %s", pretty_source, exc)
        sys.stderr.write(
            f"Error: could not load migration script for {pretty_source}: {exc}\n"
        )
        sys.exit(1)

    try:
        runner(dry_run=_parse_dry_run(flag_value))
    except Exception as exc:  # noqa: BLE001 — surface a user-facing message
        logger.exception("Migration from %s failed", pretty_source)
        sys.stderr.write(f"Error during {pretty_source} migration: {exc}\n")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Persona inspector
# ---------------------------------------------------------------------------


def _show_agents(name: str = "") -> None:
    """Print the specialist-persona catalogue, or details for a single persona."""
    try:
        from xavani_cli.subagent_personas import (
            get_persona,
            get_persona_domains,
            list_personas,
        )
    except ImportError as exc:
        sys.stderr.write(f"Error: subagent_personas module not available: {exc}\n")
        return

    if name:
        persona = get_persona(name)
        if not persona:
            sys.stderr.write(f"Unknown persona: {name}\n")
            available = ", ".join(list_personas())
            sys.stderr.write(f"Available: {available}\n")
            return
        print(f"\n  Persona: {name}")
        print(f"  {persona['description']}\n")
        print("  System prompt:")
        for line in persona["system_prompt"].split("\n"):
            print(f"    {line}")
        recommended = persona.get("recommended_toolsets") or ()
        if recommended:
            print(f"\n  Recommended toolsets: {', '.join(recommended)}")
        print()
        return

    domains = get_persona_domains()
    print(f"\n  {PRODUCT_NAME} Specialist Personas")
    print("  " + "=" * 40)
    for domain, persona_names in domains.items():
        print(f"\n  {domain}:")
        for pname in persona_names:
            persona = get_persona(pname) or {}
            desc = persona.get("description", "")
            short = desc[:65] + "…" if len(desc) > 65 else desc
            print(f"    {pname:<30s} {short}")
    print("\n  Use: xavani --agents <name> for details on a specific persona.\n")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def xavani_main(
    message: str = "",
    gateway: bool = False,
    install: str = "",
    setup: bool = False,
    agents: Optional[str] = None,
    skills: str = "",
    toolsets: str = "",
    list_tools: bool = False,
    version: bool = False,
    tui: bool = False,
    migrate_from_agent: str = "",
    migrate_from_openclaw: str = "",
) -> None:
    """Xavani Agent — open-source AI agent gateway by Enternovate.

    Args:
        message: Single query mode (non-interactive).
        gateway: Start the MCP gateway server.
        install: Install an MCP server from the registry.
        setup: Run the setup wizard to configure API keys and preferences.
        agents: List specialist personas (empty) or show details for one.
        skills: Comma-separated skills to load.
        toolsets: Comma-separated toolsets to enable.
        list_tools: List available tools and exit.
        version: Show version and exit.
        tui: Start TUI mode (reserved; falls back to interactive).
        migrate_from_agent: Import settings from another agent (``--apply``
            applies, anything else is dry-run).
        migrate_from_openclaw: Migrate from OpenClaw Agent (``--apply``
            applies, anything else is dry-run).
    """
    # Subcommand routing — handled here (not just in `main`) so the installed
    # console-script wrapper, which sometimes calls xavani_main directly and
    # never gives Fire a chance to parse sys.argv, still routes `xavani
    # update / dashboard / chat / …` to the full argparse CLI in
    # `xavani_cli.main`. Safe to call here: the delegate skips when there's
    # no positional subcommand on the command line.
    if _maybe_delegate_to_full_cli():
        return

    if version:
        print(f"{PRODUCT_NAME} v{VERSION}")
        print(f"Pronounced: {PRONUNCIATION}")
        print(f"Built by {VENDOR} — Open Source")
        print("MIT License — Free for any use.")
        return

    if setup:
        try:
            from xavani_cli.setup import run_setup_wizard

            run_setup_wizard()
        except ImportError:
            from xavani_cli.config import config_wizard

            config_wizard()
        return

    if agents is not None:
        _show_agents(agents)
        return

    if migrate_from_agent:
        _run_migration(
            migrate_from_agent,
            "scripts.migrate_from_xavani",
            "migrate_xavani",
            "another agent",
        )
        return

    if migrate_from_openclaw:
        _run_migration(
            migrate_from_openclaw,
            "scripts.migrate_from_openclaw",
            "migrate_openclaw",
            "OpenClaw",
        )
        return

    if install:
        from xavani_cli.oag_commands import oag_install

        oag_install(install)
        return

    # Locked-in skin for the rest of the modes.
    set_active_skin("xavani-darkblue")

    enabled_toolsets: Optional[Iterable[str]] = toolsets.split(",") if toolsets else None

    if gateway:
        os.environ["OAG_GATEWAY"] = "1"
        try:
            from gateway.oag_proxy import create_oag_proxy
        except ImportError as exc:
            sys.stderr.write(f"Error: missing dependencies for gateway mode: {exc}\n")
            sys.stderr.write("Install with: pip install 'xavani-agent[web]'\n")
            sys.exit(1)
        print(BUFFALO_LOGO)
        print("Starting Xavani MCP Gateway Proxy on http://localhost:8080 ...")
        print("Endpoints: /health, /mcp, /audit, /auth/token, /policies")
        proxy = create_oag_proxy()
        proxy.run_forever()
        return

    if message:
        # One-shot mode. `cli.XavaniCLI` doesn't accept a `message=` kwarg —
        # it only knows how to drive the interactive REPL. Route the request
        # through the full argparse CLI in `xavani_cli.main`, which has a
        # proper `chat -q "<message>"` handler that runs a single turn and
        # exits. Synthesizing argv keeps this fix local; the alternative
        # (pre-seeding the REPL input queue) would need surgery in cli.py.
        try:
            from xavani_cli.main import main as _cli_main_full
        except ImportError as exc:  # pragma: no cover — install-time path
            sys.stderr.write(f"Error: cannot dispatch --message: {exc}\n")
            sys.exit(1)
        sys.argv = ["xavani", "chat", "-q", message]
        if enabled_toolsets:
            sys.argv.extend(["--toolsets", ",".join(enabled_toolsets)])
        _cli_main_full()
        return

    if list_tools:
        # cli.XavaniCLI exposes `show_tools()`, not `list_tools()`.
        XavaniCLI(toolsets=enabled_toolsets).show_tools()
        return

    # Interactive mode.
    console = Console()
    show_startup_explanation(console)
    # cli.XavaniCLI's constructor parameter is `toolsets=`; the attribute it
    # stores on `self` is `enabled_toolsets`. We pass the right kwarg name.
    cli = XavaniCLI(toolsets=enabled_toolsets)
    cli.run()


# Subcommands handled by the full argparse CLI in `xavani_cli.main`. When the
# first positional arg matches one of these, we delegate there instead of
# routing through Fire — Fire would mis-interpret the subcommand name as the
# `message` positional and crash. Keep this list synced with the parser in
# `xavani_cli/_parser.py`.
_CLI_SUBCOMMANDS = frozenset({
    "dashboard", "chat", "gateway", "model", "fallback", "skills", "agents",
    "config", "logs", "sessions", "update", "debug", "kanban", "cron",
    "memory", "plan", "profile", "policies", "plugins", "sandbox", "setup",
    "telemetry", "tools", "tui", "version",
})


def _maybe_delegate_to_full_cli() -> bool:
    """Hand off to `xavani_cli.main.main` when the user invoked a subcommand.

    Returns True if delegation happened (caller should not invoke Fire).
    """
    if len(sys.argv) < 2:
        return False
    first = sys.argv[1]
    if first.startswith("-"):
        return False
    if first not in _CLI_SUBCOMMANDS:
        return False
    try:
        from xavani_cli.main import main as _cli_main_full
    except ImportError:
        return False
    _cli_main_full()
    return True


def main() -> None:
    """Console script entry point — wraps :func:`xavani_main` with Fire."""
    try:
        import fire
    except ImportError as exc:  # pragma: no cover — install-time path
        sys.stderr.write(
            f"Error: Xavani requires the 'fire' package: {exc}\n"
            "Install with: pip install xavani-agent\n"
        )
        sys.exit(1)

    try:
        if _maybe_delegate_to_full_cli():
            return
        fire.Fire(xavani_main)
    except KeyboardInterrupt:
        print("\nXavani Agent shut down. Buffalo out. ⚡")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 — top-level fatal handler
        logger.exception("Xavani Agent crashed")
        sys.stderr.write(
            "\nXavani Agent crashed. See logs in ~/.xavani/logs/ for details.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
