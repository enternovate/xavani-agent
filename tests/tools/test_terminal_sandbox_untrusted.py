"""Tests for D07 — sandboxed terminal default for untrusted (ownerless) repos.

D07: when TERMINAL_CWD points at a git repo with no owner (no user.name,
no remote.origin.url), local execution escalates to the docker sandbox by
default. Fails open when docker is unavailable. Opt out with
XAVANI_UNTRUSTED_REPO_SANDBOX=0.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional
from unittest.mock import patch

import pytest

from tools.terminal_tool import _get_env_config, _maybe_sandbox_untrusted_repo, _repo_has_no_owner


class _FakeRunner:
    """Git runner stub: returns canned stdout per command."""

    def __init__(self, inside: str = "true", name: str = "", remote: str = "") -> None:
        self._inside = inside
        self._name = name
        self._remote = remote
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> Optional[str]:
        self.calls.append(args)
        joined = " ".join(args)
        if "rev-parse" in joined:
            return self._inside
        if "user.name" in joined:
            return self._name or None
        if "remote.origin.url" in joined:
            return self._remote or None
        return None


class TestRepoHasNoOwner:
    def test_not_a_git_repo(self) -> None:
        runner = _FakeRunner(inside="false")
        assert _repo_has_no_owner("/tmp/x", git_runner=runner) is False

    def test_ownerless_repo_detected(self) -> None:
        runner = _FakeRunner(inside="true", name="", remote="")
        assert _repo_has_no_owner("/tmp/x", git_runner=runner) is True

    def test_named_repo_has_owner(self) -> None:
        runner = _FakeRunner(inside="true", name="Dev", remote="")
        assert _repo_has_no_owner("/tmp/x", git_runner=runner) is False

    def test_repo_with_remote_has_owner(self) -> None:
        runner = _FakeRunner(inside="true", name="", remote="https://github.com/a/b.git")
        assert _repo_has_no_owner("/tmp/x", git_runner=runner) is False

    def test_git_failure_fails_open(self) -> None:
        runner = _FakeRunner(inside="boom")  # unexpected output counts as not-a-repo
        assert _repo_has_no_owner("/tmp/x", git_runner=runner) is False


class TestMaybeSandboxUntrustedRepo:
    def test_ownerless_repo_escalates_to_docker(self) -> None:
        runner = _FakeRunner(inside="true", name="", remote="")
        assert _maybe_sandbox_untrusted_repo(
            "local", "/tmp/x", docker_available=True, git_runner=runner
        ) == "docker"

    def test_named_repo_stays_local(self) -> None:
        runner = _FakeRunner(inside="true", name="Dev", remote="")
        assert _maybe_sandbox_untrusted_repo(
            "local", "/tmp/x", docker_available=True, git_runner=runner
        ) == "local"

    def test_no_docker_fails_open_to_local(self) -> None:
        runner = _FakeRunner(inside="true", name="", remote="")
        assert _maybe_sandbox_untrusted_repo(
            "local", "/tmp/x", docker_available=False, git_runner=runner
        ) == "local"

    def test_non_local_env_untouched(self) -> None:
        runner = _FakeRunner(inside="true", name="", remote="")
        assert _maybe_sandbox_untrusted_repo(
            "docker", "/tmp/x", docker_available=True, git_runner=runner
        ) == "docker"


class TestGetEnvConfigD07:
    def test_defaults_to_local_when_no_terminal_cwd(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("TERMINAL_CWD", raising=False)
        monkeypatch.setenv("TERMINAL_ENV", "local")
        cfg = _get_env_config()
        assert cfg["env_type"] == "local"

    @patch("tools.terminal_tool._maybe_sandbox_untrusted_repo")
    def test_ownerless_repo_triggers_sandbox(self, mock_escalate, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("TERMINAL_ENV", "local")
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        mock_escalate.return_value = "docker"
        cfg = _get_env_config()
        assert cfg["env_type"] == "docker"
        mock_escalate.assert_called_once()

    @patch("tools.terminal_tool._maybe_sandbox_untrusted_repo")
    def test_opt_out_env_disables_sandbox(self, mock_escalate, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("TERMINAL_ENV", "local")
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        monkeypatch.setenv("XAVANI_UNTRUSTED_REPO_SANDBOX", "0")
        cfg = _get_env_config()
        assert cfg["env_type"] == "local"
        mock_escalate.assert_not_called()
