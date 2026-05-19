# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Regression tests for _apply_profile_override XAVANI_HOME guard (issue #22502).

When XAVANI_HOME is set to the xavani root (e.g. systemd hardcodes
XAVANI_HOME=/root/.xavani), _apply_profile_override must still read
active_profile and update XAVANI_HOME to the profile directory.

When XAVANI_HOME is already a profile directory (.../profiles/<name>),
_apply_profile_override must trust it and return without re-reading
active_profile (child-process inheritance contract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


def _run_apply_profile_override(
    tmp_path, monkeypatch, *, xavani_home: str | None, active_profile: str | None,
    argv: list[str] | None = None,
):
    """Run _apply_profile_override in isolation.

    Returns the value of os.environ["XAVANI_HOME"] after the call,
    or None if unset.
    """
    xavani_root = tmp_path / ".xavani"
    xavani_root.mkdir(parents=True, exist_ok=True)

    if active_profile is not None:
        (xavani_root / "active_profile").write_text(active_profile)

    if active_profile and active_profile != "default":
        (xavani_root / "profiles" / active_profile).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    if xavani_home is not None:
        monkeypatch.setenv("XAVANI_HOME", xavani_home)
    else:
        monkeypatch.delenv("XAVANI_HOME", raising=False)

    monkeypatch.setattr(sys, "argv", argv or ["xavani", "gateway", "start"])

    from xavani_cli.main import _apply_profile_override
    _apply_profile_override()

    return os.environ.get("XAVANI_HOME")


class TestApplyProfileOverrideXavaniHomeGuard:
    """Regression guard for issue #22502.

    Verifies that XAVANI_HOME pointing to the xavani root does NOT suppress
    the active_profile check, while XAVANI_HOME already pointing to a
    profile directory IS trusted as-is.
    """

    def test_xavani_home_at_root_with_active_profile_is_redirected(
        self, tmp_path, monkeypatch
    ):
        """XAVANI_HOME=/root/.xavani + active_profile=coder must redirect
        XAVANI_HOME to .../profiles/coder.

        Bug scenario from #22502: systemd sets XAVANI_HOME to the xavani root
        and the user switches to a profile via `xavani profile use`.
        Before the fix, the guard returned early and active_profile was ignored.
        """
        xavani_root = tmp_path / ".xavani"
        xavani_root.mkdir(parents=True, exist_ok=True)

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            xavani_home=str(xavani_root),
            active_profile="coder",
        )

        assert result is not None, "XAVANI_HOME must be set after profile redirect"
        assert "profiles" in result, (
            f"Expected XAVANI_HOME to point into profiles/ dir, got: {result!r}"
        )
        assert result.endswith("coder"), (
            f"Expected XAVANI_HOME to end with 'coder', got: {result!r}"
        )

    def test_xavani_home_already_profile_dir_is_trusted(self, tmp_path, monkeypatch):
        """XAVANI_HOME=.../profiles/coder must not be overridden even when
        active_profile says something different.

        Preserves the child-process inheritance contract: a subprocess spawned
        with XAVANI_HOME already set to a specific profile must stay in that
        profile.
        """
        xavani_root = tmp_path / ".xavani"
        profile_dir = xavani_root / "profiles" / "coder"
        profile_dir.mkdir(parents=True, exist_ok=True)

        (xavani_root / "active_profile").write_text("other")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("XAVANI_HOME", str(profile_dir))
        monkeypatch.setattr(sys, "argv", ["xavani", "gateway", "start"])

        from xavani_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("XAVANI_HOME") == str(profile_dir), (
            "XAVANI_HOME must remain unchanged when already pointing to a profile dir"
        )

    def test_xavani_home_unset_reads_active_profile(self, tmp_path, monkeypatch):
        """Classic case: XAVANI_HOME unset + active_profile=coder must set
        XAVANI_HOME to the profile directory (existing behaviour must not regress).
        """
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            xavani_home=None,
            active_profile="coder",
        )

        assert result is not None
        assert "coder" in result

    def test_xavani_home_unset_default_profile_no_redirect(self, tmp_path, monkeypatch):
        """active_profile=default must not redirect XAVANI_HOME."""
        xavani_root = tmp_path / ".xavani"
        xavani_root.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("XAVANI_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", ["xavani", "gateway", "start"])
        (xavani_root / "active_profile").write_text("default")

        from xavani_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("XAVANI_HOME") is None
