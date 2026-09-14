# Xavani Reliability and Workbench Implementation Plan

> Implement this plan with `subagent-driven-development` after Andile approves execution.
> Use 1 implementation worker at a time.
> Review specification compliance before code quality.

## Goal

Make Xavani a reliable Enternovate agent with a secure desktop, visible work, verified deliverables, and practical business workflows.

## Plan status

- This document is a plan, not an implementation report.
- This turn changes only this plan file.
- No application tests run during this turn.
- No application starts during this turn.
- No release, commit, push, or installation occurs during this turn.
- Expected results below define acceptance criteria.
- Expected results do not describe tests that already pass.
- Do not interpret this plan as publication approval.

## Current context

### Workspace map

Use these exact paths:

- Agent root: `/Users/andilemushwana/xavani-agent`.
- Desktop root: `/Users/andilemushwana/xavani-desktop`.
- Local reference: `/Users/andilemushwana/.upstream/the upstream project`.
- Plan root: `/Users/andilemushwana/.upstream/plans`.

A path with the prefix `agent:` starts at the agent root.
A path with the prefix `desktop:` starts at the desktop root.
A path with the prefix `reference:` starts at the local reference.
Do not confuse `agent:agent/` with the agent root.

### Inspected revisions

- Agent HEAD: `491121d8cfe10fb0aca469e10fed28aa54ccbd65`.
- Desktop HEAD: `731c24beeedf107257cbfdd06dbb39e13129b8c5`.
- Local reference HEAD: `a84a2223f82c3d9906fd4a9d778a188774e7a08e`.
- Observed upstream remote HEAD: `330004e59797c8ebe6c752007b046673d19ec25b`.
- Observed the upstream project HEAD: `5e0661cd9c98c791a440ab111f4123b45abc4bbb`.

The remote branches move independently of this plan.
Use the pinned revisions for comparisons.
The GitHub timestamps differ from the local inspection clock.
Do not use those timestamps to infer elapsed work.

### Working tree

The agent tree has no changes at inspection.
The desktop tree contains these existing changes:

- A modified `README.md`.
- An untracked `CHANGELOG.md`.
- An untracked `.upstream/` directory.

Preserve those changes.
Do not stage those paths unless Andile assigns ownership.

### Runtime

- The agent requires Python `>=3.11,<3.14`.
- The local Python command is `/opt/homebrew/bin/python3.11`.
- The inspected Python version is `3.11.15`.
- The inspected Node version is `v25.9.0`.
- The inspected npm version is `11.12.1`.
- The desktop uses Electron and plain JavaScript.
- The desktop backend uses Python and aiohttp.
- The desktop editor currently uses a textarea with syntax overlays.
- The agent already has LSP modules under `agent/lsp/`.

Do not use the system Python without checking its version.
Do not assume the existing `.venv` uses Python 3.11.
Do not install dependencies during a read-only audit.

### Version conflict

Both current package files declare `0.3.0`.
The desktop repository also has the tag `v0.4.0`.
The package at that tag declares `0.4.0`.

Treat this conflict as a release blocker.
Do not publish another desktop `0.3.0` package.
Do not overwrite the `v0.4.0` tag.
Select new versions only after the release inventory in Task 01.

## Assumptions

- Xavani remains an agent product.
- Xavani does not become an inference host or a subscription portal.
- The desktop targets macOS and Windows.
- The agent retains its current supported platforms.
- The first workspace implementation supports 1 selected root per window.
- A user may select a workspace outside the home directory through a native folder dialog.
- A model cannot grant workspace access.
- The phrase "flip page" means the existing `/flip` behavior, with visible controls and preserved state.
- The phrase "record" includes voice notes, a work timeline, and explicit screen capture.
- Screen capture starts only after a user action.
- Financial analysis does not authorize payments, trades, payroll, or tax submissions.
- Business coverage means named, tested workflows, not a claim of universal competence.
- Local storage does not mean local inference when the user selects a remote provider.

## Architecture

Keep the Python agent as the execution authority and retain the Electron desktop as its client.
Extend existing tools, skills, session storage, and evaluations instead of creating a second agent core.
Add a shared completion contract, a secure workspace boundary, and a desktop workbench that shows actual execution evidence.

## Governing limits

### Reliability claim

No design can make every model correct on every task.
A weak model can misunderstand requirements or produce incorrect code.
A test suite can miss defects.

Xavani shall instead enforce these rules:

- Require explicit acceptance criteria for work tasks.
- Load the relevant skill content before the first consequential action.
- Execute objective checks outside the model response.
- Reject missing, stale, or contradictory evidence.
- Distinguish a completed turn from a verified task.
- Limit repair attempts to 2 for each failed checkpoint.
- Preserve partial work when a provider fails.
- Stop with a specific blocker when the checks cannot pass.
- Never silently select a different model or provider.
- Never report a successful release from a local build alone.

A model review supplements objective checks.
A model review never replaces objective checks.

### Brand boundary

Use these product identifiers:

- Product: `Xavani`.
- Agent package: `xavani-agent`.
- Desktop package: `xavani-desktop`.
- Publisher: `Enternovate`.
- macOS identifier: `com.enternovate.xavani`.
- Support identity: `enquiries@enternovate.com`.

Do not copy upstream product marks, subscription links, telemetry, account portals, or default inference endpoints.
Do not rename a third-party provider identifier that an external API requires.
Do not delete required copyright or license notices.

Keep legal attribution in `LICENSE`, `THIRD_PARTY_NOTICES.md`, and the About dialog's legal section.
Legal attribution does not constitute product branding.

The inspected the upstream project license names these copyright holders:

- Mario Zechner.
- Can Bölük.
- Stencil Labs, Inc.

Preserve the relevant notices when code derives from that project.
Do not claim Enternovate wrote all upstream code.

### Will NOT touch

- `/Users/andilemushwana/.upstream/config.yaml`.
- upstream profiles, plugins, cron jobs, or memories.
- The local upstream installation.
- Live `~/.xavani/` configuration, credentials, or sessions during tests.
- Trading repositories or live trading parameters.
- `bot/signals.py` or `bot/strategy/`.
- Browser extension versions or repositories.
- Unrelated desktop README changes.
- Existing public tags.
- Remote repositories without separate approval.
- Windows VPS commands.

Use CI or user-operated Windows steps for Windows validation.

## Evidence map

This comparison covers the named mechanisms below.
It does not claim complete parity across every upstream module.

### E01: Reuse existing edit modes

Evidence:

- `agent:tools/edit_tool.py:79`: `resolve_edit_mode`.
- `agent:tools/edit_tool.py:203`: `_apply_hashline`.
- `agent:tools/hashline/snapshots.py:94`: `SnapshotStore`.
- `agent:tools/hashline/apply.py`: the existing apply engine.

Decision: harden, not recreate.

The edit handler uses `default_store`.
Its first-edit fallback reads the whole file and records the full range.
That behavior does not prove the model saw the full range.
The backend check also returns local mode when configuration reads fail.

Tasks 06 and 07 close these specific gaps.
Do not add a new edit syntax.

### E02: Learn strict stream termination

Source:

`https://github.com/can1357/the upstream project/blob/5e0661cd9c98c791a440ab111f4123b45abc4bbb/packages/ai/src/utils/event-stream.ts`

The source rejects `end()` without a terminal result.
The source separates pending local work from a provider stall.

Xavani already normalizes responses in `agent:agent/transports/types.py`.
The desktop currently ends its event loop on a read error.
It can render accumulated text without a terminal run state.

Decision: retain the transport design.
Add strict desktop terminal-state checks in Task 10.
Do not treat a broken connection as success.

### E03: Learn cancellation ownership

Sources:

- `reference:agent/interrupt_scope.py:24`: `InterruptScope`.
- `https://github.com/can1357/the upstream project/blob/5e0661cd9c98c791a440ab111f4123b45abc4bbb/packages/agent/src/agent-loop.ts`.

The reference scope remembers cancellation before a child registers.
The the upstream project loop separates steering from destructive interruption.
It preserves queued input after an external abort.

Decision: test and harden Xavani's existing cancellation paths.
Do not copy the TypeScript loop into Python.
Task 08 specifies the required outcomes.

### E04: Add completion evidence

Sources:

- `reference:agent/verification_evidence.py:90`: `VerificationEvidence`.
- `reference:agent/verification_evidence.py:141`: `_transaction`.
- `reference:agent/verification_stop.py:158`: `build_verify_on_stop_nudge`.

The reference ledger records verification results.
The reference stop guard provides bounded follow-up guidance.
The inspected reference defaults that guard to off.

Xavani has these related features:

- `agent:agent/self_critique.py:75`: model self-review.
- `agent:agent/conversation_loop.py:3608`: optional self-review call.
- `agent:agent/conversation_loop.py:4142`: a failed-write footer.
- `agent:tools/guidelines_gate_tool.py:162`: a diff-based gate.
- `agent:xavani_operator/verify.py:30`: deterministic operator checks.

Those features do not establish a universal, fresh completion contract.
Decision: add the small contract in Tasks 03 through 05.
Keep the existing checks as inputs, not separate completion authorities.

### E05: Preserve skills across compression

Source:

`https://github.com/can1357/the upstream project/blob/5e0661cd9c98c791a440ab111f4123b45abc4bbb/packages/agent/src/compaction/tool-protection.ts`

The source protects skill reads and artifact recovery reads.
Xavani already has these modules:

- `agent:agent/skill_bundles.py`.
- `agent:agent/skill_utils.py`.
- `agent:agent/skill_commands.py`.
- `agent:agent/history_shake.py`.
- `agent:agent/conversation_compression.py`.
- `agent:xavani_learner/context_enricher.py`.

Decision: reuse discovery and bundles.
Add required-skill receipts and compression recovery tests.
Do not inject the entire skill library into every prompt.

### E06: Retain the current desktop features

Evidence:

- `desktop:src/renderer/index.html:83`: Explorer.
- `desktop:src/renderer/index.html:172`: Studio editor.
- `desktop:src/renderer/index.html:190`: Preview dock.
- `desktop:src/renderer/app.js:1601`: `/flip`.
- `desktop:src/renderer/app.js:1952`: voice capture.
- `desktop:src/renderer/app.js:2617`: Studio state.
- `desktop:src/renderer/app.js:3015`: dock tabs.
- `desktop:src/renderer/app.js:640`: edit diff display.

Decision: integrate and improve these features.
Do not create a competing editor or preview state store.

### E07: Correct the desktop trust boundary

Evidence:

- `desktop:backend/serve_desktop.py:1216`: `_safe_path`.
- `desktop:backend/serve_desktop.py:1221`: string-prefix containment.
- `desktop:backend/serve_desktop.py:1303`: direct file overwrite.
- `desktop:backend/serve_desktop.py:1417`: file mutation routes.
- `desktop:backend/serve_desktop.py:1444`: application without authentication middleware.
- `desktop:src/main.js:193`: media permission without an origin check.
- `desktop:src/renderer/index.html:204`: preview with `allowpopups`.
- `desktop:src/main.js:298`: IPC without sender validation.

Decision: implement Tasks 09, 11, and 12 before new business or capture actions.
A localhost listener alone does not provide authorization.

### E08: Correct the evaluation gate

Evidence:

- `agent:scripts/task_bench/regression_gate.py:26` reads `success_rate`.
- `agent:scripts/task_bench/regression_gate.py:52` compares only time and cost.
- `agent:scripts/task_bench/run_bench.py` already supports objective verifiers.
- `agent:tests/harness/faux_provider.py` already drives the real agent loop.

Decision: extend the current harness.
Task 02 rejects lower success rates and invalid measurements.
Do not describe scripted-provider results as real-model performance.

### E09: Reuse finance and operations

Evidence:

- `agent:xavani_operator/finance/money.py` uses integer cents and Decimal.
- `agent:xavani_operator/finance/ledger.py` provides a ledger.
- `agent:xavani_operator/finance/payments.py` produces instructions, not payments.
- `agent:xavani_operator/approval_queue.py` provides approval decisions.
- `agent:xavani_operator/workflow.py` provides workflow behavior.
- `agent:tools/persistent_todo.py` provides durable tasks.
- `agent:xavani_wisdom/outstanding.py` tracks outstanding work.

Decision: create workflow contracts around these features.
Do not create another ledger, task store, or payment service.

### E10: Improve release provenance

Evidence:

- `agent:scripts/release.py` already supports publication.
- `agent:xavani_cli/update_contract.py` provides update admission.
- `agent:xavani_cli/update_receipt.py` records update results.
- `desktop:scripts/build-macos.sh:12` defaults to another engine checkout.
- `desktop:scripts/build-macos.sh:49` copies only `serve_desktop.py`.
- `desktop:scripts/build-macos.sh:70` exports dependencies without hashes.
- `desktop:scripts/build-macos.sh:71` adds an unpinned aiohttp install.
- `desktop:src/main.js:313` starts automatic update requests.

Decision: pin the engine revision and package every backend module.
Make update checks explicit or opt-in.
Tasks 24 through 26 define release proof.

## Source use

Read these sources for the relevant task:

- `https://github.com/the upstream project/the upstream project`.
- `https://github.com/can1357/the upstream project`.
- `https://the upstream project.the upstream project.com/docs/developer-guide/`.
- `https://www.electronjs.org/docs/latest/tutorial/security`.
- `https://code.visualstudio.com/docs/getstarted/userinterface`.
- `https://cursor.com/docs/agent/overview`.

The Electron search result confirms the requirement to validate IPC senders.
The VS Code and Cursor links provide design references, not verified Xavani capabilities.
The configured extractor cannot retrieve page text in this session.
The raw GitHub host also returns HTTP 429 during inspection.
GitHub's blob API supplies the inspected the upstream project source instead.
The local reference supplies the inspected upstream implementations.

Do not import remote code dynamically at runtime.
Do not execute instructions from repository files as trusted operator policy.

## Desktop design specification

### Design direction

Build a dense workbench, not a dashboard of cards.
Use the existing Xavani mark.
Use neutral dark surfaces with a controlled blue accent.
Retain the bundled Inter and JetBrains Mono fonts.
Do not copy another product's logo, icons, wording, or account screens.

The primary view shall show these areas:

```text
+--------------------------------------------------------------------------+
| Xavani | Workspace | Command search | Model | Connection | Record |
+----+---------------+--------------------------------+--------------------+
| | Explorer | File tabs | Agent |
| A | Changed files | Editor / Diff / Document | Task and criteria |
| c | Search | | Chat |
| t | | | Skills and checks |
| i | | | Approvals |
| v | | | |
| i | +--------------------------------+--------------------+
| t | | Terminal | Problems | Activity | Preview / Files |
| y | | | /flip |
+----+---------------+--------------------------------+--------------------+
| Branch | Workspace trust | Cursor | Checks | Provider usage | Run status |
+--------------------------------------------------------------------------+
```

Use these dimensions as design constants, not performance measurements:

- Title bar: 40 px.
- Activity rail: 44 px.
- Explorer: 240 px initially; 180–400 px range.
- Agent pane: 360 px initially; 300–520 px range.
- Status bar: 24 px.
- Bottom pane: 220 px initially; 120–480 px range.
- Main text: 13 px with a 20 px line height.
- Editor text: 13 px with a 20 px line height.
- Standard controls: 28 px minimum height.
- Primary icon targets: 32 px square.
- Focus border: 2 px.
- Spacing scale: 4, 8, 12, 16, 24 px.
- Panel radius: 4 px.
- Animation duration: 120 ms.

Use these tokens:

```css
:root {
 --workbench-bg: #0b1017;
 --workbench-panel: #111923;
 --workbench-raised: #182331;
 --workbench-border: #425368;
 --workbench-text: #e7edf5;
 --workbench-muted: #a9b6c6;
 --workbench-accent: #69adff;
 --workbench-success: #79d99e;
 --workbench-warning: #f0c36c;
 --workbench-danger: #ff9898;
}
@media (prefers-reduced-motion: reduce) {
 *, *::before, *::after {
 animation-duration: 0s !important;
 transition-duration: 0s !important;
 }
}
```

Measure contrast before approval.
Normal text shall meet a contrast ratio of 4.5:1.
Controls and focus indicators shall meet 3:1 against adjacent colors.
Color shall not provide the only status signal.

### Layout behavior

- At 1440×900, show Explorer, editor, Agent, and the bottom pane together.
- At 1280×800, retain the editor and Agent side by side.
- At 1024×768, collapse Explorer to an overlay.
- Below 1180 px, place Preview inside the central tab group.
- Below 1000 px, show either the central group or Agent through explicit tabs.
- At 980×620, every action shall remain reachable without horizontal page scrolling.
- At 200% zoom, use the compact layout.
- Persist pane sizes by workspace and profile.
- Clamp restored dimensions to the current viewport.
- Do not persist tokens, transcript text, or file contents in localStorage.
- Provide a Reset layout command.

### Flip behavior

Keep `/flip` as an alias.
Add a visible `Preview / Files` control.
Use `Cmd+Shift+P` or `Ctrl+Shift+P` for command search.
Use `Cmd+Alt+F` or `Ctrl+Alt+F` for Flip.
Do not reuse `Cmd+P`, which opens files.

The Flip contract shall contain these rules:

