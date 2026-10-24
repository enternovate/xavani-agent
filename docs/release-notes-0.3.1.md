# Xavani Agent 0.3.1 — Closure

Date: 2026-10-24

This release closes the 0.3 line. It ships the Omera API and its edge host,
closes every dependency advisory with a published fix, and repairs the CI
defects found in the closure audit.

## Highlights

- Omera API: `GET /health`, `GET /v1/capabilities`, `POST /v1/chat/completions`.
- Keyless research mode answers without provider keys.
- 66 npm advisories to 0 where a fix exists; 19 Python advisories to 0.
- Version reporting is consistent across `pyproject.toml`, `xavani_cli`, and the ACP manifest.
- Docs and planning trees are indexed; closed plans are archived.

## Full detail

See `CHANGELOG.md` and `docs/CLOSURE-0.3.1.md`.

## Known items

- CodeQL needs the `security_events` scope to read or dismiss alerts.
- The real-model reliability matrix stays partial by owner decision (2 of 9 passes).
- Two pre-existing engine tests stay open: the opencode-go model alias assertion and the delegate heartbeat timing budget.
