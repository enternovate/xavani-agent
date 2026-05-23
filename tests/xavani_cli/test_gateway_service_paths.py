# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

from pathlib import Path
from unittest.mock import patch


def test_service_path_skips_nonexistent_node_modules(tmp_path):
    """Service PATH should not include node_modules/.bin if it doesn't exist."""
    from xavani_cli.gateway import _build_service_path_dirs
    with patch("xavani_cli.gateway.get_xavani_home", return_value=tmp_path / ".xavani"):
        dirs = _build_service_path_dirs(project_root=tmp_path)
    node_modules_bin = str(tmp_path / "node_modules" / ".bin")
    assert node_modules_bin not in dirs


def test_service_path_includes_node_modules_when_present(tmp_path):
    """Service PATH should include node_modules/.bin when it exists."""
    nm_bin = tmp_path / "node_modules" / ".bin"
    nm_bin.mkdir(parents=True)
    from xavani_cli.gateway import _build_service_path_dirs
    with patch("xavani_cli.gateway.get_xavani_home", return_value=tmp_path / ".xavani"):
        dirs = _build_service_path_dirs(project_root=tmp_path)
    assert str(nm_bin) in dirs


def test_service_path_includes_xavani_home_node_modules(tmp_path):
    """Service PATH should include ~/.xavani/node_modules/.bin when it exists."""
    xavani_nm = tmp_path / ".xavani" / "node_modules" / ".bin"
    xavani_nm.mkdir(parents=True)
    from xavani_cli.gateway import _build_service_path_dirs
    with patch("xavani_cli.gateway.get_xavani_home", return_value=tmp_path / ".xavani"):
        dirs = _build_service_path_dirs(project_root=tmp_path)
    assert str(xavani_nm) in dirs