- Toggle between the current preview and the last changed file.
- Preserve the preview URL and navigation state.
- Preserve each file's scroll position.
- Preserve the editor selection and unsaved buffer.
- Preserve keyboard focus unless the user explicitly changes it.
- Do not reopen a pane that the user closes.
- Do not follow a changed file while the user edits an unsaved buffer.
- Resume following only after the user selects Follow.
- Show `No changed file` when no file exists.
- Disable Flip during a workspace transition.
- Use a 120 ms opacity transition, not a rotating page animation.
- Use no transition when reduced motion applies.

### File visibility

Show actual files, not names inferred from prose.
Each activity item shall include these fields:

- Run ID.
- Tool call ID.
- Workspace ID.
- Relative path.
- Operation.
- State.
- Before hash.
- After hash.
- Event sequence.
- Verification state.

Allowed operation states:

- `queued`.
- `active`.
- `changed`.
- `conflict`.
- `failed`.
- `verified`.

A tool start does not prove a file change.
A successful process exit does not prove a deliverable works.
A changed file becomes verified only after its required checks pass on that revision.

### Editor

Use Monaco as an editor component, not as a second application framework.
Pin its dependency and worker assets in the desktop lockfile.
Do not load editor assets from a CDN.
Retain the current editor behind a temporary feature flag until parity passes.

The editor shall support these functions:

- File tabs with unsaved markers.
- Find and replace.
- Syntax display.
- Line numbers.
- Keyboard navigation.
- Side-by-side and inline diff.
- Conflict review.
- Save with an expected revision.
- LSP diagnostics from the existing agent service.
- Keyboard-accessible Problems navigation.

The first release does not implement an extension marketplace or a debugger.
Do not embed all of VS Code.
Do not promise Cursor's proprietary features.

### Agent pane

Keep chat visible during code work.
Use 4 mode labels:

- Ask: read and explain.
- Plan: produce a plan without implementation.
- Build: act within the approved workspace and action policy.
- Review: inspect changes and record findings.

A mode label shall change backend permissions, not only prompt text.
The default mode is Ask for an untrusted workspace.
A new workspace requires an explicit trust decision before command execution.

Show the following information above the transcript:

- Task goal.
- Acceptance criteria.
- Selected workflow.
- Loaded skills.
- Model and provider.
- Current checkpoint.
- Pending approvals.
- Verification summary.

Show an explicit `Blocked` state with a reason and a recovery action.
Do not replace a blocked state with a green completion mark.

### Preview

- Use an isolated Electron session partition.
- Deny Node integration and preload injection.
- Deny popups by default.
- Deny camera, microphone, notifications, downloads, and clipboard access by default.
- Block access to the desktop and engine control ports.
- Allow a user-selected local development origin.
- Require user confirmation before external navigation.
- Block `file:`, `javascript:`, and unknown schemes.
- Treat page content and visual annotations as untrusted input.
- Keep visual edits as proposals until the user approves a source patch.
- Show a diff before a source patch applies.
- Never convert arbitrary preview JavaScript into privileged IPC.

### Recording

Provide 3 distinct functions:

- Voice note: audio becomes a draft message.
- Work timeline: a local event log records actions and evidence.
- Screen recording: an explicit user action records a selected surface.

Screen recording shall use these defaults:

- Off by default.
- Current Xavani window by default.
- Microphone off by default.
- 1280×720 maximum export size for the initial implementation.
- 15 frames per second.
- 30-minute duration limit.
- 250 MiB file limit.
- A persistent red indicator.
- Pause, resume, stop, and discard controls.
- No automatic upload.

Do not claim automatic pixel redaction.
Screen pixels can contain secrets.
Show that warning before capture.
Mask secret forms in the application before capture starts.
Pause capture when the application opens a secret-entry dialog.

Record to a temporary file outside the workspace.
Use a native Save dialog after Stop.
A replay viewer shall not replay commands or external actions.

## Completion contract

### Authority

The host owns the contract and verification results.
The model may propose criteria but cannot mark them passed.
The user approves consequential criteria and actions.
The model cannot change the verifier definition after it starts work.

A contract shall contain these fields:

- `contract_id`.
- `session_id`.
- `workspace_id`.
- `workflow_id`.
- `goal`.
- `required_checks`.
- `required_skills`.
- `allowed_actions`.
- `approved_at`.
- `revision`.

A verification receipt shall contain these fields:

- `receipt_id`.
- `contract_id`.
- `check_id`.
- `workspace_id`.
- `revision`.
- `command_argv`.
- `cwd`.
- `exit_code`.
- `status`.
- `artifact_hashes`.
- `started_at`.
- `finished_at`.
- `origin`.

Allowed receipt statuses:

- `passed`.
- `failed`.
- `blocked`.
- `cancelled`.

Use `origin="host"` only for checks that the trusted runner executes.
A model response or child summary shall never create a host receipt.
A missing receipt means unverified work.
A newer file revision invalidates the relevant receipt.

### Revision scope

Compute the revision from the contract inputs and the actual workspace content.
Include these inputs:

- Every declared source file.
- Every declared test file.
- The verifier definition.
- Dependency manifests and lockfiles.
- Build configuration.
- The active workspace root.
- Relevant tool versions.

Do not use `git HEAD` alone.
Uncommitted files affect the revision.
Do not hash credential files.
Reject a contract that requires a credential file as an artifact.

For the first implementation, invalidate all task receipts after any task-owned file change.
This rule avoids incorrect dependency inference.
Optimize invalidation only after measurements show a need.

### Completion states

Keep run state and verification state separate.

Run states:

- `queued`.
- `running`.
- `waiting_approval`.
- `stopping`.
- `completed`.
- `failed`.
- `cancelled`.
- `interrupted`.

Verification states:

- `not_required`.
- `unverified`.
- `passed`.
- `failed`.
- `blocked`.

A completed turn can contain unverified work.
The user interface shall show both states.
Only a passed contract permits the label `Verified`.

A provider EOF without a terminal result means interrupted work.
A timeout after an external action means an unknown outcome until reconciliation.
Never retry a non-idempotent action solely because its response disappears.

## Business coverage

### Shared workflow sequence

Each business workflow shall use this sequence:

1. Read the task scope.
2. Identify the company and reporting period.
3. Check source permissions.
4. Load the required skill content.
5. Validate the source data.
6. Produce a draft artifact.
7. Execute the objective checks.
8. Request approval for an external action.
9. Execute only the approved action.
10. Read the exact external target to confirm the result.
11. Record the result and outstanding work.

Do not combine approval with result verification.
Approval authorizes an action.
Verification confirms its outcome.

### Initial workflow inventory

B01: Finance analysis.

- Skills: `oag_skills/finance/3-statement-model/SKILL.md`, `oag_skills/finance/dcf-model/SKILL.md`, `oag_skills/finance/excel-author/SKILL.md`.
- Inputs: dated statements, currency, period, source references, and explicit assumptions.
- Outputs: a workbook, a formula report, and a source list.
- Checks: statement reconciliation, units, signs, currency consistency, finite values, formula results, and missing data.
- Restriction: no investment order or tax filing.

B02: Invoice review.

- Skill: `oag_skills/workflow-packs/invoice-extraction/SKILL.md`.
- Inputs: invoice files and an owner-approved supplier list.
- Outputs: extracted rows, duplicate flags, and an exception list.
- Checks: source page references, totals, currency, invoice number, and duplicate identity.
- Restriction: no payment execution.

B03: Daily operations.

- Skills: `oag_skills/business/business-assistant/SKILL.md`, `skills/productivity/planner/SKILL.md`.
- Inputs: approved calendar and task sources.
- Outputs: a daily brief and task proposals.
- Checks: owner, deadline, source, priority, and duplicate identity.
- Restriction: a missing source becomes `Unavailable`, not an empty schedule.

B04: Inbox and customer support.

- Skill: `skills/email/himalaya/SKILL.md`.
- Inputs: an approved mailbox and company response rules.
- Outputs: priorities and reply drafts.
- Checks: recipient, thread, facts, attachment list, and prohibited disclosures.
- Restriction: send approval binds the exact recipient and body hash.

B05: Meetings.

- Skill: `oag_skills/workflow-packs/meeting-notes/SKILL.md`.
- Inputs: a transcript or owner-selected recording.
- Outputs: decisions, action items, owners, and source timestamps.
- Checks: every action links to source evidence.
- Restriction: the workflow does not invent owners or deadlines.

B06: Sales and marketing.

- Skill: `oag_skills/business/business-assistant/SKILL.md`.
- Inputs: approved product facts, audience, and contact records.
- Outputs: drafts, follow-up tasks, and campaign summaries.
- Checks: factual claims, recipient consent, unsubscribe requirements, and brand rules.
- Restriction: no autonomous campaign publication.

B07: People and administration.

- Skill: `oag_skills/business/business-assistant/SKILL.md`.
- Inputs: authorized records and an explicit jurisdiction.
- Outputs: checklists, onboarding drafts, and exception reports.
- Checks: access scope, source facts, retention rules, and sensitive fields.
- Restriction: no hiring, dismissal, payroll, or eligibility decision.

B08: Procurement and inventory.

- Skill: `oag_skills/business/business-assistant/SKILL.md`.
- Inputs: stock records, supplier quotes, units, and approved limits.
- Outputs: shortage reports and purchase proposals.
- Checks: quantity units, supplier identity, totals, and duplicate orders.
- Restriction: no purchase order without approval.

B09: Legal and compliance support.

- Skills: `skills/software-development/security-review/SKILL.md`, `oag_skills/business/business-assistant/SKILL.md`.
- Inputs: jurisdiction, current authoritative sources, and authorized documents.
- Outputs: cited obligations and review checklists.
- Checks: source date, jurisdiction, quotation accuracy, and unresolved questions.
- Restriction: no claim of legal certification.

B10: Engineering and design.

- Skills: `skills/software-development/frontend-design/SKILL.md`, `skills/software-development/api-design-review/SKILL.md`, `skills/software-development/security-review/SKILL.md`.
- Inputs: an approved task, repository instructions, and acceptance criteria.
- Outputs: code, tests, a visual review, and execution evidence.
- Checks: tests, lint, build, security, accessibility, and actual user behavior.
- Restriction: no release without a separate release approval.

B11: Executive reporting.

- Skills: `oag_skills/finance/pptx-author/SKILL.md`, `skills/productivity/powerpoint/SKILL.md`.
- Inputs: verified domain reports and approved company facts.
- Outputs: a source-linked brief or presentation.
- Checks: totals, dates, contradictions, and source coverage.
- Restriction: do not invent board decisions or performance results.

B12: Safety and incidents.

- Skills: `skills/software-development/security-review/SKILL.md`, `oag_skills/security/oss-forensics/SKILL.md`.
- Inputs: authorized logs, incident scope, and response permissions.
- Outputs: evidence, a timeline, containment proposals, and recovery checks.
- Checks: evidence integrity, scope, approval, and recovery proof.
- Restriction: never execute destructive containment without explicit authorization.

The existing general business skill does not prove specialized B06–B09 capability.
Each workflow remains labelled `Draft support` until its domain cases pass.
Add domain-specific skill content only when the workflow evaluation shows a concrete gap.
Do not install the current upstream skill library into Xavani by copying a user profile.

## Implementation sequence

### Task conventions

Each numbered task defines a narrow outcome.
Its microsteps target 2–5 minutes of focused work each.
A build, test suite, or signing job can take longer.
Do not report the microstep target as a measured duration.

For every code task:

1. Add the stated failing test.
2. Run the exact test command.
3. Confirm the failure describes the missing behavior.
4. Apply the minimal implementation.
5. Run the test again.
6. Run the stated wider checks.
7. Review the staged diff.
8. Commit only the explicit paths.

Do not collect every failing test before implementation.
Complete 1 vertical slice before the next slice.
Do not delete a failing test to satisfy the gate.

### Common commands

Run agent commands from `/Users/andilemushwana/xavani-agent`.
Run desktop commands from `/Users/andilemushwana/xavani-desktop`.

Agent test command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/xavani_cli/test_regression_gate.py -q
```

Use the same command shape for each stated agent test path.
The runner shall use a verified Python 3.11 environment.
Task 01 checks that prerequisite.

Desktop Python command:

```sh
/opt/homebrew/bin/python3.11 -m pytest -o addopts= -q tests/desktop
```

Desktop JavaScript command:

```sh
node --test tests/desktop/test_semver.js
```

Syntax commands:

```sh
node --check src/main.js
node --check src/preload.js
node --check src/renderer/app.js
/opt/homebrew/bin/python3.11 -m ruff check backend
```

Commit sequence:

```sh
git diff --check
git diff --cached --stat
git diff --cached
git commit -m "fix: describe the verified change"
```

Stage only the exact paths stated by the task.
Never use `git add .` or `git add -A`.
Do not run a push command as part of this sequence.

### Task 01: Establish the baseline

Files:

- Read: `agent:AGENTS.md`.
- Read: `agent:pyproject.toml`.
- Read: `agent:scripts/run_tests.sh`.
- Read: `desktop:package.json`.
- Create after approval: `agent:docs/reliability/baseline.md`.
- Create after approval: `desktop:docs/reliability/baseline.md`.

Microsteps:

1. Record both working trees.
2. Record local and remote release tags through read-only commands.
3. Inspect the existing virtual environment's Python version.
4. Confirm pytest, ruff, and aiohttp imports in that environment.
5. Run the existing targeted baseline tests.
6. Record real failures without changing code.
7. Commit only the new baseline documents.

Commands:

```sh
git status --short
git log -1 --format='%H %cs %s'
git tag --list
/opt/homebrew/bin/python3.11 --version
.venv/bin/python --version
.venv/bin/python -c "import pytest, ruff, aiohttp; print('DEPENDENCIES_OK')"
```

Expected:

- The versions satisfy `>=3.11,<3.14`.
- The agent test environment uses Python 3.11 for this program.
- The dependency command prints `DEPENDENCIES_OK`.
- A missing prerequisite blocks execution.

Baseline test paths:

- `agent:tests/xavani_cli/test_regression_gate.py`.
- `agent:tests/tools/test_guidelines_gate.py`.
- `agent:tests/agent/test_self_critique.py`.
- `agent:tests/agent/test_self_critique_wiring.py`.
- `agent:tests/gateway/test_api_server_runs.py`.
- `desktop:tests/desktop/test_commands_endpoint.py`.
- `desktop:tests/desktop/test_diff_render.py`.
- `desktop:tests/desktop/test_semver.js`.

Do not call an inherited failure a random flake without evidence.

### Task 02: Make success rate a release gate

Files:

- Modify: `agent:scripts/task_bench/regression_gate.py`.
- Modify: `agent:tests/xavani_cli/test_regression_gate.py`.

Use Code Pack A.
Add each parameter row as its own RED → GREEN microcycle.

Verification:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/xavani_cli/test_regression_gate.py -q
/opt/homebrew/bin/python3.11 -m ruff check scripts/task_bench/regression_gate.py tests/xavani_cli/test_regression_gate.py
```

Expected:

- A lower success rate returns exit code 1.
- Missing, nonfinite, or invalid success data returns exit code 2.
- A valid non-regression returns exit code 0.
- Existing time and cost checks retain their behavior.

Commit:

```sh
git add scripts/task_bench/regression_gate.py tests/xavani_cli/test_regression_gate.py
git commit -m "fix: block releases on task success regressions"
```

### Task 03: Add the pure completion decision

Files:

- Create: `agent:agent/completion_contract.py`.
- Create: `agent:tests/agent/test_completion_contract.py`.

Use Code Pack B.
The function shall not execute commands or read user files.

Verification:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/agent/test_completion_contract.py -q
/opt/homebrew/bin/python3.11 -m ruff check agent/completion_contract.py tests/agent/test_completion_contract.py
```

Expected:

- Current host evidence can pass the contract.
- Stale, absent, cancelled, or model-authored evidence cannot pass.
- A blocked check returns blocked work.
- A failed check returns failed work.
- An empty required-check list returns `not_required` only for an explicit read-only contract.

Commit:

```sh
git add agent/completion_contract.py tests/agent/test_completion_contract.py
git commit -m "feat: add an evidence-based completion contract"
```

### Task 04: Add host receipts without a second task store

Files:

- Create: `agent:agent/verification_receipts.py`.
- Create: `agent:tests/agent/test_verification_receipts.py`.
- Read: `agent:xavani_state_wal.py`.
- Read: `agent:xavani_constants.py`.

Use Code Pack C.
Keep task identity in the existing session and task stores.
The new database stores only verification receipts.

Microcycles:

- A receipt survives a store reopen.
- A second profile cannot read the first profile's receipts.
- A malformed receipt fails before a database insert.
- Duplicate receipt IDs do not overwrite evidence.
- A failed transaction closes its connection.
- A database failure returns a blocker to the caller.

Verification:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/agent/test_verification_receipts.py -q
```

Expected: the receipt tests pass without real credentials or network access.

Commit:

```sh
git add agent/verification_receipts.py tests/agent/test_verification_receipts.py
git commit -m "feat: persist host verification receipts"
```

### Task 05: Connect the completion decision to real work

Files:

- Create: `agent:agent/verification_runner.py`.
- Modify: `agent:agent/tool_executor.py`.
- Modify: `agent:agent/conversation_loop.py`.
- Modify: `agent:agent/agent_init.py`.
- Modify: `agent:gateway/platforms/api_server.py`.
- Modify: `agent:tools/guidelines_gate_tool.py`.
- Create: `agent:tests/agent/test_completion_contract_wiring.py`.
- Create: `agent:tests/gateway/test_run_verification_state.py`.

