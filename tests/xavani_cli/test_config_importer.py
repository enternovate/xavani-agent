# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from pathlib import Path

import pytest

from xavani_cli import config_importer

CLAUDE_MD = """# My Rules

Always run tests before committing.

- Use ruff for linting
- *Never* push to main directly
1. Keep functions short

```python
print("not a rule")
```

<!-- a comment to skip -->
"""

CURSORRULES = """# comment line
Always answer in STE English.
Never collect telemetry.

"""


class TestDetectFormat:
    def test_markdown_sources(self):
        assert config_importer.detect_format("CLAUDE.md") == "markdown"
        assert config_importer.detect_format("/a/b/AGENTS.md") == "markdown"

    def test_plaintext_sources(self):
        assert config_importer.detect_format(".cursorrules") == "plaintext"
        assert config_importer.detect_format(".windsurfrules") == "plaintext"

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            config_importer.detect_format("README.txt")


class TestParseRules:
    def test_markdown_extracts_lists_and_paragraphs_skips_fences(self):
        rules = config_importer.parse_rules(CLAUDE_MD, "markdown")
        assert "Always run tests before committing." in rules
        assert "Use ruff for linting" in rules
        assert "Never push to main directly" in rules
        assert all("print" not in r for r in rules)
        assert all("a comment to skip" not in r for r in rules)

    def test_markdown_strips_emphasis_edges(self):
        rules = config_importer.parse_rules(CLAUDE_MD, "markdown")
        assert "*Never* push" not in " ".join(rules)

    def test_plaintext_skips_comments_and_blanks(self):
        rules = config_importer.parse_rules(CURSORRULES, "plaintext")
        assert rules == [
            "Always answer in STE English.",
            "Never collect telemetry.",
        ]

    def test_dedupes_preserving_order(self):
        rules = config_importer.parse_rules(
            "- rule a\n- rule a\n- rule b\n", "markdown"
        )
        assert rules == ["rule a", "rule b"]

    def test_caps_long_rules(self):
        long_rule = "x" * 500
        rules = config_importer.parse_rules(f"- {long_rule}\n", "markdown")
        assert len(rules[0]) == config_importer.MAX_RULE_LENGTH + 3
        assert rules[0].endswith("...")

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown format"):
            config_importer.parse_rules("x", "yaml")


class TestSlugify:
    def test_unique_via_index_prefix(self):
        a = config_importer.slugify("Same text", 0)
        b = config_importer.slugify("Same text", 1)
        assert a != b
        assert a.startswith("rule-000-")

    def test_max_length_and_charset(self):
        slug = config_importer.slugify("Ünïcode & symbols!! " * 3, 2)
        assert len(slug) <= config_importer.MAX_SLUG_LENGTH + len("rule-002-")
        assert slug == slug.lower()
        assert all(c.isalnum() or c == "-" for c in slug)


class TestToSkillEntries:
    def test_provenance_comment_present(self):
        entries = config_importer.to_skill_entries(["be honest"], "CLAUDE.md")
        content = entries[0]["content"]
        assert content.startswith("be honest\n\n<!-- imported from CLAUDE.md on ")
        assert "-->" in content


class TestImportAndWrite:
    def test_end_to_end_claude_md(self, tmp_path):
        source = tmp_path / "CLAUDE.md"
        source.write_text(CLAUDE_MD, encoding="utf-8")
        entries = config_importer.import_rules(str(source))
        assert len(entries) >= 3
        assert all("imported from" in e["content"] for e in entries)

    def test_write_skills_writes_and_reports_skipped(self, tmp_path):
        entries = config_importer.to_skill_entries(
            ["rule one", "rule two"], "CLAUDE.md"
        )
        out = tmp_path / "skills"
        written, skipped = config_importer.write_skills(entries, out)
        assert len(written) == 2
        assert skipped == []
        body = written[0].read_text(encoding="utf-8")
        assert body.startswith("---\nname: ")
        written2, skipped2 = config_importer.write_skills(entries, out)
        assert written2 == []
        assert sorted(skipped2) == sorted(e["name"] for e in entries)

    def test_write_skills_creates_nested_dirs(self, tmp_path):
        out = tmp_path / "a" / "b" / "skills"
        entries = config_importer.to_skill_entries(["rule"], "x.md")
        written, _ = config_importer.write_skills(entries, out)
        assert written[0].is_file()
