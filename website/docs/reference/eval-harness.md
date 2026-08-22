---
sidebar_position: 7
title: "Eval Harness"
description: "Eval Harness — Xavani 0.2.0 reference"
---

# Eval Harness

The task benchmark measures wall time, tokens, cost, and success rate
per task. Optimization targets: lowest cost per successful task and
median wall time under 100 seconds.

## Commands
```
/eval --faux                 # in-session, offline
python3 -m scripts.task_bench.run_bench --faux
python3 -m scripts.task_bench.run_bench --category coding
python3 -m scripts.task_bench.run_bench --runs 2      # flake check
python3 -m scripts.task_bench.run_bench --save        # fingerprinted results
python3 -m scripts.task_bench.leaderboard             # rank stored configs
python3 -m scripts.task_bench.regression_gate a.json b.json
```

## Verifier types
`contains:` `regex:` `jsonschema:` `pytest:` `exit_code:` and
`llm_judge:<rubric-file>`. See
`scripts/task_bench/README.md` for the full task-authoring guide.

## Scorecard
Every run reports pass count, median/p90/p95 wall time, per-category
medians, mean tokens, total cost, and cost per successful task.
