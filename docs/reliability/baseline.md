# R1 baseline

## Scope

The owner approves R1 implementation from the saved reliability plan.
Publication requires separate approval.

## Environment

- Inspection date: 2026-09-13.
- Dedicated interpreter: `/Users/andilemushwana/.cache/xavani-r1-venv/bin/python`.
- Python version: 3.11.15.
- Existing agent `.venv`: Python 3.13.13, unchanged.
- Installation: the agent's dev extra and aiohttp 3.14.3.
- The dedicated environment uses an editable agent install.

## Agent baseline

- Commit: `491121d8cfe10fb0aca469e10fed28aa54ccbd65`.
- Original tree: clean.
- Targeted tests: 57 passed.
- Warnings: 22 aiohttp NotAppKeyWarning entries.
- Test duration: 12.73 seconds.
- Remote maximum observed release tag: `v0.3.0`.

Command:

```sh
PYTHONHASHSEED=0 TZ=UTC LANG=C.UTF-8 /Users/andilemushwana/.cache/xavani-r1-venv/bin/python -m pytest -o addopts= -n 0 -q tests/xavani_cli/test_regression_gate.py tests/tools/test_guidelines_gate.py tests/agent/test_self_critique.py tests/agent/test_self_critique_wiring.py tests/gateway/test_api_server_runs.py
```

The direct interpreter preserves Python 3.11 selection.
The repository conftest provides credential and profile isolation.
The canonical shell runner selects the existing Python 3.13 environment.
Do not replace that environment to execute this program.

## Desktop baseline

- Commit: `731c24beeedf107257cbfdd06dbb39e13129b8c5`.
- Python tests: 8 passed in 0.27 seconds.
- JavaScript test file: 1 passed.
- Internal semver assertions: 6 passed.
- Syntax: main.js, preload.js, and renderer app.js pass.
- Existing changes: README.md, CHANGELOG.md, and .hermes/.
- Current package version: 0.3.0.
- Remote maximum observed release tag: v0.4.0.
- The package at v0.4.0 declares 0.4.0.

Do not overwrite those tags or existing document changes.
Do not publish a candidate until the version conflict has a verified resolution.

## Limits

These tests do not prove desktop runtime behavior or real-model quality.
No application or provider session starts for this baseline.
No push or publication occurs.