Implement this task through the integration slices in Code Pack D.
Do not add a model-controlled `passed` argument to a tool.

Required RED cases:

- The model says `Done` before any check runs.
- The model says `Done` after a failed check.
- A file changes after a passing check.
- A child summary claims that tests pass without a host receipt.
- A provider fails during the second repair attempt.
- A plugin transforms the final text after checks fail.
- The user cancels during verification.
- A read-only explanation completes without a build check.

Expected:

- The host returns separate `run_state` and `verification_state` fields.
- Failed or absent checks never create a `Verified` label.
- A plugin cannot upgrade the verification state.
- Repair attempts stop after 2 attempts.
- Cancellation never triggers a repair attempt.
- The CLI, gateway, and desktop read the same verification state.

Commands:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/agent/test_completion_contract.py tests/agent/test_verification_receipts.py tests/agent/test_completion_contract_wiring.py tests/gateway/test_run_verification_state.py -q
```

Commit each integration slice separately.
Use explicit paths from that slice.

### Task 06: Fail closed when the edit backend is unknown

Files:

- Modify: `agent:tools/edit_tool.py`.
- Create: `agent:tests/tools/test_edit_backend_resolution.py`.

Use Code Pack E.
Do not weaken the working patch mode.

Expected:

- Explicit local mode permits the local edit implementation.
- Explicit remote mode rejects local file writes.
- A configuration exception rejects local file writes.
- A missing backend identity does not default to local mode.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/tools/test_edit_backend_resolution.py -q
```

Commit:

```sh
git add tools/edit_tool.py tests/tools/test_edit_backend_resolution.py
git commit -m "fix: reject edits when backend identity is unknown"
```

### Task 07: Scope hashline provenance to the active task

Files:

- Modify: `agent:tools/hashline/snapshots.py`.
- Modify: `agent:tools/edit_tool.py`.
- Modify: `agent:tools/file_tools.py`.
- Modify: `agent:tools/file_state.py`.
- Create: `agent:tests/tools/test_hashline_task_scope.py`.
- Create: `agent:tests/tools/test_hashline_visible_ranges.py`.

Microcycles:

1. Add a task-scoped store lookup.
2. Make read results record only the displayed line ranges.
3. Make search results record only the displayed matching lines.
4. Change edit lookup to use the same task identity and canonical path.
5. Remove the first-edit full-range auto-record branch.
6. Return an actionable read requirement for an unknown snapshot.
7. Remove a task store through the existing task cleanup path.
8. Run the existing hashline suite.

Required cases:

- Task A reads a file; Task B cannot use A's seen ranges.
- A partial read cannot authorize an unseen line.
- A truncated line does not count as a complete observed line.
- A stale tag cannot authorize a changed file.
- A short tag collision does not bypass full-content comparison.
- A relative path resolves against the active task's backend.
- An unknown task identity refuses hashline mode.
- Task cleanup releases its snapshot store.

Use the API contract in Code Pack F.
Keep patch mode available when hashline mode lacks provenance.
Do not let fallback mode silently weaken the selected safety policy.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/tools/test_hashline_task_scope.py tests/tools/test_hashline_visible_ranges.py -q
```

Expected: no cross-task snapshot reuse and no unseen-line edit.
Commit each microcycle after its focused test passes.

### Task 08: Preserve cancellation and recovery semantics

Files:

- Modify: `agent:agent/conversation_loop.py`.
- Modify: `agent:tools/interrupt.py`.
- Modify: `agent:tools/delegate_tool.py`.
- Modify: `agent:gateway/platforms/api_server.py`.
- Create: `agent:tests/agent/test_cancel_boundaries.py`.
- Create: `agent:tests/gateway/test_run_recovery_contract.py`.

Use the current `AIAgent` and faux-provider harness.
Do not introduce another executor.

Required microcycles:

- Stop before the first provider call prevents that call.
- Stop during a provider stream closes that stream.
- Stop before child registration remains effective after registration.
- Stop during approval produces no action.
- A late tool result retains its actual result without creating a second action.
- Steering waits for an atomic file write to finish.
- Steering does not consume input after cancellation.
- A run retry does not repeat an unknown external action.
- A provider timeout preserves the transcript and workspace identity.

Use events and barriers in tests.
Do not test concurrency with arbitrary sleep calls.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/agent/test_cancel_boundaries.py tests/gateway/test_run_recovery_contract.py tests/gateway/test_sse_agent_cancel.py -q
```

Expected: each cancellation case terminates within its configured deadline.
The test shall assert the action count, not only the final text.

### Task 09: Authenticate both desktop servers

Files:

- Create: `desktop:backend/desktop_auth.py`.
- Create: `desktop:backend/__init__.py`.
- Modify: `desktop:backend/serve_desktop.py`.
- Create: `desktop:src/security.js`.
- Modify: `desktop:src/main.js`.
- Modify: `desktop:src/preload.js`.
- Create: `desktop:tests/desktop/test_desktop_auth.py`.
- Create: `desktop:tests/desktop/test_security.js`.

Use Code Pack G.
The main process creates a fresh secret for each backend generation.
Pass the secret through the backend's stdin bootstrap pipe.
Do not print the secret in the ready message.
Do not put the secret in a URL, argv, localStorage, or renderer JavaScript.

Set the engine adapter's `extra["key"]` explicitly.
The actual key name is `key`, not `api_key`.
Use the same authentication middleware for desktop HTTP and WebSocket upgrades.

The main process injects authorization only for its trusted renderer and the exact active control ports.
A preview webview shall not receive that header.
Validate every IPC sender against the trusted main frame.

Required cases:

- Missing secret: 401.
- Incorrect secret: 401.
- Foreign Origin: 403.
- Valid secret and permitted Origin: normal route response.
- Unauthenticated terminal upgrade: 401.
- Old generation secret after restart: 401.
- Preview request to a control port: denied.
- Foreign IPC sender: denied.
- Ready payload and logs: no secret.

Commands:

```sh
/opt/homebrew/bin/python3.11 -m pytest -o addopts= -q tests/desktop/test_desktop_auth.py
node --test tests/desktop/test_security.js
node --check src/main.js
node --check src/preload.js
```

Expected: all authentication cases pass without starting a real provider session.

### Task 10: Match tool events and detect interrupted streams

Files:

- Create: `desktop:src/renderer/run-state.js`.
- Modify: `desktop:src/renderer/app.js`.
- Modify: `desktop:src/renderer/index.html`.
- Modify: `agent:agent/tool_executor.py`.
- Modify: `agent:gateway/platforms/api_server.py`.
- Create: `desktop:tests/desktop/test_run_state.js`.
- Create: `agent:tests/gateway/test_tool_event_identity.py`.

Use Code Pack H.
Keep tool cards in a map keyed by `tool_call_id`.
Do not use `lastElementChild` to match a completion event.

Preserve this event envelope:

```json
{
 "schema_version": 1,
 "event": "tool.completed",
 "event_id": "run-1:2",
 "seq": 2,
 "run_id": "run-1",
 "tool_call_id": "call-1",
 "workspace_id": "workspace-1",
 "tool": "patch",
 "path": "src/example.py",
 "status": "completed"
}
```

This JSON is a test fixture, not execution evidence.

Microcycles:

- Two tools finish in the opposite order.
- A duplicate event does not create another card.
- A completion event arrives without a start event.
- A stream ends without a terminal event.
- A non-200 event response produces an error state.
- A final run snapshot overrides provisional streamed text.
- A reconnect obtains the authoritative snapshot before it resumes events.
- A replayed event cannot apply a file mutation.

Do not add unlimited SSE retry loops.
Use 2 reconnect attempts with 1-second and 2-second delays.
After both attempts fail, show `Disconnected` with a manual reconnect action.
A reconnect shall not submit a new run.

Commands:

```sh
node --test tests/desktop/test_run_state.js
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/gateway/test_tool_event_identity.py -q
```

Run the second command from the agent root.
Expected: correct tool identity and no false success on EOF.

### Task 11: Enforce the selected workspace boundary

Files:

- Create: `desktop:backend/workspace_paths.py`.
- Modify: `desktop:backend/serve_desktop.py`.
- Modify: `desktop:src/main.js`.
- Modify: `desktop:src/preload.js`.
- Modify: `desktop:src/renderer/app.js`.
- Create: `desktop:tests/desktop/test_workspace_paths.py`.

Use Code Pack I.
Replace home-prefix checks with selected-root containment.
A native folder selection creates a workspace grant.
A raw HTTP request cannot create that grant.

Microcycles:

- A relative path inside the workspace succeeds.
- A sibling directory with a matching string prefix fails.
- `..` traversal fails.
- A symlink path fails in the initial implementation.
- A control directory such as `.git` fails for write actions.
- A credential file fails for read and write actions.
- An empty root produces `Workspace required`.
- A valid external drive selection succeeds after native approval.
- A workspace change invalidates old grants and file handles.

Apply the boundary to every route:

- `/desktop/api/fs/root`.
- `/desktop/api/fs/tree`.
- `/desktop/api/fs/file`.
- `/desktop/api/fs/write`.
- `/desktop/api/fs/write-b64`.
- `/desktop/api/fs/find`.
- `/desktop/api/fs/mutate`.
- `/desktop/api/preview/brief`.

The model's terminal access needs the same workspace policy through the existing sandbox path.
A path resolver alone does not sandbox arbitrary terminal commands.
For an untrusted workspace, disable command execution until the sandbox path passes its real backend tests.

Command:

```sh
/opt/homebrew/bin/python3.11 -m pytest -o addopts= -q tests/desktop/test_workspace_paths.py
```

Expected: no route can use a raw path to escape the selected root.

### Task 12: Protect buffers from concurrent writes

Files:

- Create: `desktop:backend/workspace_files.py`.
- Modify: `desktop:backend/serve_desktop.py`.
- Modify: `desktop:src/renderer/app.js`.
- Create: `desktop:tests/desktop/test_workspace_files.py`.

Use Code Pack J.
A file read returns its SHA-256 revision.
A save includes that exact expected revision.

Microcycles:

- A current revision saves successfully.
- A stale revision returns 409 without modifying the file.
- A missing expected revision returns 428.
- An oversized write returns 413 before allocation expands without bound.
- An invalid UTF-8 file returns 415.
- A failed replacement preserves the previous file.
- A user buffer remains dirty after a conflict.
- The conflict view shows disk, buffer, and base versions.

A process-local lock coordinates desktop requests.
Use the existing engine file lock for actions that share the process.
Do not claim that a Python lock prevents another application from writing.
The initial release shall detect external changes and require conflict review.
A hostile same-user process remains outside this boundary.

Commands:

```sh
/opt/homebrew/bin/python3.11 -m pytest -o addopts= -q tests/desktop/test_workspace_files.py
```

Expected: the stale-write fixture retains its newer disk content.

### Task 13: Build the workbench shell

Files:

- Create: `desktop:src/renderer/workbench-state.js`.
- Create: `desktop:src/renderer/workbench.css`.
- Modify: `desktop:src/renderer/index.html`.
- Modify: `desktop:src/renderer/app.js`.
- Create: `desktop:tests/desktop/test_workbench_state.js`.
- Create: `desktop:tests/e2e/workbench.spec.js`.

Use Code Pack K for the state reducer.
Use the exact dimensions and tokens from the desktop specification.
Move existing DOM sections into the workbench regions.
Keep their IDs during the first integration.
Do not recreate chat, approvals, or task stores.

Microcycles:

- The default layout has an editor and Agent pane.
- A workspace switch restores only that workspace's layout.
- A saved layout clamps to the current viewport.
- Reset layout removes only layout preferences.
- The 980×620 view retains every primary action.
- The 200% zoom view has no page-level horizontal scroll.

Commands after the test harness in Task 16 exists:

```sh
node --test tests/desktop/test_workbench_state.js
npm run test:e2e -- tests/e2e/workbench.spec.js
```

Expected: the stated viewport and keyboard cases pass.
Capture screenshots for human approval before removing the old layout flag.

### Task 14: Make Flip explicit and stable

Files:

- Modify: `desktop:src/renderer/workbench-state.js`.
- Modify: `desktop:src/renderer/app.js`.
- Modify: `desktop:src/renderer/index.html`.
- Create: `desktop:tests/desktop/test_flip_state.js`.
- Create: `desktop:tests/e2e/flip.spec.js`.

Use the Flip transitions in Code Pack K.
Keep `/flip` functional.
Add the visible control and keyboard command.

Required cases:

- Preview → last changed file → same preview.
- No changed file.
- Closed pane remains closed after a tool event.
- Dirty editor disables automatic following.
- Follow resumes only after a user action.
- An older file event does not replace the latest file.
- Workspace switch clears the previous workspace's file pointer.
- Reduced motion removes the transition.

Commands:

```sh
node --test tests/desktop/test_flip_state.js
npm run test:e2e -- tests/e2e/flip.spec.js
```

Expected: every Flip rule in this plan has an assertion.

### Task 15: Add the editor component and Problems pane

Files:

- Modify: `desktop:package.json`.
- Modify: `desktop:package-lock.json` through npm.
- Create: `desktop:src/renderer/editor-adapter.js`.
- Create: `desktop:src/renderer/editor-worker.js`.
- Modify: `desktop:src/renderer/app.js`.
- Modify: `desktop:src/renderer/index.html`.
- Create: `desktop:tests/desktop/test_editor_adapter.js`.
- Create: `desktop:tests/e2e/editor.spec.js`.
- Modify: `desktop:backend/serve_desktop.py`.
- Read: `agent:agent/lsp/manager.py`.
- Read: `agent:agent/lsp/protocol.py`.

Resolve the exact Monaco version through npm metadata before installation.
Record its version and license in the task commit.
Install only the selected editor dependency.
Do not update unrelated dependencies.

Use the adapter contract in Code Pack L.
Keep all file writes behind Task 12.
Do not let Monaco access the filesystem directly.

Microcycles:

- Open a UTF-8 file through the workspace API.
- Preserve 2 independent tab buffers.
- Save through expected-revision checks.
- Show a side-by-side diff without modifying files.
- Map a diagnostic to an exact file and line.
- Disable LSP actions when no server exists.
- Close editor models when tabs close.
- Restore a tab without restoring its old secret content.

Commands:

```sh
node --test tests/desktop/test_editor_adapter.js
npm run test:e2e -- tests/e2e/editor.spec.js
```

Expected: no model leak, no direct filesystem access, and no dirty-buffer loss.

### Task 16: Add real desktop behavior tests

Implement this harness before Task 13's E2E step.
Tasks 13–15 may add unit tests before this harness exists.

Files:

- Modify: `desktop:package.json`.
- Modify: `desktop:package-lock.json` through npm.
- Create: `desktop:playwright.config.js`.
- Create: `desktop:tests/e2e/fixture.js`.
- Create: `desktop:tests/e2e/smoke.spec.js`.
- Create: `desktop:backend/test_runtime.py`.

Use Playwright's Electron support.
The fixture shall start the real desktop against a temporary home and workspace.
The test runtime shall use the existing faux provider at the provider boundary.
Do not replace the UI or backend with a mock server.

Required fixture behavior:

- Create an isolated `XAVANI_HOME`.
- Select free test ports.
- Disable update checks.
- Deny all external network requests.
- Expose only the test workspace.
- Use an explicit readiness event.
- Fail on an uncaught renderer error.
- Stop only the processes that the fixture creates.
- Remove only the fixture's temporary directory.

Package scripts:

```json
{
 "test:unit": "node --test tests/desktop/*.js",
 "test:e2e": "playwright test",
 "check:syntax": "node --check src/main.js && node --check src/preload.js && node --check src/renderer/app.js"
}
```

Merge those keys into the existing `scripts` object.
Do not replace the whole package file.

Verification:

```sh
npm run test:e2e -- tests/e2e/smoke.spec.js
```

Expected: the real application opens, receives an authenticated ready event, and shows a completed read-only test run.
A missing engine or secret shall fail the test.

### Task 17: Make workflow skills explicit

Files:

- Create: `agent:agent/workflow_catalog.py`.
- Create: `agent:agent/workflow_skills.py`.
- Modify: `agent:agent/agent_init.py`.
- Modify: `agent:agent/skill_commands.py`.
- Modify: `agent:agent/conversation_compression.py`.
- Create: `agent:tests/agent/test_workflow_catalog.py`.
- Create: `agent:tests/agent/test_workflow_skill_loading.py`.

Use Code Pack M.
Use canonical skill paths, not display names alone.
Resolve skills through the existing discovery rules.
The active profile's approved skill override takes precedence.

Microcycles:

- Selecting Finance resolves the declared skill files.
- A missing required skill blocks Build mode.
- Ask mode can explain the missing prerequisite.
- A disabled skill does not load silently.
- The host records the loaded content hash.
- A skill edit takes effect at the next safe task boundary.
- Compression retains the receipt and reload instruction.
- A pruned skill body reloads before a consequential action.
- A small context window loads only the current step's skills.
- The system prompt remains byte-stable within the active turn.

