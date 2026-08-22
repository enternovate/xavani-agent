# Task Bench Authoring Guide

How to add tasks to `tasks/baseline_tasks.json` and verify them.

## Task schema

```json
{
  "id": "unique-task-id",
  "category": "coding|extraction|summarization|planning|file|business",
  "prompt": "The exact user prompt sent to the agent.",
  "verifier": "contains:expected substring",
  "faux_response": "Scripted reply used only in --faux mode.",
  "timeout_seconds": 120
}
```

- `id` must be unique across the file.
- `category` powers `--category` filtering and per-category medians. Pick
  one of the six listed values; use `general` only when nothing fits.
- `faux_response` is REQUIRED in practice: every task needs a faux-mode
  test asserting the verifier passes on the scripted output.
- `timeout_seconds` (default 120) bounds subprocess verifiers
  (`pytest:`, `exit_code:`).

## Verifier types

| Prefix | Meaning |
|---|---|
| `contains:<text>` | response includes text |
| `regex:<pattern>` | Python regex search hits |
| `jsonschema:<schema JSON>` | response parses as JSON and validates |
| `pytest:<node-id>` | named test passes with response at BENCH_RESPONSE_FILE |
| `exit_code:<N>:<command>` | command exits N; response arrives on stdin |
| `llm_judge:<rubric-file>` | every verifier line in the rubric file passes |

Rubric files (one verifier line per line, `#` comments allowed) live in
`rubrics/`. Set `XAVANI_BENCH_JUDGE_MODEL=<model>` to add a model yes/no
verdict on top of the deterministic rubric lines.

## Gates

1. `python3 -m scripts.task_bench.run_bench --faux` — all tasks pass offline.
2. `python3 -m pytest tests/xavani_cli/ -q -k bench` — verifier unit tests.
3. `python3 -m scripts.task_bench.regression_gate baseline.json current.json`
   — no median or cost-per-success regression over 10%.

## Storing results

`--save` writes to `results/<timestamp>_<fingerprint>.json`. Compare and
rank stored configs with `python3 -m scripts.task_bench.leaderboard`.
