"""``xavani portal`` — the human-readable entry point for Xavani Portal.

Running ``xavani portal`` with no subcommand performs the one-shot Portal
onboarding: OAuth login, pick a Xavani model, switch the inference provider to
Xavani, and offer to enable the Tool Gateway. It is the friendly alias for
``xavani auth add nous --type oauth`` (which still works), is identical to
``xavani setup --portal``, and runs the same Xavani flow as the first-time quick
setup.

Subcommands:
  (none)   Log in to Xavani Portal + set it up (one-shot onboarding).
  login    Explicit alias for the default one-shot onboarding.
  info     Show Portal auth state + which Tool Gateway tools are routed.
  open     Open the Portal subscription page in the user's default browser.
  tools    List Tool Gateway tools and which are active in the current config.

This command is intentionally minimal — it does not duplicate functionality
already in ``xavani auth`` or ``xavani tools``. It's the onboarding + discovery
surface for the Portal subscription itself.
"""
from __future__ import annotations

import sys

from xavani_cli.colors import Colors, color
from xavani_cli.config import load_config

DEFAULT_PORTAL_URL = ""
SUBSCRIPTION_URL = ""
DOCS_URL = "https://enternovate.co.za/xavani-agent/docs/user-guide/features/tool-gateway"


def _cmd_status(args) -> int:
    """Show Portal auth + Tool Gateway routing summary."""
    try:
        from xavani_cli.auth import get_nous_auth_status_local
    except ImportError:
        get_nous_auth_status_local = None
    config = load_config() or {}

    try:
        # Read-only status display: refresh-free snapshot (no OAuth refresh).
        auth = get_nous_auth_status_local() or {} if get_nous_auth_status_local else {}
    except Exception:
        auth = {}

    logged_in = bool(auth.get("logged_in"))

    print()
    print(color("  Xavani Portal", Colors.MAGENTA))
    print(color("  ───────────", Colors.MAGENTA))
    if logged_in:
        portal = auth.get("portal_base_url") or DEFAULT_PORTAL_URL
        print(f"  Auth:    {color('✓ logged in', Colors.GREEN)}")
        print(f"  Portal:  {portal}")
        inference = auth.get("inference_base_url")
        if inference:
            print(f"  API:     {inference}")
    else:
        print(f"  Auth:    {color('not configured', Colors.YELLOW)}")
        print("  The portal service is unavailable in this build.")

    # Provider selection (independent of auth)
    model_cfg = config.get("model") if isinstance(config.get("model"), dict) else {}
    provider = str(model_cfg.get("provider") or "").strip().lower()
    if provider == "nous":
        print(f"  Model:   {color('✓ using Xavani as inference provider', Colors.GREEN)}")
    elif provider:
        print(f"  Model:   currently {provider} (switch with `xavani model`)")

    # Tool Gateway routing
    print()
    print(color("  Tool Gateway", Colors.MAGENTA))
    print(color("  ────────────", Colors.MAGENTA))
    features = None

    if features is None:
        print("  (could not resolve subscription state)")
        return 0

    rows = []
    for feat in features.items():
        if feat.managed_by_nous:
            state = color("via Xavani Portal", Colors.GREEN)
        elif feat.active and feat.current_provider:
            state = feat.current_provider
        elif feat.active:
            state = "active"
        else:
            state = color("not configured", Colors.DIM)
        rows.append((feat.label, state))

    width = max((len(r[0]) for r in rows), default=0)
    for label, state in rows:
        print(f"  {label:<{width}}   {state}")

    if not logged_in:
        print()
        print(color(f"  Docs: {DOCS_URL}", Colors.DIM))
    return 0


def _cmd_open(args) -> int:
    """Open the Portal subscription page in the default browser."""
    print("The portal service is unavailable in this build.")
    return 1


def _cmd_tools(args) -> int:
    """List the Tool Gateway catalog + current routing."""
    print("The portal service is unavailable in this build.")
    return 1

def _cmd_login(args) -> int:
    """Run the one-shot Xavani Portal onboarding (login + model + provider + tools).

    This is the human-readable front door for `xavani auth add nous --type
    oauth`. It reuses the exact wiring behind `xavani setup --portal` (which in
    turn runs the same Xavani flow as the first-time quick setup), so the
    commands stay in lockstep: device-code login, pick a Xavani model, switch the
    inference provider to Xavani, then offer the Tool Gateway opt-in.
    """
    try:
        from xavani_cli.setup import _run_portal_one_shot
    except ImportError:
        print("Portal onboarding needs the setup module.", file=sys.stderr)
        return 1

    config = load_config() or {}
    try:
        _run_portal_one_shot(config)
    except (KeyboardInterrupt, EOFError):
        print()
        print("Portal setup cancelled.")
        return 1
    return 0


def portal_command(args) -> int:
    """Top-level dispatch for `xavani portal <subcommand>`."""
    sub = getattr(args, "portal_command", None)
    if sub in {None, "", "login"}:
        # Default to the one-shot onboarding — `xavani portal` is the
        # human-readable alias for `xavani auth add nous --type oauth` /
        # `xavani setup --portal`.
        return _cmd_login(args)
    if sub in {"info", "status"}:
        # `status` kept as a back-compat alias for the prior default.
        return _cmd_status(args)
    if sub == "open":
        return _cmd_open(args)
    if sub == "tools":
        return _cmd_tools(args)
    print(f"Unknown portal subcommand: {sub}", file=sys.stderr)
    print("Run `xavani portal -h` for usage.", file=sys.stderr)
    return 1


def add_parser(subparsers) -> None:
    """Register `xavani portal` on the given argparse subparsers object."""
    portal_parser = subparsers.add_parser(
        "portal",
        help="Set up Xavani Portal (login, model pick, Tool Gateway); see also `portal info`",
        description=(
            "Run `xavani portal` with no subcommand to log in to Xavani Portal "
            "and set it up — pick a model, set Xavani as your provider, and offer "
            "the Tool Gateway (the human-readable alias for `xavani auth add "
            "nous --type oauth`, identical to `xavani setup --portal`). "
            "Subcommands: login (default), info, open, tools."
        ),
    )
    portal_sub = portal_parser.add_subparsers(dest="portal_command")

    portal_sub.add_parser(
        "login",
        help="Log in to Xavani Portal + set it up (default; one-shot onboarding)",
    )
    portal_sub.add_parser(
        "info",
        help="Show Portal auth + Tool Gateway routing summary",
    )
    # `status` retained as a hidden back-compat alias for `info`.
    portal_sub.add_parser("status")
    portal_sub.add_parser(
        "open",
        help="Open the Portal subscription page in your default browser",
    )
    portal_sub.add_parser(
        "tools",
        help="List Tool Gateway tools and which are routed via Xavani",
    )

    portal_parser.set_defaults(func=portal_command)
