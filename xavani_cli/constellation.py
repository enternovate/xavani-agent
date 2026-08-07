"""The ``xavani constellation`` command: install, status, update, doctor.

Manages the Enternovate constellation companion tools: the nyarhi,
gavaza, and mhangani CLIs plus the constellation MCP server bundle.
Everything runs locally. Only ``install`` and ``update`` touch the
network; the other subcommands are fully offline.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

#: Packages installed by ``xavani constellation install``.
CONSTELLATION_PACKAGES = ("constellation-mcp", "nyarhi", "gavaza", "mhangani")

#: Console scripts the constellation ships.
CLI_BINARIES = ("nyarhi", "gavaza", "mhangani", "constellation-mcp")

#: The MCP server name Xavani uses in config.yaml.
MCP_SERVER_NAME = "constellation"


def _probe_version(binary: str) -> str | None:
    """Return the version line of ``binary``, or None when missing."""
    path = shutil.which(binary)
    if path is None:
        return None
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "installed (version probe failed)"
    output = (proc.stdout or proc.stderr).strip()
    if not output:
        return "installed"
    return output.splitlines()[0][:80]


def _status_rows() -> list[dict[str, str | bool]]:
    """Probe every constellation CLI and return one row per binary."""
    rows: list[dict[str, str | bool]] = []
    for binary in CLI_BINARIES:
        version = _probe_version(binary)
        rows.append(
            {
                "binary": binary,
                "installed": version is not None,
                "version": version or "not found",
            }
        )
    return rows


def _mcp_config_state() -> dict[str, object]:
    """Read the constellation MCP server entry from the Xavani config."""
    try:
        from xavani_cli.config import load_config

        config = load_config()
    except Exception:  # noqa: BLE001 - report unreadable config as unconfigured
        return {"configured": False, "command": ""}
    servers = config.get("mcp_servers", {}) if isinstance(config, dict) else {}
    entry = servers.get(MCP_SERVER_NAME) if isinstance(servers, dict) else None
    if not isinstance(entry, dict) or not entry.get("command"):
        return {"configured": False, "command": ""}
    return {"configured": True, "command": str(entry.get("command", ""))}


def _pip_install(upgrade: bool) -> int:
    """Install the constellation packages with uv or pip.

    Prefers ``uv`` when available, then falls back to the current
    interpreter's pip. Returns the subprocess exit code.
    """
    uv = shutil.which("uv")
    if uv is not None:
        argv = [uv, "pip", "install"]
        if upgrade:
            argv.append("--upgrade")
        argv.extend(CONSTELLATION_PACKAGES)
        print("Running:", " ".join(argv))
        return subprocess.run(argv, check=False).returncode
    argv = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        argv.append("--upgrade")
    argv.extend(CONSTELLATION_PACKAGES)
    print("Running:", " ".join(argv))
    return subprocess.run(argv, check=False).returncode


def _cmd_status(args: argparse.Namespace) -> int:
    """Print the installation state of every constellation CLI."""
    rows = _status_rows()
    print(f"{'Binary':<22} {'Status':<12} Version")
    print("-" * 72)
    for row in rows:
        state = "installed" if row["installed"] else "missing"
        print(f"{row['binary']:<22} {state:<12} {row['version']}")
    missing = [str(row["binary"]) for row in rows if not row["installed"]]
    if missing:
        print()
        print(
            "Missing: "
            + ", ".join(missing)
            + ". Run 'xavani constellation install' to install them."
        )
        return 1
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    """Install the constellation packages into the current environment."""
    return _pip_install(upgrade=False)


def _cmd_update(args: argparse.Namespace) -> int:
    """Upgrade the constellation packages to the latest versions."""
    return _pip_install(upgrade=True)


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Verify the constellation installation and the MCP wiring."""
    problems = 0
    mcp = _mcp_config_state()
    print("MCP server configuration:")
    if mcp["configured"]:
        print(f"  ok: config.yaml declares mcp_servers.{MCP_SERVER_NAME}")
        command = str(mcp["command"])
        resolved = command.split()[0] if command else ""
        if resolved and shutil.which(resolved) is not None:
            print(f"  ok: command '{resolved}' resolves on PATH")
        else:
            print(f"  warn: command '{resolved}' does not resolve on PATH")
            problems += 1
    else:
        print(f"  warn: mcp_servers.{MCP_SERVER_NAME} is not configured")
        print(
            "    Add to ~/.xavani/config.yaml:\n"
            "    mcp_servers:\n"
            "      constellation:\n"
            "        command: constellation-mcp\n"
            "        args: []\n"
            "        env: {}"
        )
        problems += 1
    print()
    print("Constellation CLIs:")
    rows = _status_rows()
    for row in rows:
        state = "ok" if row["installed"] else "missing"
        print(f"  {state}: {row['binary']}")
        if not row["installed"]:
            problems += 1
    if problems:
        print()
        print(
            f"{problems} problem(s) found. Run 'xavani constellation install' "
            "or fix the config, then re-run doctor."
        )
        return 1
    print()
    print("All constellation checks passed.")
    return 0


def cmd_constellation(args: argparse.Namespace) -> int:
    """Dispatch ``xavani constellation`` subcommands."""
    command = getattr(args, "constellation_command", None)
    if command == "status":
        return _cmd_status(args)
    if command == "install":
        return _cmd_install(args)
    if command == "update":
        return _cmd_update(args)
    if command == "doctor":
        return _cmd_doctor(args)
    raise ValueError(f"unknown constellation subcommand: {command!r}")


def build_constellation_parser(parser: argparse.ArgumentParser) -> None:
    """Add the ``xavani constellation`` subcommands to ``parser``."""
    sub = parser.add_subparsers(dest="constellation_command", required=True)
    sub.add_parser("status", help="show installation state of the constellation CLIs")
    sub.add_parser("install", help="install the constellation packages")
    sub.add_parser("update", help="upgrade the constellation packages")
    sub.add_parser("doctor", help="verify the constellation installation and MCP wiring")
