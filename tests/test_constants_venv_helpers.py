from pathlib import Path

from xavani_constants import project_venv_dir, venv_bin_dir


def test_venv_bin_dir_windows_true_returns_scripts(tmp_path):
    assert venv_bin_dir(tmp_path / "venv", windows=True) == tmp_path / "venv" / "Scripts"


def test_venv_bin_dir_windows_false_returns_bin(tmp_path):
    assert venv_bin_dir(tmp_path / "venv", windows=False) == tmp_path / "venv" / "bin"


def test_project_venv_dir_prefers_venv_and_returns_none_when_absent(tmp_path: Path):
    assert project_venv_dir(tmp_path) is None
    dot = tmp_path / ".venv"
    dot.mkdir()
    assert project_venv_dir(tmp_path) == dot
    plain = tmp_path / "venv"
    plain.mkdir()
    assert project_venv_dir(tmp_path) == plain
