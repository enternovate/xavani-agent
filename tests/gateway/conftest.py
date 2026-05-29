# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Shared fixtures for gateway tests.

The ``_ensure_telegram_mock`` helper guarantees that a minimal mock of
the ``telegram`` package is registered in :data:`sys.modules` **before**
any test file triggers ``from gateway.platforms.telegram import ...``.

Without this, ``pytest-xdist`` workers that happen to collect
``test_telegram_caption_merge.py`` (bare top-level import, no per-file
mock) first will cache ``ChatType = None`` from the production
ImportError fallback, causing 30+ downstream test failures wherever
``ChatType.GROUP`` / ``ChatType.SUPERGROUP`` is accessed.

Individual test files may still call their own ``_ensure_telegram_mock``
— it short-circuits when the mock is already present.

Plugin-adapter anti-pattern guard
---------------------------------
Tests for platform plugins (``plugins/platforms/<name>/adapter.py``)
must load the adapter via
:func:`tests.gateway._plugin_adapter_loader.load_plugin_adapter`, not by
adding the plugin directory to ``sys.path`` and doing a bare
``from adapter import ...``. The guard at the bottom of this file
scans test module ASTs at collection time and fails collection with a
pointer to the helper if the anti-pattern is detected.

Rationale: every plugin ships its own ``adapter.py``, and two tests each
inserting their plugin dir on ``sys.path[0]`` race for
``sys.modules["adapter"]`` in the same xdist worker. Whichever collects
first wins; the other fails with ``ImportError``, and the polluted
``sys.path`` cascades into unrelated tests. See PR #17764 for the
incident.
"""

import ast
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _ensure_telegram_mock() -> None:
    """Install a comprehensive telegram mock in sys.modules.

    Idempotent — skips when the real library is already imported.
    Uses ``sys.modules[name] = mod`` (overwrite) instead of
    ``setdefault`` so it wins even if a partial/broken import
    already cached a module with ``ChatType = None``.
    """
    if "telegram" in sys.modules and hasattr(sys.modules["telegram"], "__file__"):
        return  # Real library is installed — nothing to mock

    mod = MagicMock()
    mod.ext.ContextTypes.DEFAULT_TYPE = type(None)

    # Configure ParseMode and ChatType on BOTH mod.constants.* (kept for
    # backward-compat) AND mod.* directly.
    # CRITICAL: sys.modules["telegram.constants"] is mapped to `mod`, so
    # ``from telegram.constants import ChatType`` gets mod.ChatType (NOT
    # mod.constants.ChatType).  If only mod.constants.ChatType is configured
    # the production module captures a bare MagicMock for ChatType and all
    # str-comparison logic (``str(ChatType.SUPERGROUP).split(".")[-1]``) breaks.
    #
    # ParseMode values use _EnumLike (a str subclass) so that:
    #   • Production code receives the real string value ("MarkdownV2")
    #   • Tests that check ``"MARKDOWN_V2" in repr(parse_mode)`` still pass
    #     because repr includes the attr name (e.g. "<ParseMode.MARKDOWN_V2>").
    class _EnumLike(str):
        """str subclass whose repr includes the constant name."""
        _enum_name: str = ""
        def __repr__(self):
            return f"<ParseMode.{self._enum_name}: {str.__repr__(self)}>"

    def _pm(name, value):
        obj = _EnumLike(value)
        obj._enum_name = name
        return obj

    for _attr, _val in (
        ("MARKDOWN", "Markdown"), ("MARKDOWN_V2", "MarkdownV2"), ("HTML", "HTML")
    ):
        _pv = _pm(_attr, _val)
        setattr(mod.constants.ParseMode, _attr, _pv)
        setattr(mod.ParseMode, _attr, _pv)
    for _attr, _val in (
        ("PRIVATE", "private"), ("GROUP", "group"),
        ("SUPERGROUP", "supergroup"), ("CHANNEL", "channel"),
    ):
        setattr(mod.constants.ChatType, _attr, _val)
        setattr(mod.ChatType, _attr, _val)

    # Real exception classes so ``except (NetworkError, ...)`` clauses
    # in production code don't blow up with TypeError.
    mod.error.NetworkError = type("NetworkError", (OSError,), {})
    mod.error.TimedOut = type("TimedOut", (OSError,), {})
    mod.error.BadRequest = type("BadRequest", (Exception,), {})
    mod.error.Forbidden = type("Forbidden", (Exception,), {})
    mod.error.InvalidToken = type("InvalidToken", (Exception,), {})
    mod.error.RetryAfter = type("RetryAfter", (Exception,), {"retry_after": 1})
    mod.error.Conflict = type("Conflict", (Exception,), {})

    # Update.ALL_TYPES used in start_polling()
    mod.Update.ALL_TYPES = []

    for name in (
        "telegram",
        "telegram.ext",
        "telegram.constants",
        "telegram.request",
    ):
        sys.modules[name] = mod
    sys.modules["telegram.error"] = mod.error


def _augment_discord_mock(discord_mod) -> None:
    """Add gateway-test-required attributes to an existing discord mock.

    Called both when we create a fresh mock AND when we adopt a mock
    that was already installed by another conftest (e.g. tests/e2e/conftest.py).
    This ensures the SAME mock object ends up with all the attrs regardless
    of which conftest runs first.

    Key invariant: ``gateway.platforms.discord`` caches a reference to
    ``sys.modules["discord"]`` at import time.  Replacing that entry with a
    *new* object after the module has been imported causes the module's
    ``discord`` global to diverge from ``sys.modules["discord"]``, breaking
    every ``isinstance(ch, discord.ForumChannel)`` style check.  By augmenting
    the already-installed mock instead of replacing it we keep both references
    pointing at the same object.
    """
    from types import SimpleNamespace

    # --- Fundamental class stubs (idempotent: only set when missing) ---
    if not isinstance(discord_mod.DMChannel, type):
        discord_mod.DMChannel = type("DMChannel", (), {})
    if not isinstance(discord_mod.Thread, type):
        discord_mod.Thread = type("Thread", (), {})
    if not isinstance(discord_mod.ForumChannel, type):
        discord_mod.ForumChannel = type("ForumChannel", (), {})
    if not isinstance(discord_mod.Message, type):
        discord_mod.Message = type("Message", (), {})
    if not isinstance(discord_mod.Interaction, type):
        discord_mod.Interaction = object

    # --- MessageType: complete integer enum so set-membership checks work.
    # The e2e conftest only sets default/reply; tests for thread_rename/pins_add/
    # new_member etc. need those attrs to be real ints (not MagicMocks), otherwise
    # set-containment checks like ``msg.type not in {MessageType.default,
    # MessageType.reply}`` may give wrong results when the value is a MagicMock.
    # Detection: check ``new_member`` (NOT ``default``) — the e2e conftest sets
    # default=0 (an int) but omits new_member, so an int-check on default would
    # always pass and we would never replace the incomplete SimpleNamespace. ---
    _mt = getattr(discord_mod, "MessageType", None)
    _mt_new_member = getattr(_mt, "new_member", None)
    if not isinstance(_mt_new_member, int):
        discord_mod.MessageType = SimpleNamespace(
            default=0,
            recipient_add=1, recipient_remove=2, call=3,
            channel_name_change=4, channel_icon_change=5,
            pins_add=6, new_member=7,
            premium_guild_subscription=8,
            premium_guild_subscription_tier_1=9,
            premium_guild_subscription_tier_2=10,
            premium_guild_subscription_tier_3=11,
            channel_follow_add=12,
            guild_discovery_disqualified=14,
            guild_discovery_requalified=15,
            guild_discovery_grace_period_initial_warning=16,
            guild_discovery_grace_period_final_warning=17,
            thread_created=18,
            reply=19,
            application_command=20,
            thread_starter_message=21,
            guild_invite_reminder=22,
            context_menu_command=23,
            auto_moderation_action=24,
        )

    # --- Real Exception subclasses — gateway code does ``except discord.Forbidden:``
    # and Python raises TypeError if the caught class doesn't inherit BaseException. ---
    if not (isinstance(discord_mod.Forbidden, type) and issubclass(discord_mod.Forbidden, BaseException)):
        discord_mod.Forbidden = type("Forbidden", (Exception,), {})
    if not (isinstance(discord_mod.NotFound, type) and issubclass(discord_mod.NotFound, BaseException)):
        discord_mod.NotFound = type("NotFound", (Exception,), {})
    if not (isinstance(discord_mod.HTTPException, type) and issubclass(discord_mod.HTTPException, BaseException)):
        discord_mod.HTTPException = type("HTTPException", (Exception,), {})

    # --- AllowedMentions: real class so test assertions on .everyone / .roles work ---
    if not isinstance(discord_mod.AllowedMentions, type):
        class _FakeAllowedMentions:
            def __init__(self, *, everyone=True, roles=True, users=True, replied_user=True):
                self.everyone = everyone
                self.roles = roles
                self.users = users
                self.replied_user = replied_user
        discord_mod.AllowedMentions = _FakeAllowedMentions

    # --- Permissions: real class so slash-auth tests work ---
    if not isinstance(discord_mod.Permissions, type):
        class _FakePermissions:
            def __init__(self, value=0, **_):
                self.value = value
        discord_mod.Permissions = _FakePermissions

    # --- Embed: accept kwargs and expose .fields for clarify-button tests ---
    if not isinstance(discord_mod.Embed, type):
        class _FakeEmbed:
            def __init__(self, *, title=None, description=None, color=None, **_):
                self.title = title
                self.description = description
                self.color = color
                self.fields = []
                self.footer = None
            def add_field(self, *, name=None, value=None, inline=False, **_):
                self.fields.append({"name": name, "value": value, "inline": inline})
                return self
            def set_footer(self, *, text=None, icon_url=None, **_):
                self.footer = {"text": text, "icon_url": icon_url}
                return self
        discord_mod.Embed = _FakeEmbed

    # --- SelectOption ---
    if not isinstance(discord_mod.SelectOption, type):
        class _FakeSelectOption:
            def __init__(self, *, label=None, value=None, description=None, **_):
                self.label = label
                self.value = value
                self.description = description
        discord_mod.SelectOption = _FakeSelectOption

    # --- ui.View / ui.Select / ui.Button: real classes so tests that subclass
    # ModelPickerView / iterate .children / clear items work ---
    # IMPORTANT: hasattr() always returns True for MagicMock objects, so we
    # must check whether discord_mod.ui.View is already a *real type* (not a
    # MagicMock).  If the e2e conftest installed discord before us, ui.View is
    # a MagicMock attribute; we MUST replace ui with a proper SimpleNamespace.
    _existing_view = getattr(getattr(discord_mod, "ui", None), "View", None)
    if not isinstance(_existing_view, type):
        class _FakeView:
            def __init__(self, timeout=None):
                self.timeout = timeout
                self.children = []
            def add_item(self, item):
                self.children.append(item)
            def clear_items(self):
                self.children.clear()

        class _FakeSelect:
            def __init__(self, *, placeholder=None, options=None, custom_id=None, **_):
                self.placeholder = placeholder
                self.options = options or []
                self.custom_id = custom_id
                self.callback = None
                self.disabled = False

        class _FakeButton:
            def __init__(self, *, label=None, style=None, custom_id=None, emoji=None,
                         url=None, disabled=False, row=None, sku_id=None, **_):
                self.label = label
                self.style = style
                self.custom_id = custom_id
                self.emoji = emoji
                self.url = url
                self.disabled = disabled
                self.row = row
                self.sku_id = sku_id
                self.callback = None

        discord_mod.ui = SimpleNamespace(
            View=_FakeView,
            Select=_FakeSelect,
            Button=_FakeButton,
            button=lambda *a, **k: (lambda fn: fn),
        )

        # If gateway.platforms.discord was already imported before we set up
        # _FakeView, the View subclasses (ExecApprovalView, SlashConfirmView,
        # etc.) are MagicMock instances (not real classes) because Python used
        # MagicMock as the metaclass when 'class Foo(mock.View):' was evaluated.
        # Force a reimport so they are re-evaluated with the correct _FakeView base.
        _gw_name = "gateway.platforms.discord"
        if _gw_name in sys.modules:
            _gw_mod = sys.modules[_gw_name]
            # Detection: if ExecApprovalView is a MagicMock (not a real class),
            # the module was imported with a bad discord.ui.View.
            _ev = getattr(_gw_mod, "ExecApprovalView", None)
            if _ev is not None and (isinstance(_ev, MagicMock) or not isinstance(_ev, type)):
                for _key in [k for k in sys.modules if k == _gw_name or k.startswith(_gw_name + ".")]:
                    del sys.modules[_key]
    else:
        # ui exists and View is already a real type — just ensure button exists
        ui = discord_mod.ui
        if not hasattr(ui, "button"):
            ui.button = lambda *a, **k: (lambda fn: fn)

    # --- ButtonStyle / Color ---
    # Use isinstance checks, not hasattr — MagicMock always answers True to hasattr.
    _bs = getattr(discord_mod, "ButtonStyle", None)
    if not (isinstance(_bs, (type, SimpleNamespace)) and hasattr(_bs, "success") and isinstance(_bs.success, int)):
        discord_mod.ButtonStyle = SimpleNamespace(
            success=1, primary=2, secondary=2, danger=3,
            green=1, grey=2, blurple=2, red=3,
        )
    _color = getattr(discord_mod, "Color", None)
    if not (isinstance(_color, (type, SimpleNamespace)) and hasattr(_color, "orange") and callable(getattr(_color, "orange", None))):
        discord_mod.Color = SimpleNamespace(
            orange=lambda: 1, green=lambda: 2, blue=lambda: 3,
            red=lambda: 4, purple=lambda: 5, greyple=lambda: 6,
        )

    # --- File / Client ---
    if not isinstance(discord_mod.File, type) and not callable(discord_mod.File):
        discord_mod.File = MagicMock
    if not isinstance(discord_mod.Client, type) and not callable(discord_mod.Client):
        discord_mod.Client = MagicMock

    # --- app_commands: Group / Command / autocomplete needed by slash tests ---
    # Check if _app.Group is a real class (not a MagicMock attribute).
    _app = getattr(discord_mod, "app_commands", None)
    _app_group = getattr(_app, "Group", None) if _app is not None else None
    if not isinstance(_app_group, type):
        class _FakeGroup:
            def __init__(self, *, name, description, parent=None):
                self.name = name
                self.description = description
                self.parent = parent
                self._children: dict = {}
                if parent is not None:
                    parent.add_command(self)
            def add_command(self, cmd):
                self._children[cmd.name] = cmd

        class _FakeCommand:
            def __init__(self, *, name, description, callback, parent=None):
                self.name = name
                self.description = description
                self.callback = callback
                self.parent = parent

        discord_mod.app_commands = SimpleNamespace(
            describe=lambda **kwargs: (lambda fn: fn),
            choices=lambda **kwargs: (lambda fn: fn),
            autocomplete=lambda **kwargs: (lambda fn: fn),
            Choice=lambda **kwargs: SimpleNamespace(**kwargs),
            Group=_FakeGroup,
            Command=_FakeCommand,
        )
    else:
        if not hasattr(_app, "autocomplete"):
            _app.autocomplete = lambda **kwargs: (lambda fn: fn)
        if not hasattr(_app, "Group"):
            class _FakeGroup:
                def __init__(self, *, name, description, parent=None):
                    self.name = name
                    self.description = description
                    self.parent = parent
                    self._children: dict = {}
                    if parent is not None:
                        parent.add_command(self)
                def add_command(self, cmd):
                    self._children[cmd.name] = cmd
            _app.Group = _FakeGroup
        if not hasattr(_app, "Command"):
            class _FakeCommand:
                def __init__(self, *, name, description, callback, parent=None):
                    self.name = name
                    self.description = description
                    self.callback = callback
                    self.parent = parent
            _app.Command = _FakeCommand


def _ensure_discord_mock() -> None:
    """Install a comprehensive discord mock in sys.modules.

    Idempotent — skips when the real library is already imported.

    IMPORTANT: Uses ``sys.modules.setdefault`` rather than a direct
    ``sys.modules[name] = mod`` assignment so that whichever conftest
    runs first (gateway or e2e) owns the mock object.
    ``gateway.platforms.discord`` caches ``sys.modules["discord"]`` at
    import time.  Replacing the entry afterwards causes the module's
    ``discord`` global to point at a *different* object than what the
    test files see via ``import discord``, breaking every
    ``isinstance(ch, discord.ForumChannel)`` check.

    Instead, we always *augment* the existing mock (see ``_augment_discord_mock``)
    so both references stay in sync regardless of conftest load order.
    """
    if "discord" in sys.modules and hasattr(sys.modules["discord"], "__file__"):
        return  # Real library is installed — nothing to mock

    if "discord" not in sys.modules:
        # No mock installed yet — create a fresh one.
        discord_mod = MagicMock()
        discord_mod.Intents.default.return_value = MagicMock()
        sys.modules.setdefault("discord", discord_mod)

    # Always augment whatever is currently installed (ours or another conftest's).
    _augment_discord_mock(sys.modules["discord"])

    ext_mod = MagicMock()
    commands_mod = MagicMock()
    commands_mod.Bot = MagicMock
    ext_mod.commands = commands_mod

    sys.modules.setdefault("discord.ext", ext_mod)
    sys.modules.setdefault("discord.ext.commands", commands_mod)


# Run at collection time — before any test file's module-level imports.
_ensure_telegram_mock()
_ensure_discord_mock()


# ---------------------------------------------------------------------------
# Plugin-adapter anti-pattern guard
# ---------------------------------------------------------------------------

_GATEWAY_DIR = Path(__file__).resolve().parent
_GUARD_HINT = (
    "Plugin adapter tests must use "
    "``from tests.gateway._plugin_adapter_loader import load_plugin_adapter`` "
    "and call ``load_plugin_adapter('<plugin_name>')`` instead of inserting "
    "``plugins/platforms/<name>/`` on sys.path and doing a bare ``import "
    "adapter`` / ``from adapter import ...``. See the 'Plugin-adapter "
    "anti-pattern guard' docstring in tests/gateway/conftest.py."
)


def _scan_for_plugin_adapter_antipattern(source: str) -> list[str]:
    """Return a list of offending-line descriptions, or [] if clean.

    Flags two things:
    1. ``sys.path.insert(..., <something mentioning 'plugins/platforms'>)``
    2. ``import adapter`` or ``from adapter import ...`` at module level.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []  # Let pytest surface the real syntax error.

    offenses: list[str] = []

    for node in ast.walk(tree):
        # sys.path.insert(0, ".../plugins/platforms/...")
        if isinstance(node, ast.Call):
            func = node.func
            target_name: str | None = None
            if isinstance(func, ast.Attribute):
                # sys.path.insert / sys.path.append
                if (
                    isinstance(func.value, ast.Attribute)
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "sys"
                    and func.value.attr == "path"
                    and func.attr in {"insert", "append", "extend"}
                ):
                    target_name = f"sys.path.{func.attr}"

            if target_name is not None:
                call_src = ast.unparse(node)
                # Match both the string-literal form
                # ``.../plugins/platforms/...`` and the Path-operator form
                # ``Path(...) / 'plugins' / 'platforms' / ...`` that
                # plugin tests typically use.
                _src_no_ws = "".join(call_src.split())
                if (
                    "plugins/platforms" in call_src
                    or "plugins\\platforms" in call_src
                    or "'plugins'/'platforms'" in _src_no_ws
                    or '"plugins"/"platforms"' in _src_no_ws
                ):
                    offenses.append(
                        f"line {node.lineno}: {target_name}(...) points into "
                        f"plugins/platforms/"
                    )

    # Bare `import adapter` / `from adapter import ...` anywhere (module level
    # OR inside functions — both are symptoms of the same pattern).
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "adapter":
                    offenses.append(
                        f"line {node.lineno}: ``import adapter`` "
                        f"(bare — resolves to whichever plugin's adapter.py "
                        f"is first on sys.path)"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module == "adapter" and node.level == 0:
                offenses.append(
                    f"line {node.lineno}: ``from adapter import ...`` "
                    f"(bare — resolves to whichever plugin's adapter.py "
                    f"is first on sys.path)"
                )

    return offenses


def pytest_configure(config):
    """Reject plugin-adapter tests that use the sys.path anti-pattern.

    Runs once per pytest session on the controller, BEFORE any xdist
    worker is spawned. If any file under ``tests/gateway/`` matches the
    anti-pattern, we fail the whole session with a clear message —
    before a polluted ``sys.path`` can cascade across workers.
    """
    # Only run on the xdist controller (or in non-xdist runs). Skip on
    # worker subprocesses so we don't scan the filesystem N times.
    if hasattr(config, "workerinput"):
        return

    violations: list[str] = []
    for path in _GATEWAY_DIR.rglob("test_*.py"):
        if path.name in {"_plugin_adapter_loader.py", "conftest.py"}:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "adapter" not in source and "plugins/platforms" not in source:
            continue
        offenses = _scan_for_plugin_adapter_antipattern(source)
        if offenses:
            violations.append(
                f"  {path.relative_to(_GATEWAY_DIR.parent.parent)}:\n    "
                + "\n    ".join(offenses)
            )

    if violations:
        raise pytest.UsageError(
            "Plugin-adapter-import anti-pattern detected in gateway tests:\n"
            + "\n".join(violations)
            + "\n\n"
            + _GUARD_HINT
        )

