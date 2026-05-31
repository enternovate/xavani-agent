<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Remediation handoff for the implementing agent. Closes the
     gaps found in Xavani's audit of the v0.3.0 work. Keep untracked (do not `git add`) unless the
     user decides to commit. Pairs with IMPLEMENTATION_GUIDE.md (the original build guide). -->

# Xavani v0.3.0 — Remediation Guide (close every audit shortfall)

> **Audience:** the implementing agent.
> **Goal:** take v0.3.0 from ~70% to **100% of the original plan, done correctly**, with every item
> verified green.
> **Bar:** make no mistakes. When unsure of an API, **READ the named real file and mirror it — never
> guess.** Each task ends with a **Verify** block; do not mark a task done until its Verify passes.
> **Status of prior work (already correct — do not redo):** WS1 guidelines+enforcement, WS4 cyber
> import (754 + manifest + attribution), WS6 elite skills, README v0.3.0 section, version bump,
> MANIFEST counts (fixed). Scrub/stubs/identity/no-push are all clean — keep them that way.

---

## 0. Global rules (unchanged — apply to every task)

- **R1 Scrub:** no new `nous`/`hermes` references in any artifact. Only the pre-existing `LICENSE`/`README.md`
  attribution lines are allowed. Check: `grep -rniE '\b(nous|hermes)\b' <changed paths>` → zero new hits.
  (Exception already in place: the gate's own detector regex in `tools/guidelines_gate_tool.py:30`.)
- **R2 Stubs:** never modify `tools/skills_hub.py` or `gateway/platforms/weixin.py` bodies, or their test skips.
- **R3 Xavani-native:** build from scratch; never copy upstream code/names.
- **R4 Surgical:** every hunk traces to a task here; no drive-by edits.
- **R5 Tests:** every new/changed module gets tests; `pytest -q` stays green; **no new skips**.
- **R7 Identity:** do not touch identity in `xavani_cli/default_soul.py` / `agent/prompt_builder.py` except to append.
- **R8 Header:** new `.py` files begin with the three-line Enternovate MIT header (copy from any current module).
- **NO PUSH:** never `git push` or change branch protection. The user controls all pushes.
- **Env:** the interpreter is `python3` (no `python` on PATH). Run tests with `python3 -m pytest`.

## 1. Shortfall checklist (do in this priority order)

| # | Task | Priority | Section |
|---|---|---|---|
| 1 | Tests for 8 new modules | **P0** | S1 |
| 2 | Wire 754 cyber skills into the skills index | **P1** | S2 |
| 3 | Port provenance + add `code-review` port | **P1** | S3 |
| 4 | Activate the (currently dormant) budget governor | **P1** | S4 |
| 5 | WS2 capabilities: FTS5 memory search, search providers, MCP refresh | P2 | S5 |
| 6 | WS3: skill registry v2 + observability/metrics | P2 | S6 |
| 7 | WS7: `README.zh-CN.md` mirror + website docs | P2 | S7 |

---

## S1 — Tests for the 8 untested new modules  [P0]

**Why:** charter §12.4 + R5 require coverage for every new module; today only
`tests/xavani_cli/test_research_guidelines.py` was extended. Behaviors work but are unlocked by CI.

**Mirror:** tool tests → `tests/tools/test_*.py`; CLI/unit tests → `tests/xavani_cli/test_research_guidelines.py`
style (synthetic `tmp_path`, `monkeypatch`). Read one neighbor test in each dir before writing.

Create these files and cover at least the listed behavior (verified public APIs given):

1. **`tests/tools/test_guidelines_gate.py`** — `from tools.guidelines_gate_tool import run_guidelines_gate`.
   `run_guidelines_gate(diff_text:str, goal:str) -> {"ok":bool,"failures":[{"check","status","reason"}],"warnings":[...]}`.
   Cases: clean tested diff + measurable goal → `ok True`; noisy/no-test/vague goal → `ok False`; a diff
   adding `nous`/`hermes-agent` → `scrub` failure; a diff editing `tools/skills_hub.py` → stub failure;
   assert each check id appears (`surgical, eval_present, no_unearned_abstraction, measurement_stated, scrub`).
2. **`tests/xavani_cli/test_guidelines_cmd.py`** — `from xavani_cli import guidelines_cmd as gc`.
   Cover `build_parser()`, `_cmd_list()` prints 21 names, `_cmd_show("hickey-guidelines")` prints body,
   `_cmd_show("does-not-exist")` returns non-zero + error, `run_slash("list")` returns a formatted string.
3. **`tests/tools/test_mixture_of_agents.py`** — `monkeypatch` `_call_model` to return canned strings;
   assert `mixture_of_agents(...)` aggregates N proposals + an aggregator pass; `_handle_mixture_of_agents`
   returns a string; assert the tool is registered (in `tools.registry`).
4. **`tests/tools/test_computer_use_tool.py`** — `monkeypatch` `_check_computer_use_available` both ways;
   when unavailable the tool returns a clear guard message; when available, `computer_screenshot/click/type`
   call the mocked backend; assert registration.
5. **`tests/tools/test_hibernation.py`** — drive `HibernationMixin` with a fake backend; assert
   hibernate→resume lifecycle + idempotency + error on resume-without-hibernate.
6. **`tests/tools/test_eval_harness.py`** — in `tmp_path`, `_save_eval`/`_load_eval` round-trip; define a
   2-case eval, run it, assert pass-rate reported; handler returns expected summary. (Read the module for
   the exact public run/report names.)
7. **`tests/test_skill_improver.py`** (or `tests/xavani_learner/`) — `extract_pattern_from_trajectory(...)`
   produces a draft; `_generate_skill_name(...)` is slug-safe/unique; drafts land in the draft dir and
   **never** under `skills/`.
8. **`tests/agent/test_budget_governor.py`** — `SessionBudgetGovernor`: `record_usage({...})` accumulates;
   `should_warn()` true at the warn threshold; `is_over_budget()` true past the cap; `format_warning()`
   returns a non-empty string; `SessionUsage` math correct.

**Verify S1:** `python3 -m pytest tests/tools tests/xavani_cli tests/agent tests/test_skill_improver.py -q`
→ all green, zero new skips. Then run the full suite: `python3 -m pytest -q` → green.

---

## S2 — Wire the 754 cyber skills into the skills index  [P1]

**Facts:** `website/scripts/extract-skills.py` already scans `("skills","built-in")` and
`("optional-skills","optional")` (L17-18) — **but** its documented path shape is
`optional-skills/<cat>/<slug>/SKILL.md` (3 levels). Cyber skills nest deeper:
`optional-skills/cybersecurity/<subdomain>/<slug>/SKILL.md` (4 levels). `scripts/build_skills_index.py`
is the **remote hub** index (uses `skills_hub`, which is a stub) — **do not touch it** (R2).

**Do:**
1. Read `website/scripts/extract-skills.py` (esp. `extract_local_skills()` and the path-mapping at
   L105-112). Extend the local walker to also match the 4-level cyber path, producing stable slugs like
   `optional/cybersecurity-<subdomain>-<slug>`. Prefer a recursive `rglob("SKILL.md")` under each root
   with slug derived from the path relative to the root, so any nesting depth works (don't special-case).
2. Confirm the **runtime** loader discovers them too: read `agent/skill_utils.py`; if it only walks a
   fixed depth, make its `optional-skills/` discovery recursive as well so `xavani skills` lists them.
3. Rebuild + verify outputs include cyber skills.

**Verify S2:**
```
python3 website/scripts/extract-skills.py && python3 -c "import json; d=json.load(open('website/src/data/skills.json')); rows=d if isinstance(d,list) else d.get('skills',[]); print('cyber:', sum('cybersecurity' in (s.get('id','')+str(s.get('categories',''))) for s in rows))"
```
→ count ≈ 754. Also `grep -rniE '\b(nous|hermes)\b'` on any file you changed → zero.

---

## S3 — Port provenance + add the missing `code-review` port  [P1]

**Why:** §8 (WS5) requires recording provenance/license for every ported skill and only porting
license-permissive sources. Today the ports (`tdd`, `brainstorming`, `frontend-design`, `mcp-builder`,
`security-review`, `verification-before-completion`) have **no** provenance, and `code-review` is missing.

**Do:**
1. For **each** ported skill under `skills/software-development/`, **verify the upstream license permits
   redistribution** (check the source plugin/repo's LICENSE). If a source is not redistributable, either
   re-author the skill originally (Xavani-native) or remove it — do not ship an unlicensed copy.
2. Append a provenance block to the **body** (not frontmatter) of each ported `SKILL.md`:
   ```
   ## Provenance
   Adapted by Enternovate for Xavani from <source name> (<license>, <url>). Reworded and
   normalized to the Xavani skill format; no upstream code copied verbatim.
   ```
   Fill `<source>` accurately per skill (e.g. superpowers TDD/brainstorming/verification-before-completion;
   Anthropic example skills frontend-design/mcp-builder). If you cannot identify a permissive source,
   treat the skill as **Xavani-original** and say so instead.
3. Create **`skills/software-development/code-review/SKILL.md`** (the missing prioritized port), Xavani
   format (`name, description, categories:[software-development], platforms:[all], tags, condition`),
   sections When-to-use / Steps / Examples / Verification, plus the `## Provenance` block.

**Verify S3:** `for f in skills/software-development/{tdd,brainstorming,frontend-design,mcp-builder,security-review,verification-before-completion,code-review}/SKILL.md; do grep -qiE 'provenance|xavani-original' "$f" && echo "$f ok" || echo "$f MISSING provenance"; done` → all ok.
Scrub the dir → zero `nous|hermes`.

---

## S4 — Activate the dormant budget governor  [P1]

**Why:** `agent/conversation_loop.py:1601-1619` uses `agent._budget_governor`, but it is lazy-set to
`None` and **never instantiated**, so the feature never runs. No code constructs `SessionBudgetGovernor`.

**Do:**
1. Read where the agent/session is initialized (`run_agent.py`, `AIAgent.__init__`, and how config/env
   options reach the agent). Instantiate `SessionBudgetGovernor` there **only when a budget is configured**
   (new optional config key, e.g. `session_token_budget` / env `XAVANI_TOKEN_BUDGET`); otherwise leave the
   feature off (None) so default behavior is unchanged.
2. Set `agent._budget_governor = SessionBudgetGovernor(...)` with the configured cap + warn threshold so
   the existing hook at L1601-1619 begins recording usage and emitting warnings.
3. Document the new config key in `README.md`'s v0.3.0 section (one line) and CHANGELOG.
4. Add an integration test (extends S1 #8): simulate usage crossing warn + cap → assert a warning is
   surfaced through the loop path.

**Verify S4:** `grep -n "SessionBudgetGovernor(" -r --include="*.py" .` shows a construction site outside
`agent/budget_governor.py`; the S4 test passes; with no budget configured, existing tests still green.

---

## S5 — WS2 capabilities: FTS5 memory, search providers, MCP refresh  [P2]

Build each Xavani-native (R3), lazy-load optional deps via `tools/lazy_deps.py`, add tests (R5). **Read the
named files first to match existing interfaces.**

**S5a FTS5 memory search + summarization.** Read `xavani_memory/`, `xavani_state.py`, `tools/memory_tool.py`,
`tools/session_search_tool.py`. Add an FTS5 virtual table over stored session/message text + a search fn
that ranks hits and (optionally) summarizes the top-K via the model. Expose by extending
`session_search_tool.py` (or a new `memory_search` tool registered in `tools/registry.py`). Test against an
in-memory SQLite fixture (insert rows → query → expect ordered hits; summarization mocked).

**S5b Extra search providers (Firecrawl, Parallel Web).** Read the existing provider abstraction
(`tools/web_tools.py` and the web-search provider module/registry). Add two providers behind the **same
interface** as the existing one (e.g. Exa); key by env (`FIRECRAWL_API_KEY`, `PARALLEL_API_KEY`); lazy-load
`firecrawl-py` / `parallel-web` via `tools/lazy_deps.py` and add them as **optional** extras in
`pyproject.toml` (do not add to the base install). Test with mocked HTTP (no network).

**S5c MCP refresh.** Read `tools/mcp_tool.py` and the pinned `mcp` version in `pyproject.toml`. Bring the
tool to current SDK capabilities (resources/prompts/transport parity) while preserving the existing OAuth
managers and backward compatibility. If a clean integration point is unclear, ship a focused subset and
leave a precise `TODO(xavani v0.3.x)` rather than a risky rewrite. Add/extend MCP tests.

**Verify S5:** each new tool imports + registers (`python3 -c "import tools.registry"`); provider tests +
memory tests green; `grep -rniE '\b(nous|hermes)\b'` on touched files → zero; base install still works
without the optional deps.

---

## S6 — WS3: skill registry v2 + observability/metrics  [P2]

**S6a Skill registry v2 (safe, audited discovery).** New module `xavani_registry/local_registry.py`
(R8 header). Functions: scan `skills/`, `optional-skills/`, and `~/.xavani/skills`; list with frontmatter
metadata (reuse `agent/skill_utils.py` parsing); **add-by-path** that validates frontmatter, enforces unique
`name`, and runs the scrub check before accepting. **No network crawler** — `tools/skills_hub.py` stays a
stub (R2). Optionally wire to the existing `reload-skills` command. Tests in `tests/` using `tmp_path`
skill fixtures (valid add, duplicate-name reject, malformed-frontmatter reject, scrub reject).

**S6b Observability/metrics.** Read `xavani_observability/` and `plugins/observability/`. Add a structured
event log (JSONL) for turns/tool-calls and an **optional** Prometheus endpoint behind a feature flag/env
(off by default). Test event emission + that the endpoint only starts when enabled.

**Verify S6:** `python3 -c "import xavani_registry.local_registry"`; registry + observability tests green;
default behavior unchanged when observability flag is off.

---

## S7 — WS7: `README.zh-CN.md` mirror + website docs  [P2]

**S7a** Mirror the English **"What's New in v0.3.0 'Perpetuity'"** section into `README.zh-CN.md` (translate
faithfully). Keep the existing attribution line mirrored as-is; add **no** new Nous/Hermes references (R1).

**S7b** Add website pages under `website/docs/` for: guidelines enforcement, eval harness, 754 cyber skills,
mixture-of-agents, computer-use; register them in `website/sidebars.ts`. Build locally:
`cd website && npm ci && npm run build` → succeeds.

**Verify S7:** `grep -c "0.3.0" README.zh-CN.md` > 0; `grep -rniE '\b(nous|hermes)\b' README.zh-CN.md website/docs`
→ only the mirrored attribution line; website build exits 0.

---

## 8. Final Definition of Done (run all; every line must pass)
```
# 1) Tests — full suite green, no new skips
python3 -m pytest -q

# 2) Imports / registry load clean
python3 -c "import agent.conversation_loop, xavani_cli.commands, tools.registry, xavani_registry.local_registry; print('OK')"

# 3) Guidelines intact
python3 -c "from xavani_cli.research_guidelines import list_guideline_names as L; assert len(L())==21; print('21 OK')"

# 4) Cyber skills indexed (~754) and discoverable
find optional-skills/cybersecurity -name SKILL.md | wc -l        # 754
python3 website/scripts/extract-skills.py                         # includes cybersecurity

# 5) Budget governor actually constructed somewhere
grep -rn "SessionBudgetGovernor(" --include="*.py" . | grep -v "agent/budget_governor.py"

# 6) Provenance on every ported skill; code-review exists
ls skills/software-development/code-review/SKILL.md

# 7) Docs
grep -c "0.3.0" README.zh-CN.md ; (cd website && npm run build)

# 8) Hard rules
grep -rniE '\b(nous|hermes)\b' $(git status --porcelain | awk '{print $2}' | grep -v optional-skills/cybersecurity) | grep -viE 'LICENSE|README'   # expect empty (only allowed attribution)
git status --porcelain | grep -E "skills_hub|weixin|default_soul" && echo "VIOLATION: stubs/identity touched" || echo "stubs+identity intact"
git log origin/main..HEAD                                         # empty — nothing committed/pushed beyond origin
```
**Done = all 7 sections complete, every Verify green, §8 all-pass, and nothing pushed.** If any item can't
be finished safely, STOP and leave a precise `TODO(xavani v0.3.x)` with the blocker — never fake a pass.
