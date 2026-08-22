# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import pytest

from xavani_cli import read_schemes


class TestParseScheme:
    def test_pr_and_issue(self):
        assert read_schemes.parse_scheme("pr://enternovate/xavani-agent#12") == {
            "scheme": "pr", "repo": "enternovate/xavani-agent", "number": "12",
        }
        assert read_schemes.parse_scheme("issue://a/b#9") == {
            "scheme": "issue", "repo": "a/b", "number": "9",
        }

    def test_skill(self):
        assert read_schemes.parse_scheme("skill://business-assistant") == {
            "scheme": "skill", "name": "business-assistant",
        }

    def test_non_scheme_returns_none(self):
        assert read_schemes.parse_scheme("/plain/path.txt") is None
        assert read_schemes.parse_scheme("README.md") is None

    def test_bad_refs_raise(self):
        with pytest.raises(read_schemes.SchemeError, match="owner/repo"):
            read_schemes.parse_scheme("pr://just-a-name")
        with pytest.raises(read_schemes.SchemeError, match="skill name"):
            read_schemes.parse_scheme("skill://")


class TestResolve:
    def test_github_fetcher_receives_parts(self):
        seen = {}

        def fake_fetch(scheme, repo, number):
            seen.update({"scheme": scheme, "repo": repo, "number": number})
            return f"text for {scheme} {repo}#{number}"

        out = read_schemes.resolve(
            "pr://o/r#7", fetcher=fake_fetch
        )
        assert seen == {"scheme": "pr", "repo": "o/r", "number": "7"}
        assert out == "text for pr o/r#7"

    def test_skill_fetch_via_root(self, tmp_path):
        skill = tmp_path / "my-skill" / "SKILL.md"
        skill.parent.mkdir()
        skill.write_text("---\nname: my-skill\n---\nbody", encoding="utf-8")
        out = read_schemes.resolve("skill://my-skill", skills_root=tmp_path)
        assert "body" in out

    def test_missing_skill_raises(self, tmp_path):
        with pytest.raises(read_schemes.SchemeError, match="no built-in skill"):
            read_schemes.resolve("skill://ghost", skills_root=tmp_path)

    def test_non_scheme_path_raises(self):
        with pytest.raises(read_schemes.SchemeError, match="not a read-scheme"):
            read_schemes.resolve("plain.txt")


class TestHandles:
    def test_true_for_all_three_schemes(self):
        for path in ("pr://a/b#1", "issue://a/b#2", "skill://x"):
            assert read_schemes.handles(path)

    def test_false_otherwise(self):
        assert not read_schemes.handles("file:///etc/hosts")
