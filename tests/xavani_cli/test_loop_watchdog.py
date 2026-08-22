# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import json

import pytest

from xavani_cli import loop_runner, loop_watchdog


@pytest.fixture
def loops_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_LOOPS_DIR", str(tmp_path / "loops"))
    return tmp_path / "loops"


def _spec(**overrides):
    defaults: dict = {
        "prompt": "check the build",
        "max_passes": 3,
    }
    defaults.update(overrides)
    return loop_runner.new_loop(**defaults)


class TestBuildPassPrompt:
    def test_includes_prompt_failure_notes_and_previous_output(self):
        spec = _spec()
        loop_runner.record_failure_note(spec, "port 8080 busy")
        spec["passes"] = [{"output": "build still red"}]
        prompt = loop_watchdog.build_pass_prompt(spec)
        assert prompt.startswith("check the build")
        assert "- port 8080 busy" in prompt
        assert "<previous_output>" in prompt
        assert "build still red" in prompt


class TestTick:
    def test_runs_one_pass_and_persists_telemetry(self, loops_dir):
        spec = _spec()
        result = loop_watchdog.tick(spec["id"], pass_fn=lambda p: "pass one done")
        assert result["action"] == "ran"
        reloaded = loop_runner.load(spec["id"])
        assert len(reloaded["passes"]) == 1
        assert reloaded["passes"][0]["output"] == "pass one done"
        assert reloaded["status"] == "active"

    def test_records_error_output_when_pass_fn_raises(self, loops_dir):
        spec = _spec()

        def boom(prompt):
            raise RuntimeError("model offline")

        result = loop_watchdog.tick(spec["id"], pass_fn=boom)
        assert result["action"] == "ran"
        reloaded = loop_runner.load(spec["id"])
        assert "pass error" in reloaded["passes"][0]["output"]

    def test_finalizes_when_max_passes_reached(self, loops_dir, monkeypatch):
        spec = _spec(max_passes=1)
        removed = []
        monkeypatch.setattr(
            "cron.jobs.remove_job", lambda job_id: removed.append(job_id)
        )
        result = loop_watchdog.tick(spec["id"], pass_fn=lambda p: "only pass")
        assert result["action"] == "completed"
        assert "max passes" in result["reason"]
        reloaded = loop_runner.load(spec["id"])
        assert reloaded["status"] == "completed"

    def test_runaway_identical_passes_finalize(self, loops_dir, monkeypatch):
        spec = _spec(max_passes=10)
        for output in ("same", "same"):
            spec["passes"].append({"n": 1, "ts": 0.0, "output": output,
                                   "duration_s": 0.0, "cost_usd": 0.0})
        loop_runner.save(spec)
        result = loop_watchdog.tick(spec["id"], pass_fn=lambda p: "same")
        assert result["action"] == "completed"
        assert "runaway" in result["reason"]

    def test_finished_spec_removes_job_without_new_pass(self, loops_dir, monkeypatch):
        spec = _spec()
        spec["status"] = "stopped"
        spec["cron_job_id"] = "job123"
        loop_runner.save(spec)
        removed = []
        monkeypatch.setattr(
            "cron.jobs.remove_job", lambda job_id: removed.append(job_id)
        )
        calls = []

        def spy(prompt):
            calls.append(prompt)
            return "should not run"

        result = loop_watchdog.tick(spec["id"], pass_fn=spy)
        assert result["action"] == "finished"
        assert removed == ["job123"]
        assert not calls


class TestWrapperScriptSource:
    def test_source_invokes_main_with_loop_id(self):
        source = loop_watchdog.wrapper_script_source("loop-1")
        assert "from xavani_cli import loop_watchdog" in source
        assert "'loop-1'" in source or '"loop-1"' in source


class TestMain:
    def test_main_silent_while_running(self, loops_dir, capsys):
        spec = _spec()
        code = loop_watchdog.main([spec["id"], "--dir", str(loops_dir)])
        assert code == 0
        assert capsys.readouterr().out == ""

    def test_main_prints_alert_json_when_finished(self, loops_dir, capsys):
        spec = _spec(max_passes=1)
        code = loop_watchdog.main([spec["id"], "--dir", str(loops_dir)])
        assert code == 0
        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert payload["action"] == "completed"

    def test_main_unknown_loop_exits_nonzero(self, loops_dir, capsys):
        code = loop_watchdog.main(["loop-missing", "--dir", str(loops_dir)])
        assert code == 1
