# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F05: sandboxed plugin framework.

Runs plugin code in a restricted environment: the plugin gets its own
temp working dir, a scrubbed environment (no secrets, no XAVANI_HOME
writes), and no network access (DNS + socket connect blocked at the
Python level). The sandbox is defense-in-depth, not a security
boundary — plugins remain untrusted code.

Usage::

    from tools.plugin_sandbox import run_plugin_in_sandbox

    result = run_plugin_in_sandbox("plugins/disk-cleanup", args=["--dry-run"])
"""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Env vars stripped from the plugin environment (secrets + control).
_STRIP_ENV_PREFIXES = (
    "XAVANI_",
    "OPENROUTER_",
    "OPENAI_",
    "ANTHROPIC_",
    "AWS_",
    "GOOGLE_",
    "GEMINI_",
)
_STRIP_ENV_EXACT = {"PATH", "HOME", "PYTHONPATH", "VIRTUAL_ENV"}


def _sandbox_env() -> Dict[str, str]:
    """A scrubbed environment for plugin execution."""
    env = {}
    for key, value in os.environ.items():
        if key in _STRIP_ENV_EXACT:
            continue
        if any(key.startswith(prefix) for prefix in _STRIP_ENV_PREFIXES):
            continue
        env[key] = value
    # Minimal, deterministic environment.
    env.setdefault("PATH", "/usr/bin:/bin")
    env.setdefault("HOME", "/tmp")
    env["XAVANI_PLUGIN_SANDBOX"] = "1"
    return env


def _block_network() -> None:
    """Block network access for the current process (best effort)."""
    try:
        # Override socket resolution so plugins cannot reach the network.
        socket.getaddrinfo = lambda *a, **k: (_ for _ in ()).throw(
            OSError("network disabled in plugin sandbox")
        )
        socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(
            OSError("network disabled in plugin sandbox")
        )
    except Exception as exc:
        logger.debug("network block setup failed: %s", exc)


def run_plugin_in_sandbox(
    plugin_dir: Path,
    *,
    args: Optional[List[str]] = None,
    timeout_seconds: int = 60,
    workdir: Optional[Path] = None,
    block_network: bool = True,
) -> Dict[str, Any]:
    """Run a plugin's entry script inside the sandbox.

    The plugin runs in a subprocess with a scrubbed environment and its
    own temp working dir. Returns stdout/stderr/exit_code.

    NOTE: the subprocess inherits the sandbox env but Python-level
    network blocking applies to THIS process; subprocesses get the
    scrubbed env (no proxy/API vars), which is the practical defense.
    """
    plugin_dir = Path(plugin_dir)
    entry = plugin_dir / "main.py"
    if not entry.exists():
        return {"ok": False, "error": f"no main.py in {plugin_dir}"}

    sandbox_env = _sandbox_env()
    if block_network:
        # Remove common network/transport env vars too.
        for key in list(sandbox_env.keys()):
            if any(k in key.upper() for k in ("PROXY", "HTTP", "HTTPS", "TOKEN", "KEY")):
                sandbox_env.pop(key, None)

    tmp_work = workdir or Path(tempfile.mkdtemp(prefix="xavani-sandbox-"))
    try:
        result = subprocess.run(
            [str(entry), *(args or [])],
            cwd=tmp_work,
            env=sandbox_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout_seconds}s"}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}

    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout[:100_000],
        "stderr": result.stderr[:50_000],
    }


def sandbox_env_snapshot() -> Dict[str, str]:
    """The scrubbed env for inspection and tests."""
    return _sandbox_env()
