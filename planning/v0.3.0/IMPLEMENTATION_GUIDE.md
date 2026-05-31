<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. In-repo copy of the approved master guide so the implementing
     agent can read it from the working tree. Keep it untracked (do not `git add`) unless the user
     explicitly decides to commit it. Authoritative source also lives at
     ~/.claude/plans/plan-well-around-xavani-agent-delightful-gray.md -->

# Xavani Agent v0.3.0 "Perpetuity" — Master Implementation Guide

> **Audience:** the implementing agent (the user's personal agent).
> **Status:** LOCAL document. **DO NOT push this file or commit it to GitHub.** Keep it on-device.
> **Authoring agent (Xavani) role after handoff:** audit and revise your changes until perfect (see §12).
> **Bar:** make no mistakes. When unsure, READ the referenced real file and mirror its pattern — never guess.

---

## 0. How to use this guide

1. Read §1 (non-negotiable rules) and §2 (verified facts) **before touching anything**.
2. Work **one workstream at a time**, in the order of §10. Each workstream is independently shippable.
3. For every file you create/modify: follow the exact path, mirror the named reference file, then run that
   workstream's **Verify** block. Do not start the next workstream until the current one is green.
4. Persist progress notes into `planning/v0.3.0/NN-<name>.md` (local, untracked) if you want tracking,
   but **this guide is the authoritative spec**.
5. **Never run `git push` or branch-protection commands.** The user controls all pushes. You may commit
   locally on a feature branch only if the user asks; otherwise leave changes in the working tree.

---

## 1. Non-negotiable global rules (apply to EVERY change)

- **R1 — No upstream callouts (scrub).** No artifact you create or edit may reference, name, or hint at
  "Nous Research", "Hermes", "hermes-agent", or Nous models. The **only** permitted references are the
  pre-existing attribution lines already in `LICENSE` and `README.md`. Before finishing any workstream,
  run: `grep -rniE 'nous|hermes' <paths you touched>` → expect zero new hits.
- **R2 — Stubs stay stubs.** Do **not** implement, expand, or un-stub `tools/skills_hub.py` or
  `gateway/platforms/weixin.py`. Do not remove their tests' skip markers. If a feature seems to need
  them, build a **new** Xavani-native module instead.
- **R3 — Xavani-native only.** Re-implement capabilities from scratch under Xavani branding. Never copy
  code, comments, or naming from any upstream project.
- **R4 — Small, surgical diffs.** Every changed line must trace to a workstream item. No drive-by
  refactors, no speculative abstractions (YAGNI), no reformatting untouched code.
- **R5 — Tests are the contract.** Add/extend tests for new behavior. Run the relevant suite after each
  change. Never weaken or skip a test to make it pass. New skips are forbidden unless documented and
  justified in the workstream notes.
- **R6 — Frontmatter is strict.** Skill/guideline frontmatter must satisfy the loader contracts in §3.
  A malformed file silently drops out of the pack — that is a defect.
- **R7 — Identity is fixed.** The agent is "Xavani Agent, created by Enternovate." Never alter the
  identity assertions in `xavani_cli/default_soul.py` / `agent/prompt_builder.py` except to *append*.
- **R8 — License headers.** New `.py` files start with the existing header style:
  `# Copyright (c) 2025-2026 Enternovate.` / `# MIT License -- See LICENSE file for full terms.` /
  `# Built by Enternovate -- Open source. Private. Local.` (copy verbatim from any current module).
- **R9 — Version discipline.** Bump `version` in `pyproject.toml` from `0.2.0` → `0.3.0` exactly once,
  in WS7, after all features land. Update the banner/version strings the same place.

---

## 2. Verified repo facts (ground truth — do not re-derive)

- Root: `/Users/andilemushwana/xavani-agent`. Remote `github.com/enternovate/xavani-agent` (leave untouched).
- Skills today: **90** `SKILL.md` under `skills/`, **81** under `optional-skills/`. Discovery: `agent/skill_utils.py`. Index workflow: `.github/workflows/skills-index.yml` → `skills/index-cache/`.
- Skill frontmatter keys in use: `name, description, categories, platforms, tags, condition` (markdown body after).
- Tools: registered through `tools/registry.py` (AST-discovered at module load, circular-import-safe). Function-calling schemas assembled in `model_tools.py`. Skill-management tool: `tools/skill_manager_tool.py`.
- Agent loop: `agent/conversation_loop.py` + `run_agent.py` (`AIAgent`). Prompt build: `agent/prompt_builder.py`, `agent/system_prompt.py`. Soul: `xavani_cli/default_soul.py`.
- **Research-guidelines system (the feature to extend):**
  - Loader: `xavani_cli/research_guidelines.py`. Public API: `load_mandatory_guidelines(reload=False)`, `compose_system_prompt_block(guidelines=None)`, `get_guideline(name)`, `list_guideline_names()`, `guideline_dir()`.
  - Discovery dir: `skills/research-guidelines/`, glob `*-guidelines.md`.
  - **REQUIRED frontmatter (all six, or the file is rejected):** `name, description, domain, mandatory, priority, version`. Optional: `sources` (str or list). `mandatory: true` to be loaded; sorted by `priority` desc, then `name` asc.
  - Spliced into the soul by `xavani_cli/default_soul.py::_build_default_soul()` via `compose_system_prompt_block()` (condensed: one `### name (domain, priority N)` heading + the description line per guideline).
  - Index doc: `skills/research-guidelines/MANIFEST.md` (has a priority table — keep it in sync).
  - **Test contract:** `tests/xavani_cli/test_research_guidelines.py` defines `EXPECTED_THINKERS` (currently 11) and an integration test asserting the bundled pack discovers each and that the composed block contains each. **Editing the roster REQUIRES editing this tuple** or CI fails.
- Current roster (11): `karpathy, lecun, hinton, sutskever, olah, hassabis` (AI) + `hamming, knuth, popper, polya, tukey` (method). Priorities: karpathy=100, method tier=95, AI tier=90.
- Confirmed stubs: `tools/skills_hub.py`, `gateway/platforms/weixin.py`.

---

## 3. Patterns you MUST reuse (read these before writing)

- **Guideline files:** copy `skills/research-guidelines/karpathy-guidelines.md` as your structural template (frontmatter block, then `# <Name> — Operating Guidelines`, a one-line epigraph, `## Core Principles (always-on)`, `## Heuristics for the agent`, `## Anti-patterns to reject`, `## When to invoke`).
- **Loader API:** never re-parse files yourself; call `xavani_cli.research_guidelines` functions.
- **New tool:** open `tools/registry.py` to learn the **exact** `register(...)` signature, then open one
  small existing tool that calls it (e.g. `tools/skill_manager_tool.py`) and mirror its module shape
  (license header → imports → handler fn → `registry.register(...)` at module level). Do **not** invent
  the signature from memory.
- **New CLI subcommand:** open `xavani_cli/commands.py` and an existing command module (e.g.
  `xavani_cli/kanban.py`) to learn how subcommands are wired/dispatched, then mirror it.
- **New skill (`SKILL.md`):** copy an existing one under `skills/software-development/` for structure.
- **Tests:** mirror `tests/xavani_cli/test_research_guidelines.py` style (synthetic tmp_path unit tests +
  one integration test against the real bundle).

---

## 4. WORKSTREAM 1 — Research Guidelines v2 + Enforcement engine  ⭐ flagship

**Objective:** expand the mandatory roster and make the principles *enforced*, not merely *injected*.

### 4.1 Roster expansion (10 new files → 21 total)
Create each under `skills/research-guidelines/<file>` using the karpathy template. Frontmatter must
include all six required keys + `sources`. Suggested `domain`/`priority`:

| File | name | domain | priority | Key sources (put in `sources:`) |
|---|---|---|---|---|
| `chollet-guidelines.md` | chollet-guidelines | ai-research | 90 | "On the Measure of Intelligence" (arXiv:1911.01547); "Deep Learning with Python" |
| `weng-guidelines.md` | weng-guidelines | ai-engineering | 90 | "LLM Powered Autonomous Agents" (lilianweng.github.io, 2023); "Extrinsic Hallucinations in LLMs" (2024) |
| `huyen-guidelines.md` | huyen-guidelines | ml-systems | 90 | "Designing Machine Learning Systems" (O'Reilly); "AI Engineering" (2025) |
| `yan-guidelines.md` | yan-guidelines | ai-engineering | 90 | "Patterns for Building LLM-based Systems & Products" (eugeneyan.com, 2023) |
| `beck-guidelines.md` | beck-guidelines | software-craft | 88 | "Test-Driven Development by Example"; "Tidy First?"; "Extreme Programming Explained" |
| `hickey-guidelines.md` | hickey-guidelines | software-design | 87 | "Simple Made Easy" (Strange Loop 2011); "The Value of Values" |
| `fowler-guidelines.md` | fowler-guidelines | software-craft | 86 | "Refactoring, 2nd ed."; martinfowler.com (code smells, CI/CD) |
| `carmack-guidelines.md` | carmack-guidelines | software-craft | 85 | "Functional Programming in C++" (2018); .plan archives |
| `kernighan-pike-guidelines.md` | kernighan-pike-guidelines | software-craft | 85 | "The Practice of Programming" (1999); "The Unix Programming Environment" |
| `dijkstra-guidelines.md` | dijkstra-guidelines | software-craft | 84 | "Go To Statement Considered Harmful" (1968); "A Discipline of Programming"; EWD notes |

**Content rules per file:** 4–6 *operational* principles (imperatives the agent can act on), 4–6
agent heuristics, 3–5 anti-patterns, and a `## When to invoke` list. No fluff; every bullet must change
behavior. Keep each file ~2.5–3.5 KB (match existing). Cite real works only.

**Strengthen Karpathy:** edit `karpathy-guidelines.md` to fold in the four operational rules
(Think-Before-Coding, Simplicity-First, Surgical-Changes, Goal-Driven-Execution) as a new
`## Operating rules` block. Keep `priority: 100`. Do not delete existing content.

### 4.2 Update the index + test contract (MANDATORY or CI breaks)
- `skills/research-guidelines/MANIFEST.md`: add the 10 rows to the priority table; update the "Why these
  N" prose from "eleven" → the new total; keep the multica-ai pattern reference.
- `tests/xavani_cli/test_research_guidelines.py`: extend `EXPECTED_THINKERS` to all 21 names:
  `karpathy-guidelines, lecun-guidelines, hinton-guidelines, sutskever-guidelines, olah-guidelines, hassabis-guidelines, hamming-guidelines, knuth-guidelines, popper-guidelines, polya-guidelines, tukey-guidelines, chollet-guidelines, weng-guidelines, huyen-guidelines, yan-guidelines, beck-guidelines, hickey-guidelines, fowler-guidelines, carmack-guidelines, kernighan-pike-guidelines, dijkstra-guidelines`.

### 4.3 Enforcement engine (this is what makes them "mandatory")
**(a) CLI — `xavani_cli/guidelines_cmd.py` (new):** subcommands `list` (print roster via
`list_guideline_names()`), `show <name>` (print full body via `get_guideline(name).body`), `check`
(run the gate from (b) against the current diff). Wire into the CLI by mirroring how `xavani_cli/kanban.py`
is registered in `xavani_cli/commands.py`. Add unit tests.

**(b) Pre-ship verification gate — `tools/guidelines_gate_tool.py` (new tool):** a tool the agent calls
before declaring a task done. Inputs: the working diff (`git diff` + `git diff --cached`) and a short
"goal + measurement" statement. Checks (each returns pass/warn/fail + reason):
- **Surgical:** diff touches only files relevant to the stated goal; flag large/unrelated hunks (R4).
- **Eval present:** a test/eval was added or run for the change (Karpathy "eval is all you need").
- **No unearned abstraction:** flag new base classes/flags/indirection with a single caller (YAGNI).
- **Measurement stated:** the agent provided a concrete before/after signal, not "looks good".
- **Scrub:** diff introduces no new `nous|hermes` reference (R1).
- **Stubs intact:** diff does not modify `skills_hub.py`/`weixin.py` bodies (R2).
Return a structured verdict (`ok: bool`, `failures: [...]`, `warnings: [...]`). Register it by mirroring
`tools/skill_manager_tool.py`'s registration exactly (read `tools/registry.py` first for the signature).
Add a tool test mirroring an existing tool test.

**(c) Loop hook:** in `agent/conversation_loop.py`, on completion-type turns, surface the gate's verdict
(advisory). Keep this a **small, isolated** addition; if the integration point is unclear, ship (a)+(b)
and leave a `TODO(xavani v0.3.1)` note rather than risk the loop (R4).

### 4.4 Verify WS1
```
pytest tests/xavani_cli/test_research_guidelines.py -q          # roster + block contains all 21
python -c "from xavani_cli.research_guidelines import list_guideline_names as L; print(len(L()), L())"  # == 21
xavani guidelines list                                          # prints 21
xavani guidelines show hickey-guidelines                        # prints body
# gate: feed a noisy diff → fails 'surgical'; a clean tested diff → ok:true
grep -rniE 'nous|hermes' skills/research-guidelines tools/guidelines_gate_tool.py xavani_cli/guidelines_cmd.py   # zero hits
```

---

## 5. WORKSTREAM 2 — Capability catch-up (Xavani-native)

**Objective:** add the modern agent capabilities Xavani lacks, built from scratch (R3), no upstream
names anywhere (R1). Each is an independent tool/module + tests. Build in this order:

| Capability | New file(s) | Mirror / reuse | Notes |
|---|---|---|---|
| Mixture-of-Agents | `tools/mixture_of_agents_tool.py` | registry pattern; provider client in `agent/` | N parallel model calls → aggregator pass. Config: models list, rounds. |
| Computer-use | `tools/computer_use_tool.py` | `tools/mcp_tool.py` | Drive screen/keyboard/mouse via an MCP computer-use server; guard behind `check_fn` + env. |
| FTS5 memory search | extend `xavani_memory/` + `tools/session_search_tool.py` | existing SQLite usage in `xavani_state.py` | Add an FTS5 virtual table + LLM summarization of hits. |
| Serverless hibernation runtimes | `tools/environments/` adapters | existing `tools/environments/modal.py` | Add hibernate/resume lifecycle for long-running sandboxes. |
| Skill auto-improvement loop | module under `xavani_learner/` | existing learner code | After a successful trajectory, propose a draft `SKILL.md` for review (never auto-write to `skills/`). |
| Extra search providers | extend the web-search provider abstraction | existing `tools/web_tools.py` | Add Firecrawl + Parallel Web behind the same interface; lazy-load deps via `tools/lazy_deps.py`. |
| MCP refresh | `tools/mcp_tool.py` | current MCP code | Bring to current MCP SDK capabilities; keep OAuth managers. |

**Do-not:** do not add these to the base install; lazy-load optional deps. Do not reference upstream.

**Verify WS2 (per capability):** unit test the tool in isolation (mock providers/servers); confirm it
registers (appears in `model_tools` schema list); `grep -rniE 'nous|hermes'` on touched files → zero.

---

## 6. WORKSTREAM 3 — Features & optimizations (the 10+)

Most rows are delivered by WS1/WS2/WS4/WS6. The net-new items unique to WS3:

| # | Feature | New/Modified | Spec |
|---|---|---|---|
| 2 | **Eval harness** tool | `tools/eval_harness_tool.py` + skill `skills/software-development/eval-harness/SKILL.md` | Define eval cases (input→expected/assertion), run, report pass-rate. Encodes "build the eval first." |
| 4 | **Skill registry v2** (safe discovery) | new module e.g. `xavani_registry/local_registry.py` | Index local + user `~/.xavani/skills`; audited add-by-path; **no network crawler**, `skills_hub.py` stays stub. |
| 5 | **Diff/trajectory guard** | reuse WS1 gate | Wire the gate's "surgical" check as a reusable helper. |
| 6 | **Token/cost budget governor** | integrate existing token-optimization module into `agent/conversation_loop.py` | Per-session budget; warn/trim at thresholds. |
| 7 | **Observability/metrics** | extend `xavani_observability/` + `plugins/observability/` | Structured event log + optional Prometheus endpoint. |

**Optimizations to existing code (small diffs):**
- Expose guidelines via the new CLI (WS1); add on-demand per-domain loading to the loader if needed.
- Integrate the token-optimization module into the loop (feature 6).
- Tidy `oag_cli.py` (readability only — no behavior change; covered by existing tests).
- Version bump is deferred to WS7.

**Verify WS3:** new tools register and have tests; `pytest -q` green; budget governor unit-tested with a
synthetic over-budget session; metrics endpoint returns valid output behind its feature flag.

---

## 7. WORKSTREAM 4 — Cybersecurity skills, ALL ~754 (vendored)

**Objective:** import every skill from `mukul975/Anthropic-Cybersecurity-Skills` (Apache-2.0) into Xavani.

### 7.1 Layout
Vendor into `optional-skills/cybersecurity/<subdomain>/<skill-name>/`, preserving each skill's
`SKILL.md` + `references/` + `scripts/` + `assets/`. Keep upstream kebab-case names.

### 7.2 Attribution (required by Apache-2.0)
- Create `optional-skills/cybersecurity/NOTICE` and `optional-skills/cybersecurity/ATTRIBUTION.md`
  crediting `mukul975/Anthropic-Cybersecurity-Skills`, Apache-2.0, with the license text/link. (This is
  unrelated to R1 — crediting mukul975 is allowed and required.)

### 7.3 Frontmatter reconciliation (do not break the loader/index)
Upstream frontmatter has extra keys (`domain, subdomain, tags, version, author, license, nist_csf,
atlas_techniques, d3fend_techniques, nist_ai_rmf`). For Xavani's `skills/` loader the canonical keys are
`name, description, categories, platforms, tags, condition`. **Procedure:**
1. Keep `name`, `description`, `tags`.
2. Map `subdomain` → add to `categories: [cybersecurity, <subdomain>]`.
3. Preserve framework mappings (`nist_csf`, `atlas_techniques`, etc.) by moving them into a
   `## Standards mapping` section in the **body** (not required frontmatter), so nothing is lost and the
   loader stays happy. Keep `license` note in body.
4. Validate each converted file parses (frontmatter splits cleanly; `name` unique).

### 7.4 Reproducible import
Write `scripts/import_cybersecurity_skills.py` (Xavani header per R8) that: clones/downloads the upstream
repo at a pinned commit, transforms frontmatter per §7.3, writes into the target tree, and emits a
`optional-skills/cybersecurity/IMPORT_MANIFEST.json` with per-file SHA-256 so the vendoring is auditable
and re-runnable. **Pin the upstream commit** in the script.

### 7.5 Index + budget
Extend `.github/workflows/skills-index.yml` (and/or the indexer it calls) to include
`optional-skills/cybersecurity/`. Confirm the frontmatter-only scan stays cheap (~tens of tokens per
skill). Run the indexer locally and confirm it completes.

**Verify WS4:**
```
find optional-skills/cybersecurity -name SKILL.md | wc -l     # ~754
python scripts/import_cybersecurity_skills.py --check          # idempotent; manifest matches
# loader/index build succeeds; spot-check 5 random skills parse; ATTRIBUTION/NOTICE present
grep -rniE 'nous|hermes' optional-skills/cybersecurity         # zero hits
```

---

## 8. WORKSTREAM 5 — Port Claude Code / user skills  &  WS6 — Elite build-and-ship skills

### WS5 (`port`)
Convert redistributable Claude Code skills (superpowers, everything-claude-code, anthropic example
skills, etc.) into Xavani `SKILL.md` format. **Procedure:** for each source skill, map its frontmatter →
Xavani keys, normalize the body to the Xavani section shape, drop tool-name assumptions that don't exist
in Xavani. **Only port skills whose license permits redistribution; record provenance** in each ported
skill's body. Prioritize: TDD, systematic-debugging, brainstorming, code-review, frontend-design,
mcp-builder, security-review, verification-before-completion. Place under the matching `skills/<category>/`.

### WS6 (`elite`)
Author new original skills (Xavani-authored, R8 header inside scripts if any) under
`skills/software-development/` and `skills/devops/`:
- `ship-it-preflight` (release checklist), `rfc-writer`, `prd-writer`, `release-engineering`,
  `perf-profiling`, `incident-response`, `api-design-review`, `observability-setup`,
  `database-migration-playbook`, `secure-by-default-checklist`.
Each: When-to-use / Prerequisites / Steps / Examples / Verification. Concrete, runnable, no fluff.

**Verify WS5/WS6:** every new `SKILL.md` parses and appears in the rebuilt index; `xavani skills`
lists them; no duplicate `name`; scrub grep clean; licensing/provenance recorded for ported skills.

---

## 9. WORKSTREAM 7 — Docs, README, website  &  version bump

- **README.md:** add a "v0.3.0 — what's new" section (guidelines enforcement, eval harness, 754 cyber
  skills, MoA/computer-use, registry v2, observability). **Keep the existing Nous attribution line as-is;
  add no new Nous/Hermes references** (R1). Update counts (skills, tools) to real post-import numbers.
- **README.zh-CN.md:** mirror the additions.
- **Website `website/docs/`:** add pages for guidelines enforcement, eval harness, cyber-skills, new
  tools; update `sidebars.ts`. Build the site locally (`cd website && npm run build`) to confirm.
- **Version:** bump `pyproject.toml` `0.2.0`→`0.3.0`; update banner/version strings (search for `0.2.0`).
- **CHANGELOG:** add a `0.3.0` entry summarizing the workstreams.

**Verify WS7:** `grep -rn "0.2.0"` shows no stale version in shipped code; website builds; README links
resolve; `grep -rniE 'nous|hermes' README* website/docs` → only the pre-existing attribution line.

---

## 10. Sequencing (local; no push by Xavani)
1. **WS1** (guidelines v2 + enforcement) — highest leverage, smallest blast radius.
2. **WS3** features 2, 5, 6 (eval harness, diff guard, budget) — they enforce quality for all later work.
3. **WS2** capabilities, then **WS6** elite skills.
4. **WS4** cyber-skills import (largest; keep as its own logical change), then **WS5** ports.
5. **WS7** docs/website + version bump last.
Run the **global gate** (below) after each workstream. The user decides if/when anything is pushed.

## 11. Global test gate (run after every workstream)
```
ruff check .            # or the repo's configured linter (see .github/workflows/lint.yml)
pytest -q               # full suite; no new failures, no new skips
python -c "import xavani_cli.research_guidelines, tools.registry"   # imports clean
grep -rniE 'nous|hermes' <files changed in this workstream>          # zero new hits (R1)
git diff --stat         # confirm the diff is scoped to the workstream (R4)
```

## 12. Audit charter — what Xavani (authoring agent) will check on your output
For each workstream Xavani will verify, with file:line evidence, and revise until all pass:
1. **Scrub (R1):** no new Nous/Hermes references anywhere in the diff.
2. **Stubs (R2):** `tools/skills_hub.py` & `gateway/platforms/weixin.py` bodies + their test skips unchanged.
3. **Guidelines:** 21 files present & valid; `EXPECTED_THINKERS` updated; `MANIFEST.md` table matches;
   `compose_system_prompt_block()` contains all 21; gate tool fails a noisy diff, passes a clean one.
4. **Tests (R5):** full `pytest` green; coverage added for every new module; zero new skips.
5. **Diffs (R4):** every hunk traces to a workstream item; no dead code, no unearned abstractions.
6. **Cyber import:** ~754 skills present; `IMPORT_MANIFEST.json` reproducible; NOTICE/ATTRIBUTION present;
   index builds; token budget intact.
7. **Identity (R7):** soul identity assertions intact (append-only).
8. **Version (R9):** single clean 0.2.0→0.3.0 bump; no stale strings.
9. **No push:** `git log origin/main` unchanged unless the user explicitly authorized a push.

## 13. Definition of Done ("make no mistakes")
- All 7 workstreams green against §11; §12 audit fully passing.
- `xavani guidelines list` → 21; `xavani skills` lists cyber + ported + elite skills; new tools appear in
  the model schema; website builds; README/CHANGELOG updated and scrub-clean.
- Working tree contains the full v0.3.0 implementation; **nothing pushed by you**; this guide and any
  `planning/v0.3.0/` notes remain local.
- If any item can't be completed safely, STOP, leave a precise `TODO(xavani v0.3.x)` with the blocker,
  and report it — never paper over it.
