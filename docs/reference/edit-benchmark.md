# Edit Format Benchmark

> Harness: `scripts/edit_benchmark/runner.py` — measures edit pass rate,
> retries, and approximate tokens for each edit wire format, through the
> real tool path (`tools/edit_tool.py`), against a fixed task suite.

## Run

```bash
# Deterministic fake-mode baseline (no API key needed, CI-safe)
python3 scripts/edit_benchmark/runner.py --mode hashline --model fake
python3 scripts/edit_benchmark/runner.py --mode patch    --model fake
python3 scripts/edit_benchmark/runner.py --mode replace  --model fake

# Live-model comparison (needs a key)
XAVANI_EDIT_MODEL=<model> XAVANI_API_KEY=<key> \
  python3 scripts/edit_benchmark/runner.py --mode hashline --model live
```

## Task suite

20 tasks in `tasks.jsonl`, covering: single/multi-line replace, insert,
append tail, function rewrite, decorated-function rewrite, move between
files, markdown section edit, JSX component edit, docstring edit, and
more. Each task records the original, the exact target, and a canned
payload per mode (fake mode uses the canned payloads; live mode asks a
real model to produce the payload).

## Baseline results — 2026-08-10 (fake mode, deterministic payloads)

| mode     | pass | total | retries | tokens (est) |
|----------|------|-------|---------|--------------|
| hashline | 20/20|  20   |   0     |  300         |
| patch    | 20/20|  20   |   0     |  876         |
| replace  | 20/20|  20   |   0     |  687         |

Interpretation: fake mode proves the harness applies each format
end-to-end through the real tool path; it is NOT a model-capability
comparison. Live-model runs will fill the table with real pass rates per
format (the omp recipe: hashline lifts weak models most, e.g. Grok Code
Fast 1 6.7% -> 68.3%, and collapses output tokens).

## Notes

- Token estimate = `chars/4` of the payload (cheap approximation, labeled
  `token_estimate: chars/4`).
- `--max-tasks N` limits the suite; `--max-retries N` bounds re-attempts.
- Unknown mode exits 2 (argparse usage error); a missing tasks file exits
  1 with a JSON error.
- The `ok`/`success` contract: patch mode reports `success`, replace and
  hashline report `ok`; the runner normalizes both.
