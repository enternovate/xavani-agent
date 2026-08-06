# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""D07: sandboxed terminal default for ownerless git repos."""

from __future__ import annotations

from tools.terminal_tool import _maybe_sandbox_untrusted_repo, _repo_has_no_owner


class _FakeGit:
    """Injectable git runner: inside-work-tree + identity answers."""

    def __init__(self, inside="true", name="", remote=""):
        self._inside = inside
        self._name = name
        self._remote = remote

    def __call__(self, args):
        if "rev-parse" in args:
            return self._inside
        if "user.name" in args:
            return self._name
        if "remote.origin.url" in args:
            return self._remote
        return None


def test_repo_has_no_owner_true_when_no_identity():
    git = _FakeGit(inside="true", name="", remote="")
    assert _repo_has_no_owner("/tmp/repo", git_runner=git) is True


def test_repo_has_no_owner_false_when_name_configured():
    git = _FakeGit(inside="true", name="Alice", remote="")
    assert _repo_has_no_owner("/tmp/repo", git_runner=git) is False


def test_repo_has_no_owner_false_when_remote_configured():
    git = _FakeGit(inside="true", name="", remote="https://github.com/x/y.git")
    assert _repo_has_no_owner("/tmp/repo", git_runner=git) is False


def test_repo_has_no_owner_false_outside_repo():
    git = _FakeGit(inside="false", name="", remote="")
    assert _repo_has_no_owner("/tmp/plain", git_runner=git) is False


def test_maybe_sandbox_escalates_ownerless_repo():
    git = _FakeGit(inside="true", name="", remote="")
    assert _maybe_sandbox_untrusted_repo(
        "local", "/tmp/repo", docker_available=True, git_runner=git
    ) == "docker"


def test_maybe_sandbox_keeps_local_when_docker_missing():
    git = _FakeGit(inside="true", name="", remote="")
    assert _maybe_sandbox_untrusted_repo(
        "local", "/tmp/repo", docker_available=False, git_runner=git
    ) == "local"


def test_maybe_sandbox_keeps_local_for_owned_repo():
    git = _FakeGit(inside="true", name="Alice", remote="")
    assert _maybe_sandbox_untrusted_repo(
        "local", "/tmp/repo", docker_available=True, git_runner=git
    ) == "local"


def test_maybe_sandbox_keeps_non_local_env():
    git = _FakeGit(inside="true", name="", remote="")
    assert _maybe_sandbox_untrusted_repo(
        "docker", "/tmp/repo", docker_available=True, git_runner=git
    ) == "docker"


def test_get_env_config_escalates_with_TERMINAL_CWD(monkeypatch, tmp_path):
    import tools.terminal_tool as tt
    from tools.terminal_tool import _get_env_config

    monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
    monkeypatch.setattr(
        tt,
        "_maybe_sandbox_untrusted_repo",
        lambda env_type, cwd: "docker" if env_type == "local" else env_type,
    )
    assert _get_env_config()["env_type"] == "docker"


def test_get_env_config_opt_out_skips_escalation(monkeypatch, tmp_path):
    import tools.terminal_tool as tt
    from tools.terminal_tool import _get_env_config

    monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
    monkeypatch.setenv("XAVANI_UNTRUSTED_REPO_SANDBOX", "0")
    monkeypatch.setattr(
        tt,
        "_maybe_sandbox_untrusted_repo",
        lambda env_type, cwd: (_ for _ in ()).throw(
            AssertionError("escalation must be skipped when opted out")
        ),
    )
    assert _get_env_config()["env_type"] == "local"


def test_get_env_config_no_TERMINAL_CWD_skips_escalation(monkeypatch):
    import tools.terminal_tool as tt
    from tools.terminal_tool import _get_env_config

    monkeypatch.delenv("TERMINAL_CWD", raising=False)
    monkeypatch.setattr(
        tt,
        "_maybe_sandbox_untrusted_repo",
        lambda env_type, cwd: (_ for _ in ()).throw(
            AssertionError("escalation must be skipped without TERMINAL_CWD")
        ),
    )
    assert _get_env_config()["env_type"] == "local"
