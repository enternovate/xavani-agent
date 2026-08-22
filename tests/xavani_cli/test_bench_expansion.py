# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import json

import pytest

from scripts.task_bench import leaderboard, run_bench


@pytest.fixture
def rubric(tmp_path, monkeypatch):
    path = tmp_path / "rubric.txt"
    path.write_text(
        "# rubric\ncontains:alpha\nregex:beta\\d+\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return path


class TestLlmJudgeVerifier:
    def test_rubric_lines_must_all_pass(self, rubric):
        check = run_bench.parse_verifier(f"llm_judge:{rubric}", "t1")
        assert check("alpha beta1") is True
        assert check("alpha only") is False
        assert check("nothing") is False

    def test_missing_rubric_raises(self, tmp_path):
        with pytest.raises(run_bench.BenchError, match="not found"):
            run_bench.parse_verifier(
                f"llm_judge:{tmp_path}/missing.txt", "t2"
            )

    def test_empty_rubric_raises(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("# only comments\n", encoding="utf-8")
        with pytest.raises(run_bench.BenchError, match="no verifier lines"):
            run_bench.parse_verifier(f"llm_judge:{empty}", "t3")

    def test_model_judge_env_adds_verdict(self, rubric, monkeypatch):
        calls = []

        def fake_call_llm(**kwargs):
            calls.append(kwargs)
            return "YES"

        monkeypatch.setenv("XAVANI_BENCH_JUDGE_MODEL", "judge-model")
        monkeypatch.setattr(
            "agent.auxiliary_client.call_llm", fake_call_llm
        )
        check = run_bench.parse_verifier(f"llm_judge:{rubric}", "t4")
        assert check("alpha beta9") is True
        assert calls[0]["model"] == "judge-model"

    def test_model_judge_tolerates_preamble(self, rubric, monkeypatch):
        monkeypatch.setenv("XAVANI_BENCH_JUDGE_MODEL", "judge-model")
        monkeypatch.setattr(
            "agent.auxiliary_client.call_llm",
            lambda **kwargs: "reasoning... final answer: YES",
        )
        check = run_bench.parse_verifier(f"llm_judge:{rubric}", "t4b")
        assert check("alpha beta9") is True

    def test_model_judge_handles_reasoning_only_response(
        self, rubric, monkeypatch
    ):
        from types import SimpleNamespace

        monkeypatch.setenv("XAVANI_BENCH_JUDGE_MODEL", "judge-model")
        monkeypatch.setattr(
            "agent.auxiliary_client.call_llm",
            lambda **kwargs: SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content=None, reasoning="looks correct, so YES"))]
            ),
        )
        check = run_bench.parse_verifier(f"llm_judge:{rubric}", "t4c")
        assert check("alpha beta1") is True

    def test_model_judge_no_rejects(self, rubric, monkeypatch):
        monkeypatch.setenv("XAVANI_BENCH_JUDGE_MODEL", "judge-model")
        monkeypatch.setattr(
            "agent.auxiliary_client.call_llm",
            lambda **kwargs: "after review: NO",
        )
        check = run_bench.parse_verifier(f"llm_judge:{rubric}", "t4d")
        assert check("alpha beta1") is False


