---
title: "Perf Profiling — Profile and optimise application performance systematically — measure first, optimise second"
sidebar_label: "Perf Profiling"
description: "Profile and optimise application performance systematically — measure first, optimise second"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Perf Profiling

Profile and optimise application performance systematically — measure first, optimise second.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/perf-profiling` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Performance Profiling

> "Premature optimisation is the root of all evil — but premature pessimation is worse."

## When to use

- Application is slow or uses too much memory/CPU.
- Latency is above acceptable thresholds.
- Before optimising: profile first to find the bottleneck.

## Prerequisites

- A reproducible slow path.
- Baseline measurements.

## Steps

### 1. Measure the baseline

```bash
# Python
python -m cProfile -o profile.prof your_script.py

# Node.js
node --prof your_script.js

# Go
go test -bench=. -cpuprofile=cpu.prof

# Rust
cargo bench
```

Record: execution time, memory usage, CPU usage.

### 2. Identify the hot path

Use the profiler output to find:
- Functions consuming >20% of total time.
- Unexpected allocations (memory profiling).
- I/O waits vs CPU-bound work.

### 3. Analyse the bottleneck

Ask:
- Is it algorithmic? (O(n²) where O(n) is possible)
- Is it I/O? (blocking on network/disk)
- Is it allocation? (too many temporary objects)
- Is it lock contention? (threads waiting)

### 4. Optimise the bottleneck

Apply the smallest change that addresses the root cause:
- Algorithmic: change the algorithm.
- I/O: batch, cache, or parallelise.
- Allocation: reuse objects, use pools.
- Contention: reduce lock scope, use lock-free structures.

### 5. Verify the improvement

Re-run the same benchmark. Record:
- New execution time.
- Improvement percentage.
- Any regressions in other areas.

### 6. Document

Record what you found, what you changed, and the measured improvement.

## Verification

- Baseline and optimised measurements are recorded.
- Improvement is measured, not guessed.
- No regressions in other areas.
