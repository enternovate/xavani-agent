# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for get_xavani_home() profile-mode fallback warning.

Regression test for https://github.com/NousResearch/hermes-agent/issues/18594.

When XAVANI_HOME is unset but an active_profile file indicates a non-default
profile is active, get_xavani_home() should:
  1. STILL return ~/.xavani (raising would brick 30+ module-level callers)
  2. Emit a loud one-shot warning to stderr so operators can diagnose
     cross-profile data contamination after the fact.

The warning goes to stderr directly (not through logging) because this
function is called at module-import time from 30+ sites, often before the
logging subsystem has been configured.
"""

from pathlib import Path

import pytest


@pytest.fixture
def fresh_constants(monkeypatch, tmp_path):
    """Import xavani_constants fresh and reset the one-shot warn flag."""
    import importlib
    import xavani_constants
    importlib.reload(xavani_constants)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("XAVANI_HOME", raising=False)
    return xavani_constants


class TestGetXavaniHomeProfileWarning:
    def test_classic_mode_no_active_profile_no_warning(
        self, fresh_constants, tmp_path, capsys
    ):
        """Classic mode: no active_profile file → silent, returns ~/.xavani."""
        result = fresh_constants.get_xavani_home()
        assert result == tmp_path / ".xavani"
        assert "XAVANI_HOME fallback" not in capsys.readouterr().err

    def test_default_active_profile_no_warning(
        self, fresh_constants, tmp_path, capsys
    ):
        """active_profile=default → still no warning, returns ~/.xavani."""
        xavani_dir = tmp_path / ".xavani"
        xavani_dir.mkdir()
        (xavani_dir / "active_profile").write_text("default\n")
        result = fresh_constants.get_xavani_home()
        assert result == tmp_path / ".xavani"
        assert "XAVANI_HOME fallback" not in capsys.readouterr().err

    def test_named_profile_unset_home_warns_once(
        self, fresh_constants, tmp_path, capsys
    ):
        """active_profile=coder + XAVANI_HOME unset → warn loudly, still return fallback."""
        xavani_dir = tmp_path / ".xavani"
        xavani_dir.mkdir()
        (xavani_dir / "active_profile").write_text("coder\n")

        result = fresh_constants.get_xavani_home()

        # 1. Still returns the fallback — no import-time crash
        assert result == tmp_path / ".xavani"
        # 2. Stderr got the warning exactly once
        err = capsys.readouterr().err
        assert err.count("XAVANI_HOME fallback") == 1
        assert "'coder'" in err
        assert "#18594" in err

        # 3. One-shot: second and third calls don't re-warn
        fresh_constants.get_xavani_home()
        fresh_constants.get_xavani_home()
        err2 = capsys.readouterr().err
        assert "XAVANI_HOME fallback" not in err2

    def test_xavani_home_set_suppresses_warning(
        self, fresh_constants, tmp_path, capsys, monkeypatch
    ):
        """Even if active_profile is 'coder', setting XAVANI_HOME suppresses warning."""
        profile_dir = tmp_path / ".xavani" / "profiles" / "coder"
        profile_dir.mkdir(parents=True)
        (tmp_path / ".xavani" / "active_profile").write_text("coder\n")
        monkeypatch.setenv("XAVANI_HOME", str(profile_dir))

        result = fresh_constants.get_xavani_home()

        assert result == profile_dir
        assert "XAVANI_HOME fallback" not in capsys.readouterr().err

    def test_unreadable_active_profile_no_crash(
        self, fresh_constants, tmp_path, capsys
    ):
        """active_profile that can't be decoded → fall through silently."""
        xavani_dir = tmp_path / ".xavani"
        xavani_dir.mkdir()
        # Write bytes that aren't valid utf-8
        (xavani_dir / "active_profile").write_bytes(b"\xff\xfe\x00\x00")

        result = fresh_constants.get_xavani_home()

        assert result == tmp_path / ".xavani"
        # Shouldn't crash; shouldn't warn either (can't tell what profile was intended)
        assert "XAVANI_HOME fallback" not in capsys.readouterr().err

    def test_empty_active_profile_no_warning(
        self, fresh_constants, tmp_path, capsys
    ):
        """Empty active_profile file → treated as default, no warning."""
        xavani_dir = tmp_path / ".xavani"
        xavani_dir.mkdir()
        (xavani_dir / "active_profile").write_text("")

        result = fresh_constants.get_xavani_home()

        assert result == tmp_path / ".xavani"
        assert "XAVANI_HOME fallback" not in capsys.readouterr().err
