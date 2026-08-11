# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Import/smoke guards for the standalone ``oag_cli.py`` entry point.

``oag_cli.py`` is a standalone runnable script (``python oag_cli.py ...``)
with no other importers, so an import-time break in it is invisible to the
rest of the suite.  Regression guard for the fork-rename bug where
``oag_cli`` imported ``_ensure_oag_dirs`` from ``xavani_cli.oag_commands``
while the actual function is ``_ensure_xavani_dirs`` — which crashed every
invocation with ``ImportError`` at module load.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_oag_commands_exports_names_oag_cli_imports():
    """Every symbol ``oag_cli`` imports from oag_commands must exist."""
    from xavani_cli import oag_commands

    required = (
        "OAG_COMMAND_DEFS",
        "OAG_COMMAND_HANDLERS",
        "register_oag_commands",
        "_ensure_xavani_dirs",
        "_append_audit",
        "_oag_home",
    )
    missing = [name for name in required if not hasattr(oag_commands, name)]
    assert not missing, f"xavani_cli.oag_commands is missing: {missing}"


def test_oag_cli_help_runs_without_crashing(tmp_path):
    """`python oag_cli.py --help` must exit cleanly (no import-time crash)."""
    env = dict(os.environ)
    env["XAVANI_HOME"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "oag_cli.py"), "--help"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    # --help must not raise an ImportError / traceback at module load.
    assert "ImportError" not in proc.stderr, proc.stderr[-2000:]
    assert "Traceback (most recent call last)" not in proc.stderr, proc.stderr[-2000:]
