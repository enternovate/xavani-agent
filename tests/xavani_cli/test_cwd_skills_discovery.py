# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for automatic discovery of project-scoped ``.xavani/skills`` dirs."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def xavani_home(tmp_path):
    """Create a minimal XAVANI_HOME with an empty local skills dir."""
    home = tmp_path / "xavani-home"
    (home / "skills").mkdir(parents=True)
    return home


class TestGetCwdSkillsDir:
    def test_no_cwd_skills_dir_returns_none(self, tmp_path):
        from agent.skill_utils import get_cwd_skills_dir

        start = tmp_path / "project"
        start.mkdir(parents=True)
        assert get_cwd_skills_dir(start=start, home=tmp_path) is None

    def test_finds_nearest_ancestor(self, tmp_path):
        from agent.skill_utils import get_cwd_skills_dir

        proj = tmp_path / "project"
        (proj / ".xavani" / "skills").mkdir(parents=True)
        start = proj / "sub" / "deep"
        start.mkdir(parents=True)
        result = get_cwd_skills_dir(start=start, home=tmp_path)
        assert result == (proj / ".xavani" / "skills").resolve()

    def test_nearest_wins_over_higher(self, tmp_path):
        from agent.skill_utils import get_cwd_skills_dir

        (tmp_path / ".xavani" / "skills").mkdir(parents=True)
        proj = tmp_path / "project"
        (proj / ".xavani" / "skills").mkdir(parents=True)
        result = get_cwd_skills_dir(start=proj, home=tmp_path)
        assert result == (proj / ".xavani" / "skills").resolve()

    def test_stops_before_home(self, tmp_path):
        """The home-level dir is the local catalog (get_skills_dir), not cwd scope."""
        from agent.skill_utils import get_cwd_skills_dir

        (tmp_path / ".xavani" / "skills").mkdir(parents=True)
        start = tmp_path / "project"
        start.mkdir(parents=True)
        assert get_cwd_skills_dir(start=start, home=tmp_path) is None

    def test_default_start_is_getcwd(self, tmp_path):
        from agent.skill_utils import get_cwd_skills_dir

        proj = tmp_path / "project"
        (proj / ".xavani" / "skills").mkdir(parents=True)
        with patch("os.getcwd", return_value=str(proj)):
            result = get_cwd_skills_dir(home=tmp_path)
        assert result == (proj / ".xavani" / "skills").resolve()

    def test_walk_stops_at_filesystem_root(self, tmp_path):
        from agent.skill_utils import get_cwd_skills_dir

        start = tmp_path / "project"
        start.mkdir(parents=True)
        assert get_cwd_skills_dir(start=start, home=tmp_path / "missing") is None

    def test_ignores_plain_xavani_dir_without_skills(self, tmp_path):
        from agent.skill_utils import get_cwd_skills_dir

        proj = tmp_path / "project"
        (proj / ".xavani").mkdir(parents=True)
        assert get_cwd_skills_dir(start=proj, home=tmp_path) is None


class TestGetAllSkillsDirsIntegration:
    def test_builtin_catalog_unchanged_without_cwd_dir(self, xavani_home, tmp_path):
        proj = tmp_path / "project"
        proj.mkdir()
        with (
            patch.dict(os.environ, {"XAVANI_HOME": str(xavani_home)}),
            patch("os.getcwd", return_value=str(proj)),
        ):
            from agent.skill_utils import get_all_skills_dirs

            result = get_all_skills_dirs()
        assert result == [xavani_home / "skills"]

    def test_cwd_skills_dir_appended(self, xavani_home, tmp_path):
        proj = tmp_path / "project"
        (proj / ".xavani" / "skills").mkdir(parents=True)
        with (
            patch.dict(os.environ, {"XAVANI_HOME": str(xavani_home)}),
            patch("os.getcwd", return_value=str(proj)),
        ):
            from agent.skill_utils import get_all_skills_dirs

            result = get_all_skills_dirs()
        assert result == [
            xavani_home / "skills",
            (proj / ".xavani" / "skills").resolve(),
        ]

    def test_cwd_dir_appended_after_external_dirs(self, xavani_home, tmp_path):
        ext = tmp_path / "ext-skills"
        ext.mkdir()
        (xavani_home / "config.yaml").write_text(
            f"skills:\n  external_dirs:\n    - {ext}\n"
        )
        proj = tmp_path / "project"
        (proj / ".xavani" / "skills").mkdir(parents=True)
        with (
            patch.dict(os.environ, {"XAVANI_HOME": str(xavani_home)}),
            patch("os.getcwd", return_value=str(proj)),
        ):
            from agent.skill_utils import get_all_skills_dirs

            result = get_all_skills_dirs()
        assert result == [
            xavani_home / "skills",
            ext.resolve(),
            (proj / ".xavani" / "skills").resolve(),
        ]

    def test_cwd_dir_duplicate_of_local_skipped(self, xavani_home):
        from agent import skill_utils

        with (
            patch.dict(os.environ, {"XAVANI_HOME": str(xavani_home)}),
            patch(
                "agent.skill_utils.get_cwd_skills_dir",
                return_value=(xavani_home / "skills").resolve(),
            ),
        ):
            result = skill_utils.get_all_skills_dirs()
        assert result == [xavani_home / "skills"]
