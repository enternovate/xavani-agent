---
title: v0.4.0 Capabilities
sidebar_label: v0.4.0 Capabilities
---

# v0.4.0 Capabilities

The v0.4.0 line adds a **zero-cost cognition** layer plus several full-stack and
security capabilities. All detection and routing run in pure Python — the model is
used only for generation, never for the agent's own routing or self-governance.

## Deterministic-first (zero-cost cognition)

Xavani never spends an API call on work it can decide locally. This is enforced,
not just encouraged:

- **Deterministic tool pre-filter** (`tools/tool_prefilter.py`) — picks the relevant
  subset of tools for each turn from the user's message using keyword/intent rules,
  shrinking the function-call schema sent to the model and cutting input-token cost.
  It never hides a needed tool: with no clear intent it returns the full set, and
  essentials are always included.
- **Detector registry** (`agent/detectors.py`) — a uniform home for pure-Python
  checks: scrub (no prohibited references), stub-guard, and a secret-leak heuristic.
- **Deterministic skill routing** — the existing skill orchestrator ranks skills by
  keyword/n-gram overlap, with no embeddings and no model call.

The invariant is locked in by `tests/agent/test_deterministic_no_llm.py`, which fails
CI if any detection/routing module imports a model client.

## Cybersecurity skills

A large vendored cybersecurity skill pack lives under
`optional-skills/cybersecurity/`, organized by subdomain and indexed alongside the
other optional skills. Attribution and a reproducible import manifest accompany the
pack.

## MCP server hosting

`tools/mcp_server.py` exposes Xavani's tool registry over the Model Context Protocol,
so any MCP-compatible client can list and call Xavani's tools. Tool schemas are reused
verbatim from the registry, and calls dispatch through the same path the agent uses.

## Document reading

`read_document` (`tools/document_tools.py`) extracts text from `.txt`/`.md`/`.csv`/`.json`
natively and from `.pdf`/`.docx`/`.xlsx`/`.pptx` via optional parsers, returning the text
with its format and character count.

## Sandbox hardening

Local execution can be confined with:

- **Network egress allowlist** (`tools/egress_policy.py`) — restrict outbound hosts,
  with optional default-deny, configured via `XAVANI_EGRESS_ALLOWLIST` /
  `XAVANI_EGRESS_DEFAULT_DENY`.
- **Resource caps** (`tools/sandbox_hardening.py`) — address-space, CPU-time, and
  open-file limits via the OS, never raised above the existing hard cap.
- **Kernel confinement** — seccomp syscall filtering and Landlock filesystem
  confinement are available on Linux (with the appropriate binding) and degrade to a
  clear status on other platforms.

## Governance

A `security` CI workflow runs Bandit, Gitleaks, Semgrep, pip-audit, and Trivy, plus the
deterministic-first invariant. A `.pre-commit-config.yaml` provides matching local
hooks (Ruff, Gitleaks, the R10 check, and a scrub check).
