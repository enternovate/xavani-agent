# Testing Guide

## Running tests

Use the repo venv and `python3 -m pytest` (never the bare `pytest`):

```bash
source .venv/bin/activate
python3 -m pytest tests/xavani_cli/ -q
```

The default addopts deselect integration tests (`-m 'not integration'`),
run tests in parallel (`-n auto`), and apply a 60s timeout.

## Marker taxonomy

Every test file carries one of three markers:

| Marker | Meaning |
|--------|---------|
| `unit` | Fast tests. No I/O beyond pure logic. Mocks replace real subsystems. |
| `integration` | Tests that touch a real subsystem: network, filesystem, sqlite, subprocess, websocket, real provider clients. |
| `e2e` | Full CLI/agent loop tests: spawn the CLI, drive a full conversation, exercise the web server. |

Rules:

- One `pytestmark` per file when every test shares the tier.
- Per-test marks only when a file mixes tiers.
- Merge with existing marks: `pytestmark = [pytest.mark.skipif(...), pytest.mark.unit]`.
- Unknown markers fail collection. Register any new marker in
  `pyproject.toml` under `[tool.pytest.ini_options] markers`.

## Where the tiers live

- `tests/run_agent/` — loop core. Mostly unit; `*_live.py` files are e2e.
- `tests/tools/` — tool implementations. Unit when the tool logic is pure,
  integration when it drives a real backend.
- `tests/xavani_cli/` — CLI behavior. Unit for parsers and pure helpers,
  integration for config/auth/store paths, e2e for spawned CLI processes.

## Quarantine and special markers

- `flaky` — timing-sensitive tests in `tests/flaky/`. They run but never
  block CI.
- `long_running` — tests that exceed the 30s global timeout by design.
- `forked` — tests that need a real forked subprocess (pytest-forked).
- `live_system_guard_bypass` — deliberate bypass of the live-system guard.

Do not add new special markers. Register them only if a pre-existing test
already uses one.
