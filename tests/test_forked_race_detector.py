# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A06: forked race detector tests.

The detector script must exist, list the race-prone modules, and invoke
pytest with --forked. The guard tests pin the contract so the detector
cannot silently drift back to threaded-only runs.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_script() -> str:
    path = REPO_ROOT / "scripts" / "run_forked_race_tests.py"
    assert path.exists(), "scripts/run_forked_race_tests.py must exist (A06)"
    return path.read_text(encoding="utf-8")


def test_script_uses_forked_flag():
    src = _read_script()
    assert '"--forked"' in src
    assert "pytest" in src


def test_script_lists_race_prone_modules():
    src = _read_script()
    assert "test_approval.py" in src
    assert "test_mixture_of_agents_tool.py" in src
    assert "test_tirith_security.py" in src


def test_forked_plugin_available():
    """pytest-forked must be installed (dev extra)."""
    import pytest_forked  # noqa: F401


@pytest.mark.long_running
def test_script_is_executable_contract():
    """The script must run and return 0 on a clean module."""
    # Runs a forked pytest subprocess over a whole module; under full-suite
    # load it legitimately exceeds the 30s global test timeout, so it opts
    # out via the long_running marker (its internal timeout is 180s).
    result = subprocess.run(
        [sys.executable, "scripts/run_forked_race_tests.py",
         "tests/xavani_state/test_state_integrity.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-1000:]
    assert "passed" in result.stdout


def test_pyproject_pins_forked_plugin():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "pytest-forked" in pyproject
