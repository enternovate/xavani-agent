# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Windows subprocess compatibility helpers.

Xavani is developed on Linux / macOS and tested natively on Windows too.
Several common subprocess patterns break silently-or-loudly on Windows:

* ``["npm", "install", ...]`` — on Windows ``npm`` is ``npm.cmd``, a batch
  shim.  ``subprocess.Popen(["npm", ...])`` fails with WinError 193
  ("not a valid Win32 application") because CreateProcessW can't run a
  ``.cmd`` file without ``shell=True`` or PATHEXT resolution.

* ``start_new_session=True`` — on POSIX, this maps to ``os.setsid()`` and
  actually detaches the child.  On Windows it's silently ignored; the
  Windows equivalent is ``CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS``
  creationflags, which Python only applies when you pass them explicitly.

* Console-window flashes — every ``subprocess.Popen`` of a ``.exe`` on
  Windows spawns a cmd window briefly unless ``CREATE_NO_WINDOW`` is
  passed.  Cosmetic but jarring for background daemons.

This module centralizes the platform-branching logic so the rest of the
codebase doesn't sprinkle ``if sys.platform == "win32":`` everywhere.

**All helpers are no-ops on non-Windows** — calling them in Linux/macOS
code paths is safe by design.  That's the "do no damage on POSIX"
guarantee.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Mapping, Optional, Sequence

__all__ = [
    "IS_WINDOWS",
    "resolve_node_command",
    "windows_detach_flags",
    "windows_hide_flags",
    "windows_detach_popen_kwargs",
]


IS_WINDOWS = sys.platform == "win32"


# -----------------------------------------------------------------------------
# Node ecosystem launcher resolution
# -----------------------------------------------------------------------------


def resolve_node_command(name: str, argv: Sequence[str]) -> list[str]:
    """Resolve a Node-ecosystem command name to an absolute-path argv.

    On Windows, commands like ``npm``, ``npx``, ``yarn``, ``pnpm``,
    ``playwright``, ``prettier`` ship as ``.cmd`` files (batch shims).
    ``subprocess.Popen(["npm", "install"])`` fails with WinError 193
    because CreateProcessW doesn't execute batch files directly.

    ``shutil.which(name)`` *does* resolve ``.cmd`` via PATHEXT and returns
    the fully-qualified path — which CreateProcessW accepts because the
    extension tells Windows to route through ``cmd.exe /c``.

    On POSIX ``shutil.which`` also returns a fully-qualified path when
    found.  That's a small change from bare-name resolution (the OS does
    its own PATH search) but functionally identical and has the side
    benefit of making the argv reproducible in logs.

    Behavior when the command is not on PATH:
    - On Windows: return the bare name — caller can still try with
      ``shell=True`` as a last resort, OR the subsequent Popen will
      raise FileNotFoundError with a readable error we want to surface.
    - On POSIX: same.  Bare ``npm`` on a Linux box without npm installed
      fails the same way it did before this function existed.

    Args:
        name: The command name to resolve (``npm``, ``npx``, ``node`` …).
        argv: The remaining arguments.  Must NOT include ``name`` itself —
            this function builds the full argv list.

    Returns:
        A list suitable for passing to subprocess.Popen/run/call.
    """
    resolved = shutil.which(name)
    if resolved:
        return [resolved, *argv]
    return [name, *argv]


# -----------------------------------------------------------------------------
# Detached / hidden process creation
# -----------------------------------------------------------------------------


# Win32 CreationFlags — defined here rather than imported from subprocess
# because CREATE_NO_WINDOW and DETACHED_PROCESS aren't guaranteed to be
# present on stdlib subprocess on older Pythons or non-Windows builds.
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_DETACHED_PROCESS = 0x00000008
_CREATE_NO_WINDOW = 0x08000000


def windows_detach_flags() -> int:
    """Return Win32 creationflags that detach a child from the parent
    console and process group.  0 on non-Windows.

    Pair with ``start_new_session=False`` (default) when calling
    subprocess.Popen — on POSIX use ``start_new_session=True`` instead,
    which maps to ``os.setsid()`` in the child.

    Rationale:
    - ``CREATE_NEW_PROCESS_GROUP`` — child has its own process group so
      Ctrl+C in the parent console doesn't propagate.
    - ``DETACHED_PROCESS`` — child has no console at all.  Necessary for
      background daemons (gateway watchers, update respawners) because
      without it, closing the console kills the child.
    - ``CREATE_NO_WINDOW`` — suppress the brief cmd flash that would
      otherwise appear when launching a console app.  Redundant with
      DETACHED_PROCESS but explicit for clarity.
    """
    if not IS_WINDOWS:
        return 0
    return _CREATE_NEW_PROCESS_GROUP | _DETACHED_PROCESS | _CREATE_NO_WINDOW