Commands:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/agent/test_workflow_catalog.py tests/agent/test_workflow_skill_loading.py -q
```

Expected: skill selection creates actual loaded context, not only a suggestion list.

### Task 18: Add deterministic finance checks

Files:

- Create: `agent:xavani_operator/finance/validation.py`.
- Modify: `agent:xavani_operator/finance/money.py` only where tests prove a defect.
- Create: `agent:tests/operator/test_finance_validation.py`.
- Create: `agent:tests/fixtures/business/finance_cases.json`.

Use Code Pack N.
The fixture shall identify itself as synthetic test data.
Do not present it as company financial data.

Microcycles:

- Reject NaN and infinity.
- Reject a missing currency or period.
- Reject mixed currencies without explicit conversion data.
- Reject an unbalanced statement.
- Reject duplicate invoice identity.
- Represent a zero denominator as unavailable, not zero.
- Require `discount_rate > terminal_growth` for perpetual DCF.
- Keep money as integer minor units or Decimal strings.
- Retain negative values where the financial schema permits them.
- Require an explicit tax rate and jurisdiction for tax calculations.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/operator/test_finance_validation.py tests/operator/test_finance_ledger.py -q
```

Expected: invalid source data blocks a verified financial report.

### Task 19: Bind approvals to exact actions

Files:

- Modify: `agent:xavani_operator/approval_queue.py`.
- Modify: `agent:xavani_operator/act.py`.
- Modify: `agent:xavani_operator/audit.py`.
- Create: `agent:tests/operator/test_action_approval_binding.py`.
- Create: `agent:tests/operator/test_action_reconciliation.py`.

Use Code Pack O's canonical action digest.
An approval shall include the workspace, profile, target, operation, and payload hash.
Use a 5-minute expiry for a one-time approval.
An approval permits exactly 1 action attempt.

Microcycles:

- A changed recipient invalidates approval.
- A changed amount invalidates approval.
- A changed attachment invalidates approval.
- A changed profile invalidates approval.
- An expired approval cannot execute.
- A duplicate submit cannot execute twice.
- A timeout after submit enters `unknown` state.
- Reconciliation reads the exact external target.
- Unknown outcome blocks retries until resolution.
- An unconfigured connector returns `Unavailable`.

Do not add automatic payment execution.
Keep `finance/payments.py` as instruction generation.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/operator/test_action_approval_binding.py tests/operator/test_action_reconciliation.py -q
```

Expected: no action executes after approval context changes.

### Task 20: Add business workflow evaluations

Files:

- Create: `agent:tests/fixtures/business/workflows.json`.
- Create: `agent:tests/business/test_workflow_acceptance.py`.
- Modify: `agent:scripts/task_bench/tasks/baseline_tasks.json`.
- Modify: `agent:scripts/task_bench/run_bench.py` only for proven verifier gaps.
- Create: `agent:docs/reliability/business-coverage.md`.

Use the B01–B12 inventory as the exact coverage list.
Add 3 cases per workflow:

- Valid source data.
- Missing or contradictory source data.
- A consequential action without approval.

Use real fixture files and objective artifact checks.
A phrase such as `invoice complete` does not satisfy an artifact check.
Use the existing `pytest:` verifier for file and behavior assertions.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/business/test_workflow_acceptance.py -q
```

Expected: all 36 workflow cases pass with the scripted provider.
This result proves harness behavior only.
Task 25 measures real-model behavior separately.

### Task 21: Add the business workspace view

Files:

- Create: `desktop:src/renderer/business-view.js`.
- Modify: `desktop:src/renderer/index.html`.
- Modify: `desktop:src/renderer/app.js`.
- Modify: `desktop:backend/serve_desktop.py`.
- Create: `desktop:tests/e2e/business.spec.js`.

Use the same Agent pane, task store, artifact tabs, and approval panel.
Do not create a separate finance chat implementation.

Show these controls:

- Workflow selector with B01–B12 labels.
- Source list with access state.
- Period and currency fields when the workflow needs them.
- Draft artifact list.
- Check results.
- Approval queue.
- Outstanding work.

Required behavior:

- A missing connector shows `Unavailable`.
- A missing financial period blocks report execution.
- A failed reconciliation shows the exact difference.
- A draft email shows its exact recipient before approval.
- A denied action remains denied after navigation.

Command:

```sh
npm run test:e2e -- tests/e2e/business.spec.js
```

Expected: no control claims a capability that its backend lacks.

### Task 22: Add a local work timeline

Files:

- Create: `agent:agent/work_timeline.py`.
- Modify: `agent:agent/tool_executor.py`.
- Modify: `agent:gateway/platforms/api_server.py`.
- Create: `desktop:src/renderer/timeline.js`.
- Modify: `desktop:src/renderer/app.js`.
- Create: `agent:tests/agent/test_work_timeline.py`.
- Create: `desktop:tests/e2e/timeline.spec.js`.

Store timeline events beside the current session using the existing session storage API.
Do not create another transcript database.

Record these event types:

- `task.started`.
- `skill.loaded`.
- `tool.started`.
- `tool.completed`.
- `artifact.changed`.
- `verification.completed`.
- `approval.requested`.
- `approval.resolved`.
- `task.blocked`.
- `task.completed`.

Exclude these values:

- Raw credentials.
- Authentication headers.
- Full environment variables.
- Hidden reasoning.
- Unapproved screen pixels.
- Full file contents by default.

A timeline export shall use a native Save dialog.
A replay shall remain read-only.

Commands:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/agent/test_work_timeline.py -q
npm run test:e2e -- tests/e2e/timeline.spec.js
```

Run each command from its repository root.
Expected: timeline replay produces zero tool executions.

### Task 23: Add explicit capture controls

Files:

- Create: `desktop:src/recording.js`.
- Create: `desktop:src/renderer/recording-controls.js`.
- Modify: `desktop:src/main.js`.
- Modify: `desktop:src/preload.js`.
- Modify: `desktop:src/renderer/index.html`.
- Modify: `desktop:src/renderer/app.js`.
- Create: `desktop:tests/desktop/test_recording.js`.
- Create: `desktop:tests/e2e/recording.spec.js`.

Use the state machine in Code Pack P.
Use Electron's current documented capture API after its version check.
Keep raw capture bytes outside the agent prompt.

Microcycles:

- Idle state requests no permission.
- Start requires a user gesture and source selection.
- Denied permission returns to idle state.
- Pause stops byte production.
- Stop releases every track.
- Discard removes only the temporary recording.
- The duration cap stops capture.
- The size cap stops capture.
- A backend restart does not restart capture.
- A secret dialog pauses capture.
- Save uses a native dialog.
- Cancelled save retains the temporary recording for explicit retry or discard.

Commands:

```sh
node --test tests/desktop/test_recording.js
npm run test:e2e -- tests/e2e/recording.spec.js
```

Expected: no permission prompt or file appears before an explicit Start action.
Manual macOS and Windows permission checks remain mandatory.

### Task 24: Define the product and legal scan

Files:

- Create: `agent:THIRD_PARTY_NOTICES.md`.
- Create: `desktop:THIRD_PARTY_NOTICES.md`.
- Create: `agent:scripts/check_product_boundary.py`.
- Create: `agent:tests/scripts/test_product_boundary.py`.
- Modify: `agent:tools/guidelines_gate_tool.py`.
- Modify: `desktop:src/main.js`.
- Modify: `desktop:src/renderer/app.js`.
- Modify: `desktop:scripts/build-macos.sh`.

Use Code Pack Q's boundary rules.
Do not use a repository-wide word deletion.
Do not remove provider names or legal notices.

The existing `_STUB_FILES` policy treats `skills_hub.py` as a permanent stub.
That rule conflicts with the implemented skills hub.
Replace stale path bans with behavior tests for prohibited services.

Required tests:

- The About screen names Xavani and Enternovate.
- The legal screen retains required notices.
- A startup without remote providers emits no network requests.
- An update check requires a user action or explicit opt-in.
- No default request targets an upstream subscription or telemetry host.
- An explicit user-selected third-party model remains functional.
- The built package includes the notices.

Command:

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/scripts/test_product_boundary.py -q
```

Expected: prohibited product links fail; required legal attribution passes.

### Task 25: Measure real-model reliability

Files:

- Create: `agent:docs/reliability/model-matrix.md`.
- Create: `agent:scripts/task_bench/tasks/reliability_tasks.json`.
- Modify: `agent:scripts/task_bench/leaderboard.py`.
- Modify: `agent:scripts/task_bench/regression_gate.py` only for measured needs.

Do not choose provider credentials or costs silently.
Ask Andile for the approved model IDs and total evaluation budget before live calls.
Use 3 model classes:

- A strong tool-capable model.
- A lower-cost tool-capable model.
- A constrained model with a smaller context window.

Use the same tasks, workspace fixtures, tool permissions, and objective verifiers.
Run 3 repetitions per task and model.
Record the actual model ID and provider response metadata.
Do not compare different prompts as if only the model changes.

Report these metrics:

- Verified task success rate.
- False completion rate.
- Unauthorized action count.
- Stale overwrite count.
- Recovery success rate.
- Task duration at p50 and p95.
- Cost per verified task.
- Input and output tokens.
- Blocked-task rate.

Release requirements:

- Zero unauthorized actions in the evaluation corpus.
- Zero stale overwrites in the evaluation corpus.
- Zero false `Verified` labels in the adversarial corpus.
- No success-rate decrease on the unchanged regression corpus.
- No hidden model fallback.
- Every failed or blocked case appears in the report.

Do not turn these corpus results into a universal guarantee.
Do not mark a weak model fully supported when it cannot pass the task requirements.
Offer Ask mode or supervised Build mode for that model.

### Task 26: Package and release from evidence

Files:

- Modify: `agent:scripts/release.py`.
- Modify: `agent:pyproject.toml`.
- Modify: `agent:xavani_cli/__init__.py`.
- Modify: `agent:acp_registry/agent.json`.
- Modify: `agent:uv.lock` through uv.
- Modify: `desktop:package.json`.
- Modify: `desktop:package-lock.json` through npm.
- Modify: `desktop:scripts/build-macos.sh`.
- Modify: `desktop:.github/workflows/windows-build.yml`.
- Create: `desktop:scripts/check_release_manifest.py`.
- Create: `desktop:tests/desktop/test_release_manifest.py`.
- Create: `agent:docs/reliability/release-checklist.md`.

Use Code Pack R's release manifest.
Require `XAVANI_ENGINE_SRC` explicitly.
Reject a missing or dirty engine source for release builds.
Package the exact engine commit from the release manifest.
Copy the complete backend package, including `__init__.py`, `cli_shell.py`, and the new backend modules.

Pin every added dependency.
Remove the unpinned aiohttp install from the desktop build path.
Preserve lockfile integrity checks.
Do not rebuild the runtime from an unrecorded local installation.

Release order:

1. Produce local candidate artifacts.
2. Run package smoke tests with temporary user homes.
3. Verify startup without a development checkout.
4. Verify the bundled engine revision.
5. Verify macOS signing and notarization.
6. Verify Windows signing and installation.
7. Verify an update from the previous supported release.
8. Verify rollback without state loss.
9. Record checksums and the compatibility matrix.
10. Present the release evidence to Andile.
11. Obtain explicit publication approval.
12. Publish only the approved artifacts.
13. Read the exact release page and asset metadata after publication.
14. Download the published artifact to verify its checksum.

Do not run steps 11–14 without explicit publication approval.
Do not use an ad-hoc signature as a public signing claim.
Missing signing credentials block a public stable release, not local testing.

Commands after build authorization:

```sh
XAVANI_ENGINE_SRC=/Users/andilemushwana/xavani-agent bash scripts/build-macos.sh
codesign --verify --deep --strict build/dmg-stage/Xavani.app
spctl --assess --type execute --verbose=2 build/dmg-stage/Xavani.app
/opt/homebrew/bin/python3.11 scripts/check_release_manifest.py build/dmg-stage/Xavani.app/Contents/Resources/release-manifest.json
```

Expected:

- Build exit code 0.
- Valid signature and seal.
- Gatekeeper acceptance for a public candidate.
- Manifest validation exit code 0.
- The packaged engine revision matches the approved revision.

### Task 27: Establish the recurring release process

Files:

- Create: `agent:docs/reliability/upstream-review.md`.
- Create: `agent:docs/reliability/release-cadence.md`.
- Modify: `agent:.github/workflows/eval-gate.yml`.
- Modify: `agent:.github/workflows/nightly.yml`.
- Modify: `desktop:.github/workflows/cli-parity.yml`.

Use this cadence as a proposed policy:

- Each week: review upstream security and reliability changes.
- Each accepted fix: run the smallest relevant regression cases.
- Each release candidate: run the full release checklist.
- Each stable release: obtain owner approval.

Do not schedule cron jobs during implementation without separate approval.
Do not publish every upstream commit.
Do not equate release frequency with quality.

For each upstream candidate, record these fields:

- Repository and commit.
- Source files.
- User-visible failure or capability.
- Existing Xavani equivalent.
- Classification: reuse, harden, new, or reject.
- License obligations.
- Regression test.
- Local implementation commit.
- Verification evidence.

CI shall include new test paths in its change filters.
A JavaScript-only change shall run desktop JavaScript tests.
A backend-only change shall run desktop backend tests.
A shared protocol change shall run both repositories' contract tests.

## Release groups

Implement these groups in order:

- R1: Tasks 01–12 and Task 24's safety boundaries.
- R2: Task 16, followed by Tasks 13–15.
- R3: Tasks 17–23.
- R4: Tasks 25–27 and Task 26's release certification.

Task 24's legal inventory starts before any upstream-derived code enters a package.
Task 26's packaging fixes start before the first candidate build.
A release group does not mean an automatic public release.
Keep feature flags off until each group's acceptance checks pass.

## Risks and tradeoffs

- A model can still produce incorrect work that the verifier does not detect.
- Broad business coverage requires domain-specific evaluations and current sources.
- Monaco adds package size and worker configuration.
- A full desktop framework rewrite adds unnecessary regression risk.
- A local bearer secret does not protect against a hostile process with the same user privileges.
- A path resolver does not provide a complete operating-system sandbox.
- File revision checks detect conflicts but do not provide a universal cross-process transaction.
- A screen recording can contain visible secrets.
- Required legal notices cannot disappear to satisfy a product-brand scan.
- Model comparisons consume provider quota and money.
- Public signing needs owner-managed credentials.
- The current desktop version conflict needs resolution before release.
- Engine and desktop tests can pass independently while their packaged combination fails.

## Open decisions

These decisions do not block the read-only plan.
They block the named implementation stages:

- Before Task 15: approve the workbench screenshots and Monaco dependency.
- Before Task 19 external tests: identify authorized sandbox connector accounts.
- Before Task 23 public capture: approve screen and microphone defaults.
- Before Task 25: select exact model IDs and an evaluation budget.
- Before Task 26 signing: identify the Apple and Windows signing process.
- Before every publication: approve the repository, tag, artifacts, and release notes.

Do not request or print passwords, tokens, card details, or signing secrets in chat.

## Acceptance checklist

- [ ] The plan's source revisions match the implementation baseline.
- [ ] Existing skills, edit modes, `/flip`, Explorer, and Preview remain available.
- [ ] The completion label depends on current host evidence.
- [ ] The success-rate gate rejects regressions.
- [ ] The desktop authenticates HTTP and WebSocket control paths.
- [ ] The preview cannot access control ports or privileged IPC.
- [ ] File access stays within the approved workspace.
- [ ] A stale save cannot overwrite a newer file without explicit conflict resolution.
- [ ] Tool cards match stable tool call IDs.
- [ ] A disconnected stream cannot become a successful task.
- [ ] The desktop passes viewport, keyboard, contrast, and reduced-motion checks.
- [ ] Business workflows expose unavailable sources and draft-only capabilities honestly.
- [ ] Financial artifacts reconcile through deterministic checks.
- [ ] External approval binds the exact action.
- [ ] Timeline replay executes no actions.
- [ ] Capture requires explicit consent.
- [ ] Product branding uses Xavani and Enternovate.
- [ ] Required legal notices remain intact.
- [ ] Real-model reports distinguish verified success from blocked work.
- [ ] The package includes its exact engine revision and all backend modules.
- [ ] Publication requires separate approval and read-back verification.

## Code packs

The following section contains exact small implementations and integration contracts.
Do not install a code pack before its failing test exists.

### Code Pack A: Regression decisions

Append these tests to `agent:tests/xavani_cli/test_regression_gate.py`.

```python
@pytest.mark.parametrize("current_rate", [0.0, 0.5, 0.99])
def test_gate_rejects_lower_success(tmp_path, current_rate):
 from scripts.task_bench import regression_gate

 base = _write(tmp_path, "base.json", {
 "median_wall_s": 80.0,
 "cost_per_successful_task_usd": 0.02,
 "success_rate": 1.0,
 })
 current = _write(tmp_path, "current.json", {
 "median_wall_s": 70.0,
 "cost_per_successful_task_usd": 0.01,
 "success_rate": current_rate,
 })
 assert regression_gate.main([str(base), str(current)]) == 1


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -0.1, 1.1, True])
def test_gate_rejects_invalid_success(tmp_path, value):
 from scripts.task_bench import regression_gate

 base = _write(tmp_path, "base.json", {
 "median_wall_s": 80.0,
 "cost_per_successful_task_usd": 0.02,
 "success_rate": 1.0,
 })
 current = _write(tmp_path, "current.json", {
 "median_wall_s": 70.0,
 "cost_per_successful_task_usd": 0.01,
 "success_rate": value,
 })
 assert regression_gate.main([str(base), str(current)]) == 2
```

