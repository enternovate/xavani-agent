# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

from pathlib import Path
from unittest.mock import patch
import pytest

pytestmark = pytest.mark.integration


def test_pip_install_detected_when_no_git_dir(tmp_path):
    """When PROJECT_ROOT has no .git, detect as pip install."""
    with patch("xavani_cli.config.get_managed_system", return_value=None), \
         patch("xavani_cli.config.get_xavani_home", return_value=tmp_path):
        from xavani_cli.config import detect_install_method
        method = detect_install_method(project_root=tmp_path)
        assert method == "pip"


def test_git_install_detected_when_git_dir_exists(tmp_path):
    """When PROJECT_ROOT has .git, detect as git install."""
    (tmp_path / ".git").mkdir()
    with patch("xavani_cli.config.get_managed_system", return_value=None), \
         patch("xavani_cli.config.get_xavani_home", return_value=tmp_path):
        from xavani_cli.config import detect_install_method
        method = detect_install_method(project_root=tmp_path)
        assert method == "git"


def test_managed_install_takes_precedence(tmp_path):
    """When XAVANI_MANAGED is set, that takes precedence over git detection."""
    (tmp_path / ".git").mkdir()
    with patch("xavani_cli.config.get_managed_system", return_value="NixOS"), \
         patch("xavani_cli.config.get_xavani_home", return_value=tmp_path):
        from xavani_cli.config import detect_install_method
        method = detect_install_method(project_root=tmp_path)
        assert method == "nixos"


def test_recommended_update_command_pip():
    """Pip installs recommend pip install --upgrade."""
    from xavani_cli.config import recommended_update_command_for_method
    cmd = recommended_update_command_for_method("pip")
    assert "pip install" in cmd or "uv pip install" in cmd
    assert "--upgrade" in cmd
    assert "xavani-agent" in cmd


def test_stamp_file_takes_precedence(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".install_method").write_text("docker\n")
    with patch("xavani_cli.config.get_managed_system", return_value=None), \
         patch("xavani_cli.config.get_xavani_home", return_value=tmp_path):
        from xavani_cli.config import detect_install_method
        assert detect_install_method(project_root=tmp_path) == "docker"


def test_docker_detected_via_dockerenv(tmp_path):
    with patch("xavani_cli.config.get_managed_system", return_value=None), \
         patch("xavani_cli.config.get_xavani_home", return_value=tmp_path), \
         patch("xavani_constants.is_container", return_value=True):
        from xavani_cli.config import detect_install_method
        assert detect_install_method(project_root=tmp_path) == "docker"


def test_recommended_update_command_docker():
    from xavani_cli.config import recommended_update_command_for_method
    assert "docker pull" in recommended_update_command_for_method("docker")