def windows_hide_flags() -> int:
    """Return Win32 creationflags that merely hide the child's console
    window without detaching the child.  0 on non-Windows.

    Use for short-lived console apps spawned as part of a larger
    operation (``taskkill``, ``where``, version probes) where we want no
    flash but also want to collect stdout/exit code synchronously.

    The key difference from :func:`windows_detach_flags`: NO
    ``DETACHED_PROCESS`` — the child still inherits stdio handles so
    ``capture_output=True`` works.  ``DETACHED_PROCESS`` would sever
    stdio and break stdout capture.
    """
    if not IS_WINDOWS:
        return 0
    return _CREATE_NO_WINDOW


def windows_detach_popen_kwargs() -> dict:
    """Return a dict of Popen kwargs that detach a child on Windows and
    fall back to the POSIX equivalent (``start_new_session=True``) on
    Linux/macOS.

    Usage pattern:

    .. code-block:: python

        subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            **windows_detach_popen_kwargs(),
        )

    This replaces the unsafe-on-Windows pattern:

    .. code-block:: python

        subprocess.Popen(..., start_new_session=True)

    which silently fails to detach on Windows (the flag is accepted but
    has no effect — the child stays attached to the parent's console
    and dies when the console closes).
    """
    if IS_WINDOWS:
        return {"creationflags": windows_detach_flags()}
    return {"start_new_session": True}


def noninteractive_git_env(
    base: "Mapping[str, str] | None" = None,
) -> dict[str, str]:
    """Environment for *internal* git invocations that must never prompt.

    Xavani shells out to git from many non-interactive contexts — MCP catalog
    installs, plugin install/update, profile distribution staging, worktree
    base fetches, desktop review-pane fetch/push. When the remote is private,
    misconfigured, or requires auth, git's default behavior is to prompt on
    the inherited terminal (or via an askpass helper), which silently hangs
    the operation until its timeout — or forever at call sites without one.
    Ported from openai/codex#34540 / #34612 ("detach non-interactive
    subprocesses from stdin"): a background tool invocation must fail fast
    with a readable error, not wait for input nobody can type.

    Returns a copy of ``base`` (default ``os.environ``) with:

    * ``GIT_TERMINAL_PROMPT=0`` — git fails with "terminal prompts disabled"
      instead of prompting for credentials.
    * ``GCM_INTERACTIVE=Never`` — Git Credential Manager (the default
      credential helper on Windows installs) never pops its own dialog.
    * isolated git config — inherited ``GIT_CONFIG_*`` overrides, global/system
      config, pagers, editors, fsmonitor, external diff, and hooks are disabled
      for the child process. A user's repo/global config should not be able to
      hang or mutate Xavani's internal plumbing calls.

    ``GIT_ASKPASS`` / ``SSH_ASKPASS`` are deliberately left alone: when the
    user has a *working* askpass helper or ssh-agent configured, auth should
    still succeed non-interactively. The env only disables paths that block
    on a human.

    Pair with ``stdin=subprocess.DEVNULL`` so git (and any credential helper
    it spawns) also can't read the parent's inherited stdin.

    This is for internal plumbing calls only — the agent-facing terminal tool
    has its own policy layer and user-visible PTY, where prompting can be
    legitimate.
    """
    env = dict(base if base is not None else os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"

    # Do not inherit caller-supplied config injection. We rebuild the
    # GIT_CONFIG_COUNT block below so ambient -c values cannot re-enable
    # pagers, hooks, fsmonitor, editors, or credential prompts.
    for key in list(env):
        if (
            key == "GIT_CONFIG_PARAMETERS"
            or key.startswith("GIT_CONFIG_KEY_")
            or key.startswith("GIT_CONFIG_VALUE_")
        ):
            env.pop(key, None)
    env.pop("GIT_CONFIG_COUNT", None)

    devnull = os.devnull
    env["GIT_CONFIG_GLOBAL"] = devnull
    env["GIT_CONFIG_SYSTEM"] = devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_PAGER"] = "cat"
    env["PAGER"] = "cat"
    env["GIT_EDITOR"] = "true"

    config_overrides = {
        "credential.helper": "",
        "core.askPass": "",
        "core.fsmonitor": "false",
        "core.untrackedCache": "false",
        "core.hooksPath": devnull,
        "core.pager": "cat",
        "core.editor": "true",
        "sequence.editor": "true",
        "diff.external": "",
    }
    env["GIT_CONFIG_COUNT"] = str(len(config_overrides))
    for idx, (key, value) in enumerate(config_overrides.items()):
        env[f"GIT_CONFIG_KEY_{idx}"] = key
        env[f"GIT_CONFIG_VALUE_{idx}"] = value

    return env