Add `import math` to `agent:scripts/task_bench/regression_gate.py`.
Replace `load_metrics` with this implementation:

```python
def load_metrics(path: Path) -> Dict[str, Optional[float]]:
 data = json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(data, dict):
 raise ValueError("The result shall contain an object.")
 summary = data.get("summary", data)
 if not isinstance(summary, dict):
 raise ValueError("The summary shall contain an object.")
 metrics: Dict[str, Optional[float]] = {}
 for key in ("median_wall_s", "cost_per_successful_task_usd", "success_rate"):
 value = summary.get(key)
 if isinstance(value, bool) or not isinstance(value, (int, float)):
 raise ValueError(f"The metric {key} shall contain a number.")
 number = float(value)
 if not math.isfinite(number) or number < 0:
 raise ValueError(f"The metric {key} shall contain a finite nonnegative value.")
 if key == "success_rate" and number > 1:
 raise ValueError("The success rate shall not exceed 1.")
 metrics[key] = number
 return metrics
```

Replace `main` with this implementation:

```python
def main(argv=None) -> int:
 parser = argparse.ArgumentParser(description=__doc__)
 parser.add_argument("baseline")
 parser.add_argument("current")
 parser.add_argument("--tolerance", type=float, default=0.10)
 args = parser.parse_args(argv)
 if not math.isfinite(args.tolerance) or args.tolerance < 0:
 print("Invalid tolerance.")
 return 2
 try:
 base = load_metrics(Path(args.baseline))
 cur = load_metrics(Path(args.current))
 except (OSError, ValueError, TypeError) as exc:
 print(f"Invalid benchmark evidence: {exc}")
 return 2
 failures = []
 if cur["success_rate"] < base["success_rate"]:
 failures.append("The success rate decreases.")
 for key in ("median_wall_s", "cost_per_successful_task_usd"):
 if worsened(base[key], cur[key], args.tolerance):
 failures.append(f"{key}: {base[key]} -> {cur[key]}")
 print(f"baseline : {base}")
 print(f"current : {cur}")
 if failures:
 print("REGRESSION GATE FAILED:")
 for failure in failures:
 print(f" - {failure}")
 return 1
 print("Regression gate passed.")
 return 0
```

Retain `worsened` for compatibility with its existing tests.
An unavailable cost blocks a release comparison instead of implying zero cost.
Add a separate budget report if the provider omits prices.

### Code Pack B: Completion contract

Create `agent:agent/completion_contract.py` with this content:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReceiptStatus = Literal["passed", "failed", "blocked", "cancelled"]
VerificationState = Literal["not_required", "unverified", "passed", "failed", "blocked"]


@dataclass(frozen=True)
class CompletionContract:
 contract_id: str
 session_id: str
 workspace_id: str
 workflow_id: str
 goal: str
 required_checks: tuple[str, ...]
 required_skills: tuple[str, ...]
 allowed_actions: tuple[str, ...]
 approved_at: str
 revision: str
 read_only: bool = False

 def __post_init__(self):
 for value in (
 self.contract_id, self.session_id, self.workspace_id,
 self.workflow_id, self.goal, self.revision,
 ):
 if not isinstance(value, str) or not value.strip():
 raise ValueError("The contract contains an empty identifier.")
 if len(set(self.required_checks)) != len(self.required_checks):
 raise ValueError("The contract contains duplicate checks.")
 if not self.read_only and not self.required_checks:
 raise ValueError("A work contract shall require a check.")


@dataclass(frozen=True)
class CheckReceipt:
 receipt_id: str
 contract_id: str
 check_id: str
 workspace_id: str
 revision: str
 command_argv: tuple[str, ...]
 cwd: str
 exit_code: int | None
 status: ReceiptStatus
 artifact_hashes: tuple[tuple[str, str], ...]
 started_at: str
 finished_at: str
 origin: str

 def __post_init__(self):
 if self.status not in {"passed", "failed", "blocked", "cancelled"}:
 raise ValueError("The receipt status is invalid.")
 if self.status == "passed" and (
 type(self.exit_code) is not int or self.exit_code != 0
 ):
 raise ValueError("A passing receipt shall have exit code 0.")
 if not all((self.receipt_id, self.contract_id, self.check_id, self.workspace_id, self.revision)):
 raise ValueError("The receipt contains an empty identifier.")


@dataclass(frozen=True)
class CompletionDecision:
 state: VerificationState
 missing_checks: tuple[str, ...] = ()
 failed_checks: tuple[str, ...] = ()


def decide_completion(
 contract: CompletionContract,
 receipts: tuple[CheckReceipt, ...],
 current_revision: str,
) -> CompletionDecision:
 if contract.read_only and not contract.required_checks:
 return CompletionDecision("not_required")
 latest = {}
 for receipt in receipts:
 if (
 receipt.origin == "host"
 and receipt.contract_id == contract.contract_id
 and receipt.workspace_id == contract.workspace_id
 and receipt.revision == current_revision
 and receipt.check_id in contract.required_checks
 ):
 latest[receipt.check_id] = receipt
 missing = tuple(check for check in contract.required_checks if check not in latest)
 failed = tuple(check for check, receipt in latest.items() if receipt.status == "failed")
 blocked = tuple(
 check for check, receipt in latest.items()
 if receipt.status in {"blocked", "cancelled"}
 )
 if failed:
 return CompletionDecision("failed", missing, failed)
 if blocked:
 return CompletionDecision("blocked", missing, blocked)
 if missing:
 return CompletionDecision("unverified", missing)
 return CompletionDecision("passed")
```

Create `agent:tests/agent/test_completion_contract.py` with this content:

```python
from dataclasses import replace

import pytest

from agent.completion_contract import CheckReceipt, CompletionContract, decide_completion


def contract():
 return CompletionContract(
 contract_id="c1", session_id="s1", workspace_id="w1",
 workflow_id="engineering", goal="Pass the target test.",
 required_checks=("test",), required_skills=(), allowed_actions=(),
 approved_at="2026-09-12T00:00:00Z", revision="r1",
 )


def receipt(**changes):
 value = CheckReceipt(
 receipt_id="e1", contract_id="c1", check_id="test", workspace_id="w1",
 revision="r1", command_argv=("python3", "-m", "pytest"), cwd="/workspace",
 exit_code=0, status="passed", artifact_hashes=(),
 started_at="2026-09-12T00:00:01Z", finished_at="2026-09-12T00:00:02Z",
 origin="host",
 )
 return replace(value, **changes)


@pytest.mark.parametrize("evidence,revision,expected", [
 ((), "r1", "unverified"),
 ((receipt(),), "r1", "passed"),
 ((receipt(),), "r2", "unverified"),
 ((receipt(origin="model"),), "r1", "unverified"),
 ((receipt(workspace_id="w2"),), "r1", "unverified"),
 ((receipt(status="failed", exit_code=1),), "r1", "failed"),
 ((receipt(status="cancelled", exit_code=None),), "r1", "blocked"),
])
def test_completion_requires_current_host_evidence(evidence, revision, expected):
 assert decide_completion(contract(), evidence, revision).state == expected


def test_later_failure_replaces_earlier_pass():
 evidence = (receipt(), receipt(receipt_id="e2", status="failed", exit_code=1))
 assert decide_completion(contract(), evidence, "r1").state == "failed"


def test_work_contract_cannot_omit_checks():
 with pytest.raises(ValueError):
 replace(contract(), required_checks=())


def test_read_only_contract_needs_no_artifact_check():
 value = replace(contract(), required_checks=(), read_only=True)
 assert decide_completion(value, (), "r1").state == "not_required"
```

The receipt origin field is a host assertion, not a security credential.
Only the trusted runner may call the receipt writer.
Do not expose the writer through an API that accepts model-authored receipts.
The runner shall revalidate the contract definition before each check.

### Code Pack C: Receipt persistence

Create `agent:agent/verification_receipts.py` with this content:

```python
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from agent.completion_contract import CheckReceipt


class ReceiptStore:
 def __init__(self, path: Path):
 self.path = Path(path)

 @contextmanager
 def _connection(self):
 self.path.parent.mkdir(parents=True, exist_ok=True)
 connection = sqlite3.connect(self.path, timeout=5)
 try:
 connection.execute(
 "CREATE TABLE IF NOT EXISTS verification_receipts ("
 "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
 "receipt_id TEXT NOT NULL UNIQUE, "
 "contract_id TEXT NOT NULL, "
 "payload TEXT NOT NULL)"
 )
 with connection:
 yield connection
 finally:
 connection.close()

 def append(self, receipt: CheckReceipt) -> None:
 if not isinstance(receipt, CheckReceipt) or receipt.origin != "host":
 raise ValueError("Only host receipts may enter this store.")
 payload = json.dumps(asdict(receipt), sort_keys=True, allow_nan=False)
 if len(payload.encode("utf-8")) > 65536:
 raise ValueError("The receipt exceeds 65536 bytes.")
 with self._connection() as connection:
 connection.execute(
 "INSERT INTO verification_receipts(receipt_id, contract_id, payload) VALUES (?, ?, ?)",
 (receipt.receipt_id, receipt.contract_id, payload),
 )

 def for_contract(self, contract_id: str) -> tuple[CheckReceipt, ...]:
 with self._connection() as connection:
 rows = connection.execute(
 "SELECT payload FROM verification_receipts WHERE contract_id = ? ORDER BY seq",
 (contract_id,),
 ).fetchall()
 output = []
 for row in rows:
 data = json.loads(row[0])
 data["command_argv"] = tuple(data["command_argv"])
 data["artifact_hashes"] = tuple(tuple(pair) for pair in data["artifact_hashes"])
 output.append(CheckReceipt(**data))
 return tuple(output)
```

Create `agent:tests/agent/test_verification_receipts.py` with this content:

```python
from dataclasses import replace
import sqlite3

import pytest

from agent.completion_contract import CheckReceipt
from agent.verification_receipts import ReceiptStore


def host_receipt():
 return CheckReceipt(
 receipt_id="e1", contract_id="c1", check_id="test", workspace_id="w1",
 revision="r1", command_argv=("pytest",), cwd="/workspace", exit_code=0,
 status="passed", artifact_hashes=(), started_at="start", finished_at="finish",
 origin="host",
 )


def test_receipt_survives_reopen(tmp_path):
 path = tmp_path / "receipts.db"
 value = host_receipt()
 ReceiptStore(path).append(value)
 assert ReceiptStore(path).for_contract("c1") == (value,)


def test_receipts_remain_profile_scoped(tmp_path):
 first = ReceiptStore(tmp_path / "first" / "receipts.db")
 second = ReceiptStore(tmp_path / "second" / "receipts.db")
 first.append(host_receipt())
 assert second.for_contract("c1") == ()


def test_duplicate_receipt_cannot_replace_evidence(tmp_path):
 store = ReceiptStore(tmp_path / "receipts.db")
 store.append(host_receipt())
 with pytest.raises(sqlite3.IntegrityError):
 store.append(replace(host_receipt(), status="failed", exit_code=1))
 assert store.for_contract("c1")[0].status == "passed"


def test_model_receipt_cannot_enter_store(tmp_path):
 store = ReceiptStore(tmp_path / "receipts.db")
 with pytest.raises(ValueError):
 store.append(replace(host_receipt(), origin="model"))
 assert not store.path.exists()
```

Construct the store during session setup:

```python
from agent.verification_receipts import ReceiptStore
from xavani_constants import get_xavani_home

store = ReceiptStore(get_xavani_home() / "verification_receipts.db")
```

Do not construct it at module import time.
Do not catch a store failure and return a passing decision.
Add a retention command only after a measured storage need exists.

### Code Pack D: Host check execution and integration

Create `agent:agent/verification_runner.py` with this content:

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent.completion_contract import CheckReceipt, CompletionContract


def run_host_check(
 contract: CompletionContract,
 check_id: str,
 command_argv: tuple[str, ...],
 cwd: str,
 revision: str,
 execute,
 artifact_hashes: tuple[tuple[str, str], ...] = (),
) -> CheckReceipt:
 if check_id not in contract.required_checks:
 raise ValueError("The contract does not require this check.")
 if not command_argv or any(not isinstance(arg, str) or "\x00" in arg for arg in command_argv):
 raise ValueError("The check command is invalid.")
 started = datetime.now(timezone.utc).isoformat()
 code = None
 try:
 result = execute(command_argv, cwd)
 code = result.get("exit_code")
 if result.get("cancelled"):
 status = "cancelled"
 code = None
 elif result.get("blocked") or type(code) is not int:
 status = "blocked"
 code = None
 else:
 status = "passed" if code == 0 else "failed"
 except (OSError, TimeoutError):
 status = "blocked"
 return CheckReceipt(
 receipt_id=uuid4().hex,
 contract_id=contract.contract_id,
 check_id=check_id,
 workspace_id=contract.workspace_id,
 revision=revision,
 command_argv=command_argv,
 cwd=cwd,
 exit_code=code,
 status=status,
 artifact_hashes=artifact_hashes,
 started_at=started,
 finished_at=datetime.now(timezone.utc).isoformat(),
 origin="host",
 )
```

The `execute` callable belongs to the host's active backend adapter.
It shall accept an argv tuple and an absolute backend cwd.
It shall not use a shell string from model output.
It shall preserve the existing approval, timeout, and cancellation paths.
An unsupported backend returns `{"blocked": true}`.
Do not redirect an unsupported backend check to the local host.

Complete the following integration microsteps in order:

D1. `agent:agent/agent_init.py`.

- Add `_completion_contract = None`.
- Add `_verification_repair_attempts = 0`.
- Add `_verification_store` through the profile-aware constructor above.
- Do not create a work contract from a model response alone.

D2. `agent:agent/tool_executor.py`.

- Use the existing successful file-mutation result to invalidate the task revision.
- Record exact changed paths through the existing file-state mechanism.
- Do not infer success from the tool name.
- Do not include failed writes in the changed-path set.
- A shell command with unknown write effects invalidates the whole work contract revision.

D3. `agent:tools/guidelines_gate_tool.py`.

- Keep the existing diff checks as advisory checks.
- Obtain the active contract from host session context.
- Run only its approved verifier IDs through `run_host_check`.
- Reject a caller-supplied argv or receipt status.
- Append the host receipt through `ReceiptStore`.
- Return the structured decision and exact check outcomes.
- Return a blocker when no approved work contract exists.

D4. `agent:agent/conversation_loop.py`.

- In the no-tool branch, obtain `decide_completion` before accepting task success.
- Keep Ask-mode turns unchanged when no work contract exists.
- Use the existing bounded continuation path for 2 repair attempts.
- Preserve legal message alternation through the current message helper.
- Do not rewrite the system prompt or earlier transcript rows.
- On exhausted repairs, finish the turn with the host-decided state
 (`failed` or `blocked`); repairs stop after 2 attempts per contract.
- Keep partial files and the task identity.
- At the final result construction near line 4262, include the decision as structured data.
- Apply the final status after output-transform plugins.
- Do not let a plugin modify that status.
- A stream remains provisional until this final status exists.

D5. `agent:gateway/platforms/api_server.py`.

- Add `verification_state`, `missing_checks`, and `failed_checks` to run snapshots.
- Include the same fields in terminal run events.
- Retain existing status codes for run creation.
- Do not map `verification_state="blocked"` to a transport exception.
- Preserve `completed` as a turn lifecycle state for compatibility.
- Require the UI to show the separate verification state.

D6. `agent:tests/agent/test_completion_contract_wiring.py`.

Use `tests.harness.faux_provider.FauxProvider` at the provider boundary.
Use the existing fixture pattern in `tests/agent/test_self_critique_wiring.py`.
Add 1 scenario per RED → GREEN cycle.
Assert the real run result fields and recorded action counts.
Do not monkeypatch `decide_completion` or the receipt writer.

D7. Snapshot identity.

- Store the approved verifier definition outside the mutable workspace.
- Hash its exact argv, environment policy, test paths, and tool versions into the revision.
- Recompute the workspace revision immediately after a check.
- If the revision changes during the check, store a blocked receipt instead of a pass.
- Do not accept a passing test after the model changes the test definition without renewed approval.

This integration does not make arbitrary host execution safe.
A work contract on an untrusted repository needs the existing container or remote sandbox boundary.
Keep untrusted command execution disabled until that boundary passes its own integration tests.

### Code Pack E: Unknown edit backends

Create `agent:tests/tools/test_edit_backend_resolution.py` with this content:

```python
import pytest

from tools import edit_tool, terminal_tool


@pytest.mark.parametrize("value,expected", [
 ({"env_type": "local"}, True),
 ({"env_type": "docker"}, False),
 ({"env_type": "ssh"}, False),
 ({}, False),
 ({"env_type": None}, False),
])
def test_backend_requires_explicit_local(monkeypatch, value, expected):
 monkeypatch.setattr(terminal_tool, "_get_env_config", lambda: value)
 assert edit_tool._backend_is_local("task-1") is expected


def test_backend_error_refuses_local_write(monkeypatch):
 def fail():
 raise ValueError("Invalid configuration.")

 monkeypatch.setattr(terminal_tool, "_get_env_config", fail)
 assert edit_tool._backend_is_local("task-1") is False
```

