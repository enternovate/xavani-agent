# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Shared fixtures for tools tests.

Three concerns addressed here:

1. **Tool-defs cache isolation**: Clears ``model_tools._tool_defs_cache``
   before every test so that ``get_tool_definitions`` re-evaluates the
   current environment instead of returning a stale cached result.
   Without this, ``test_terminal_and_execute_code_tools_hide_*`` can fail
   intermittently in the full suite because a prior test that called
   ``get_tool_definitions(enabled_toolsets=["terminal", ...])`` with
   ``env_type="local"`` populated the cache.

2. **Telegram sys.modules**: Ensures ``telegram`` (and sub-modules) are
   always present in ``sys.modules`` for this directory so that tools like
   ``_send_telegram`` (which do ``from telegram import Bot`` inline) never
   raise ``ModuleNotFoundError`` when the worker was not assigned any
   tests from ``tests/gateway/`` (where ``conftest.py`` installs the mock
   at collection time).  Real tests that need a fully configured bot use
   ``_install_telegram_mock`` on top of this baseline.

3. **Lazy-deps bypass for mocked packages**: ``lazy_deps.ensure`` checks
   ``importlib.metadata`` (not ``sys.modules``) to decide whether a package
   is installed.  Tests that inject fake SDK modules via ``monkeypatch.setitem``
   would otherwise trigger a real pip-install attempt.  The
   ``_bypass_lazy_ensure_for_mocked_packages`` fixture patches
   ``feature_missing`` to treat packages already present in ``sys.modules``
   as satisfied, making the lazy-install path a no-op for mocked deps.
"""

import sys

import pytest
from unittest.mock import MagicMock

import model_tools as _model_tools
from tools import registry as _registry


def _ensure_telegram_stub() -> None:
    """Install a minimal telegram stub if the real library is absent."""
    if "telegram" in sys.modules:
        return  # Already installed (real or mock)
    stub = MagicMock()
    stub.Bot = MagicMock
    stub.constants.ParseMode.MARKDOWN_V2 = "MarkdownV2"
    stub.constants.ParseMode.HTML = "HTML"
    stub.error.NetworkError = type("NetworkError", (OSError,), {})
    stub.error.BadRequest = type("BadRequest", (Exception,), {})
    stub.error.TimedOut = type("TimedOut", (OSError,), {})
    sys.modules.setdefault("telegram", stub)
    sys.modules.setdefault("telegram.constants", stub.constants)
    sys.modules.setdefault("telegram.error", stub.error)
    sys.modules.setdefault("telegram.ext", stub.ext)
    sys.modules.setdefault("telegram.request", stub.request)


_ensure_telegram_stub()


def _ensure_fal_client_stub() -> None:
    """Install a minimal fal_client stub if the real library is absent.

    ``tools.image_generation_tool._load_fal_client`` tries to lazy-install
    ``fal-client`` (PyPI) on first use, then does ``import fal_client``.
    Tests that only exercise the *managed gateway* path (not direct fal usage)
    still trigger the load via ``_submit_fal_request``.  Pre-populating
    ``sys.modules["fal_client"]`` with a stub lets both the ``_try_import``
    check in ``_bypass_lazy_ensure_for_mocked_packages`` and the bare
    ``import fal_client`` that follows succeed without a real install.
    """
    if "fal_client" in sys.modules:
        return
    stub = MagicMock()
    stub.__name__ = "fal_client"
    sys.modules.setdefault("fal_client", stub)


_ensure_fal_client_stub()


@pytest.fixture(autouse=True)
def _clear_tool_defs_cache(monkeypatch):
    """Clear both caches and bypass TTL caching for the duration of each test.

    Two-layer cache isolation:

    1. ``model_tools._tool_defs_cache`` — outer cache keyed on toolset +
       registry generation + config.
    2. ``registry._check_fn_cache`` — ~30 s TTL inner cache for check_fn
       results (e.g. ``check_terminal_requirements``).

    Clearing both caches is necessary but not sufficient: if another xdist
    task (on the same worker, run just before the fixture setup) populated the
    check_fn cache in the sub-millisecond window, the TTL might not have
    expired yet.  As a belt-and-suspenders fix we also monkeypatch
    ``registry._check_fn_cached`` to call the fn directly (no TTL), so
    monkeypatched ``_get_env_config`` values are ALWAYS consulted.
    """
    _model_tools._tool_defs_cache.clear()
    _registry.invalidate_check_fn_cache()
    def _no_ttl_check_fn(fn):
        try:
            return bool(fn())
        except Exception:
            return False
    monkeypatch.setattr(_registry, "_check_fn_cached", _no_ttl_check_fn)
    yield
    _model_tools._tool_defs_cache.clear()
    _registry.invalidate_check_fn_cache()


@pytest.fixture(autouse=True)
def _bypass_lazy_ensure_for_mocked_packages(monkeypatch):
    """Make lazy_deps.ensure a no-op when packages are already importable.

    ``lazy_deps.ensure`` checks ``importlib.metadata`` (the installed-package
    database), not ``sys.modules``.  Tests that stub optional SDKs via
    ``monkeypatch.setitem(sys.modules, "pkg", fake)`` would otherwise trigger
    a live pip-install attempt, which fails consistently with "install reported
    success but packages still not importable" because the process can't reload
    its import path without a restart.

    The fix: wrap ``ensure`` so that we first attempt to actually import every
    package for the feature.  If all imports succeed (which they will for
    mocked packages already in ``sys.modules``), the function returns
    immediately without touching pip.  When any import fails, we fall through
    to the original logic.

    Note: PyPI package names ≠ import names (e.g. ``parallel-web`` → import
    ``parallel``).  We therefore try several candidate import names derived
    from the PyPI spec: the normalized underscored form, the hyphen-stripped
    prefix, and the exact package name.
    """
    import importlib as _importlib
    import tools.lazy_deps as _lazy_deps

    _orig_ensure = _lazy_deps.ensure

    def _try_import(pkg_name: str) -> bool:
        """Return True if any common import-name variant of pkg_name is importable."""
        candidates = {
            pkg_name,
            pkg_name.replace("-", "_"),
            pkg_name.split("-")[0],
            pkg_name.split("_")[0],
        }
        for name in candidates:
            try:
                _importlib.import_module(name)
                return True
            except (ImportError, ModuleNotFoundError):
                pass
        return False

    def _patched_ensure(feature: str, *, prompt: bool = True) -> None:
        try:
            specs = _lazy_deps.feature_specs(feature)
            if specs and all(_try_import(_lazy_deps._pkg_name_from_spec(s)) for s in specs):
                return  # All packages importable — nothing to do
        except Exception:
            pass
        return _orig_ensure(feature, prompt=prompt)

    monkeypatch.setattr(_lazy_deps, "ensure", _patched_ensure)
