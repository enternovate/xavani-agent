---
sidebar_position: 6
title: "Loops"
description: "Loops — Xavani 0.2.0 reference"
---

# Loops

The loop engine reruns a task until a stop condition fires.

## Inline loops
```
/loop [passes N] [every S] [budget USD] <prompt>
/loop stop <id>
/loops            # list saved loops
/loops prune [days]
```
Each pass receives the previous output and failure notes (reflexion).
Loops stop on max passes, budget cap, wall-clock limit, user stop, a
success predicate, or three identical outputs (runaway guard). State
persists at `~/.xavani/loops/<id>.json` and survives restarts.

## Watchdog loops
```
/loop watch [every S] [passes N] [budget USD] [alert C] <prompt>
```
A watchdog loop runs on the cron scheduler instead of blocking your
session. Each scheduled tick executes one pass through `xavani -z`.
The job stays silent while the loop runs, delivers a summary alert
when it finishes, and removes itself.

## Eval loops
```
/eval-loop <rubric-file> [threshold F] [passes N] <prompt>
```
Rubric files contain `contains:` and `regex:` verifier lines, one per
line. Each pass gets a score; the loop stops at your threshold.