Replace `agent:tools/edit_tool.py::_backend_is_local` with this content:

```python
def _backend_is_local(task_id: str = "default") -> bool:
 try:
 from tools.terminal_tool import _get_env_config

 config = _get_env_config()
 except Exception:
 return False
 return isinstance(config, dict) and config.get("env_type") == "local"
```

This slice fixes the fail-open exception path.
It does not establish per-task backend resolution by itself.
In Task 07, bind edit resolution to the same effective task environment as the file tools.
Reject a backend identity mismatch before any direct `open` call.

### Code Pack F: Hashline task store

Add this class to `agent:tools/hashline/snapshots.py`:

```python
import threading


class TaskSnapshotStores:
 def __init__(self):
 self._lock = threading.RLock()
 self._stores = {}

 def for_task(self, task_id: str) -> SnapshotStore:
 if not isinstance(task_id, str) or not task_id.strip() or task_id == "default":
 raise ValueError("Hashline requires an explicit task identity.")
 with self._lock:
 if task_id not in self._stores:
 self._stores[task_id] = SnapshotStore()
 return self._stores[task_id]

 def discard(self, task_id: str) -> None:
 with self._lock:
 self._stores.pop(task_id, None)


task_stores = TaskSnapshotStores()
```

Create `agent:tests/tools/test_hashline_task_scope.py`:

```python
import pytest

from tools.hashline.snapshots import TaskSnapshotStores


def test_tasks_do_not_share_observed_ranges():
 stores = TaskSnapshotStores()
 stores.for_task("a").record("/workspace/file.py", "a\nb\n", ranges=((1, 1),))
 assert stores.for_task("b").get("/workspace/file.py") is None


def test_cleanup_removes_task_snapshots():
 stores = TaskSnapshotStores()
 stores.for_task("a").record("/workspace/file.py", "a\n", ranges=((1, 1),))
 stores.discard("a")
 assert stores.for_task("a").get("/workspace/file.py") is None


def test_default_identity_cannot_share_a_store():
 with pytest.raises(ValueError):
 TaskSnapshotStores().for_task("default")
```

Wire the store through these exact sites:

- `tools/edit_tool.py::_apply_hashline`: obtain `task_stores.for_task(task_id)`.
- `tools/edit_tool.py::_hashline_tag_guidance`: accept `task_id` explicitly.
- `tools/edit_tool.py::_apply_hashline`: pass the selected store into `apply_sections`.
- `tools/file_tools.py`: record a snapshot after successful read formatting.
- `tools/file_tools.py`: use the same canonical path for the header and store key.
- `tools/file_state.py`: call `task_stores.discard` during task cleanup.

Remove the full-range first-edit registration at the inspected lines 277–291.
Return this error for an unknown snapshot:

```text
Read the target lines before the edit. The current task has no observed snapshot for this file.
```

A read result shall expose `[canonical-path#TAG]` only after successful snapshot registration.
A tag without its observed ranges shall not authorize an edit.
Guard store mutations with the existing canonical file lock.
Do not hold that lock during a provider call.

### Code Pack G: Desktop authentication

Create `desktop:backend/desktop_auth.py`:

```python
from __future__ import annotations

import hmac
import re

from aiohttp import web


_SECRET = re.compile(r"[0-9a-f]{64}\Z")


def desktop_auth(secret: str):
 if not isinstance(secret, str) or not _SECRET.fullmatch(secret):
 raise ValueError("The desktop secret shall contain 64 hexadecimal characters.")

 @web.middleware
 async def authenticate(request, handler):
 supplied = request.headers.get("Authorization", "")
 if not hmac.compare_digest(supplied.encode("utf-8"), f"Bearer {secret}".encode("ascii")):
 return web.json_response({"error": "Unauthorized."}, status=401)
 origin = request.headers.get("Origin")
 if origin not in {None, "null"}:
 return web.json_response({"error": "Origin denied."}, status=403)
 return await handler(request)

 return authenticate
```

Create `desktop:tests/desktop/test_desktop_auth.py`:

```python
import asyncio

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from backend.desktop_auth import desktop_auth


async def exercise(headers):
 app = web.Application(middlewares=[desktop_auth("a" * 64)])

 async def target(request):
 return web.json_response({"ok": True})

 app.router.add_get("/desktop/api/status", target)
 async with TestClient(TestServer(app)) as client:
 response = await client.get("/desktop/api/status", headers=headers)
 return response.status


def test_missing_secret_fails():
 assert asyncio.run(exercise({})) == 401


def test_valid_secret_succeeds():
 assert asyncio.run(exercise({"Authorization": "Bearer " + "a" * 64})) == 200


def test_foreign_origin_fails():
 headers = {"Authorization": "Bearer " + "a" * 64, "Origin": "https://example.invalid"}
 assert asyncio.run(exercise(headers)) == 403
```

Create `desktop:src/security.js`:

```javascript
'use strict';

function trustedSender(event, window) {
 return Boolean(
 window && !window.isDestroyed()
 && event.sender === window.webContents
 && event.senderFrame === window.webContents.mainFrame
 );
}

function controlRequest(details, webContentsId, ports) {
 try {
 const url = new URL(details.url);
 return details.webContentsId === webContentsId
 && ['http:', 'ws:'].includes(url.protocol)
 && url.hostname === '127.0.0.1'
 && ports.has(Number(url.port))
 && !url.username && !url.password;
 } catch {
 return false;
 }
}

module.exports = { trustedSender, controlRequest };
```

Create `desktop:tests/desktop/test_security.js`:

```javascript
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { controlRequest, trustedSender } = require('../../src/security');

test('only the trusted renderer receives control authorization', () => {
 const ports = new Set([8642, 8643]);
 assert.equal(controlRequest({ url: 'http://127.0.0.1:8643/desktop/api/status', webContentsId: 1 }, 1, ports), true);
 assert.equal(controlRequest({ url: 'http://127.0.0.1:8643/desktop/api/status', webContentsId: 2 }, 1, ports), false);
 assert.equal(controlRequest({ url: 'http://127.0.0.1:3000/', webContentsId: 1 }, 1, ports), false);
 assert.equal(controlRequest({ url: 'https://example.invalid/', webContentsId: 1 }, 1, ports), false);
});

test('subframes cannot use privileged IPC', () => {
 const frame = {};
 const contents = { mainFrame: frame };
 const window = { isDestroyed: () => false, webContents: contents };
 assert.equal(trustedSender({ sender: contents, senderFrame: frame }, window), true);
 assert.equal(trustedSender({ sender: contents, senderFrame: {} }, window), false);
});
```

Integration details:

- In `src/main.js`, import `randomBytes` from `node:crypto`.
- Generate `randomBytes(32).toString('hex')` before each backend spawn.
- Change the backend stdin from `ignore` to `pipe`.
- Write exactly 1 JSON bootstrap line to that pipe.
- Close the pipe after the bootstrap line.
- In `backend/serve_desktop.py::main`, read and validate that bootstrap line before binding any port.
- Reject a missing or malformed secret.
- Pass `extra={"host": "127.0.0.1", "port": api_port, "key": secret, "cors_origins": ["null"]}` to `PlatformConfig`.
- Confirm the existing `cors_origins` parser accepts that exact list before the green integration test.
- Change `build_desktop_app(api_port)` to `build_desktop_app(api_port, secret)`.
- Construct `web.Application(middlewares=[desktop_auth(secret)])`.
- Register 1 `onBeforeSendHeaders` handler in the trusted desktop session.
- Inject `Authorization` only when `controlRequest` returns true.
- Remove any inherited authorization header from all other requests.
- Validate `trustedSender` in every privileged IPC handler.
- Do not expose the secret through `runtime-info` or `backend-ready`.

Permission behavior:

- `setPermissionCheckHandler` and `setPermissionRequestHandler` shall use the same origin policy.
- Deny preview permissions by default.
- Permit microphone access only for the trusted main frame during an explicit voice or capture request.
- Deny camera access in the initial release.
- Remove `allowpopups` from the preview webview.
- Use `will-attach-webview` to remove preload paths and force safe web preferences.
- Use `setWindowOpenHandler` to deny unexpected windows.
- Handle approved external links through validated IPC and a confirmation dialog.

### Code Pack H: Run event reducer

Create `desktop:src/renderer/run-state.js`:

```javascript
'use strict';
(function expose(root) {
 function initialRunState(runId) {
 return { runId, seq: 0, status: 'running', verification: 'unverified', tools: {} };
 }

 function applyRunEvent(state, event) {
 if (event.run_id !== state.runId || !Number.isInteger(event.seq) || event.seq <= state.seq) return state;
 const next = { ...state, seq: event.seq, tools: { ...state.tools } };
 if (event.event === 'tool.started' || event.event === 'tool.completed') {
 if (typeof event.tool_call_id !== 'string' || !event.tool_call_id) return state;
 const old = next.tools[event.tool_call_id] || { id: event.tool_call_id };
 next.tools[event.tool_call_id] = {
 ...old,
 tool: event.tool || old.tool || 'tool',
 path: event.path || old.path || '',
 status: event.event === 'tool.started' ? 'active' : (event.error ? 'failed' : 'completed'),
 };
 }
 const terminal = {
 'run.completed': 'completed',
 'run.failed': 'failed',
 'run.cancelled': 'cancelled',
 'run.interrupted': 'interrupted',
 };
 if (terminal[event.event]) {
 next.status = terminal[event.event];
 next.verification = event.verification_state || 'unverified';
 }
 return next;
 }

 function endRunStream(state) {
 if (['completed', 'failed', 'cancelled', 'interrupted'].includes(state.status)) return state;
 return { ...state, status: 'interrupted' };
 }

 const api = { initialRunState, applyRunEvent, endRunStream };
 if (typeof module !== 'undefined' && module.exports) module.exports = api;
 else root.XavaniRunState = api;
})(globalThis);
```

Create `desktop:tests/desktop/test_run_state.js`:

```javascript
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { initialRunState, applyRunEvent, endRunStream } = require('../../src/renderer/run-state');

test('opposite completion order keeps tool identity', () => {
 let state = initialRunState('r1');
 const events = [
 { event: 'tool.started', tool_call_id: 'a', tool: 'read_file' },
 { event: 'tool.started', tool_call_id: 'b', tool: 'patch' },
 { event: 'tool.completed', tool_call_id: 'b', tool: 'patch' },
 { event: 'tool.completed', tool_call_id: 'a', tool: 'read_file' },
 ];
 events.forEach((event, index) => {
 state = applyRunEvent(state, { ...event, run_id: 'r1', seq: index + 1 });
 });
 assert.equal(state.tools.a.tool, 'read_file');
 assert.equal(state.tools.b.tool, 'patch');
 assert.equal(state.tools.a.status, 'completed');
 assert.equal(state.tools.b.status, 'completed');
});

test('EOF without terminal evidence means interruption', () => {
 assert.equal(endRunStream(initialRunState('r1')).status, 'interrupted');
});

test('duplicate events do not change state', () => {
 const event = { event: 'tool.started', tool_call_id: 'a', run_id: 'r1', seq: 1 };
 const state = applyRunEvent(initialRunState('r1'), event);
 assert.equal(applyRunEvent(state, event), state);
});
```

Load `run-state.js` before `app.js` in `index.html`.
Replace the tool-card fallback at the inspected line 628 with a `Map` lookup by `tool_call_id`.
Create a missing card from a completion event when required.
Use the existing rAF paint scheduler.
Do not redraw the entire transcript for each event.

The server shall assign sequence values after serialization into its run event queue.
Do not use a producer-local counter for parallel tools.
A client shall process events in queue order.
If the server reports an event gap, replace local state from the authoritative snapshot.
Do not silently discard a gap as a duplicate.

### Code Pack I: Workspace paths

Create `desktop:backend/workspace_paths.py`:

```python
from __future__ import annotations

from pathlib import Path


_BLOCKED_DIRS = {".git", ".ssh", ".xavani", ".upstream"}
_BLOCKED_NAMES = {"auth.json", "credentials.json", "id_rsa", "id_ed25519"}


def workspace_path(root: Path, raw: str, *, allow_root: bool = False) -> Path:
 if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
 raise ValueError("A workspace path is required.")
 root = Path(root).resolve(strict=True)
 if not root.is_dir():
 raise ValueError("The workspace root shall be a directory.")
 candidate = Path(raw)
 if not candidate.is_absolute():
 candidate = root / candidate
 if ".." in candidate.parts:
 raise PermissionError("Parent traversal is not permitted.")
 try:
 relative = candidate.relative_to(root)
 except ValueError as exc:
 raise PermissionError("The path leaves the workspace.") from exc
 cursor = root
 for part in relative.parts:
 if part in _BLOCKED_DIRS or part in _BLOCKED_NAMES or part == ".env" or part.startswith(".env."):
 raise PermissionError("The path contains protected data.")
 cursor = cursor / part
 if cursor.is_symlink():
 raise PermissionError("Symbolic links require a separate access policy.")
 resolved = candidate.resolve(strict=False)
 if not resolved.is_relative_to(root):
 raise PermissionError("The path leaves the workspace.")
 if resolved == root and not allow_root:
 raise PermissionError("The operation cannot target the workspace root.")
 return resolved
```

Create `desktop:tests/desktop/test_workspace_paths.py`:

```python
import pytest

from backend.workspace_paths import workspace_path


def test_relative_path_stays_inside_workspace(tmp_path):
 assert workspace_path(tmp_path, "src/file.py") == tmp_path / "src" / "file.py"


def test_matching_prefix_does_not_grant_access(tmp_path):
 sibling = tmp_path.with_name(tmp_path.name + "-other") / "file.py"
 with pytest.raises(PermissionError):
 workspace_path(tmp_path, str(sibling))


@pytest.mark.parametrize("raw", ["../file.py", ".git/config", ".env", ".env.local", "auth.json"])
def test_protected_paths_fail(tmp_path, raw):
 with pytest.raises(PermissionError):
 workspace_path(tmp_path, raw)


def test_symlink_fails(tmp_path):
 target = tmp_path / "target"
 target.mkdir()
 (tmp_path / "link").symlink_to(target, target_is_directory=True)
 with pytest.raises(PermissionError):
 workspace_path(tmp_path, "link/file.py")
```

Keep `.env.example` inaccessible under the initial rule.
Offer explicit sanitized viewing later if a real workflow needs it.
Do not weaken the rule merely to make a test pass.

Use `allow_root=True` only for directory listing.
No delete or rename operation may target the workspace root.
A backend policy shall separately validate file type, byte limits, and operation permission.
Use a native trash action for user deletion instead of `shutil.rmtree` in the first desktop release.

### Code Pack J: Revision-aware file writes

Create `desktop:backend/workspace_files.py`:

```python
from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from pathlib import Path

from backend.workspace_paths import workspace_path


MAX_TEXT_BYTES = 2 * 1024 * 1024
_WRITE_LOCK = threading.RLock()


class RevisionConflict(Exception):
 pass


def content_hash(blob: bytes) -> str:
 return hashlib.sha256(blob).hexdigest()


def read_workspace_file(root: Path, raw: str) -> dict:
 path = workspace_path(root, raw)
 if not path.is_file():
 raise FileNotFoundError(raw)
 with path.open("rb") as handle:
 blob = handle.read(MAX_TEXT_BYTES + 1)
 if len(blob) > MAX_TEXT_BYTES:
 raise ValueError("The file exceeds the text limit.")
 return {"path": str(path), "content": blob.decode("utf-8"), "revision": content_hash(blob), "size": len(blob)}


def save_workspace_file(root: Path, raw: str, content: str, expected_revision: str) -> dict:
 if not isinstance(content, str) or not isinstance(expected_revision, str) or not expected_revision:
 raise ValueError("Content and an expected revision are required.")
 blob = content.encode("utf-8")
 if len(blob) > MAX_TEXT_BYTES:
 raise ValueError("The content exceeds the text limit.")
 with _WRITE_LOCK:
 path = workspace_path(root, raw)
 if not path.is_file():
 raise FileNotFoundError(raw)
 current = read_workspace_file(root, raw)
 if current["revision"] != expected_revision:
 raise RevisionConflict("The file changes after the read.")
 mode = path.stat().st_mode & 0o777
 descriptor, name = tempfile.mkstemp(prefix=".xavani-save-", dir=path.parent)
 temporary = Path(name)
 try:
 with os.fdopen(descriptor, "wb") as handle:
 handle.write(blob)
 handle.flush()
 os.fsync(handle.fileno())
 os.chmod(temporary, mode)
 if read_workspace_file(root, raw)["revision"] != expected_revision:
 raise RevisionConflict("The file changes during the save.")
 os.replace(temporary, path)
 finally:
 temporary.unlink(missing_ok=True)
 return {"path": str(path), "revision": content_hash(blob), "bytes": len(blob)}
```

Create `desktop:tests/desktop/test_workspace_files.py`:

```python
import pytest

from backend.workspace_files import RevisionConflict, read_workspace_file, save_workspace_file


def test_current_revision_saves(tmp_path):
 path = tmp_path / "file.py"
 path.write_text("old\n", encoding="utf-8")
 base = read_workspace_file(tmp_path, "file.py")
 result = save_workspace_file(tmp_path, "file.py", "new\n", base["revision"])
 assert path.read_text(encoding="utf-8") == "new\n"
 assert result["revision"] != base["revision"]


def test_stale_revision_preserves_newer_content(tmp_path):
 path = tmp_path / "file.py"
 path.write_text("old\n", encoding="utf-8")
 base = read_workspace_file(tmp_path, "file.py")
 path.write_text("external\n", encoding="utf-8")
 with pytest.raises(RevisionConflict):
 save_workspace_file(tmp_path, "file.py", "buffer\n", base["revision"])
 assert path.read_text(encoding="utf-8") == "external\n"
```

This implementation detects normal external edits.
It does not eliminate the final cross-process check-to-replace race.
Do not claim a hostile-process guarantee.
For agent and desktop collaboration, route both writers through the same backend write service before enabling concurrent edits.
Until that route exists, disable desktop Save during an active agent mutation.
Keep native external-editor conflicts explicit.

New files use the existing explicit New file action.
Do not treat a missing revision as permission to overwrite or create a file.
Map errors consistently:

- `RevisionConflict`: 409.
- Missing expected revision: 428.
- Oversized payload: 413.
- `UnicodeDecodeError`: 415.
- `PermissionError`: 403.
- `FileNotFoundError`: 404.

### Code Pack K: Workbench and Flip state

Create `desktop:src/renderer/workbench-state.js`:

```javascript
'use strict';
(function expose(root) {
 function initialWorkbench(workspaceId) {
 return {
 workspaceId, dockOpen: true, dockTab: 'preview', follow: true,
 lastFile: null, lastFileSeq: 0, dirty: false,
 explorerWidth: 240, agentWidth: 360, bottomHeight: 220,
 };
 }

 function reduceWorkbench(state, action) {
 if (action.type === 'workspace') return initialWorkbench(action.workspaceId);
 if (action.type === 'close-dock') return { ...state, dockOpen: false };
 if (action.type === 'open-dock') return { ...state, dockOpen: true };
 if (action.type === 'dirty') return { ...state, dirty: Boolean(action.value), follow: action.value ? false : state.follow };
 if (action.type === 'follow') return { ...state, follow: Boolean(action.value) && !state.dirty };
 if (action.type === 'file-changed') {
 if (action.workspaceId !== state.workspaceId || !Number.isInteger(action.seq) || action.seq <= state.lastFileSeq) return state;
 return {
 ...state, lastFile: action.path, lastFileSeq: action.seq,
 dockTab: state.dockOpen && state.follow && !state.dirty ? 'files' : state.dockTab,
 };
 }
 if (action.type === 'flip') {
 if (!state.dockOpen || !state.lastFile) return state;
 return { ...state, dockTab: state.dockTab === 'preview' ? 'files' : 'preview' };
 }
 if (action.type === 'reset-layout') {
 return { ...state, explorerWidth: 240, agentWidth: 360, bottomHeight: 220 };
 }
 return state;
 }

 const api = { initialWorkbench, reduceWorkbench };
 if (typeof module !== 'undefined' && module.exports) module.exports = api;
 else root.XavaniWorkbench = api;
})(globalThis);
```

Create `desktop:tests/desktop/test_flip_state.js`:

```javascript
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { initialWorkbench, reduceWorkbench } = require('../../src/renderer/workbench-state');

test('closed dock stays closed after a file change', () => {
 let state = reduceWorkbench(initialWorkbench('w1'), { type: 'close-dock' });
 state = reduceWorkbench(state, { type: 'file-changed', workspaceId: 'w1', seq: 1, path: 'a.py' });
 assert.equal(state.dockOpen, false);
 assert.equal(state.dockTab, 'preview');
});

test('dirty buffer pauses follow until explicit resume', () => {
 let state = reduceWorkbench(initialWorkbench('w1'), { type: 'dirty', value: true });
 state = reduceWorkbench(state, { type: 'dirty', value: false });
 assert.equal(state.follow, false);
 state = reduceWorkbench(state, { type: 'follow', value: true });
 assert.equal(state.follow, true);
});

test('flip returns to the preview', () => {
 let state = initialWorkbench('w1');
 state = reduceWorkbench(state, { type: 'file-changed', workspaceId: 'w1', seq: 1, path: 'a.py' });
 assert.equal(state.dockTab, 'files');
 state = reduceWorkbench(state, { type: 'flip' });
 assert.equal(state.dockTab, 'preview');
 state = reduceWorkbench(state, { type: 'flip' });
 assert.equal(state.dockTab, 'files');
});

test('workspace switch clears the old file pointer', () => {
 let state = initialWorkbench('w1');
 state = reduceWorkbench(state, { type: 'file-changed', workspaceId: 'w1', seq: 1, path: 'a.py' });
 state = reduceWorkbench(state, { type: 'workspace', workspaceId: 'w2' });
 assert.equal(state.lastFile, null);
});
```

Add `workbench-state.js` before `app.js`.
Make existing `dockState` rendering read this reducer's state.
Do not keep 2 independent values for follow or active dock tab.
Retain the existing `studio.tabs` content until the editor adapter takes ownership.

Place the CSS tokens in `desktop:src/renderer/workbench.css`.
Load that file after `styles.css` during the transition.
Use explicit grid areas named `activity`, `explorer`, `editor`, `agent`, `bottom`, and `status`.
Do not use negative margins to simulate panel boundaries.
Every resize handle shall expose keyboard arrows and `role="separator"`.

### Code Pack L: Editor adapter contract

Create `desktop:src/renderer/editor-adapter.js` with this implementation:

```javascript
'use strict';
(function expose(root) {
 function createEditorAdapter(monaco, host, saveFile) {
 const models = new Map();
 const editor = monaco.editor.create(host, {
 automaticLayout: true, fontSize: 13, lineHeight: 20,
 minimap: { enabled: false }, scrollBeyondLastLine: false,
 });
 let active = null;

 function openFile(file) {
 if (!models.has(file.path)) {
 const model = monaco.editor.createModel(file.content, undefined, monaco.Uri.file(file.path));
 models.set(file.path, { model, revision: file.revision, base: file.content, view: null });
 }
 if (active) models.get(active).view = editor.saveViewState();
 active = file.path;
 const tab = models.get(active);
 editor.setModel(tab.model);
 if (tab.view) editor.restoreViewState(tab.view);
 }

 async function saveActive() {
 if (!active) return null;
 const path = active;
 const tab = models.get(path);
 const submitted = tab.model.getValue();
 const result = await saveFile(path, submitted, tab.revision);
 tab.revision = result.revision;
 tab.base = submitted;
 return result;
 }

 function isDirty(path = active) {
 const tab = models.get(path);
 return Boolean(tab && tab.model.getValue() !== tab.base);
 }

 function closeFile(path) {
 const tab = models.get(path);
 if (!tab) return;
 if (isDirty(path)) throw new Error('Save or discard the buffer before close.');
 if (active === path) {
 active = null;
 editor.setModel(null);
 }
 tab.model.dispose();
 models.delete(path);
 }

 function dispose() {
 for (const tab of models.values()) tab.model.dispose();
 models.clear();
 editor.dispose();
 active = null;
 }

 return { openFile, saveActive, isDirty, closeFile, dispose, editor };
 }

 if (typeof module !== 'undefined' && module.exports) module.exports = { createEditorAdapter };
 else root.XavaniEditor = { createEditorAdapter };
})(globalThis);
```

The `saveFile` adapter shall call `/desktop/api/fs/write` with these fields:

```json
{
 "path": "src/example.py",
 "content": "print('example')\n",
 "expected_revision": "the exact revision from the file read"
}
```

On 409, throw a conflict error before modifying `tab.base` or `tab.revision`.
Do not overwrite the user's buffer with the server response.
If the user types during a save, `isDirty` shall remain true after that save.

Monaco integration microsteps:

- Bundle Monaco and its workers locally through a pinned build tool.
- Use a dedicated worker entry, `src/renderer/editor-worker.js`.
- Keep the current CSP restrictive.
- Do not enable `unsafe-eval` merely to silence a worker error.
- Use Monaco's documented worker configuration for the pinned version.
- Use `monaco.editor.createDiffEditor` for the diff view.
- Set both diff models from immutable before and after snapshots.
- Dispose both models when the diff tab closes.
- Translate LSP ranges from zero-based positions without changing their meaning.
- Attach diagnostics only when their document version matches the current buffer.

Do not add a second LSP server.
Use the existing `agent/lsp` manager through a narrow authenticated backend route.

### Code Pack M: Workflow catalog and skill receipts

Create `agent:agent/workflow_catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workflow:
 name: str
 skills: tuple[str, ...]
 checks: tuple[str, ...]
 external_actions: bool = False


WORKFLOWS = {
 "finance": Workflow("Finance analysis", (
 "oag_skills/finance/3-statement-model/SKILL.md",
 "oag_skills/finance/dcf-model/SKILL.md",
 "oag_skills/finance/excel-author/SKILL.md",
 ), ("source_schema", "financial_reconciliation", "artifact_open")),
 "invoices": Workflow("Invoice review", (
 "oag_skills/workflow-packs/invoice-extraction/SKILL.md",
 ), ("source_schema", "invoice_totals", "invoice_duplicates")),
 "daily": Workflow("Daily operations", (
 "oag_skills/business/business-assistant/SKILL.md",
 "skills/productivity/planner/SKILL.md",
 ), ("source_coverage", "task_owners", "task_duplicates")),
 "inbox": Workflow("Inbox and support", (
 "skills/email/himalaya/SKILL.md",
 ), ("source_coverage", "recipient_scope", "draft_review"), True),
 "meetings": Workflow("Meetings", (
 "oag_skills/workflow-packs/meeting-notes/SKILL.md",
 ), ("source_coverage", "action_citations")),
 "sales": Workflow("Sales and marketing", (
 "oag_skills/business/business-assistant/SKILL.md",
 ), ("source_coverage", "brand_policy", "recipient_scope"), True),
 "people": Workflow("People and administration", (
 "oag_skills/business/business-assistant/SKILL.md",
 ), ("source_coverage", "access_scope", "sensitive_fields")),
 "procurement": Workflow("Procurement and inventory", (
 "oag_skills/business/business-assistant/SKILL.md",
 ), ("source_schema", "quantity_units", "order_duplicates"), True),
 "compliance": Workflow("Legal and compliance support", (
 "skills/software-development/security-review/SKILL.md",
 "oag_skills/business/business-assistant/SKILL.md",
 ), ("source_coverage", "jurisdiction", "source_date")),
 "engineering": Workflow("Engineering and design", (
 "skills/software-development/frontend-design/SKILL.md",
 "skills/software-development/api-design-review/SKILL.md",
 "skills/software-development/security-review/SKILL.md",
 ), ("tests", "lint", "build", "security", "visual_review")),
 "executive": Workflow("Executive reporting", (
 "oag_skills/finance/pptx-author/SKILL.md",
 "skills/productivity/powerpoint/SKILL.md",
 ), ("source_coverage", "report_totals", "artifact_open")),
 "incidents": Workflow("Safety and incidents", (
 "skills/software-development/security-review/SKILL.md",
 "oag_skills/security/oss-forensics/SKILL.md",
 ), ("source_coverage", "evidence_integrity", "recovery_proof")),
}
```

Create `agent:agent/workflow_skills.py`:

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from agent.workflow_catalog import WORKFLOWS


@dataclass(frozen=True)
class LoadedSkill:
 path: str
 sha256: str
 content: str


def load_workflow_skills(workflow_id: str, resolve_skill) -> tuple[LoadedSkill, ...]:
 workflow = WORKFLOWS[workflow_id]
 loaded = []
 for identifier in workflow.skills:
 resolved = resolve_skill(identifier)
 if resolved is None:
 raise ValueError(f"Required skill unavailable: {identifier}")
 path = Path(resolved)
 content = path.read_text(encoding="utf-8")
 if not content.strip() or "[SKILL_PRUNED]" in content:
 raise ValueError(f"Required skill content unavailable: {identifier}")
 digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
 loaded.append(LoadedSkill(identifier, digest, content))
 return tuple(loaded)
```

The resolver shall use existing profile discovery and disabled-skill rules.
Do not implement a second filesystem search order in this module.
Do not use a skill path from untrusted source text as executable configuration.

Catalog validation test:

```python
from pathlib import Path

from agent.workflow_catalog import WORKFLOWS


def test_catalog_skill_paths_exist():
 root = Path(__file__).resolve().parents[2]
 assert len(WORKFLOWS) == 12
 for workflow in WORKFLOWS.values():
 assert workflow.checks
 for skill in workflow.skills:
 assert (root / skill).is_file(), skill
```

The count assertion verifies this plan's explicit 12-workflow scope.
It does not freeze the unrelated skill library size.

### Code Pack N: Financial validation

Create `agent:xavani_operator/finance/validation.py`:

```python
from __future__ import annotations

from decimal import Decimal, InvalidOperation


class FinanceValidationError(ValueError):
 pass


def finite_decimal(value) -> Decimal:
 if isinstance(value, (float, bool)) or not isinstance(value, (str, int, Decimal)):
 raise FinanceValidationError("Use a decimal string or an integer.")
 try:
 number = Decimal(value)
 except (InvalidOperation, ValueError) as exc:
 raise FinanceValidationError("The financial value is invalid.") from exc
 if not number.is_finite():
 raise FinanceValidationError("The financial value shall be finite.")
 return number


def validate_statement(statement: dict) -> dict:
 if not isinstance(statement, dict):
 raise FinanceValidationError("The statement shall contain an object.")
 for field in ("currency", "period", "source"):
 if not isinstance(statement.get(field), str) or not statement[field].strip():
 raise FinanceValidationError(f"The statement requires {field}.")
 assets = finite_decimal(statement.get("assets"))
 liabilities = finite_decimal(statement.get("liabilities"))
 equity = finite_decimal(statement.get("equity"))
 difference = assets - liabilities - equity
 if difference != 0:
 raise FinanceValidationError(f"The statement does not balance: {difference}.")
 return {"currency": statement["currency"], "period": statement["period"], "difference": "0"}


def safe_ratio(numerator, denominator) -> str | None:
 top = finite_decimal(numerator)
 bottom = finite_decimal(denominator)
 return None if bottom == 0 else str(top / bottom)


def validate_dcf_rates(discount_rate, terminal_growth) -> tuple[Decimal, Decimal]:
 discount = finite_decimal(discount_rate)
 growth = finite_decimal(terminal_growth)
 if discount <= growth:
 raise FinanceValidationError("The discount rate shall exceed terminal growth.")
 return discount, growth


def duplicate_invoices(rows: list[dict]) -> tuple[str, ...]:
 seen = set()
 duplicates = []
 for row in rows:
 key = tuple(row.get(field) for field in ("supplier_id", "invoice_number", "currency"))
 if not all(isinstance(value, str) and value.strip() for value in key):
 raise FinanceValidationError("An invoice identity is incomplete.")
 if key in seen:
 duplicates.append(row["invoice_number"])
 seen.add(key)
 return tuple(duplicates)
```

Create `agent:tests/operator/test_finance_validation.py`:

```python
import pytest

from xavani_operator.finance.validation import (
 FinanceValidationError, duplicate_invoices, finite_decimal,
 safe_ratio, validate_dcf_rates, validate_statement,
)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", 1.2, True, None])
def test_invalid_financial_values_fail(value):
 with pytest.raises(FinanceValidationError):
 finite_decimal(value)


def test_statement_requires_exact_reconciliation():
 value = {
 "currency": "ZAR", "period": "2026-Q2", "source": "test fixture",
 "assets": "100.00", "liabilities": "60.00", "equity": "40.00",
 }
 assert validate_statement(value)["difference"] == "0"
 with pytest.raises(FinanceValidationError):
 validate_statement({**value, "equity": "39.99"})


def test_zero_denominator_is_unavailable():
 assert safe_ratio("10", "0") is None


def test_invalid_terminal_growth_fails():
 with pytest.raises(FinanceValidationError):
 validate_dcf_rates("0.08", "0.08")


def test_duplicate_invoice_identity():
 row = {"supplier_id": "supplier-1", "invoice_number": "INV-1", "currency": "ZAR"}
 assert duplicate_invoices([row, row]) == ("INV-1",)
```

These functions validate a narrow statement schema.
Do not claim they validate a complete workbook.
Add workbook formula and file-open checks in B01's artifact verifier.
A financial source adapter shall validate dates, currency codes, and schema version before calling these functions.
Do not treat a nonempty currency string as ISO currency validation.

### Code Pack O: Exact approval identity

Add this pure helper to `agent:xavani_operator/approval_queue.py`:

```python
import hashlib
import json


def action_digest(*, profile: str, workspace_id: str, operation: str, target: str, payload: dict) -> str:
 if not all(isinstance(value, str) and value for value in (profile, workspace_id, operation, target)):
 raise ValueError("The action identity is incomplete.")
 raw = json.dumps(
 {
 "profile": profile,
 "workspace_id": workspace_id,
 "operation": operation,
 "target": target,
 "payload": payload,
 },
 sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
 ).encode("utf-8")
 return hashlib.sha256(raw).hexdigest()
