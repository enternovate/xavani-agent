# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C07: tool auto-discovery.

Discovers tools from all sources with provenance tracking and
idempotence:

- builtin self-registering modules (tools/*.py)
- declarative user tools in ``$XAVANI_HOME/tools/*.yaml``
- plugin-registered tools (via PluginContext)

Declarative YAML tools are the new surface (C07): a user drops a small
YAML file describing a shell command tool and it appears in the
registry with an honest schema. Provenance means every discovered tool
records WHERE it came from — a discovered tool is never silently
trusted.

Usage::

    from tools.auto_discovery import discover_all_tools, load_user_tools

    load_user_tools(registry)          # declarative YAML tools
    discovered = discover_all_tools()  # provenance report
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

USER_TOOLS_DIR_NAME = "tools"
# Keys a declarative tool manifest must provide.
_REQUIRED_KEYS = ("name", "description", "command")


@dataclass
class DiscoveryRecord:
    """One discovered tool and its provenance."""

    name: str
    source: str          # "builtin" | "user-yaml" | "plugin"
    path: Optional[str] = None
    ok: bool = True
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "path": self.path,
            "ok": self.ok,
            "error": self.error,
        }


def user_tools_dir(home: Optional[Path] = None) -> Path:
    """Resolve the declarative user tools directory."""
    if home is not None:
        return home / USER_TOOLS_DIR_NAME
    xavani_home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return xavani_home / USER_TOOLS_DIR_NAME


def _validate_manifest(data: Dict[str, Any], source_path: Path) -> str:
    """Validate a declarative tool manifest. Returns an error string."""
    for key in _REQUIRED_KEYS:
        if not data.get(key):
            return f"missing required key '{key}' in {source_path}"
    name = str(data["name"]).strip()
    if not name or any(ch.isspace() for ch in name):
        return f"invalid tool name '{name}' in {source_path}"
    command = str(data["command"]).strip()
    if not command:
        return f"empty command in {source_path}"
    return ""


def _load_declarative(path: Path, registry) -> DiscoveryRecord:
    """Load one YAML tool file into the registry."""
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return DiscoveryRecord(
                name=path.stem, source="user-yaml", path=str(path),
                ok=False, error="manifest is not a mapping",
            )
        error = _validate_manifest(data, path)
        if error:
            return DiscoveryRecord(
                name=path.stem, source="user-yaml", path=str(path),
                ok=False, error=error,
            )
        name = str(data["name"]).strip()
        # Register a shell-call tool with an honest schema.
        registry.register(
            name=name,
            toolset="user",
            schema={
                "name": name,
                "description": str(data["description"]).strip(),
                "parameters": {
                    "type": "object",
                    "properties": {"args": {"type": "string"}},
                    "required": [],
                },
            },
            handler=_make_declarative_handler(name, str(data["command"])),
            check_fn=lambda: True,
        )
        return DiscoveryRecord(
            name=name, source="user-yaml", path=str(path), ok=True,
        )
    except Exception as exc:
        return DiscoveryRecord(
            name=path.stem, source="user-yaml", path=str(path),
            ok=False, error=str(exc),
        )


def _make_declarative_handler(name: str, command: str):
    """Build a handler that shells out to the declarative command.

    The command runs with ``shlex.split``; the tool's ``args`` string is
    appended verbatim. Timeout and working dir come from the process
    environment, never from the manifest (manifest input is untrusted).
    """

    def _handler(args: Dict[str, Any]) -> Dict[str, Any]:
        import tempfile

        user_args = str((args or {}).get("args", "") or "")
        parts = shlex.split(command) + shlex.split(user_args)
        if not parts:
            return {"error": f"tool {name}: empty command"}
        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {"error": f"tool {name}: command timed out after 120s"}
        except OSError as exc:
            return {"error": f"tool {name}: {exc}"}
        return {
            "stdout": result.stdout[:200_000],
            "stderr": result.stderr[:50_000],
            "exit_code": result.returncode,
        }

    return _handler


def load_user_tools(registry, home: Optional[Path] = None) -> List[DiscoveryRecord]:
    """Load every declarative YAML tool under the user tools dir.

    Returns a discovery record per file (ok=True or ok=False with an
    error). Never raises — a bad tool file must not break startup.
    """
    tools_dir = user_tools_dir(home)
    records: List[DiscoveryRecord] = []
    if not tools_dir.is_dir():
        return records
    for path in sorted(tools_dir.glob("*.yaml")) + sorted(tools_dir.glob("*.yml")):
        records.append(_load_declarative(path, registry))
    return records


def discover_all_tools(
    registry,
    home: Optional[Path] = None,
    *,
    include_builtin: bool = True,
) -> List[DiscoveryRecord]:
    """Discover tools from all sources; return provenance records."""
    records: List[DiscoveryRecord] = []

    if include_builtin:
        try:
            from tools.registry import discover_builtin_tools

            for mod_name in discover_builtin_tools():
                records.append(
                    DiscoveryRecord(name=mod_name, source="builtin", ok=True)
                )
        except Exception as exc:
            logger.warning("builtin tool discovery failed: %s", exc)

    records.extend(load_user_tools(registry, home=home))
    return records
