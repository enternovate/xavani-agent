# Evaluation home rig (Task 25)

This rig drives the reliability task corpus against real models and records
provider response metadata for the model matrix report.

## Components

- `bench-capture/` — a Xavani plugin. It appends one JSON line per API call
  (requested model, served model, usage, finish reason, timing) to the file
  named by `XAVANI_BENCH_META`.
- `setup_eval_home.sh` — creates an isolated evaluation home.

## Setup

```sh
bash scripts/task_bench/eval_home/setup_eval_home.sh /tmp/xavani-bench-home
```

The script copies the active config and credentials into the target home
and installs the plugin. Secret values are never printed.

## Run one evaluation pass

```sh
python3 scripts/task_bench/reliability_check.py seed-all
XAVANI_HOME=/tmp/xavani-bench-home \
XAVANI_BENCH_META=/tmp/bench/meta-<model>.jsonl \
XAVANI_BENCH_EVIDENCE=/tmp/bench/evidence-<model>.jsonl \
python3 -m scripts.task_bench.run_bench \
  scripts/task_bench/tasks/reliability_tasks.json \
  --model <model-id> --resolve-runtime --out /tmp/bench/run-<model>.json
```

- `--resolve-runtime` resolves credentials, base URL, and api_mode from the
  active config, like the CLI does.
- The check script resets each task workspace after every run, so
  repetitions start from the same fixture state.
- Evidence lines (verdict plus flags) land in `XAVANI_BENCH_EVIDENCE`; per
  call provider metadata lands in `XAVANI_BENCH_META`.
- Run three repetitions per task and model, each as its own invocation.

## Notes

- Use an isolated `XAVANI_HOME` only. Sweep any processes you start.
- Faux mode (`--faux`) checks response text only; it executes no tools.
