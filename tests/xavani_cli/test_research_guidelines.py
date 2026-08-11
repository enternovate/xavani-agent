# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for :mod:`xavani_cli.research_guidelines`.

Two test surfaces:

* **Unit tests** drive the loader against synthetic guideline files in
  ``tmp_path`` so we can exercise frontmatter validation, priority
  sorting, malformed-file handling, and the cache-reload semantics
  hermetically.
* **Integration tests** assert that the *real* bundled pack
  (``skills/research-guidelines/``) discovers all twenty-one mandatory
  thinkers and that the composed system-prompt block contains every
  one of them — so a missing file in the bundle is caught by CI rather
  than at first agent boot.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xavani_cli import research_guidelines as rg
from xavani_cli.research_guidelines import (
    Guideline,
    REQUIRED_FRONTMATTER_FIELDS,
    compose_system_prompt_block,
    get_guideline,
    guideline_dir,
    list_guideline_names,
    load_mandatory_guidelines,
)

pytestmark = pytest.mark.integration


EXPECTED_THINKERS = (
    "karpathy-guidelines",
    "lecun-guidelines",
    "hinton-guidelines",
    "sutskever-guidelines",
    "olah-guidelines",
    "hassabis-guidelines",
    "hamming-guidelines",
    "knuth-guidelines",
    "popper-guidelines",
    "polya-guidelines",
    "tukey-guidelines",
    "chollet-guidelines",
    "weng-guidelines",
    "huyen-guidelines",
    "yan-guidelines",
    "beck-guidelines",
    "hickey-guidelines",
    "fowler-guidelines",
    "carmack-guidelines",
    "kernighan-pike-guidelines",
    "dijkstra-guidelines",
)


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    """Clear the module-level cache between tests."""
    rg._cached = None  # type: ignore[attr-defined]
    yield
    rg._cached = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Integration — the real bundled pack
# ---------------------------------------------------------------------------


class TestBundledPack:
    def test_directory_exists(self) -> None:
        assert guideline_dir().is_dir(), f"missing pack at {guideline_dir()}"

    def test_all_eleven_thinkers_loaded(self) -> None:
        names = set(list_guideline_names())
        missing = set(EXPECTED_THINKERS) - names
        assert not missing, f"missing mandatory guidelines: {sorted(missing)}"

    def test_priority_ordering(self) -> None:
        items = load_mandatory_guidelines()
        priorities = [g.priority for g in items]
        assert priorities == sorted(priorities, reverse=True), (
            "guidelines must be returned in descending priority order"
        )

    def test_karpathy_is_highest_priority(self) -> None:
        items = load_mandatory_guidelines()
        assert items[0].name == "karpathy-guidelines"
        assert items[0].priority >= max(g.priority for g in items[1:])

    def test_every_bundled_guideline_is_mandatory(self) -> None:
        for g in load_mandatory_guidelines():
            assert g.mandatory is True, f"{g.name} is not mandatory"

    def test_frontmatter_complete(self) -> None:
        for g in load_mandatory_guidelines():
            for field in REQUIRED_FRONTMATTER_FIELDS:
                assert field in g.raw_frontmatter, (
                    f"{g.name} is missing required field {field!r}"
                )

    def test_sources_populated(self) -> None:
        """Every guideline should cite at least one source."""
        for g in load_mandatory_guidelines():
            assert g.sources, f"{g.name} has no `sources:` field"

    def test_system_prompt_block_mentions_every_thinker(self) -> None:
        block = compose_system_prompt_block()
        for name in EXPECTED_THINKERS:
            assert name in block, f"composed block missing {name!r}"


# ---------------------------------------------------------------------------
# Unit — synthetic guidelines under tmp_path
# ---------------------------------------------------------------------------


def _write_guideline(
    directory: Path,
    name: str,
    *,
    priority: int = 50,
    mandatory: bool = True,
    domain: str = "test",
    description: str = "synthetic test guideline",
    sources: tuple = ("synthetic",),
    body: str = "Body text.",
) -> Path:
    sources_yaml = "\n".join(f"  - {s}" for s in sources) or "  []"
    text = (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"domain: {domain}\n"
        f"mandatory: {str(mandatory).lower()}\n"
        f"priority: {priority}\n"
        "version: 1.0\n"
        "sources:\n" + sources_yaml + "\n"
        "---\n\n"
        + body
        + "\n"
    )
    path = directory / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


