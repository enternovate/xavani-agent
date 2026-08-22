# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from xavani_cli import handoff_writer


SECTIONS = {
    "title": "Session Handoff — demo",
    "processes": [
        {"pid": "123", "description": "bench run", "output": "results/", "eta": "~1h"},
    ],
    "outputs": ["logs/run.log", "results/master.json"],
    "state_done": ["audit complete"],
    "state_pending": ["wire /macro command"],
    "decisions": ["serial children only"],
    "preferences": ["quality over speed"],
    "resume_prompt": 'continue 0.2.0 plan from handoff',
}


class TestRender:
    def test_renders_all_sections(self):
        text = handoff_writer.render_handoff(SECTIONS)
        assert "# Session Handoff — demo" in text
        assert "| 123 | bench run | results/ | ~1h |" in text
        assert "- [x] audit complete" in text
        assert "- [ ] wire /macro command" in text
        assert "- serial children only" in text
        assert "```" in text
        assert "continue 0.2.0 plan from handoff" in text

    def test_empty_sections_render_title_only(self):
        text = handoff_writer.render_handoff({})
        assert text.strip() == "# Session Handoff"

    def test_date_defaults_when_written(self, tmp_path):
        path = handoff_writer.write_handoff(tmp_path / "SESSION_HANDOFF.md", {})
        body = path.read_text(encoding="utf-8")
        assert "Date: " in body

    def test_ends_with_single_newline(self):
        text = handoff_writer.render_handoff({"title": "t"})
        assert text.endswith("\n") and not text.endswith("\n\n")


class TestWriteHandoff:
    def test_never_overwrites(self, tmp_path):
        first = handoff_writer.write_handoff(tmp_path / "H.md", {"title": "one"})
        second = handoff_writer.write_handoff(tmp_path / "H.md", {"title": "two"})
        assert first != second
        assert "one" in first.read_text(encoding="utf-8")
        assert "two" in second.read_text(encoding="utf-8")

    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "deep" / "nest" / "H.md"
        written = handoff_writer.write_handoff(target, SECTIONS)
        assert written.is_file()

    def test_collect_session_state(self):
        state = handoff_writer.collect_session_state(
            project_path="/repo", extra_decisions=["d1"]
        )
        assert state["project_path"] == "/repo"
        assert state["decisions"] == ["d1"]
