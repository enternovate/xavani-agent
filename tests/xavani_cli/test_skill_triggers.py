# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from xavani_cli import skill_triggers


class TestParseCondition:
    def test_string_clauses_split_on_semicolon(self):
        fm = {"condition": "cwd-contains:xavani; env:X=1"}
        assert skill_triggers.parse_condition(fm) == [
            "cwd-contains:xavani", "env:X=1",
        ]

    def test_list_form(self):
        assert skill_triggers.parse_condition(
            {"condition": ["a:1", "b:2"]}
        ) == ["a:1", "b:2"]

    def test_absent_condition_is_none(self):
        assert skill_triggers.parse_condition({}) is None
        assert skill_triggers.parse_condition({"condition": ""}) is None


class TestEvaluate:
    def test_cwd_contains(self, tmp_path):
        assert skill_triggers.evaluate_clause(
            "cwd-contains:xavani", cwd=tmp_path / "xavani-agent", env={}
        ) is True
        assert skill_triggers.evaluate_clause(
            "cwd-contains:zzz", cwd=tmp_path, env={}
        ) is False

    def test_env_equals(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAVANI_MODE", "fast")
        assert skill_triggers.evaluate_clause(
            "env:XAVANI_MODE=fast", cwd=tmp_path, env={}
        ) is True
        assert skill_triggers.evaluate_clause(
            "env:XAVANI_MODE=slow", cwd=tmp_path, env={}
        ) is False

    def test_file_exists(self, tmp_path):
        (tmp_path / "marker.txt").touch()
        assert skill_triggers.evaluate_clause(
            "file-exists:marker.txt", cwd=tmp_path, env={}
        ) is True
        assert skill_triggers.evaluate_clause(
            "file-exists:nope.txt", cwd=tmp_path, env={}
        ) is False

    def test_unknown_clause_fails_closed(self, tmp_path):
        assert skill_triggers.evaluate_clause(
            "magic:yes", cwd=tmp_path, env={}
        ) is False

    def test_all_clauses_and_combined(self, tmp_path):
        (tmp_path / "m.txt").touch()
        fm = {"condition": "file-exists:m.txt; cwd-contains:zzz"}
        assert skill_triggers.should_autoload(fm, cwd=tmp_path, env={}) is False


class TestEvaluateSkill:
    def test_autoload_true_logged(self, tmp_path):
        (tmp_path / "m.txt").touch()
        log = tmp_path / "triggers.log"
        loaded = skill_triggers.evaluate_skill(
            "my-skill",
            {"condition": "file-exists:m.txt"},
            cwd=tmp_path,
            log_path=log,
        )
        assert loaded is True
        line = log.read_text(encoding="utf-8").strip()
        assert "skill=my-skill autoload=True" in line
        assert "reason=file-exists:m.txt" in line

    def test_no_condition_never_autoloads_but_logs(self, tmp_path):
        log = tmp_path / "triggers.log"
        loaded = skill_triggers.evaluate_skill(
            "plain-skill", {}, cwd=tmp_path, log_path=log
        )
        assert loaded is False
        assert "reason=no-condition" in log.read_text(encoding="utf-8")


class TestReadConditionFromSkill:
    def test_reads_condition_line(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: x\ncondition: cwd-contains:repo\n---\nbody\n",
            encoding="utf-8",
        )
        assert skill_triggers.read_condition_from_skill(skill) == [
            "cwd-contains:repo"
        ]

    def test_none_without_frontmatter(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text("just body\n", encoding="utf-8")
        assert skill_triggers.read_condition_from_skill(skill) is None
