# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F05: sandboxed plugin framework tests."""

import os
import sys
from pathlib import Path

import pytest

from tools.plugin_sandbox import (
    _sandbox_env,
    run_plugin_in_sandbox,
    sandbox_env_snapshot,
)

pytestmark = pytest.mark.integration


def _write_plugin(tmp_path, code: str) -> Path:
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "main.py").write_text(code, encoding="utf-8")
    return plugin_dir


# ── env scrubbing ──────────────────────────────────────────────────


def test_env_strips_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("XAVANI_YOLO_MODE", "1")
    monkeypatch.setenv("SAFE_VAR", "hello")
    env = _sandbox_env()
    assert "OPENAI_API_KEY" not in env
    assert "XAVANI_YOLO_MODE" not in env
    assert env["SAFE_VAR"] == "hello"


def test_env_strips_path_and_home():
    env = _sandbox_env()
    assert "PATH" not in env or env["PATH"] == "/usr/bin:/bin"
    assert "HOME" not in env or env["HOME"] == "/tmp"


def test_env_sandbox_marker():
    env = _sandbox_env()
    assert env.get("XAVANI_PLUGIN_SANDBOX") == "1"


def test_sandbox_env_snapshot():
    assert isinstance(sandbox_env_snapshot(), dict)


# ── execution ──────────────────────────────────────────────────────


def test_run_plugin_success(tmp_path):
    plugin = _write_plugin(tmp_path, "print('plugin ran')\n")
    result = run_plugin_in_sandbox(plugin)
    assert result["ok"] is True
    assert "plugin ran" in result["stdout"]
    assert result["exit_code"] == 0


def test_run_plugin_failure_exit_code(tmp_path):
    plugin = _write_plugin(tmp_path, "import sys; sys.exit(3)\n")
    result = run_plugin_in_sandbox(plugin)
    assert result["ok"] is False
    assert result["exit_code"] == 3


def test_run_plugin_args_passed(tmp_path):
    plugin = _write_plugin(tmp_path, "import sys; print(sys.argv[1])\n")
    result = run_plugin_in_sandbox(plugin, args=["hello-arg"])
    assert "hello-arg" in result["stdout"]


def test_missing_main_py(tmp_path):
    empty = tmp_path / "no-entry"
    empty.mkdir()
    result = run_plugin_in_sandbox(empty)
    assert result["ok"] is False
    assert "no main.py" in result["error"]


def test_timeout_enforced(tmp_path):
    plugin = _write_plugin(tmp_path, "import time; time.sleep(30)\n")
    result = run_plugin_in_sandbox(plugin, timeout_seconds=1)
    assert result["ok"] is False
    assert "timeout" in result["error"]


def test_plugin_has_no_secrets_in_env(tmp_path):
    os.environ["OPENAI_API_KEY"] = "sk-should-not-leak"
    plugin = _write_plugin(
        tmp_path,
        "import os; print(os.environ.get('OPENAI_API_KEY', 'CLEAN'))\n",
    )
    result = run_plugin_in_sandbox(plugin)
    assert "CLEAN" in result["stdout"]
    assert "sk-should-not-leak" not in result["stdout"]


def test_plugin_workdir_is_isolated(tmp_path):
    plugin = _write_plugin(tmp_path, "import os; print(os.getcwd())\n")
    result = run_plugin_in_sandbox(plugin)
    assert result["ok"] is True
    assert "xavani-sandbox" in result["stdout"]
