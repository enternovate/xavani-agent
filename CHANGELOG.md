# Changelog

All notable changes to Xavani Agent are documented in this file.

## [0.3.0] - 2025-05-30

### Added

#### Research Guidelines Enforcement
- Expanded mandatory research guidelines from 11 to 21 thinkers.
- New AI/ML thinkers: Chollet, Weng, Huyen, Yan.
- New software craft thinkers: Beck, Hickey, Fowler, Carmack, Kernighan & Pike, Dijkstra.
- Karpathy guidelines strengthened with 4 operating rules (Think-Before-Coding, Simplicity-First, Surgical-Changes, Goal-Driven-Execution).
- CLI: `xavani guidelines list|show|check` subcommand.
- Pre-ship verification gate tool (`guidelines_gate`).

#### New Tools
- `eval_harness` — define, run, and report evaluation cases.
- `mixture_of_agents` — route problems through multiple models collaboratively.
- `computer_use` — drive screen/keyboard/mouse via MCP server.
- `guidelines_gate` — pre-ship verification against research principles.
- Budget governor — per-session token/cost monitoring with threshold warnings.

#### Cybersecurity Skills (754)
- Full import from mukul975/Anthropic-Cybersecurity-Skills (Apache-2.0).
- Covers: threat hunting, incident response, cloud security, red team, forensics, and more.
- Located under `optional-skills/cybersecurity/`.
- Import script: `scripts/import_cybersecurity_skills.py`.
- Attribution: `optional-skills/cybersecurity/NOTICE` and `ATTRIBUTION.md`.

#### Elite Build-and-Ship Skills (10)
- `ship-it-preflight` — pre-release checklist.
- `rfc-writer` — RFC authoring guide.
- `prd-writer` — PRD authoring guide.
- `release-engineering` — release management.
- `perf-profiling` — performance profiling.
- `incident-response` — incident response playbook.
- `api-design-review` — API design review checklist.
- `observability-setup` — observability setup guide.
- `database-migration-playbook` — safe database migrations.
- `secure-by-default-checklist` — security review checklist.

#### Ported Skills (6)
- `tdd` — test-driven development.
- `brainstorming` — structured brainstorming.
- `frontend-design` — frontend design principles.
- `mcp-builder` — MCP server builder.
- `security-review` — security review checklist.
- `verification-before-completion` — verification before declaring done.

#### Infrastructure
- Skill auto-improvement loop (`xavani_learner/skill_improver.py`).
- Hibernation adapters (`tools/environments/hibernation.py`).
- Session budget governor (`agent/budget_governor.py`).

### Changed
- Version bumped from 0.2.0 to 0.3.0.
- README updated with v0.3.0 "What's New" section.
- MANIFEST.md updated with all 21 guideline entries.
- Test contract updated: `EXPECTED_THINKERS` now includes all 21 names.

## [0.2.0] - Previous release

Initial release.