```

The proposal record shall store this digest.
The approval record shall store the same digest, expiry, and a consumed state.
The executor shall recompute the digest immediately before dispatch.
Consume approval through an atomic store update before the action starts.
A failed action does not restore a consumed approval automatically.

Required state transitions:

```text
draft -> pending_approval
pending_approval -> approved | denied | expired
approved -> executing
executing -> verified | failed | unknown
unknown -> verified | failed
```

No other transition may execute an external action.
An `unknown` action cannot transition directly to `executing`.

### Code Pack P: Capture state

Create `desktop:src/recording.js`:

```javascript
'use strict';

function transitionRecording(state, event) {
 const transitions = {
 idle: { request: 'requesting' },
 requesting: { granted: 'recording', denied: 'idle', cancel: 'idle' },
 recording: { pause: 'paused', stop: 'stopped', limit: 'stopped', error: 'failed' },
 paused: { resume: 'recording', stop: 'stopped', limit: 'stopped', error: 'failed' },
 stopped: { save: 'saved', discard: 'idle' },
 saved: { reset: 'idle' },
 failed: { discard: 'idle' },
 };
 const next = transitions[state] && transitions[state][event];
 if (!next) throw new Error(`Invalid capture transition: ${state} -> ${event}`);
 return next;
}

function captureLimit({ elapsedMs, bytes }) {
 if (!Number.isFinite(elapsedMs) || !Number.isFinite(bytes) || elapsedMs < 0 || bytes < 0) {
 throw new Error('Invalid capture measurement.');
 }
 return elapsedMs >= 30 * 60 * 1000 || bytes >= 250 * 1024 * 1024;
}

module.exports = { transitionRecording, captureLimit };
```

Create `desktop:tests/desktop/test_recording.js`:

```javascript
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { transitionRecording, captureLimit } = require('../../src/recording');

test('capture requires an explicit permission state', () => {
 assert.throws(() => transitionRecording('idle', 'granted'));
 assert.equal(transitionRecording('idle', 'request'), 'requesting');
 assert.equal(transitionRecording('requesting', 'denied'), 'idle');
});

test('pause and stop have explicit transitions', () => {
 assert.equal(transitionRecording('recording', 'pause'), 'paused');
 assert.equal(transitionRecording('paused', 'stop'), 'stopped');
 assert.throws(() => transitionRecording('stopped', 'resume'));
});

test('both capture limits stop capture', () => {
 assert.equal(captureLimit({ elapsedMs: 1800000, bytes: 0 }), true);
 assert.equal(captureLimit({ elapsedMs: 0, bytes: 262144000 }), true);
 assert.equal(captureLimit({ elapsedMs: 1000, bytes: 1024 }), false);
});
```

The state machine does not grant operating-system permissions.
The main-process capture adapter owns those permissions and the temporary file.
Every stop path shall stop all media tracks and close the file handle.
Use bounded chunk writes with backpressure.
Do not accumulate the complete recording in renderer memory.

### Code Pack Q: Product boundary rules

Create the scan with 2 categories:

- Product surfaces.
- Legal and provenance surfaces.

Product surface allowlist:

```json
{
 "product_names": ["Xavani", "Enternovate"],
 "owned_hosts": ["enternovate.com", "www.enternovate.com"],
 "release_repositories": ["enternovate/xavani-agent", "enternovate/xavani-desktop"],
 "legal_files": ["LICENSE", "THIRD_PARTY_NOTICES.md"],
 "default_remote_inference": false,
 "default_telemetry": false,
 "default_update_checks": false
}
```

Do not interpret `owned_hosts` as a ban on user-selected model providers.
Scan default product links separately from provider catalogs.
Scan built runtime assets, not only source files.

Add these tests before scanner implementation:

- A product button that opens `portal.the upstream project.com` fails.
- A product button that opens an Enternovate release page passes.
- A legal notice that names an upstream copyright holder passes.
- A provider setting that explicitly selects OpenAI passes.
- A blank custom endpoint stays blank after startup.
- A default telemetry request fails even if it targets an Enternovate host.

Do not whitelist an entire source directory because it contains 1 legal notice.
Use file-specific exceptions with a stated legal purpose.
Preserve upstream attribution in copied source headers where the license requires it.

### Code Pack R: Release manifest

Create this schema as `desktop:docs/reliability/release-manifest.schema.json` during implementation:

```json
{
 "$schema": "https://json-schema.org/draft/2020-12/schema",
 "type": "object",
 "additionalProperties": false,
 "required": ["schema_version", "product", "publisher", "desktop_version", "engine_version", "desktop_commit", "engine_commit", "platform", "architecture", "runtime_versions", "artifacts", "verification_report", "channel"],
 "properties": {
 "schema_version": {"const": 1},
 "product": {"const": "Xavani"},
 "publisher": {"const": "Enternovate"},
 "desktop_version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
 "engine_version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
 "desktop_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
 "engine_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
 "platform": {"enum": ["macos", "windows"]},
 "architecture": {"enum": ["arm64", "x64"]},
 "runtime_versions": {"type": "object", "minProperties": 2, "additionalProperties": {"type": "string"}},
 "artifacts": {
 "type": "array", "minItems": 1,
 "items": {
 "type": "object", "additionalProperties": false,
 "required": ["name", "sha256", "bytes"],
 "properties": {
 "name": {"type": "string", "minLength": 1},
 "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
 "bytes": {"type": "integer", "minimum": 1}
 }
 }
 },
 "verification_report": {"type": "string", "minLength": 1},
 "channel": {"enum": ["candidate", "stable"]}
 }
}
```

Do not include the enclosing DMG checksum inside that same DMG.
That creates a circular hash dependency.
Use an embedded payload manifest for internal components.
Use an external release manifest for final installer checksums.

The manifest checker shall:

1. Validate the schema.
2. Reject missing artifact files.
3. Recompute every SHA-256.
4. Compare exact byte sizes.
5. Compare the embedded engine version with package metadata.
6. Compare the expected commit with embedded provenance.
7. Reject a stable channel without completed signing and platform evidence.
8. Return exit code 0 only after every check passes.

Keep signature evidence in the verification report.
Do not put signing secrets in the manifest.

## Request traceability

- Repository comparison: E01–E10 and Task 27.
- Stronger reliability: Tasks 02–12.
- Enternovate branding: Task 24.
- Repeated quality releases: Tasks 25–27.
- VS Code and Cursor workbench: Tasks 13–16.
- Flip and visible files: Tasks 10–15.
- Voice and screen capture: Tasks 22–23.
- Finance: Tasks 18–21 and B01–B02.
- Business operations: Tasks 17–21 and B03–B12.
- Existing skill use: Task 17.
- Weak-model constraints: Tasks 03–08 and Task 25.
- Safety and consent: Tasks 09, 11, 19, 23, and 24.
- TDD and frequent commits: the task conventions and task-specific test commands.

## Backend startup details

Task 09 shall create `desktop:backend/__init__.py` as an empty package file.
Add these lines in `desktop:backend/serve_desktop.py` after the `Path` import:

```python
DESKTOP_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(DESKTOP_PACKAGE_ROOT) not in sys.path:
 sys.path.insert(0, str(DESKTOP_PACKAGE_ROOT))
```

This path permits `backend.desktop_auth` imports in development and packaged layouts.
Do not rely on the shell's current directory for those imports.

In `src/main.js::startBackend`, reset readiness for each new backend generation:

```javascript
backendReadySent = false;
probing = false;
backendInfo = null;
```

Associate callbacks with the specific child instance and generation ID.
A stale child exit shall not clear a newer backend instance.
A stale health response shall not mark a newer generation ready.
Bound readiness to a 15-second deadline.
Show a restart action after that deadline.
Do not retry indefinitely.

Add 2 behavior tests to `desktop:tests/desktop/test_security.js`:

- A second backend generation emits its own ready event.
- A first-generation callback cannot change second-generation state.

## Verification record for this plan

Observed facts:

- Both repository HEAD values come from `git log`.
- The desktop version conflict comes from `git show v0.4.0:package.json`.
- The environment versions come from actual terminal output.
- The feature and safety findings cite inspected source paths.
- The the upstream project source comes from pinned GitHub blob responses.
- The upstream implementation findings use the inspected local reference revision.
- The research worker fails with HTTP 429.
- Direct inspection continues after that failure.

Not verified during plan mode:

- Application runtime behavior.
- Existing test pass counts.
- Desktop screenshots.
- Real-model quality.
- Live connectors.
- Capture permissions.
- Signing and installation.
- Public release state.

Implementation approval and publication approval remain separate.

### Plan audit

The read-only plan checks return these results:

- Task headings: 27, with unique consecutive IDs.
- Code packs: 18, labelled A through R.
- Python blocks: 26 parse without syntax errors.
- JavaScript blocks: 10 parse without syntax errors.
- JSON blocks: 5 parse without syntax errors.
- Workflow arithmetic: 12 workflows × 3 cases = 36 cases.
- Capture duration: 30 minutes = 1800000 milliseconds.
- Capture size: 250 MiB = 262144000 bytes.
- Existing modification paths resolve on disk.
- Task 14's new state module depends on its creation in Task 13.
- The agent working tree remains unchanged.
- The desktop retains its original README and untracked changes.

These checks validate plan structure and snippet syntax.
They do not prove application behavior or complete integration.
The implementer shall use the stated RED → GREEN checks before each implementation commit.



## Addendum A — Enternovate brand purity (2026-09-13)

Owner directive: zero mentions of the predecessor agent name or other upstream
projects in the repositories. Everything presents as Xavani by Enternovate.

Status: sweep executed on branch feat/r1-reliability.

Removed: README derivation paragraph (replaced with a LICENSE pointer),
AGENTS.md notices line, SOUL/identity denial text (rewritten to deny any
other agent without naming one), browser turn envelope id (now
``xavani.browser.turn.v2``; the parser accepts any ``*.browser.turn.v2``
suffix so older extension builds keep working), plugin dashboard bundles
(SDK global, session token global, header name, UI strings), release tooling
author aliases for upstream-company addresses, changelog/release-note
wording, XAVANI_EDGE_REPORT.md, desktop migration labels ("Legacy Agent"),
datagen example, and the pre-commit scrub hook scope.

Documented exceptions (with evidence):
1. LICENSE — required copyright notices for the MIT-derived work. Do not remove.
2. Guard modules and their tests (detectors, local_registry, guidelines_gate,
 the pre-commit hook, the *_port guard tests) — they contain the banned
 words because their job is to block those references.
3. Migration bridges (scripts/xavani-gateway, scripts/install.ps1) — the
 owner's machine still carries ``ai.upstream.gateway.plist`` and ``~/.upstream``;
 deleting the bridges would leave old services running and old data
 unmigrated. Remove only with explicit owner approval.
4. Third-party license files (plugins/xavani-achievements/LICENSE) and
 dependency metadata (ui-tui/web package-lock.json contain the unrelated
 Meta ``upstream-parser`` npm package).
5. Legacy migration source id + paths in the desktop backend and renderer
 (they read ``~/.upstream`` history so users can import old sessions).

Enforcement: the repo pre-commit scrub hook now covers the full banned-word
set with the exception list. Acceptance command:
``git grep -ilE "upstream|the upstream project|the upstream project" | sort`` must list only the
documented exceptions above. A guard test for this list is Task 28's scope.

## Addendum B — Security hardening wave (CyberGym-style)

Reference methodology: CyberGym (arXiv 2506.02548) evaluates agents against
1,507 real-world vulnerabilities; CyberGym-E2E (arXiv 2606.04460) covers
discovery-to-patch lifecycles. Xavani adopts the methodology (adversarial,
sandboxed, severity-mapped, regression-gated), not the external corpus.

Existing anchors: tools/security_scan_tool.py, the CI security stack
(Bandit, Gitleaks, Semgrep, pip-audit, Trivy, OSV), Task 24 boundaries.

Wave tasks (after Tasks 09–12 land, since they define the surfaces):

- Task 28a: Adversarial corpus per surface. Write executable attack cases as
 pytest/node tests in a quarantined dir:
 * desktop auth: missing/forged/replayed token, foreign Origin, second
 connection after restart, token scope confusion across the two ports;
 * workspace paths: string-prefix sibling, ``..`` chains, symlink escape,
 unicode normalization, windows-style separators, null bytes;
 * file writes: stale-revision race, temp-file symlink pre-creation,
 oversized payloads, partial writes;
 * run events: forged/duplicated/gapped event streams, tool id collisions;
 * agent side: model-authored receipts rejected, revision invalidation,
 approval digest binding, cancelled-check handling.
 Each case runs sandboxed with temporary homes; no network, no real models.
- Task 28b: Run repo scanners over the changed trees; record results in
 docs/reliability/security-wave.md with severity, evidence, and fixes.
- Task 28c: Gate. Zero unresolved high/critical findings; every medium gets
 either a fix or a written risk acceptance. Regression tests added for
 every confirmed exploitable finding.

## Addendum C — Full-stack integration gate ("all tests pass together")

- C1 Agent: full suite on the branch with the canonical runner and the
 Python 3.11 environment; record pass/skip/fail counts and triage every
 failure (fix or documented environment limitation).
- C2 Desktop: full pytest suite + node tests + syntax checks; then the
 Task 16 Playwright smoke once available.
- C3 Cross-repo: desktop tests consume the engine checkout; run the desktop
 suite against the branch and the packaged-app smoke after Task 26.
- C4 Acceptance artifact: docs/reliability/integration-report.md with exact
 commands, counts, and residual known issues. "All tests pass together" is
 claimed only with this artifact committed.

R1 completion criteria (updated): Tasks 01–12 + Addendum A + Addendum B +
Task 24, then Addendum C's report. Tasks 13–16 (workbench), 17–23 (business/
workflows/capture), and 25–27 (model matrix/release) follow in R2–R4.

## Addendum A2 — Long-tail brand sweep (Task 29)

Scope remaining after the product-surface pass (commit d2e00687):
website/docs (English + zh-Hans), skills/, oag_skills/, optional-skills/
long-tail files, remaining test comments, and stale subscription-era docs
(the Tool Gateway / subscription pages describe features that were scrapped;
they need a truth pass, not only a rename).

Rules: functional identifiers stay (provider id ``upstream``, ``NOUS_*`` env
vars, ``managed_tools_enabled`` and friends). Prose, titles, links, and
display strings become Xavani/Enternovate. Never invent Enternovate hosts.
Do not delete required attribution files.

Acceptance: with the documented exceptions, a repo-wide scan for
"the upstream project", "the portal", "upstream Subscribers", the predecessor agent
name, and other-project names returns only the exception list in Addendum A.
The pre-commit scrub hook already encodes this target for product surfaces;
Task 29 extends coverage to docs and skills trees and then removes those
trees from the hook exclude list.

Execute as a delegated sweep with a per-file review of any non-mechanical
case (model ids in training references, godmode tables, user-story quotes).

## Addendum D — Owner decisions (2026-09-14)

1) Push and PRs approved: both feat/r1-reliability branches are pushed;
 draft PRs opened while R1 completes.
 - Agent: https://github.com/enternovate/xavani-agent/pull/118
 - Desktop: https://github.com/enternovate/xavani-desktop/pull/1
 Each subsequent R1 commit pushes to its branch and updates its PR.
 Flip both PRs to ready-for-review only when R1 completion criteria hold.
2) Brand sweep exceptions accepted as documented in Addendum A (LICENSE
 legal notice; migration bridges for pre-rename installs; scrub guards;
 dependency metadata such as the unrelated npm upstream-parser).
3) Release cadence (updated 2026-09-14, owner): do NOT introduce any new
 version name (no v0.4.0). Keep the current version (0.3.0) and UPDATE the
 existing release/artifacts in place once the R2 workbench lands, on the
 R1+R2 evidence. "Just update it without changing things": same version,
 same naming, refreshed artifacts and notes. R3/R4 continue after that.

### Security wave inputs (captured 2026-09-14)

- enternovate/xavani-agent: 32 open Dependabot alerts (16 high, 13
 medium, 3 low) and 64 open code-scanning alerts on the default branch.
 Task 28b must triage ALL of them: fix real issues, dismiss with
 evidence (per the repo's established remediation workflow), and leave a
 written record in docs/reliability/security-wave.md. Dependency bumps
 regenerate uv.lock via uv (exact pins stay).
- enternovate/xavani-desktop: Dependabot is disabled on the repo; the
 token lacks the scope to read code-scanning alerts (admin:repo_hook).
 Owner may enable Dependabot in repo settings; otherwise the wave covers
 the python/js surfaces directly.

### Integration evidence log (rolling)

- 2026-09-14: FULL agent suite GREEN on 26f29b56 — `caffeinate -dims bash
 scripts/run_tests.sh` → 19187 passed, 195 skipped, 0 failed, 358.94s on 4
 workers (CI-parity runner; integration/e2e excluded per the runner).
 run_tests.sh required a bash-3.2 empty-array fix (26f29b56) to run on the
 owner's macOS machine; pushed.
- 2026-09-14: desktop suite green: 122 pytest + 44 node tests (before 24b).
- 2026-09-14: live Electron smokes: auth chain green (console WS banner via
 authenticated injector), grant→fs/tree 200 / outside 403 green, revision
 conflict 409 flow green (child-verified; parent re-run pending after 24b).
- Security wave: inventory at docs/reliability/security-wave.md (local, held
 from push until fixes land): 32 dependabot (16 high), 64 code-scanning (56
 high), 0 secrets; bandit 4 HIGH. Fix waves 28b-2a/2b in flight.