class TestLoaderUnit:
    def test_priority_descending(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_guideline(tmp_path, "alpha-guidelines", priority=10)
        _write_guideline(tmp_path, "bravo-guidelines", priority=80)
        _write_guideline(tmp_path, "charlie-guidelines", priority=80)
        monkeypatch.setattr(rg, "guideline_dir", lambda: tmp_path)
        rg._cached = None  # type: ignore[attr-defined]
        items = load_mandatory_guidelines()
        assert [g.name for g in items] == [
            "bravo-guidelines",
            "charlie-guidelines",
            "alpha-guidelines",
        ]

    def test_skips_non_mandatory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_guideline(tmp_path, "keep-guidelines", priority=10, mandatory=True)
        _write_guideline(tmp_path, "drop-guidelines", priority=20, mandatory=False)
        monkeypatch.setattr(rg, "guideline_dir", lambda: tmp_path)
        rg._cached = None  # type: ignore[attr-defined]
        names = {g.name for g in load_mandatory_guidelines()}
        assert names == {"keep-guidelines"}

    def test_malformed_frontmatter_is_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_guideline(tmp_path, "ok-guidelines", priority=10)
        bad = tmp_path / "bad-guidelines.md"
        bad.write_text("no frontmatter here\n", encoding="utf-8")
        monkeypatch.setattr(rg, "guideline_dir", lambda: tmp_path)
        rg._cached = None  # type: ignore[attr-defined]
        names = {g.name for g in load_mandatory_guidelines()}
        assert names == {"ok-guidelines"}

    def test_missing_required_field_is_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = tmp_path / "missing-priority-guidelines.md"
        bad.write_text(
            "---\n"
            "name: missing-priority-guidelines\n"
            "description: x\n"
            "domain: x\n"
            "mandatory: true\n"
            "version: 1.0\n"
            "---\n\nbody\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(rg, "guideline_dir", lambda: tmp_path)
        rg._cached = None  # type: ignore[attr-defined]
        assert load_mandatory_guidelines() == ()

    def test_reload_invalidates_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_guideline(tmp_path, "v1-guidelines", priority=10)
        monkeypatch.setattr(rg, "guideline_dir", lambda: tmp_path)
        rg._cached = None  # type: ignore[attr-defined]

        first = load_mandatory_guidelines()
        assert {g.name for g in first} == {"v1-guidelines"}

        _write_guideline(tmp_path, "v2-guidelines", priority=20)
        cached = load_mandatory_guidelines()
        assert cached == first, "cache should be returned without reload=True"

        refreshed = load_mandatory_guidelines(reload=True)
        assert {g.name for g in refreshed} == {"v1-guidelines", "v2-guidelines"}

    def test_get_guideline_lookup(self) -> None:
        karpathy = get_guideline("karpathy-guidelines")
        assert karpathy is not None
        assert "Karpathy" in karpathy.body

        # Case-insensitive
        assert get_guideline("KARPATHY-GUIDELINES") is karpathy

        # Unknown
        assert get_guideline("nonexistent") is None
        assert get_guideline("") is None

    def test_headline_falls_back_to_description(self) -> None:
        guideline = Guideline(
            name="t",
            description="fallback description",
            domain="test",
            mandatory=True,
            priority=1,
            version="1.0",
            sources=(),
            body="",
            path=Path("/tmp/x"),
        )
        assert guideline.headline == "fallback description"


# ---------------------------------------------------------------------------
# Compose block
# ---------------------------------------------------------------------------


class TestComposeBlock:
    def test_empty_when_no_guidelines(self) -> None:
        assert compose_system_prompt_block(guidelines=()) == ""

    def test_includes_header_and_priority(self) -> None:
        block = compose_system_prompt_block()
        assert "Mandatory Research Guidelines" in block
        assert "priority 100" in block  # Karpathy
        assert "ai-engineering" in block
