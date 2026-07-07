<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Roadmap handoff for the implementing agent. Authored by Xavani
     after auditing v0.3.0 (258ec6b). Keep untracked (do not `git add`) unless the user decides to
     commit. Pairs with planning/v0.3.0/{IMPLEMENTATION,REMEDIATION}_GUIDE.md. -->

# Xavani Agent — v0.3.1 → v0.6.0 Roadmap (100 updates)

> **Audience:** the implementing agent.
> **Goal:** 100 updates — ≥12 **[MAJOR]**, ≥20 **[FEAT]** — covering a deterministic zero-LLM-cost
> detection layer, full Xavani-native parity with the upstream agent, the full stack, and full-stack
> security. **No mistakes; verify every item.**
> **Bar:** when unsure of an API, **READ the named file and mirror it — never guess.** Each update is
> its own small change with its own tests + Verify; do not start the next until the current is green.
> **Cost rule (R10) is the spine of this roadmap:** the LLM is for *generation only* — never for
> detection/routing/governance the agent can do in Python.

## 0. Global rules (apply to every update)
- **R1 Scrub:** no new `nous`/`hermes` references in any shipped artifact (only the existing
  `LICENSE`/`README.md` attribution). Check `grep -rniE '\b(nous|hermes)\b' <changed paths>` → zero new.
  (Allowed exception already present: the gate's detector regex in `tools/guidelines_gate_tool.py`.)
- **R2 Stubs:** never touch `tools/skills_hub.py` / `gateway/platforms/weixin.py` bodies or their test skips.
- **R3 Xavani-native:** re-implement from scratch; never copy upstream code/names.
- **R4 Surgical diffs.** **R5 Tests for every change; `pytest -q` stays green; no new skips.**
- **R7 Identity** (don't alter `default_soul.py`/`prompt_builder.py` except to append). **R8 Enternovate header on new `.py`.**
- **R9 Version:** bump once per milestone tag in `pyproject.toml` + `xavani_cli/__init__.py` + `xavani.py`.
- **R10 Deterministic-first:** never spend an LLM/API call on routing, detection, matching, filtering, or
  governance. Every detector is unit-tested to make **zero** model-client calls.
- **NO PUSH** by you. The user controls all pushes. Interpreter is `python3`.

---

## 1. Workstream A — Deterministic, zero-cost detection (M1; the core ask)

**Already deterministic (verified at 258ec6b — keep, add tests, do not regress):**
`model_tools.handle_function_call → registry.dispatch`; `tools/guidelines_gate_tool.py`;
`tools/eval_harness_tool.py`; `xavani_learner/skill_improver.py` (Python template, not LLM);
`agent/skill_utils.py` (`extract_skill_conditions`, `skill_matches_platform`).

**A1 — Deterministic skill router** → new `agent/skill_router.py` (R8 header).
- `rank_skills(text:str, skills:Iterable[Frontmatter], k:int=5) -> list[(name, score)]` — score by
  keyword/token overlap of `text` against each skill's `tags` + `condition` + `description`, plus regex
  triggers; **stdlib only** (no embeddings, no model client). Tie-break alphabetical for determinism.
- Read `agent/skill_utils.py` for the frontmatter shape; reuse its parser. Read
  `xavani_learner/skill_orchestrator.py` + `context_enricher.py`; if either consults the model to pick
  skills, rewire to call `rank_skills`. Confirm neither imports a model client afterward.
- Test `tests/agent/test_skill_router.py`: fixtures of synthetic skills → assert ranking is stable,
  deterministic, and correct; assert module imports no model client.

**A2 — Deterministic tool pre-filter** → new `tools/tool_prefilter.py`.
- `select_tools(text:str, all_tool_names:list[str]) -> list[str]` — keyword/intent rules mapping user text
  to a relevant tool subset, so `model_tools.get_definitions(...)` is called with fewer schemas (cuts
  input tokens every turn). Default to the full set when uncertain (never hide a needed tool).
- Wire optionally into the schema-build path in `model_tools.py` behind a config flag (default on, safe).
- Test: relevant text → subset contains the right tool; ambiguous text → full set; zero model calls.

**A3 — Detector registry** → new `agent/detectors/__init__.py` + `registry.py`.
- Uniform `Detector` protocol: `name`, `detect(context: dict) -> Verdict{ok, findings, warnings}`; **pure
  Python, no I/O to a model.** Register wrappers for: guidelines-gate, scrub, stub-guard, eval-check,
  guideline-compliance, skill-match (A1), and (later) PII (U48) + prompt-injection (U39).
- Test `tests/agent/test_detectors_no_llm.py`: a fixture monkeypatches the model-client chokepoint to
  raise; run every registered detector; **any model call fails the test.** (Find the single client
  chokepoint first — likely `tools/openrouter_client.py` / the provider in `agent/`/`providers/`.)

**A4 — No-LLM CLI/slash entrypoints** → mirror `xavani_cli/guidelines_cmd.py` + its dispatch in `cli.py`.
- `xavani route <text>` (A1), `xavani skills match <text>` (A1), `xavani gate` / `xavani guidelines check`
  (existing gate), `xavani eval run <name>` (existing harness). All run in Python with **no** model call.

**A5 — Avoided-cost telemetry** → extend the existing usage tracking; add `xavani usage --savings`
showing count of detections served deterministically (i.e., LLM calls avoided). Test the counter.

**A6 — `xavani doctor` guard** → extend `xavani_cli/doctor.py`: scan `agent/detectors/`, `skill_router.py`,
`tool_prefilter.py`, gate, eval for imports of any model client; **fail** if found. Test it.

**A7 — R10 guideline + gate rule** → add `skills/research-guidelines/determinism-guidelines.md`
(frontmatter per the loader contract; bump `EXPECTED_THINKERS`/MANIFEST only if it's a *thinker* pack —
otherwise place R10 as a project rule doc and add a gate check that flags new model-client imports in
detection paths). Wire the check into `tools/guidelines_gate_tool.py`.

**Verify A:** `python3 -m pytest tests/agent/test_skill_router.py tests/agent/test_detectors_no_llm.py tests/tools/test_tool_prefilter.py -q` green; `xavani route "fix a failing test"` returns skills with no API call; `xavani doctor` passes; `grep -rniE '\b(nous|hermes)\b'` on new files → zero.

---

## 2. The 100 updates (each: → files / approach / verify)

### M0 — v0.3.1 "Finish line" (close audit gaps)
1. **[FIX] Cyber index** → `website/scripts/extract-skills.py`: replace the fixed-depth walk with
   `rglob("optional-skills/**/SKILL.md")`, deriving slug from the path relative to `optional-skills/`
   (so `cybersecurity/<subdomain>/<slug>` works). Verify: regenerate, `skills.json` cyber ≈ 754.
2. **[FIX] Runtime discovery** → `agent/skill_utils.py`: make optional-skills discovery depth-agnostic.
   Verify: `xavani skills` lists cyber skills; loader token cost stays frontmatter-only.
3. **[FEAT][DOC] Website pages** → `website/docs/{guidelines-enforcement,eval-harness,cyber-skills,mixture-of-agents,computer-use}.md` + register in `website/sidebars.ts`. Verify: `cd website && npm run build` exits 0.
4. **[FEAT] MCP refresh** → read `tools/mcp_tool.py` + pinned `mcp` in `pyproject.toml`; bring to current
   SDK (resources/prompts/transport) keeping OAuth managers. Verify: MCP smoke test + existing MCP tests green.
5. **[TEST]** cyber-index count test (`tests/test_skills_index_cyber.py`), MCP smoke, router smoke.
6. **[DOC]** `README.md` + `README.zh-CN.md`: document `XAVANI_TOKEN_BUDGET`/budget-governor config + cyber-pack usage. R1 scrub.

### M1 — v0.3.2 "Zero-cost cognition" (Workstream A above) [MAJOR theme]
7. **[MAJOR][FEAT]** A1 deterministic skill router.
8. **[FEAT]** A2 tool pre-filter.
9. **[MAJOR]** A3 detector registry.
10. **[FEAT]** A4 no-LLM CLI/slash entrypoints.
11. **[TEST]** A3 no-LLM assertion harness.
12. **[FEAT]** A5 avoided-cost telemetry.
13. **[PERF]** per-session content-hash cache for detector verdicts (reuse any existing cache util).
14. **[FEAT]** A-rewire `skill_orchestrator.py` / `context_enricher.py` → deterministic.
15. **[FEAT]** optional local intent classifier (regex/keyword; pluggable tiny local model), zero API cost.
16. **[DOC]** A7 R10 guideline + gate rule.
17. **[TEST]** router offline precision/recall eval (fixtures).
18. **[DX]** A6 `xavani doctor` model-client guard.

### M2 — v0.4.0 "Full parity" (Xavani-native) [MAJOR]
19. **[MAJOR][TEST] Parity matrix** → `tests/test_parity_matrix.py`: assert each capability below resolves
    to a registered tool/module + a smoke import. Drives the rest of M2.
20. **[MAJOR][FEAT] Local-model mode** → provider adapter for Ollama/llama.cpp behind the existing model
    interface (`providers/` or `tools/openrouter_client.py` sibling); fully offline path; lazy-loaded.
21. **[TEST]** platforms A: telegram/discord/slack/whatsapp/signal → import+config+webhook-parse smoke (`gateway/platforms/`).
22. **[TEST]** platforms B: matrix/mattermost/feishu/dingtalk/wecom/bluebubbles/sms/email → smoke. (weixin stays stub.)
23. **[FEAT]** `gateway/platforms/api_server.py` + `webhook.py` hardening + OpenAPI spec emitted.
24. **[TEST]** runtime backends `tools/environments/*` (local/docker/ssh/modal/daytona/singularity/vercel_sandbox) + `hibernation` lifecycle.
25. **[FEAT]** browser parity: `browser_cdp_tool.py`/`browser_camofox.py`/`browser_supervisor.py` + dialog handling smoke.
26. **[FEAT]** vision + `image_generation_tool.py` + `video_generation_tool.py` behind one provider abstraction.
27. **[FEAT]** TTS/STT: `tts_tool.py`/`transcription_tools.py`/`neutts_synth.py`/`voice_mode.py` parity.
28. **[FEAT]** unified web search across `web_tools.py`/`x_search_tool.py` (exa/firecrawl/parallel) + deterministic rank.
29. **[FEAT]** `delegate_tool.py` subagents parity (foundation for U61 teams).
30. **[FEAT]** `cronjob_tools.py` durable scheduler parity.
31. **[MAJOR][FEAT]** memory parity: `xavani_memory/episodic.py` FTS5 + LLM summarization + deterministic user model.
32. **[FEAT]** MCP server hosting: expose Xavani tools as an MCP server (new `tools/mcp_server.py`).
33. **[FEAT]** datagen pipeline parity (`datagen-config-examples/` + runner).
34. **[MAJOR][FEAT]** plugin system parity + local plugin registry (reuse `xavani_registry/`).
35. **[FEAT]** `homeassistant_tool.py` / smart-home parity.
36. **[FEAT]** document tools: pdf/docx/xlsx/pptx (new `tools/document_tools.py`, lazy deps).
37. **[FEAT]** diagramming (mermaid) + manim video tool.
38. **[DOC]** auto-generated parity report page from U19's matrix.

### M3 — v0.4.x "Full-stack security" [MAJOR]
39. **[MAJOR][SEC]** prompt-injection defense layer → `agent/detectors/injection.py` (deterministic patterns) + policy engine; register in A3.
40. **[SEC]** tool RBAC/capability scoping per session/persona (extend `tools/registry.py` dispatch gate).
41. **[SEC]** secrets manager + log/telemetry redaction (reuse `tools/credential_files.py`).
42. **[MAJOR][SEC]** sandbox hardening: egress allowlist + seccomp/landlock for local exec + resource caps (`tools/environments/local.py`).
43. **[SEC]** SSRF/DNS-rebind hardening → extend `tools/url_safety.py`/`website_policy.py`.
44. **[SEC]** path-traversal hardening across file tools (reuse `tools/path_security.py`).
45. **[SEC]** hash-chained tamper-evident audit log of all tool calls (hook `model_tools` dispatch).
46. **[SEC]** per-platform rate limiting + quotas (generalize `gateway/platforms/signal_rate_limit.py`).
47. **[MAJOR][SEC][FEAT]** cyber-skills router: deterministic selection across 754 skills by ATT&CK/NIST tags (extends A1).
48. **[SEC]** deterministic PII detection + redaction → `agent/detectors/pii.py`; register in A3.
49. **[SEC]** configurable content-safety filters.
50. **[SEC]** supply-chain: OSV (`tools/osv_check.py`) + pip-audit + CycloneDX SBOM + signed releases.
51. **[SEC]** security CI gates: bandit, semgrep, gitleaks, trivy (`.github/workflows/`).
52. **[SEC]** optional encrypted memory at rest.
53. **[SEC]** mTLS + webhook signature verification on every gateway platform (audit each adapter).
54. **[SEC]** permission-prompt + destructive-action confirmation hardening (`tools/slash_confirm.py`/`approval.py`).
55. **[MAJOR][SEC]** red-team eval harness (injection/jailbreak/exfil) gating releases (extends eval harness).
56. **[DOC][SEC]** STRIDE threat model + `SECURITY.md` + hardening guide.
57. **[SEC]** dependency pinning + reproducible `nix` build verification.
58. **[SEC]** pre-commit secret/egress scanning.
59. **[SEC]** sandboxed execution for cyber-skill scripts (run under U42 sandbox).
60. **[DOC][SEC]** prompt-injection/red-team docs on website.

### M4 — v0.5.0 "New capabilities" (net-new features)
61. **[MAJOR][FEAT]** multi-agent teams (parallel agents, file-ownership coordination, message bus) — builds on `delegate_tool.py`.
62. **[MAJOR][FEAT]** workflow/DAG engine for durable multi-step tasks (resume/retries).
63. **[FEAT]** knowledge-graph memory (entities/relations) — deterministic query.
64. **[FEAT]** local vector store (no external cost) + RAG over local docs.
65. **[FEAT]** reflection/self-eval loop (deterministic triggers; LLM only for critique).
66. **[FEAT]** cost analytics dashboard (per-tool/per-model + A5 savings) in `xavani_observability/dashboard.py`.
67. **[FEAT]** agent personas/profiles manager.
68. **[FEAT]** structured-output / JSON-schema enforcement layer.
69. **[FEAT]** long-context compaction strategies (deterministic selection).
70. **[FEAT]** checkpoint/resume for long runs (extend `tools/checkpoint_manager.py`).
71. **[FEAT]** cost-aware model router (cheap-first, escalate on failure).
72. **[FEAT]** cross-session tool-result cache (content-hash; reuse `tools/tool_result_storage.py`).
73. **[FEAT]** browser automation recorder → replayable scripts.
74. **[FEAT]** data-analysis toolkit (pandas/sql + charts).
75. **[FEAT]** scheduled autonomous "watcher" tasks (deterministic triggers).
76. **[FEAT]** web dashboard: real-time agent monitor + run history.
77. **[FEAT]** voice assistant mode (optional wakeword; reuse `voice_mode.py`).
78. **[FEAT]** notebook/REPL tool.
79. **[FEAT]** email/calendar ops expansion (reuse `microsoft_graph_client.py`).
80. **[FEAT]** social/content ops toolkit.
81. **[FEAT]** artifact builder (images/diagrams/reports).
82. **[FEAT]** offline knowledge-base bundling.

### M5 — v0.5.x "DX, performance, quality"
83. **[PERF]** fix the slow prompt/banner build (10s category lookup noted in `agent/skill_utils.py`).
84. **[TEST]** coverage → 80%+; eliminate new skips.
85. **[DX]** mypy strict + ruff + pre-commit + type coverage.
86. **[PERF]** lazy-import audit + startup-time budget.
87. **[DX]** benchmark suite + perf-regression CI.
88. **[DX]** one-line installer + docker + nix + pypi parity (`install.sh`/`docker/`/`nix/`/`packaging/`).
89. **[DX]** pydantic config validation + expanded `xavani doctor`.
90. **[DOC]** tutorials/quickstart/cookbook.
91. **[I18N]** additional locales beyond zh-CN (`locales/`).
92. **[DX]** resilience: retries, circuit breakers, graceful degradation.
93. **[DX]** structured logging + redaction + levels.
94. **[TEST]** fuzz/property tests for `tools/patch_parser.py` + `tools/schema_sanitizer.py`.

### M6 — v0.6.0 "Release engineering & governance"
95. **[DX]** automated CHANGELOG + semantic-release.
96. **[SEC][DX]** signed, reproducible releases + provenance attestations.
97. **[DOC]** versioned docs site + migration guides.
98. **[TEST]** full E2E smoke across platforms in CI.
99. **[MAJOR]** guidelines gate as a **CI merge gate** (`.github/workflows/`) — block merges failing the deterministic checks.
100. **[DOC]** "1.0 readiness" review + roadmap refresh.

**Tally:** [MAJOR] = U7, U9, U19, U20, U31, U34, U39, U42, U47, U55, U61, U62, U99 (13 ≥ 10 ✓).
[FEAT] ≥ 20 ✓ (M1/M2/M4 alone exceed it). Security: M3 (22 items) + cross-cutting ✓. Parity: M2 ✓.

---

## 3. Sequencing
**M0 → M1 (do first — it cuts token cost on every later turn) → M3 security ∥ M2 parity → M4 → M5 → M6.**
One update = one small PR-sized change + its tests + its Verify. Milestones are independently releasable.
Bump the version (R9) once per milestone tag.

## 4. Definition of Done (per milestone + global)
```
python3 -m pytest -q                      # full suite green, no new skips (R5)
python3 -m pytest -k "no_llm or detector" # R10: detectors make ZERO model calls
xavani doctor                             # passes incl. the U18 model-client guard
xavani route "<any task>"                 # returns skills with NO API call (A4)
find optional-skills/cybersecurity -name SKILL.md | wc -l   # 754, all indexed (M0)
python3 -c "import agent.skill_router, agent.detectors, tools.tool_prefilter; print('OK')"
grep -rniE '\b(nous|hermes)\b' <changed files>   # only existing LICENSE/README attribution (R1)
git status --porcelain | grep -E "skills_hub|weixin|default_soul" && echo VIOLATION || echo "stubs+identity intact"
git log origin/main..HEAD                 # only what the USER chose to land — Xavani never pushes
```
**Done = all 100 updates shipped, every Verify green, R1/R2/R7/R10 clean, nothing pushed by the agent.**
If an item can't be done safely, STOP and leave a precise `TODO(xavani v0.x)` with the blocker — never fake a pass.

## 5. Xavani's audit charter (after each milestone)
Xavani re-runs §4 + the v0.3.0 charter (scrub, stubs, identity, tests, surgical diffs, no-push) with
file:line evidence and revises until green — **one milestone at a time**, to respect the user's budget.
