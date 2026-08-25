"""Pre-compress transcript checkpoint tests.

Before context compression mutates the conversation, a durable JSON
snapshot of the transcript must land on disk. When snapshot writing
fails and the gate is required, compression is BLOCKED (fail closed)
instead of risking silent context loss.
"""

import json

import agent.conversation_compression as cc


class TestSnapshotPath:
    def test_snapshot_written(self, tmp_path, monkeypatch):
        captured = {}
        monkeypatch.setattr(cc, "_transcript_checkpoint_dir", lambda: tmp_path)
        monkeypatch.setattr(
            cc, "_write_snapshot_file",
            lambda path, payload: captured.update(path=path, payload=payload) or True,
        )
        ok = cc.write_transcript_snapshot({"session": "s1"}, messages=[{"role": "user", "content": "hi"}])
        assert ok is True
        assert captured["payload"]["messages"] == [{"role": "user", "content": "hi"}]
        assert captured["payload"]["session"] == "s1"

    def test_failed_write_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cc, "_transcript_checkpoint_dir", lambda: tmp_path)
        monkeypatch.setattr(cc, "_write_snapshot_file", lambda path, payload: False)
        assert cc.write_transcript_snapshot(None, messages=[]) is False


class TestGate:
    def _agent(self):
        a = type("A", (), {})()
        a.session_id = "sess-1"
        a.model = "m"
        a._emit_status = lambda *_a, **_k: None
        return a

    def test_gate_blocks_when_required_and_fails(self, monkeypatch):
        monkeypatch.setenv("XAVANI_COMPRESS_CHECKPOINT", "required")
        monkeypatch.setattr(cc, "write_transcript_snapshot", lambda *a, **k: False)
        agent = self._agent()
        assert cc.ensure_pre_compress_snapshot(agent, [{"role": "user"}]) is False

    def test_gate_passes_on_success(self, monkeypatch):
        monkeypatch.delenv("XAVANI_COMPRESS_CHECKPOINT", raising=False)
        monkeypatch.setattr(cc, "write_transcript_snapshot", lambda *a, **k: True)
        agent = self._agent()
        assert cc.ensure_pre_compress_snapshot(agent, [{"role": "user"}]) is True

    def test_default_best_effort_never_blocks(self, monkeypatch):
        monkeypatch.delenv("XAVANI_COMPRESS_CHECKPOINT", raising=False)
        monkeypatch.setattr(cc, "write_transcript_snapshot", lambda *a, **k: False)
        agent = self._agent()
        # Default mode: failure logged but not blocking.
        assert cc.ensure_pre_compress_snapshot(agent, [{"role": "user"}]) is True
