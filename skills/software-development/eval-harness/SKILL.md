---
name: eval-harness
description: Define, run, and report evaluation cases. Build the eval first — define what success looks like before writing code. Use before and after changes to verify behaviour.
categories:
  - software-development
  - testing
platforms:
  - all
tags:
  - testing
  - evaluation
  - quality
  - tdd
condition: Before writing any new feature or fix, or when verifying a change didn't break existing behaviour.
---

# Eval Harness — Build the Eval First

> "If you cannot measure it, you cannot improve it." — Karpathy

## When to use

- Before writing a new feature: define what "works" means as eval cases.
- After a refactor: run evals to verify behaviour is preserved.
- When debugging: capture the failing case as an eval, then fix until it passes.
- Before declaring a task done: run the eval suite and show the pass rate.

## Prerequisites

- The `eval_harness` tool must be available (registered in `tools/registry.py`).
- Evals are stored as JSON files under `~/.xavani/evals/`.

## Steps

### 1. Create an eval set

```json
{"action": "create", "name": "my-feature-eval", "description": "Evaluates the new parser"}
```

### 2. Add cases

```json
{
  "action": "add",
  "name": "my-feature-eval",
  "case_id": "basic-input",
  "input": "hello world",
  "expected": "HELLO WORLD"
}
```

For complex assertions:
```json
{
  "action": "add",
  "name": "my-feature-eval",
  "case_id": "json-valid",
  "input": "{\"key\": \"value\"}",
  "assertion": "import json; json.loads(output) == {'key': 'value'}"
}
```

### 3. Run the eval

```json
{"action": "run", "name": "my-feature-eval"}
```

### 4. Review results

The tool returns a structured report:
```
total: 10, passed: 9, failed: 1, pass_rate: 90.0%
```

### 5. Iterate

Fix the failing case, re-run, until 100% pass rate (or document known failures).

## Examples

**Pre-feature eval:**
1. Create eval set for the feature.
2. Add 3-5 cases covering normal, edge, and error inputs.
3. Run eval — expect 0% pass (no implementation yet).
4. Implement the feature.
5. Run eval — target 100% pass.

**Post-refactor verification:**
1. Run existing eval set.
2. If pass rate drops, the refactoring broke something.
3. Investigate and fix before committing.

## Verification

- Every eval set has at least 3 cases (normal, edge, error).
- Pass rate is reported as a concrete percentage.
- Failing cases show the actual output alongside the expected.
