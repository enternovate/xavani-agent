# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""The engine reports one version in three places; they must agree."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def _init_version() -> str:
    from xavani_cli import __version__

    return __version__


def _acp_version() -> str:
    payload = json.loads(
        (REPO_ROOT / "acp_registry" / "agent.json").read_text(encoding="utf-8")
    )
    return payload["version"]


def test_versions_agree() -> None:
    assert _init_version() == _pyproject_version()
    assert _acp_version() == _pyproject_version()