class TestPerTaskTimeout:
    def test_load_tasks_accepts_positive_timeout(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_text(
            json.dumps([{"id": "a", "prompt": "p", "verifier": "contains:x",
                         "timeout_seconds": 30}]),
            encoding="utf-8",
        )
        assert run_bench.load_tasks(path)[0]["timeout_seconds"] == 30

    def test_load_tasks_rejects_bad_timeout(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_text(
            json.dumps([{"id": "a", "prompt": "p", "verifier": "contains:x",
                         "timeout_seconds": -5}]),
            encoding="utf-8",
        )
        with pytest.raises(run_bench.BenchError, match="timeout_seconds"):
            run_bench.load_tasks(path)

    def test_parse_verifier_timeout_reaches_subprocess_verifiers(self):
        check = run_bench.parse_verifier("exit_code:0:true", "t5", timeout_s=5)
        assert check("") is True


class TestSummary:
    def test_p95_and_per_category_medians(self):
        results = [
            {"category": "a", "success": True, "wall_seconds": 1.0,
             "total_tokens": 0, "estimated_cost_usd": 0.0},
            {"category": "a", "success": True, "wall_seconds": 3.0,
             "total_tokens": 0, "estimated_cost_usd": 0.0},
            {"category": "b", "success": False, "wall_seconds": 10.0,
             "total_tokens": 0, "estimated_cost_usd": 0.0},
        ]
        summary = run_bench.summarize_results(results)
        assert summary["p95_wall_seconds"] == pytest.approx(9.3)
        assert summary["per_category_median_wall_seconds"] == {"a": 2.0, "b": 10.0}

    def test_category_carries_into_results(self):
        task = {"id": "x", "category": "coding", "prompt": "p",
                "verifier": "contains:x", "faux_response": "x"}
        result = run_bench.run_task(task, faux=True)
        assert result["category"] == "coding"


class TestFlakeRuns:
    def test_unstable_tasks_dropped_and_listed(self, monkeypatch):
        task = {"id": "x", "prompt": "p", "verifier": "contains:x",
                "faux_response": "x"}
        flips = iter([True, False, True, False])

        def fake_run_task(task, **kwargs):
            return {"id": task["id"], "category": "general",
                    "success": next(flips), "wall_seconds": 0.1,
                    "total_tokens": 0, "estimated_cost_usd": 0.0,
                    "prompt_tokens": 0, "completion_tokens": 0,
                    "api_calls": 0, "response_chars": 1, "error": None}

        monkeypatch.setattr(run_bench, "run_task", fake_run_task)
        payload = run_bench.run_benchmark([task], runs=2)
        assert payload["unstable_ids"] == ["x"]
        assert payload["results"] == []

    def test_stable_tasks_survive(self, monkeypatch):
        task = {"id": "x", "prompt": "p", "verifier": "contains:x",
                "faux_response": "x"}
        monkeypatch.setattr(
            run_bench, "run_task",
            lambda task, **kwargs: {
                "id": "x", "category": "general", "success": True,
                "wall_seconds": 0.1, "total_tokens": 0,
                "estimated_cost_usd": 0.0, "prompt_tokens": 0,
                "completion_tokens": 0, "api_calls": 0,
                "response_chars": 1, "error": None,
            },
        )
        payload = run_bench.run_benchmark([task], runs=3)
        assert payload["unstable_ids"] == []
        assert len(payload["results"]) == 1


class TestCategoryFilterAndFingerprint:
    def test_category_filter_main(self, capsys):
        code = run_bench.main(["--faux", "--category", "coding"])
        assert code == 0
        assert "median[coding]" in capsys.readouterr().out

    def test_category_filter_empty_errors(self, capsys):
        code = run_bench.main(["--faux", "--category", "no-such-cat"])
        assert code == 2

    def test_config_fingerprint_stable(self):
        payload = {"tasks_file": "t.json", "mode": "faux", "model": None,
                   "provider": None, "runs": 1}
        assert run_bench.config_fingerprint(payload) == run_bench.config_fingerprint(payload)
        assert len(run_bench.config_fingerprint(payload)) == 8

    def test_save_writes_fingerprinted_file(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(run_bench, "RESULTS_DIR", tmp_path / "results")
        code = run_bench.main(["--faux", "--save"])
        assert code == 0
        files = list((tmp_path / "results").glob("*.json"))
        assert len(files) == 1
        assert len(files[0].stem.split("_")[-1]) == 8


class TestLeaderboard:
    def test_ranks_by_cost_per_success(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "cheap.json").write_text(json.dumps({
            "mode": "faux", "model": "m1",
            "summary": {"task_count": 2, "success_rate": 1.0,
                        "median_wall_seconds": 0.1,
                        "cost_per_successful_task_usd": 0.001},
        }), encoding="utf-8")
        (results_dir / "pricey.json").write_text(json.dumps({
            "mode": "live", "model": "m2",
            "summary": {"task_count": 2, "success_rate": 0.5,
                        "median_wall_seconds": 5.0,
                        "cost_per_successful_task_usd": 0.5},
        }), encoding="utf-8")
        (results_dir / "corrupt.json").write_text("{bad", encoding="utf-8")
        rows = leaderboard.load_rankings(results_dir)
        assert [r["model"] for r in rows] == ["m1", "m2"]
        rendered = leaderboard.render_rankings(rows)
        assert "cheap.json" in rendered and "corrupt" not in rendered

    def test_missing_cost_sorts_last(self, tmp_path):
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "nocost.json").write_text(json.dumps({
            "mode": "faux", "summary": {"task_count": 1,
                                        "success_rate": 0.0,
                                        "median_wall_seconds": 1.0,
                                        "cost_per_successful_task_usd": None},
        }), encoding="utf-8")
        rows = leaderboard.load_rankings(results_dir)
        assert rows[0]["cost_per_successful_task_usd"] is None

    def test_main_empty_dir(self, tmp_path, capsys):
        assert leaderboard.main(["--results-dir", str(tmp_path / "none")]) == 0
