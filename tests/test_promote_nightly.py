# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the nightly channel promotion helper (backlog H190)."""

import json
import subprocess
import sys
from pathlib import Path

from scripts.promote_nightly import _changelog_has_version, _summary_green

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_summary(path: Path, passed: int, failed: int) -> Path:
    path.write_text(json.dumps({"passed": passed, "failed": failed}), encoding="utf-8")
    return path


def _make_repo(tmp_path: Path, version: str, changelog: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "xavani-agent"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    if changelog:
        (repo / "CHANGELOG.md").write_text(f"## [{version}]\n\n- nightly test\n", encoding="utf-8")
    return repo


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, timeout=30)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True, timeout=30)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True, timeout=30)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, timeout=30)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, timeout=30)


def test_summary_green_accepts_zero_failures(tmp_path):
    path = _write_summary(tmp_path / "s.json", passed=100, failed=0)

    assert _summary_green(path) is True


def test_summary_green_rejects_failures(tmp_path):
    path = _write_summary(tmp_path / "s.json", passed=99, failed=1)

    assert _summary_green(path) is False


def test_summary_green_rejects_empty_run(tmp_path):
    path = _write_summary(tmp_path / "s.json", passed=0, failed=0)

    assert _summary_green(path) is False


def test_changelog_has_version(tmp_path):
    repo = _make_repo(tmp_path, "1.2.3")

    assert _changelog_has_version(repo, "1.2.3") is True
    assert _changelog_has_version(repo, "9.9.9") is False


def test_dry_run_refuses_failed_summary(tmp_path):
    repo = _make_repo(tmp_path, "0.1.0")
    _init_git(repo)
    summary = _write_summary(tmp_path / "s.json", passed=10, failed=2)

    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "promote_nightly.py"),
         "--summary", str(summary), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 1
    assert "refusing promote" in proc.stdout


def test_dry_run_refuses_missing_changelog_entry(tmp_path):
    repo = _make_repo(tmp_path, "0.1.0", changelog=False)
    _init_git(repo)
    summary = _write_summary(tmp_path / "s.json", passed=10, failed=0)

    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "promote_nightly.py"),
         "--summary", str(summary), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 1
    assert "CHANGELOG.md" in proc.stdout


def test_dry_run_refuses_duplicate_version_tag(tmp_path):
    repo = _make_repo(tmp_path, "0.1.0")
    _init_git(repo)
    subprocess.run(["git", "tag", "-a", "nightly-0.1.0-20260810", "-m", "x"],
                   cwd=repo, check=True, timeout=30)
    summary = _write_summary(tmp_path / "s.json", passed=10, failed=0)

    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "promote_nightly.py"),
         "--summary", str(summary), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 1
    assert "already exists" in proc.stdout


def test_execute_creates_tag(tmp_path):
    repo = _make_repo(tmp_path, "0.2.0")
    _init_git(repo)
    summary = _write_summary(tmp_path / "s.json", passed=10, failed=0)

    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "promote_nightly.py"),
         "--summary", str(summary), "--repo", str(repo), "--execute"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0
    assert "created tag nightly-0.2.0-" in proc.stdout
    tags = subprocess.run(["git", "tag", "--list", "nightly-*"], cwd=repo,
                          capture_output=True, text=True, timeout=30).stdout
    assert "nightly-0.2.0-" in tags
