> **CLOSED-EXECUTED 2026-10-24.** Evidence: `docs/CLOSURE-0.3.1.md`.

# Xavani E103 Durable State Quality Control Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Complete the E103 turn-bank repair with durable restart behavior, strict memory checks, full review, and one green repository test run.

**Architecture:** The parent agent owns the specification, architecture, prompts, evidence review, and final verdict. Fresh OpenCode Zen DeepSeek agents plan, build, and review each slice.

**Tech Stack:** Python 3.11+, pytest, Ruff, setuptools, Git, OpenCode Zen, and `deepseek-v4-flash`.

---

## Standing Goal

Set this session goal before implementation:

```text
/goal Complete Xavani quality control at the highest evidence-backed quality. Lead architecture and acceptance. Use OpenCode Zen DeepSeek V4 Flash agents for planning, building, testing, and independent review. Require all default repository tests to pass together before completion.
```

Verify the goal with:

```text
/goal status
```

The parent agent shall keep final authority.

The parent agent shall not accept a child summary without direct evidence.

The parent agent shall not edit production or test files during this workflow.

The parent agent shall use fresh child agents to implement each repair slice.

## Current Context

Repository:

```text
/Users/andilemushwana/xavani-agent
```

Current state:

- Branch: `main`.
- `HEAD`: `1af70489e1d9f33d0140754f1b2d6af3f5e4df6c`.
- Git reports 33 changed or untracked paths.
- Git reports 29 collapsed status entries.
- The E103 diff touches 2 tracked files.
- No test process runs now.
- No deployment target exists.
- The full-suite result predates the current E103 changes.
- The prior full-suite exit code equals `0`.
- The prior E103 result reports `13 passed`.
- The current plan does not treat those results as final evidence.

The verified child route uses:

- Provider: `opencode-zen`.
- Model: `deepseek-v4-flash`.
- Reasoning effort: `high`.

A historical 3-child batch against the free route returned HTTP `429` for all 3 tasks.

Those tasks produced no review verdict.

A paid-route test completed successfully on 2026-08-15.

A later paid 3-child planning batch completed without a transport error.

One challenger failed its output contract and produced no verdict.

Do not treat that result as approval.

Use up to 3 read-only children for independent planning work.

Run only 1 E103 builder at a time because all E103 work shares the same 2-file scope.

If the paid DeepSeek route returns HTTP `429`, stop the active batch.

Do not dispatch another child in parallel.

Retry after the provider permits a new request.

Preserve the exact reviewer verdict and direct evidence.

## Source Evidence

Read these files before each child prompt:

- `AGENTS.md`.
- `SESSION_HANDOFF.md`.
- `agent/turn_bank.py`.
- `tests/run_agent/test_turn_bank.py`.

Inspect these exact code areas:

- `agent/turn_bank.py:20-24` for state constants.
- `agent/turn_bank.py:86-110` for state parsing.
- `agent/turn_bank.py:117-149` for persisted-prefix detection.
- `agent/turn_bank.py:152-186` for state writes.
- `agent/turn_bank.py:188-211` for hydration.
- `agent/turn_bank.py:238-243` for memory result checks.
- `agent/turn_bank.py:258-297` for memory writes.
- `agent/turn_bank.py:300-341` for turn completion.
- `tests/run_agent/test_turn_bank.py:24-338` for E103 tests.

Inspect this history before implementation:

```bash
git show 2b158d4:agent/turn_bank.py
git show 1af7048:agent/turn_bank.py
git diff -- agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

## Defect Inventory

The parent audit finds 15 E103 defects or risks.

### Defect 1: Legacy count drift

A legacy state can contain:

```json
{"version":1,"completed_count":1,"pending_count":2}
```

The state represents 2 completed turns at an interval of 2.

The current reader restores a completed count of `1`.

The next turn then uses the wrong bank cadence.

### Defect 2: State schema collision

Committed version-1 code stores lagging boundary counts.

The current working code stores accurate boundary counts under the same version.

One state version must not have 2 meanings.

### Defect 3: Stale state after a write failure

A pre-boundary state write can fail.

A memory write can then fail.

The previous state can omit a new pending turn after restart.

A final state write can also fail after memory succeeds.

The stale state can then duplicate persisted turns after restart.

### Defect 4: Memory-disabled writes

The agent can have a memory store while memory writes remain disabled.

The current guard checks only the store.

The turn bank can write when `_memory_enabled` equals `False`.

### Defect 5: Malformed staged values

The current success check rejects only the Boolean value `True`.

Values such as `1`, `"true"`, or `null` can pass as successful writes.

The code can then clear pending turns without a valid write contract.

### Risk 6: Duplicate fallback content

The memory store rejects exact duplicate entries as an idempotent success.

Two identical fallback turns can therefore share 1 stored entry.

The restart proof must match this real store contract.

### Defect 7: Resume-tail loss

The CLI loads only the latest 40 messages by default.

A configured interval can exceed 20 completed turns.

The current hydration path then restores fewer turns than `pending_count`.

### Defect 8: Compression state split

Context compression changes the session ID.

The current sidecar path derives from the current session ID.

A compression split can therefore leave the pending state under the old ID.

### Defect 9: Synthetic compression turns

Compression can store a summary under the `user` role.

Compression can also store an active task list under the `user` role.

The current turn extractor can pair either synthetic message with a real assistant response.

The turn bank can then store synthetic content as a completed user turn.

### Defect 10: Session boundary leak

The CLI reuses one agent across `/new`, `/resume`, and `/branch`.

The current session reset does not clear turn-bank fields.

A fresh session can write pending turns from the previous session.

### Defect 11: Retry cadence gap

The current code retries once on the first turn after a failed boundary.

If that retry also fails, the code can wait until the next configured boundary.

The requirement says to retry on the next completed turn.

### Defect 12: Transcript mismatch

The conversation loop persists the transcript before output transforms run.

The turn bank receives the transformed final response after that persistence.

The current restart proof can therefore compare 2 different assistant texts.

### Defect 13: Branch transcript baseline

An explicit branch copies the parent transcript into the child session.

The branch must not treat copied parent turns as new child pending turns.

The branch must keep a separate sidecar and a separate cadence.

### Defect 14: Internal continuation turns

The conversation loop persists internal user-role continuation prompts.

These prompts cover length continuation, Codex acknowledgement continuation, maximum-iteration summaries, and kanban recovery.

The current extractor pairs these prompts with assistant text as new completed turns.

Restart hydration can then increase the count and write internal control text to memory.

### Defect 15: Compression state ownership

Compression changes the physical session ID but keeps one logical conversation.

The current state path uses the physical session ID.

Without lineage-aware lookup, a descendant can miss the nearest valid sidecar.

The bank can then lose pending turns or restart its cadence.

## Chosen Design

Use a versioned state contract.

Do not patch only the reported count.

That narrow patch leaves the other defects open.

### State Version 2

Set the current state version to `2`.

Keep read support for version `1`.

Write only version `2` after this repair.

Use this version-2 shape:

```json
{
  "version": 2,
  "completed_count": 2,
  "pending_count": 2,
  "checkpoint_digest": "64 lowercase hexadecimal characters",
  "pending_digest": "64 lowercase hexadecimal characters",
  "write_due": true
}
```

The state file shall not contain raw user text.

The state file shall not contain raw assistant text.

Use SHA-256 for all state digests.

Create a turn digest from this byte sequence:

```text
xavani-turn-bank-turn-v2\0<UTF-8 formatted turn>
```

Create the checkpoint digest from this byte sequence:

```text
xavani-turn-bank-checkpoint-v2\0<compact JSON array [completed_count, turn_digest]>
```

Create the pending digest from this byte sequence:

```text
xavani-turn-bank-pending-v2\0<compact JSON array [base_count, completed_count, ordered turn-digest array]>
```

Set `base_count` to `completed_count - pending_count`.

Use `ensure_ascii=True` and separators `(",", ":")` for both digest arrays.

Use an empty ordered turn-digest array for an empty pending list.

The count fields shall change both state digests even when all formatted turn text repeats.

Keep the current state payload compact.

Use the session database to recover history that the CLI tail omits.

Resolve the compression lineage before each state read.

Check the current physical session sidecar first.

Then check compression ancestors from nearest to oldest.

Use the nearest existing sidecar as the lineage barrier.

If that sidecar has a supported valid schema, use it.

If that sidecar has a supported malformed schema, use safe history recovery.

Do not skip a malformed nearer sidecar to use an older valid sidecar.

If that sidecar has an unsupported future version, block state recovery and memory writes.

Do not skip an unsupported nearer sidecar to use an older valid sidecar.

Treat an unsupported future-version sidecar at any nearest existing lineage position as a barrier.

Do not skip that future sidecar to use an older compression ancestor.

Keep the future sidecar unchanged.

Block memory writes until compatible software handles that sidecar.

Write each new checkpoint under the current physical session ID.

Keep an explicit test path as the highest-priority path override.

Do not merge state across an explicit session branch.

Do not modify the CLI lazy-load behavior.

### State Invariants

Enforce these invariants:

- `completed_count` shall equal the known completed-turn count at the checkpoint.
- `pending_count` shall equal the pending sequence length at the checkpoint.
- `checkpoint_digest` shall bind the last completed turn to `completed_count`.
- `pending_digest` shall bind the complete ordered pending sequence to its base and completed counts.
- `write_due` shall identify an unproved write attempt that must retry.
- `_turn_bank_write_due` shall mirror the active in-memory retry state.
- A compression descendant shall read the nearest valid lineage sidecar.
- A new checkpoint shall use the current physical session sidecar.
- A branch shall not read its parent sidecar.
- Version-2 state shall require all version-2 fields.
- Version-1 state may omit `persisted_count`.
- A future version without a readable current-session sidecar shall use safe history recovery.
- A future version under the current physical session shall block ancestor fallback and state rewrite.
- A malformed state shall trigger the history fallback.

After each successful fallback turn, remove that turn from the in-memory pending prefix.

Write the remaining pending suffix to version 2.

Do not store a separate version-2 `persisted_count`.

Set `write_due=false` for a non-boundary checkpoint.

Set `_turn_bank_write_due=false` for the same in-memory checkpoint.

Set `write_due=true` before a boundary memory attempt.

Set `_turn_bank_write_due=true` before the same attempt.

Keep `write_due=true` after a failed or staged memory result.

Keep `_turn_bank_write_due=true` after the same result.

During hydration, restore `_turn_bank_write_due` from a valid version-2 `write_due` field.

If an older sidecar omits an observed boundary turn, reconstruct `_turn_bank_write_due=true` from complete history and pending state.

Do not wait for the next modulo boundary after this recovery.

Keep `write_due=true` after a partial fallback result.

Set `write_due=false` only after the complete pending sequence has valid persistence proof.

Set `_turn_bank_write_due=false` only after the same proof.

### Legacy Version-1 Migration

Version-1 state has 2 observed writer meanings.

The committed writer can store a lagging count during a failed boundary attempt.

The current uncommitted writer can store an accurate count under the same version.

Do not apply an unconditional arithmetic formula.

Use the completed conversation history as the primary count when it covers the state checkpoint.

Set the recovered completed count to the complete observed count for this covered case.

Calculate the conservative pending base as `max(0, state_completed_count - pending_count)`.

Keep all observed turns from that conservative base through the complete history end.

This formula covers the exact writer and retries at most 1 extra turn from the lagging boundary writer.

Do not select only the latest `pending_count` turns when post-state turns exist.

Treat the version-1 `persisted_count` as advisory only.

Do not clear a version-1 turn from `persisted_count` alone.

Use real memory entries as the persistence proof during migration.

Do not use an individual fallback entry as version-1 proof when the same formatted turn appears outside the candidate pending occurrence.

Treat that occurrence as ambiguous.

Keep the candidate pending for an idempotent retry.

If proof is absent, retry the turn.

If history does not cover the checkpoint, keep the state count and block memory writes.

If version-1 `pending_count` exceeds the supplied completed-turn count, query full current-session history.

Block writes when full history cannot prove the complete version-1 pending suffix.

Prefer duplicate retry over a silent count decrease.

Do not rewrite the legacy state during hydration alone.

Write version `2` on the next completed turn.

### Version-2 Checkpoint Recovery

Store one digest for the last completed turn.

Store one digest for the complete ordered pending sequence.

During hydration:

- Use `completed_count - pending_count` as the pending base count.
- Verify `checkpoint_digest` at the exact `completed_count - 1` index.
- Verify `pending_digest` against the exact pending window that ends at `completed_count`.
- Use `completed_count` to disambiguate repeated identical turn digests.
- Do not select an earlier digest match only because its text matches.
- Query full history when the provided history cannot prove that index.
- Rebuild only compression-continuation lineage.
- Use each physical parent transcript to prove the next child replay.
- Use the recursively reconstructed logical parent only to assemble completed turns.
- Project each database message to `role`, normalized text, `tool_call_id`, normalized `tool_calls`, and tool name.
- Ignore row IDs, timestamps, token counts, and reasoning fields during replay identity.
- Use `finish_reason` only for completed-turn extraction when that field exists.
- Split each child transcript at its compaction summary marker.
- Match the protected head as an exact parent prefix.
- Match the protected tail as an exact parent suffix.
- Remove only those 2 proved replay segments.
- Preserve all child turns after the proved tail replay.
- Do not use unordered or subsequence matching.
- Restore the state pending suffix ending at the verified checkpoint.
- Append all logical turns after the checkpoint.
- Add the new suffix length to `completed_count`.
- Reconcile the candidate pending list against memory entries.
- Block memory writes when full history cannot prove the pending digest.
- Keep the prior sidecar unchanged while recovery remains blocked.
- Retry full-history recovery on the next completed turn.

Verification: Run the stale-state, resume-tail, and compression-lineage tests after Task 7.

Expected: The selected tests pass with 0 failures.

If full history contains the claimed checkpoint index and disproves its digest, reject the version-2 state.

Rebuild the count and pending sequence from complete history and memory proof.

Do not keep a disproved state count as a lower bound.

If complete history ends before the claimed checkpoint index, do not declare the digest disproved.

Block writes until complete history can prove or disprove that checkpoint.

Retry all observable unproved turns after a proved state rejection.

Prefer a duplicate retry over silent turn loss.

### Canonical Transcript

Use the latest completed turn from `agent._session_messages` when it matches the current user turn.

Use the function arguments only when no persisted transcript turn exists.

Hash the same normalized text that `_format_turn()` uses.

Write the canonical transcript text to memory.

Do not hash a transformed display response that differs from the persisted transcript.

### Full-History Fallback

Use `agent._session_db` only when the provided history is insufficient.

Load the full current session before its compression ancestors.

Follow an ancestor only when its `end_reason` equals `compression`.

Also require the child `started_at` value to equal or exceed the parent `ended_at` value.

This time rule excludes delegate children that existed before a later parent compression.

Do not follow a normal branch parent.

For a branch child, strip the exact copied parent message prefix.

Treat that child prefix as either the complete parent transcript or an exact contiguous parent suffix.

Use the longest unambiguous child-prefix and parent-suffix match.

If repeated message patterns make 2 boundary lengths valid, block writes instead of selecting one silently.

Start the branch cadence at `0` after that copied prefix.

Use `get_session()` to inspect each parent relation.

Use `get_messages()` to load unsanitized persisted messages.

The database message rows do not preserve private fields such as `_thinking_prefill` or `_empty_recovery_synthetic`.

Apply the exact text, role, finish-reason, and sequence rules after those private fields disappear.

Do not use ancestor replay that includes a normal branch parent.

If a branch prefix cannot be proved, block memory writes for that hydration.

If a compression replay cannot be proved, keep the last valid sidecar count.

Retry recovery after the next completed turn.

Keep this fallback inside `agent/turn_bank.py`.

### Synthetic Message Filter

Exclude a message in either role when its text contains a complete context-summary envelope.

```text
[CONTEXT COMPACTION — REFERENCE ONLY]
```

Treat these exact texts as control candidates:

```text
[Your active task list was preserved across context compression]
```

```text
[System: Your previous response was truncated by the output
```

```text
[System: Continue now. Execute the required tool calls
```

```text
[System: You are a Xavani kanban worker.
```

```text
You've reached the maximum number of tool-calling iterations allowed.
```

```text
You just executed tool calls but returned an empty response.
```

```text
[IMPORTANT: MCP servers have been reloaded.
```

Exclude messages with these in-memory flags without further text checks:

- `_kanban_stop_synthetic`.
- `_empty_recovery_synthetic`.
- `_thinking_prefill`.

If a compression summary prefixes a real user message, keep only the text after the exact end-summary marker.

Do not discard the real user suffix.

For an unflagged control candidate, require sequence provenance before exclusion.

The extractor shall already hold an outer real user request for these continuation controls:

- Length-limit continuation.
- Codex acknowledgement continuation.
- Maximum-iteration summary.
- Empty-response recovery.
- Kanban recovery.

The MCP reload marker is an out-of-band transcript control.

Exclude the MCP reload marker only when it appears between completed turns or before a later genuine user request.

Do not exclude the first genuine user request only because its text equals or starts with a control candidate.

Treat the preserved task-list marker as synthetic without an outer request only when a context-summary envelope directly precedes it.

Keep a genuine first request that starts with the task-list marker when no context-summary envelope precedes it.

Add 1 focused test where a genuine first user request starts with each unflagged control prefix.

Assert that each genuine request remains a completed turn.

Apply this rule before completed-turn pairing.

### Logical Turn Extraction

Keep the latest real user message pending until one final assistant message closes it.

Do not let an internal user control replace the pending real user message.

Ignore assistant messages that contain tool calls.

Ignore an assistant message with `finish_reason="incomplete"`.

Ignore the assistant text before a Codex acknowledgement continuation marker.

Append assistant fragments before a length-continuation marker.

Concatenate those fragments with the final assistant text without an inserted separator.

Ignore a synthetic assistant value of `(empty)`.

Ignore an assistant message with `_empty_terminal_sentinel=True`.

If the persisted transcript contains the current real user but no completed assistant, do not use function arguments as canonical fallback.

Return no canonical turn for that incomplete persisted request.

Apply this rule when an earlier completed turn has identical user text.

Do not select the earlier assistant response for the unmatched latest request.

Return 1 logical turn for each outer user request.

Use this same extractor for hydration and canonical transcript selection.

### Persisted-Prefix Proof

Keep whole-bank proof exact.

Use the whole-bank header count and ordered body as one proof.

For a candidate sequence with base count `b`, a bank entry that ends at candidate index `e` shall use header count `b + e`.

Reject a matching body when its header count does not equal `b + e`.

Add focused proof tests for a valid header count and a mismatched header count.

Keep fallback proof occurrence-aware.

Consume each stored fallback entry at most once during one reconciliation.

Allow 1 stored fallback entry to prove only 1 repeated occurrence.

Do not let an older identical fallback entry outside the candidate pending window prove a newer occurrence.

Do not use an individual fallback entry to clear a valid version-2 pending suffix.

Retry that suffix through the idempotent memory add contract.

Keep the current contiguous-prefix rule.

Prefer a duplicate retry over an unproved clear.

### Memory Result Contract

Accept these results:

```json
{"success":true}
```

```json
{"success":true,"staged":false}
```

Reject these results:

```json
{"success":true,"staged":true}
```

```json
{"success":true,"staged":1}
```

```json
{"success":true,"staged":"true"}
```

```json
{"success":true,"staged":null}
```

Reject malformed JSON and non-dictionary results.

### Memory Enable Gate

Require all 3 conditions:

- A positive interval.
- `_memory_enabled` equals `True`.
- `_memory_store` exists.

Apply the same gate to hydration and turn completion.

### Session Binding

Track the current session key in the in-memory turn-bank state.

Use `_turn_bank_session_id` as the internal key.

Track `_turn_bank_write_due` with the same session binding.

On the first turn-bank call, bind the key to the current session ID.

If the key changes across `/new`, `/resume`, or `/branch`, clear the in-memory count and pending list before hydration.

Clear `_turn_bank_write_due` at the same fresh-session boundary.

Do not clear these fields for a compression continuation.

Use the session database to prove that the old session is a compression ancestor.

If no session ID exists, keep the current library behavior.

### Retry Cadence

If the pending list exists and the latest write attempt lacks proof, retry on each subsequent completed turn.

Do not wait for the next modulo boundary.

Keep the exact completed count after each attempt.

## Files That May Change

Modify only:

- `agent/turn_bank.py`.
- `tests/run_agent/test_turn_bank.py`.

The plan file may remain under `.hermes/plans/`.

Do not stage the plan file.

## Files That Shall Not Change

Do not modify:

- `agent/agent_init.py`.
- `agent/conversation_loop.py`.
- `agent/background_review.py`.
- `agent/codex_runtime.py`.
- `agent/api_call_watchdog.py`.
- `agent/chat_completion_helpers.py`.
- `tools/memory_tool.py`.
- `tools/delegate_tool.py`.
- `cli.py`.
- `pyproject.toml`.
- `xavani.py`.
- `xavani_cli/`.
- `dist/`.
- `build/`.
- `uv.lock`.
- `SESSION_HANDOFF.md`.
- Any unrelated dirty path.

Do not reset the tree.

Do not use `git add -A`.

Do not use `git add .`.

Do not commit without separate user approval.

## Agent Roles

Use 1 child at a time.

### Child 1: Plan Challenger

Use a fresh read-only child.

Require this output:

```json
{
  "verdict": "APPROVED or REQUEST_CHANGES",
  "missing_invariants": [],
  "missing_tests": [],
  "scope_risks": [],
  "evidence": []
}
```

The child shall inspect the 2 files and the 2 E103 commits.

The child shall not edit files.

The parent shall resolve each valid issue before build work.

### Child 2: Test Builder

Use a fresh child to add only 1 RED test.

The child shall run that test before the matching production change.

The child shall capture the expected business failure.

The child shall not accept setup failures as RED evidence.

The child shall not commit.

### Child 3: Source Builder

Use a fresh child to implement the smallest source change for that RED test.

The child shall use the accepted test as the contract.

The child shall not change the test expectation.

The child shall not edit another file.

The child shall not commit.

Repeat Child 2 and Child 3 for each defect slice.

### Child 4: Specification Reviewer

Use a fresh read-only child after GREEN.

The child shall compare each requirement one by one.

The child shall report exact line evidence.

The child shall return `APPROVED` only with no open requirement.

### Child 5: Quality Reviewer

Use a fresh read-only child after specification approval.

The child shall inspect state safety, privacy, complexity, and test quality.

The child shall inspect all lines in the 2-file E103 diff.

The child shall return `APPROVED` only with no P0 or P1 issue.

### Child 6: Integration Reviewer

Use a fresh read-only child after the complete test run.

The child shall verify the captured exit code.

The child shall verify package evidence and scope evidence.

The child shall not rely on prior summaries.

## Task 1: Freeze Baseline Evidence

**Objective:** Record the exact starting state without changing project files.

**Files:**

- Inspect: `agent/turn_bank.py`.
- Inspect: `tests/run_agent/test_turn_bank.py`.
- Inspect: `SESSION_HANDOFF.md`.

**Step 1: Record the branch and commit**

Run:

```bash
git branch --show-current
git rev-parse HEAD
```

Expected:

```text
main
1af70489e1d9f33d0140754f1b2d6af3f5e4df6c
```

**Step 2: Record the full dirty path list**

Run:

```bash
git status --short --untracked-files=all
```

Expected: 33 changed or untracked paths.

**Step 3: Record the 2-file E103 diff**

Run:

```bash
git diff -- agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

Expected: Only the known E103 work appears.

**Step 4: Run the focused baseline**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short
```

Expected: `13 passed` before new tests.

If the count differs, record the real count.

Do not continue if a baseline test fails.

## Task 2: Challenge This Plan

**Objective:** Obtain 1 independent plan verdict before code changes.

**Files:**

- Read: `AGENTS.md`.
- Read: `SESSION_HANDOFF.md`.
- Read: `agent/turn_bank.py`.
- Read: `tests/run_agent/test_turn_bank.py`.

**Step 1: Dispatch 1 read-only child**

Give the child the full defect inventory and state invariants.

Require the JSON contract from the Plan Challenger section.

**Step 2: Check the verdict**

Expected: `APPROVED`.

If the child returns `REQUEST_CHANGES`, verify each issue directly.

Revise the architecture section only if direct evidence disproves a stated invariant.

If OpenCode Zen returns HTTP `429`, stop the batch.

Do not dispatch another child in parallel.

Retry after the provider permits a new request.

**Task 2 evidence:**

- Delegation: `deleg_d876d19f`.
- Provider: `opencode-zen`.
- Model: paid `deepseek-v4-flash`.
- Verdict: `APPROVED`.
- Missing invariants: `0`.
- Missing tests: `0`.
- Scope risks: `0`.
- Verified project files: `2`.
- Verified defects: `15`.

The parent reviewed the complete JSON result.

The parent accepts the verdict because all issue arrays are empty.

Task 2 now satisfies the independent approval gate.

## Task 3: Add Test Helpers and Memory Gates

**Objective:** Make the test agents explicit about memory enable state.

**Files:**

- Modify: `tests/run_agent/test_turn_bank.py:24-36`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Set the enabled fixture state**

Add this field to the existing fixture:

```python
_memory_enabled=True,
```

Add `_memory_enabled=True` to each enabled restart agent.

Add `_session_messages=[]` to the shared fixture.

Add `_session_messages=[]` to each restart agent that calls `add_completed_turn()`.

**Step 2: Add a conversation helper**

Use this helper for new restart tests:

```python
def _messages(*turns):
    return [
        message
        for user_text, assistant_text in turns
        for message in (
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        )
    ]
```

**Step 3: Add the first disabled-memory RED test**

Add this test first:

```python
def test_memory_disabled_agent_does_not_write_turn_bank(tmp_path):
    disabled = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=tmp_path / "turn-bank.json",
        _memory_enabled=False,
        _memory_store=_Store(),
    )
    with patch("tools.memory_tool.memory_tool") as write:
        assert add_completed_turn(disabled, "first", "answer one") is False
        assert add_completed_turn(disabled, "second", "answer two") is False
    write.assert_not_called()
    assert disabled._turn_bank_completed_count == 0
    assert disabled._turn_bank_pending == []
    assert not disabled._turn_bank_state_path.exists()
```

**Step 4: Run the first test**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'does_not_write_turn_bank'
```

Expected: The test fails for the intended missing guard.

Implement the matching production guard.

Run only the first test again.

Expected: The test passes.

**Step 5: Add the second disabled-memory RED test**

Add this test after the first GREEN result:

```python
def test_memory_disabled_agent_does_not_hydrate_turn_bank(tmp_path):
    state_path = tmp_path / "turn-bank.json"
    state_path.write_text(
        json.dumps({"version": 1, "completed_count": 1, "pending_count": 1}),
        encoding="utf-8",
    )
    disabled = SimpleNamespace(
        _turn_bank_interval=2,
        _turn_bank_completed_count=0,
        _turn_bank_pending=[],
        _turn_bank_state_path=state_path,
        _memory_enabled=False,
        _memory_store=_Store(),
    )
    hydrate_turn_bank(disabled, _messages(("first", "answer one")))
    assert disabled._turn_bank_completed_count == 0
    assert disabled._turn_bank_pending == []
```

**Step 6: Run the second test**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'does_not_hydrate_turn_bank'
```

Expected: The test fails for the intended missing hydration guard.

Implement the matching hydration guard.

Run only the second test again.

Expected: The test passes.

## Task 4: Add Legacy State RED Tests

**Objective:** Capture both observed version-1 count meanings.

**Files:**

- Modify: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Add the missing-progress test**

Create a version-1 state without `persisted_count`.

Use `completed_count=1` and `pending_count=2`.

Hydrate 2 completed turns at interval 2.

Assert these values:

```python
assert restarted._turn_bank_completed_count == 2
assert restarted._turn_bank_pending == [
    ("first", "answer one"),
    ("second", "answer two"),
]
```

Add a third completed turn after hydration.

Assert that the retry writes all 3 pending turns.

Assert that the final count equals `3`.

**Step 2: Run only the missing-progress test**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'legacy_missing_progress'
```

Expected: The completed-count assertion fails.

Implement the smallest covered-history normalization.

Run only the missing-progress test again.

Expected: The test passes.

**Step 3: Add the accurate-count characterization test**

Create this version-1 state:

```json
{"version":1,"completed_count":3,"pending_count":3,"persisted_count":0}
```

Hydrate 3 completed turns at interval 2.

Assert that the completed count remains `3`.

This test prevents an unconditional legacy arithmetic correction.

Expected: The test passes after the covered-history normalization.

**Step 3A: Add the bounded version-1 tail RED test**

Create a version-1 state with `completed_count=25` and `pending_count=25`.

Pass only the latest 20 completed turns to hydration.

Provide all 25 completed turns through the fake session database.

Assert that the completed count equals `25`.

Assert that all 25 turns remain pending without memory proof.

Run only this test.

Expected: The pending assertion fails before full-history version-1 migration.

Implement only the version-1 full-history lookup for this RED test.

Run only this test again.

Expected: The test passes.

**Step 3B: Add the post-checkpoint legacy RED test**

Create a version-1 state with `completed_count=1` and `pending_count=2`.

Provide 3 complete history turns.

Treat turns 1 and 2 as the legacy checkpoint window.

Assert that hydration keeps turns 1 and 2 in the pending window.

Assert that hydration appends turn 3 after the checkpoint.

Assert that the completed count equals `3`.

Run only this test.

Expected: The oldest pending turn disappears before post-checkpoint reconstruction.

Implement the smallest legacy checkpoint-window reconstruction.

Run only this test again.

Expected: The test passes.

**Step 4: Add the partial-progress test**

Create this version-1 state:

```json
{"version":1,"completed_count":1,"pending_count":2,"persisted_count":1}
```

Put only the first formatted turn in `memory_entries`.

Hydrate 2 completed turns.

Assert these values:

```python
assert restarted._turn_bank_completed_count == 2
assert restarted._turn_bank_pending == [("second", "answer two")]
```

Run only this test.

Expected: The pending assertion fails before memory-entry migration proof.

Implement the smallest occurrence-aware memory proof for this test.

Run only this test again.

Expected: The test passes.

**Step 5: Add the stale progress test**

Create the same state with `persisted_count=1`.

Leave `memory_entries` empty.

Hydrate 2 completed turns.

Assert that both turns remain pending.

This test prevents version-1 state from clearing an unproved turn.

Run only this test.

Expected: The test passes after the partial-progress GREEN change.

If it fails, implement only the smallest stale-proof correction.

**Step 5A: Add the older-identical-entry RED test**

Create complete history with an older completed turn that formats identically to the version-1 candidate pending turn.

Place 1 identical fallback entry in memory.

Assert that the older entry does not clear the candidate pending occurrence.

Run only this test.

Expected: The candidate clears before ambiguity protection.

Implement the smallest history-aware ambiguity check.

Run only this test again.

Expected: The test passes.

**Step 6: Run the legacy tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'legacy'
```

Expected: All selected tests pass after the first RED-GREEN cycle.

## Task 5: Implement State Version 2

**Objective:** Separate current state semantics from legacy semantics.

**Files:**

- Modify: `agent/turn_bank.py:20-24`.
- Modify: `agent/turn_bank.py:86-110`.
- Modify: `agent/turn_bank.py:152-186`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Execution order:**

1. Run Step 1 to obtain RED. Verify: the isolated test fails at the version assertion.
2. Implement Steps 2 through 5. Verify: the scoped diff changes only the required state contract.
3. Run the Step 1 test again. Verify: the isolated test reports GREEN.
4. Change and run Step 1A. Verify: the partial fallback test reports GREEN with version-2 assertions.
5. Run each Step 4A cycle. Verify: each case reports the intended RED and then GREEN.
6. Run the Step 4B cycle. Verify: the digest mismatch case reports the intended RED and then GREEN.
7. Run Step 6. Verify: the selected legacy and version tests report 0 failures.

Do not start Step 4A while the round-trip test remains RED.

**Step 1: Add the version-2 round-trip RED test**

After 1 completed turn, read the state JSON.

Assert these values:

```python
assert state["version"] == 2
assert state["completed_count"] == 1
assert state["pending_count"] == 1
assert len(state["checkpoint_digest"]) == 64
assert len(state["pending_digest"]) == 64
assert state["write_due"] is False
```

Assert that the state text excludes the raw turn text.

Compute a checkpoint digest for the same formatted turn at counts `1` and `2`.

Assert that those checkpoint digests differ.

Compute a pending digest for the same 1-turn list at base counts `0` and `1`.

Assert that those pending digests differ.

Run only this test.

Expected: The version assertion fails.

**Step 1A: Replace the version-1 partial-fallback state assertions**

Replace the version-1 assertions in `test_partial_large_content_fallback_retries_only_unpersisted_suffix_after_restart`.

Remove the version-1 `persisted_count` assertion after the first version-2 writer exists.

Assert these version-2 facts instead:

- `version` equals `2`.
- `completed_count` equals `2`.
- `pending_count` equals `1`.
- `write_due` equals `true`.
- Both digests match the exact helper output.

Keep the existing restart assertion for the unpersisted suffix.

Run this existing test alone after the version-2 source change.

**Step 2: Add version constants**

Use this shape:

```python
_LEGACY_STATE_VERSION = 1
_STATE_VERSION = 2
_SUPPORTED_STATE_VERSIONS = {_LEGACY_STATE_VERSION, _STATE_VERSION}
```

**Step 3: Add a turn digest helper**

Use deterministic JSON and SHA-256.

Use lowercase hexadecimal output.

Do not store raw turn content in state.

Normalize user and assistant text before hashing.

Use the exact turn and pending domains from the State Version 2 section.

**Step 4: Read both state versions**

Return the state version from `_read_state()`.

Require both digests for version `2`.

Require a Boolean `write_due` for version `2`.

Allow a missing `persisted_count` only for version `1`.

Parse only the fields needed by the version-2 round-trip GREEN change.

Do not add malformed-field validation before Step 4A establishes RED evidence.

**Step 4A: Add invalid-state RED tests**

Add 1 test for a future state version.

Make the future-version test use a current-session sidecar and a valid older compression-ancestor sidecar.

Assert that hydration does not load the older ancestor.

Assert that memory writes remain blocked.

Assert that both sidecars remain unchanged.

Add 1 test for the first malformed version-2 field class:

- A missing field.

Provide completed history for this test.

Assert that hydration uses the safe history fallback.

Assert that the state payload does not clear an unproved pending turn.

Run only this test.

Expected: The state does not enter the safe fallback before field validation.

Implement the smallest complete-field validation.

Run only this test again.

Expected: The test passes.

Then repeat one RED-GREEN cycle for each remaining field class:

- A Boolean count.
- A negative count.
- An invalid digest.
- A non-Boolean `write_due` value.

During these cycles, add the matching validation rules:

- Reject negative counts.
- Reject invalid digests.
- Reject Boolean and non-integer count fields.
- Require `pending_count <= completed_count` for version `2`.

Do not add the next malformed case before the current case passes.

**Step 4B: Add a digest-mismatch RED test**

Create complete history that contains the claimed checkpoint index.

Create a structurally valid version-2 state with the wrong checkpoint digest.

Assert that hydration rejects the state count.

Assert that hydration rebuilds the count and pending sequence from complete history.

Run only this test.

Expected: The stale state count survives before digest-mismatch rejection.

Implement the smallest exact-index digest rejection.

Run only this test again.

Expected: The test passes.

**Step 4C: Add repeated-text count-binding RED tests**

Create complete history with 3 identical formatted turns.

Create a state with `completed_count=2` and a checkpoint digest generated for count `1`.

Assert that hydration rejects the checkpoint although the turn text matches.

Run only this test.

Expected: The state passes before checkpoint count binding.

Implement only the checkpoint count binding.

Run only this test again.

Expected: The test passes.

Then create a state whose pending digest uses the correct repeated turn text but the wrong base count.

Assert that hydration rejects the pending proof.

Run only this test.

Expected: The state passes before pending base-count binding.

Implement only the pending count binding.

Run only this test again.

Expected: The test passes.

**Step 5: Write only version 2**

Make `_write_state()` include `checkpoint_digest` and `pending_digest`.

Make `_write_state()` include `write_due`.

Make `_write_state()` return `True` after atomic replacement.

Make `_write_state()` return `False` after a write failure.

Keep state writes best effort.

Run only the version-2 round-trip test again.

Expected: The test passes.

Run the existing partial-fallback state test from Step 1A.

Expected: The test passes with version-2 state assertions.

**Step 6: Run the legacy and version tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'legacy or version_two'
```

Expected: All selected tests pass.

## Task 6: Add Stale-State RED Tests

**Objective:** Capture both state-write failure orders.

**Files:**

- Modify: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Test a failed pre-boundary state write**

Write the first turn and its valid state.

Make `atomic_replace` fail during the second turn.

Make the memory result staged.

Restart from the stale first-turn state.

Hydrate both conversation turns.

Assert these values:

```python
assert restarted._turn_bank_completed_count == 2
assert restarted._turn_bank_pending == [
    ("first", "answer one"),
    ("second", "answer two"),
]
```

Run only this test.

Expected: The pending assertion fails.

Implement checkpoint reconciliation for this failure order.

Run only this test again.

Expected: The test passes.

**Step 2: Test a failed final state write**

Allow the boundary pre-state write.

Persist the whole bank in `memory_entries`.

Make the final atomic replacement fail.

Restart from the stale pending state.

Hydrate both conversation turns.

Assert these values:

```python
assert restarted._turn_bank_completed_count == 2
assert restarted._turn_bank_pending == []
```

Add turns 3 and 4.

Assert that the next bank contains only turns 3 and 4.

Run only this test.

Expected: The pending assertion fails before memory proof reconciliation.

Implement memory proof reconciliation for this failure order.

Run only this test again.

Expected: The test passes.

**Step 2A: Test a failed due-state write before memory**

Write a valid non-boundary state for turn 1 at interval `2`.

Make the due-state atomic replacement fail for turn 2.

Make the memory tool raise before it writes anything.

Restart from the stale turn-1 state with complete history through turn 2.

Assert that hydration restores both pending turns.

Assert that `_turn_bank_write_due` equals `True`.

Add turn 3.

Assert that the memory tool retries on turn 3.

Run only this test.

Expected: The turn-3 retry does not occur before due-state reconstruction.

Implement only the due-state reconstruction.

Run only this test again.

Expected: The test passes.

**Step 3: Run all stale-state tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'stale_state or state_write_failure'
```

Expected: Both tests pass after both RED-GREEN cycles.

## Task 7: Implement Checkpoint Reconciliation

**Objective:** Recover newer history while rejecting unproved persistence.

**Files:**

- Modify: `agent/turn_bank.py:188-211`.
- Modify: `agent/turn_bank.py:300-341`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Normalize version-1 counts**

This step implements only the RED version-1 tests from Task 4.

Use observed completed history when it covers the version-1 checkpoint.

Use the greater value from the state count and the observed count.

Keep the state count when history does not cover the checkpoint.

Keep version-2 counts exact.

**Step 2: Locate the version-2 checkpoint**

Use `completed_count - 1` as the exact checkpoint index.

Verify the digest only at that exact index.

Use only the supplied history in this first GREEN change.

Do not query full history before the resume-tail RED test in Task 7A.

Do not search another matching occurrence.

Append all turns after the checkpoint.

**Step 3: Handle an absent checkpoint**

Treat all loaded completed turns as unproved candidates.

Keep the checkpoint count as the lower bound.

Increase it only for turns that follow a proved checkpoint.

Mark the recovery as blocked when the supplied history cannot prove the exact checkpoint.

Do not add database history lookup before the resume-tail RED test.

Do not silently discard a loaded turn.

**Step 4: Reconcile memory proof**

Compare candidate pending turns with current `memory_entries`.

Use the greater valid prefix from state proof and memory proof.

Clear only the proved prefix.

**Step 5: Retry a failed state write**

After a failed memory write, retry the current pending state once.

Keep the call best effort.

**Step 6: Run stale-state tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'stale_state or state_write_failure'
```

Expected: All selected tests pass.

## Task 7A: Add Resume and Compression Recovery Tests

**Objective:** Recover complete pending turns from bounded history and compression lineage.

**Files:**

- Modify: `agent/turn_bank.py`.
- Modify: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Add the resume-tail test**

Create 25 completed turns.

Create version-2 state with these values:

```json
{"version":2,"completed_count":25,"pending_count":25,"checkpoint_digest":"use the production turn-digest helper for turn 25","pending_digest":"use the production pending-digest helper for all 25 turns","write_due":false}
```

Import the private digest helpers from `agent.turn_bank` for this test.

Do not hardcode placeholder digest text.

Pass only the latest 20 turns to hydration.

Provide all 25 turns through a fake session database.

Assert these values:

```python
assert restarted._turn_bank_completed_count == 25
assert restarted._turn_bank_pending == turns
```

Run only this test.

Expected: The pending assertion fails before full-history recovery.

Implement the smallest full-current-session recovery.

Run only this test again.

Expected: The test passes.

**Step 2: Add the compression-lineage test**

Create a root session and a compression child.

Set the root end reason to `compression`.

Set the child start time after the root end time.

Store version-2 state under the root state path.

Use the production digest helpers to create its checkpoint and pending digests.

Put 2 pending turns in the root session history.

Pass a compressed child tail that contains only turn 2.

Assert that hydration restores both root turns.

Assert that the completed count equals `2`.

Run only this test.

Expected: The state lookup fails before nearest compression ancestor resolution.

Implement nearest compression ancestor state lookup.

Do not implement compression lineage lookup before this RED test runs.

Run only this test again.

Expected: The test passes.

**Step 2AA: Add the false-compression-parent RED test**

Create a child before its parent end time.

End the parent with reason `compression` after the child already exists.

Place a valid sidecar under the parent.

Assert that the child does not read that parent sidecar.

Assert that the child uses safe current-session history recovery.

Run only this test.

Expected: The parent sidecar loads before the lineage time rule.

Implement only the lineage time rule.

Run only this test again.

Expected: The test passes.

**Step 2A: Add the chained-compression test**

Create root, middle, and current physical sessions.

Set the root and middle end reasons to `compression`.

Give the root a valid older sidecar.

Give the middle a valid newer sidecar.

Leave the current sidecar absent.

Assert that hydration uses the middle sidecar.

Assert that the root checkpoint does not replace the middle checkpoint.

Run only this test.

Expected: The state selection fails before nearest-first lineage lookup.

Implement the smallest nearest-first lineage selection.

Run only this test again.

Expected: The test passes.

**Step 2B: Add compression-summary placement tests**

Add the standalone assistant-summary test first.

Use the exact `SUMMARY_PREFIX` without an end marker.

Provide the parent protected head and protected tail.

Assert that replay proof removes only the parent replay.

Assert that each post-compression real turn appears exactly once.

Run only this test.

Expected: The replay assertion fails before standalone-summary replay support.

Implement only the standalone-summary replay rule.

Run only this test again.

Expected: The test passes.

Then add the merged-summary test.

Merge the summary into the first real user tail message with the exact end marker.

Use the same replay assertions.

Run only this test.

Expected: The replay assertion fails before merged-summary replay support.

Implement only the merged-summary replay rule.

Run only this test again.

Expected: The test passes.

**Step 3: Add the branch-isolation test**

Create a root session and a branch child.

Set the root end reason to `branched`.

Store a root state file.

Hydrate the branch child with 1 branch turn.

Assert that the branch does not load the root state.

Assert that copied parent turns do not enter the child pending list.

Assert that the child completed count starts at `0` before its first new turn.

Expected: The baseline assertions fail before branch-baseline filtering.

Run this test alone before the branch-baseline implementation.

Implement the smallest branch-baseline filter.

Use the parent transcript as the copied prefix proof.

Keep only child turns after the copied prefix.

Run only this test again.

Expected: The test passes.

**Step 3AA: Add the resumed-tail branch test**

Create a parent transcript with 30 completed turns.

Copy only its latest 20 completed turns into the branch child.

Add 1 new child turn.

Assert that the copied parent suffix adds 0 child completed turns.

Assert that the child count equals `1`.

Assert that only the new child turn remains pending.

Run only this test before parent-suffix matching.

Expected: The copied suffix enters the child count before parent-suffix matching.

Implement the smallest longest-suffix boundary match.

Run only this test again.

Expected: The test passes.

Add a repeated-pattern ambiguity case.

Assert that ambiguous branch boundaries block memory writes.

Run only the ambiguity case.

Expected: The code selects a boundary before ambiguity blocking.

Implement only the ambiguity block.

Run only the ambiguity case again.

Expected: The test passes.

**Step 3A: Add the blocked-history test**

Provide a version-2 sidecar whose checkpoint cannot be proved from the loaded tail.

Make the fake session database fail to provide complete history.

Add 1 completed turn.

Assert that the memory tool does not run.

Assert that the prior sidecar remains unchanged.

Assert that the agent keeps the observable unproved turn for retry.

Run only this test.

Expected: The memory call occurs before blocked-recovery state exists.

Implement the smallest blocked-recovery state.

Run only this test again.

Expected: The test passes.

**Step 4: Add the synthetic-summary test**

Pass a standalone user-role context summary followed by an assistant message.

Assert that completed-turn extraction returns an empty list.

Run only this test.

Expected: The assertion fails before the synthetic message filter.

Implement the summary filter.

Run only this test again.

Expected: The test passes.

**Step 5: Add the merged-summary test**

Prefix a real user message with the context summary and its end marker.

Assert that extraction keeps only the real user suffix.

Run only this test.

Expected: The test passes after the summary filter.

**Step 6: Add the task-list test**

Pass 1 outer real user request.

Then pass the preserved task-list marker.

Then pass 1 final assistant message.

Assert that extraction returns exactly the outer request and final assistant response.

Expected: The test passes after the synthetic message filter.

Add a separate genuine-text test where the task-list prefix starts the first real user request.

Follow it directly with a real assistant response.

Assert that extraction preserves that genuine request.

Run only each task-list test.

Expected: Both tests pass.

**Step 7: Add internal-continuation RED tests**

Add 1 test for each persisted control path:

- Length-limit continuation.
- Codex acknowledgement continuation.
- Maximum-iteration summary.
- Kanban stop recovery.
- Empty-response recovery.
- Thinking-prefill recovery.
- Terminal empty sentinel.

For each test, start with 1 real user message.

Include the required assistant fragments and the internal user control.

End with 1 final assistant response.

Assert that extraction returns exactly 1 logical turn.

Assert that the extracted request text equals the outer request text.

Assert that the extracted text excludes all defined internal control markers.

Assert the exact expected assistant text for each continuation class.

For the maximum-iteration case, assert that extraction returns no completed turn.

The production loop marks this exit as `completed=False`.

Do not count its final summary only during restart hydration.

Do not use the generic 1-logical-turn assertion for this case.

For each flagged runtime path, repeat the extraction after removing all private underscore-prefixed fields.

This second assertion simulates the real SQLite message shape.

For the terminal empty sentinel case, end without a real assistant response.

Assert that extraction returns no completed turn.

Assert that `add_completed_turn()` does not write the `(empty)` function argument when the persisted request remains incomplete.

Precede that unmatched request with a completed turn that uses identical user text.

Assert that canonical selection does not reuse the earlier assistant response.

Add 1 MCP reload control test.

Place the exact reload marker after 1 completed turn and before a later real user request.

Assert that the reload marker creates no completed turn.

Assert that the later real request remains paired with its assistant response.

Run each new test alone before implementation.

Expected: The current test fails before its logical-turn extraction rule.

Implement only the smallest extraction rule for the current failing test.

Run only the same test again.

Require GREEN before the next continuation test.

After those tests pass, add 1 genuine-text preservation test for each unflagged control prefix.

Use each control prefix as the start of the first real user request.

End each request with a real assistant response.

Assert that extraction keeps the complete genuine user text.

Run each preservation test alone before the next preservation test.

Expected: Each preservation test passes.

**Step 8: Run all recovery tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'resume_tail or compression_lineage or branch_isolation or synthetic or continuation or recovery'
```

Expected: All selected tests pass.

## Task 7B: Add Session and Retry Tests

**Objective:** Keep banks isolated across session changes and retry each failed bank on the next turn.

**Files:**

- Modify: `agent/turn_bank.py`.
- Modify: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Add the fresh-session isolation test**

Add 1 pending turn under session `old`.

Change the agent session ID to `new`.

Add 1 completed turn under session `new`.

Assert that the memory write does not contain the old turn.

Assert that the new session count equals `1`.

Run only this test.

Expected: The content assertion fails before session binding.

Implement the smallest session binding.

Run only this test again.

Expected: The test passes.

**Step 2: Add the compression-continuation characterization test**

Add 1 pending turn under a compression parent.

Change the session ID to its compression child.

Prove the relationship through the fake session database.

Add the next completed turn.

Assert that the write contains both turns.

Run only this test.

Expected: The test passes after session binding supports compression continuation.

**Step 2A: Add normal-pending cadence proof**

Use interval `4`.

Add turns 1 through 3.

Assert that memory receives 0 calls.

Assert that `_turn_bank_write_due` equals `False` after each turn.

Add turn 4.

Assert that memory receives 1 call.

This test separates normal pending state from failed due state.

Run only this test.

Expected: The test passes before and after retry-cadence repair.

**Step 3: Add the repeated-retry test**

Use interval `2`.

Make the boundary write fail.

Make the turn-3 retry fail.

Make the turn-4 retry succeed.

Assert that memory writes occur on turns 2, 3, and 4.

Assert that the final bank contains turns 1 through 4.

Run only this test.

Expected: The write count fails before retry cadence repair.

Implement a retry on each subsequent completed turn while pending proof remains.

Run only this test again.

Expected: The test passes.

**Step 4: Run the session and retry tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'session_isolation or compression_continuation or repeated_retry'
```

Expected: All selected tests pass.

**Step 5: Add the canonical-transcript test**

Set `agent._session_messages` to a persisted user and assistant pair.

Pass the same user text and a transformed assistant response to `add_completed_turn()`.

Assert that the state checkpoint digest matches the persisted pair.

Assert that the memory content uses the persisted assistant text.

Assert that the transformed display text does not enter memory.

Repeat the test with 2 consecutive outer requests that use identical user text.

Give the requests different raw assistant text.

Assert that canonical selection uses the latest completed occurrence.

Run only this test.

Expected: The content assertion fails before canonical transcript selection.

Do not implement the canonical selector yet.

**Step 5A: Prove the production persistence order**

Add an integration-style test in `tests/run_agent/test_turn_bank.py`.

Construct a local `AIAgent` with the established pattern from `tests/run_agent/test_run_agent.py:61-79`.

Patch `run_agent.get_tool_definitions` to return an empty list.

Patch `run_agent.check_toolset_requirements` to return an empty dictionary.

Patch `run_agent.OpenAI`.

Use the autouse isolated `XAVANI_HOME` fixture.

Also set `XAVANI_HOME` to a `tmp_path` child before `AIAgent` construction.

Assert that the session log and state paths remain under that isolated path.

Set `skip_context_files=True`.

Set `skip_memory=True` during construction.

After construction, set `_memory_enabled=True`.

Attach a local `_Store` with `memory_entries`, `memory_char_limit`, and `_char_count()`.

Set `_turn_bank_state_path` under `tmp_path`.

Configure 1 final model response with raw text `raw answer`.

Build the response with `SimpleNamespace` objects that match the existing `_mock_response()` shape.

Patch `xavani_cli.plugins.invoke_hook`.

Return `["display answer"]` only for the `transform_llm_output` hook.

Return `[]` for all other hooks.

Set the turn-bank interval to `1`.

Use a real in-memory turn-bank store.

Patch only `tools.memory_tool.memory_tool` to append the requested content to that store and return `{"success":true,"staged":false}`.

Run `agent.run_conversation("request")` through the production loop.

Assert that the returned final response equals `display answer`.

Assert that `agent._session_messages` contains `raw answer`.

Assert that the turn-bank memory entry contains `raw answer`.

Assert that the turn-bank memory entry excludes `display answer`.

Run only this test.

Expected: The memory entry contains `display answer` before canonical transcript selection.

Run this integration test before the canonical selector implementation from Step 5.

Require both tests to fail for transformed text.

Implement the smallest canonical transcript selector.

Run the unit test again.

Expected: The unit test passes.

Run the integration test again.

Expected: The integration test passes.

Do not modify `agent/conversation_loop.py`.

**Step 5B: Add whole-bank header proof tests**

Create 2 candidate turns with base count `0`.

Add one memory entry with the exact bank body and header count `2`.

Assert that both turns have proof.

Run only this test.

Expected: The proof fails before header-aware matching.

Implement the smallest exact header-count proof.

Run only this test again.

Expected: The test passes.

Add the mismatched-header test next.

Change only the header count to `3`.

Assert that neither turn has proof.

Run only this test.

Expected: The test passes after exact header-count proof.

Add the nonzero-base test last.

Create a candidate base count of `4` with 2 candidate turns.

Use header count `6`.

Assert that both turns have proof.

Run only this test.

Expected: The proof fails before base-count support.

Implement the smallest base-count support.

Run only this test again.

Expected: The test passes.

Change only the header count to `2` in a final characterization test.

Assert that neither turn has proof.

Run only this final test.

Expected: The test passes.

**Step 6: Run all session tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'session_isolation or compression_continuation or repeated_retry or canonical_transcript'
```

Expected: All selected tests pass.

## Task 8: Add Memory Result RED Tests

**Objective:** Enforce the real memory response contract.

**Files:**

- Modify: `agent/turn_bank.py:238-243`.
- Modify: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Add malformed staged cases**

Add the `staged=1` case first:

```python
def test_integer_staged_value_keeps_pending_turns(agent):
    with patch("tools.memory_tool.memory_tool") as write:
        write.return_value = json.dumps({"success": True, "staged": 1})
        assert add_completed_turn(agent, "first", "answer one") is False
        assert add_completed_turn(agent, "second", "answer two") is False
    assert len(agent._turn_bank_pending) == 2
```

Run only this test.

Expected: The pending assertion fails.

Implement the strict identity check.

Run only this test again.

Expected: The test passes.

Then add `staged="true"` as the next characterization case.

Run only that case.

Expected: The test passes after the strict identity check.

Then add `staged=None` as the final characterization case.

Run only that case.

Expected: The test passes after the strict identity check.

Do not add the next case before the current case passes.

**Step 2: Test a direct success response**

Return this response:

```json
{"success":true}
```

Assert that the boundary write succeeds.

Assert that the pending list becomes empty.

Run only this test.

Expected: The test passes before and after the strict identity check.

**Step 2A: Add exact result-shape characterization tests**

Add the `{"success":true,"staged":false}` case first.

Assert that the result succeeds.

Run only this test.

Expected: The test passes after the strict staged-value GREEN change.

Then add each invalid result as 1 separate case:

- `{"success":1}`.
- `{"success":"true"}`.
- `{"staged":false}`.
- A JSON list.
- Malformed JSON.

For each invalid result:

1. Add only that case. Verify: the scoped test diff contains no second result case.
2. Add the failure assertion. Verify: the assertion keeps the pending turns.
3. Run only that case. Verify: the case reports the intended RED without a setup failure.
4. Implement the smallest result rule. Verify: the source diff changes only the result parser.
5. Run only that case again. Verify: the same case reports GREEN.
6. Require GREEN before the next case. Verify: no later case exists before the current GREEN evidence.

**Step 3: Run the selected tests**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'staged_value or direct_success'
```

Expected: All selected tests pass after the first malformed-case repair.

The direct-success case shall pass before and after the source repair.

## Task 9: Add Duplicate-Content RED Test

**Objective:** Match the real memory store idempotency contract.

**Files:**

- Modify: `agent/turn_bank.py:117-149`.
- Modify: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Use the real memory store**

Force per-turn fallback with 2 identical turns.

Assert that both live writes return success.

Assert that the store contains 1 formatted entry.

Fail the state write after the first duplicate fallback succeeds.

Restart with both completed turns and the stale state.

Assert that 1 stored fallback entry proves only the first occurrence.

Assert that the second occurrence remains pending.

Retry the second occurrence.

Assert that the idempotent memory add returns success.

Restart from the updated state.

Assert that the pending list is empty.

**Step 2: Run the test**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short -k 'duplicate_content'
```

Expected: The first pending assertion fails before occurrence-aware proof.

Implement the smallest occurrence-aware fallback proof.

Keep valid version-2 pending state independent from individual fallback proof.

Run only this test again.

Expected: The test passes.

## Task 10: Verify Strict Memory Proof

**Objective:** Accept only valid writes and keep exact persistence proof.

**Files:**

- Modify: `agent/turn_bank.py:117-149`.
- Modify: `agent/turn_bank.py:238-243`.
- Modify: `agent/turn_bank.py:300-341`.
- Test: `tests/run_agent/test_turn_bank.py`.

**Step 1: Verify all prior source cycles**

Confirm these source changes already have exact GREEN evidence:

- The occurrence-aware fallback proof from Task 9.
- The strict result contract from Task 8.
- The memory-enabled guards from Task 3.

Do not implement these changes again.

**Step 2: Run the focused test file**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py -q --tb=short
```

Expected: All tests pass.

The expected case count equals 25 or more.

Record the exact collected count.

## Task 11: Run Focused Integration Gates

**Objective:** Verify E103 against the real memory store contract.

**Files:**

- Test: `tests/run_agent/test_turn_bank.py`.
- Test: `tests/tools/test_memory_tool.py`.

**Step 1: Run both suites together**

Run:

```bash
.venv/bin/python -m pytest -n 0 -p no:cacheprovider -o addopts='' tests/run_agent/test_turn_bank.py tests/tools/test_memory_tool.py -q --tb=short
```

Expected: `0 failed`.

**Step 2: Run Ruff**

Run:

```bash
.venv/bin/python -m ruff check agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

Expected:

```text
All checks passed!
```

**Step 3: Compile both files**

Run:

```bash
.venv/bin/python -m py_compile agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

Expected: Exit code `0`.

**Step 4: Check whitespace**

Run:

```bash
git diff --check -- agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

Expected: Exit code `0` and no output.

## Task 12: Run Review Pass 1

**Objective:** Prove specification compliance before quality review.

**Files:**

- Review: `agent/turn_bank.py`.
- Review: `tests/run_agent/test_turn_bank.py`.

Dispatch 1 fresh read-only child.

Require checks for each defect in this plan.

Require checks for each state invariant.

Require direct line evidence.

Require the focused test command and exit code.

Expected verdict:

```text
APPROVED
```

If the reviewer reports an issue, verify it directly.

Dispatch a fresh repair child for each valid issue.

Rerun the failed test first.

Rerun all Task 11 gates after the repair.

Repeat Review Pass 1 until approval.

## Task 13: Run Review Pass 2

**Objective:** Prove code quality, state safety, privacy, and test quality.

**Files:**

- Review: `agent/turn_bank.py`.
- Review: `tests/run_agent/test_turn_bank.py`.

Dispatch 1 fresh read-only child.

Require checks for:

- Raw content in state files.
- Digest validation.
- Negative state values.
- Future state versions.
- Truncated conversation tails.
- Repeated identical turns.
- Partial fallback progress.
- Final state-write failure.
- Pre-state-write failure.
- Malformed memory responses.
- Memory-disabled behavior.
- Unnecessary abstractions.
- Narration comments.
- Unrelated changes.

Expected verdict:

```text
APPROVED
```

Do not start the complete suite before this approval.

If the reviewer reports an issue, use the repair loop from Task 12.

## Task 14: Run the Complete Default Suite Together

**Objective:** Prove that all default repository tests pass in one process.

Run the complete suite only after both review approvals.

Start the run as a tracked background process.

Use `notify_on_complete=true`.

Use this command:

```bash
bash -lc 'set -o pipefail; .venv/bin/python -m pytest -n 0 -p no:cacheprovider tests -q --tb=short 2>&1 | tee /tmp/xavani-full-qc-e103-v2.log; rc=${PIPESTATUS[0]}; printf "%s\n" "$rc" > /tmp/xavani-full-qc-e103-v2.exit; exit "$rc"'
```

Expected:

- Exit file: `0`.
- Failed tests: `0`.
- One combined test process.
- One complete summary line.

Record these values:

- Passed count.
- Skipped count.
- Deselected count.
- Warning count.
- Runtime.
- Exit code.

Do not replace this gate with targeted tests.

Do not repeatedly poll the process.

Confirm the process once.

Write a session handoff if the run outlives the active session.

If the suite fails, classify each failure.

For each E103 failure, add a reproducer before a repair in the 2-file scope.

Do not alter an unrelated dirty file without a new approved scope.

## Task 15: Verify Package, Secrets, and Scope

**Objective:** Produce release evidence without changing `dist/`.

**Step 1: Build a fresh wheel in a temporary directory**

Run:

```bash
tmp_dir=$(mktemp -d)
uv build --offline --wheel --out-dir "$tmp_dir"
```

Expected: Exit code `0`.

**Step 2: Inspect required wheel files**

Verify these paths:

- `agent/turn_bank.py`.
- `xavani_cli/templates/scaffold/skill/SKILL.md.tmpl`.
- `xavani_cli/templates/scaffold/plugin/plugin.yaml.tmpl`.
- `xavani_cli/templates/scaffold/plugin/__init__.py.tmpl`.
- `xavani_cli/templates/scaffold/provider/plugin.yaml.tmpl`.
- `xavani_cli/templates/scaffold/provider/__init__.py.tmpl`.

Run:

```bash
.venv/bin/python -c 'import glob,json,zipfile; wheel=glob.glob("'"'"$tmp_dir"'"'"+"/*.whl"); assert len(wheel)==1, wheel; required=["agent/turn_bank.py","xavani_cli/templates/scaffold/skill/SKILL.md.tmpl","xavani_cli/templates/scaffold/plugin/plugin.yaml.tmpl","xavani_cli/templates/scaffold/plugin/__init__.py.tmpl","xavani_cli/templates/scaffold/provider/plugin.yaml.tmpl","xavani_cli/templates/scaffold/provider/__init__.py.tmpl"]; names=set(zipfile.ZipFile(wheel[0]).namelist()); print(json.dumps({"wheel":wheel[0],"missing":[p for p in required if p not in names]},sort_keys=True))'
```

Expected: Missing paths equal `[]`.

**Step 3: Calculate the wheel hash**

Run:

```bash
shasum -a 256 "$tmp_dir"/*.whl
```

Record the exact SHA-256 value.

**Step 4: Run a bounded secret scan**

Scan only these changed project files:

- `agent/turn_bank.py`.
- `tests/run_agent/test_turn_bank.py`.

Do not print matched secret content.

Run this standard-library scanner:

```bash
.venv/bin/python -c 'from pathlib import Path; import re,json,sys; paths=[Path("agent/turn_bank.py"),Path("tests/run_agent/test_turn_bank.py")]; patterns={"private_key":re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),"aws_access_key":re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),"github_token":re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),"openai_key":re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),"slack_token":re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),"literal_secret":re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*[\"'"'"'][^\"'"'"'\s]{16,}[\"'"'"']")}; findings=[{"path":str(path),"line":line_no,"pattern":name} for path in paths for line_no,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1) for name,pattern in patterns.items() if pattern.search(line)]; print(json.dumps({"matches":len(findings),"findings":findings},sort_keys=True)); sys.exit(1 if findings else 0)'
```

The scanner shall print only the file path, line number, and pattern name for a match.

Expected: `0` matches.

**Step 5: Verify scope**

Run:

```bash
git status --short --untracked-files=all
git diff --name-only -- agent/turn_bank.py tests/run_agent/test_turn_bank.py
git diff --check -- agent/turn_bank.py tests/run_agent/test_turn_bank.py
git diff --numstat -- agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

Expected:

- The original unrelated paths remain present.
- The E103 repair changes only 2 project files.
- The scoped diff check exits with code `0`.
- The scoped diff reports exactly the 2 allowed project paths.

## Task 16: Run Review Pass 3

**Objective:** Verify final integration evidence and completion claims.

Dispatch 1 fresh read-only child.

Give the child:

- The accepted specification.
- The final 2-file diff.
- The focused test output.
- The complete-suite log path.
- The complete-suite exit file.
- The wheel inspection result.
- The bounded secret-scan result.
- The final Git status.

Require this output:

```json
{
  "verdict": "APPROVED or REQUEST_CHANGES",
  "focused_tests": "PASS or FAIL",
  "full_suite": "PASS or FAIL",
  "package": "PASS or FAIL",
  "security": "PASS or FAIL",
  "scope": "PASS or FAIL",
  "open_issues": []
}
```

Expected verdict:

```text
APPROVED
```

The parent shall verify each field directly.

A child verdict does not replace direct evidence.

## Task 17: Request Commit Approval

**Objective:** Stop before any Git commit.

Do not stage files before approval.

Present:

- The exact 2-file diff summary.
- The focused test counts.
- The complete-suite counts.
- The 3 review verdicts.
- The wheel SHA-256 value.
- The final scope result.

Ask for separate commit approval.

If Andile approves, stage only:

```bash
git add agent/turn_bank.py tests/run_agent/test_turn_bank.py
```

Use this commit message:

```text
fix: migrate turn bank restart state
```

Verify the staged file list before commit.

Do not stage `.hermes/plans/`.

Do not stage `SESSION_HANDOFF.md`.

## Builder Prompt Contract

Use this contract for each builder child:

```text
Repository: /Users/andilemushwana/xavani-agent.
Read AGENTS.md and SESSION_HANDOFF.md first.
Read the accepted E103 plan fully.
Modify only the assigned file paths.
Preserve all unrelated dirty paths.
Do not reset or stash the tree.
Do not use git add.
Do not commit.
Follow one RED-GREEN cycle at a time.
Run only the assigned tests before GREEN.
Use .venv/bin/python.
Use no network calls.
Add no dependency.
Store no raw conversation text in state.
Return changed paths, commands, exit codes, and open issues.
```

## Reviewer Prompt Contract

Use this contract for each reviewer child:

```text
Repository: /Users/andilemushwana/xavani-agent.
Work read-only.
Read AGENTS.md, SESSION_HANDOFF.md, and the accepted E103 plan.
Read both changed files completely.
Check one requirement at a time.
Use direct line evidence.
Run only the stated verification commands.
Do not edit or commit.
Return APPROVED only when no required issue remains.
Treat a timeout or HTTP 429 as no verdict.
```

## Quality Acceptance Criteria

The parent may declare completion only when all criteria pass:

- The plan challenger approves the architecture.
- Each new test shows valid RED evidence before source changes.
- The focused E103 suite has 0 failures.
- The memory integration suite has 0 failures.
- Ruff reports 0 errors.
- Python compilation reports 0 errors.
- `git diff --check` reports 0 errors.
- Specification Review Pass 1 reports `APPROVED`.
- Quality Review Pass 2 reports `APPROVED`.
- The complete default suite exits with code `0`.
- The complete default suite runs as 1 process.
- The wheel build exits with code `0`.
- The wheel contains all required files.
- The bounded secret scan reports 0 matches.
- Integration Review Pass 3 reports `APPROVED`.
- The parent directly verifies all critical claims.
- The E103 project diff contains only 2 files.
- No P0 issue remains.
- No P1 issue remains.
- No commit occurs without explicit approval.

## Risks and Tradeoffs

### Risk: OpenCode Zen rate limits and weak worker output

The historical free route returned HTTP `429` during a 3-child batch.

The paid route removes that known free-route constraint but does not guarantee output quality.

A paid challenger inspected the complete plan and then returned no verdict.

Mitigation:

- Use the paid `deepseek-v4-flash` route.
- Give each child 1 narrow objective and 1 strict output schema.
- Run only 1 builder when tasks share files.
- Use no more than 3 independent read-only children.
- Keep prompts bounded.
- Reuse file paths, not copied source text.
- Treat a rate-limit result as no verdict.
- Treat a missing or malformed output as no verdict.
- Require the parent to verify each claim directly.
- Do not switch models without user approval.

### Risk: Conversation tail truncation

The CLI loads only the latest configured message tail.

A raw `len(turns)` repair cannot recover a global count safely.

Mitigation:

- Store an ordered pending-sequence digest.
- Reconcile the loaded suffix.
- Prefer retry over silent loss.

### Risk: Version-1 ambiguity

Version-1 states can contain or omit `persisted_count`.

Mitigation:

- Use observed history when it covers the state checkpoint.
- Use memory entries as persistence proof.
- Write only version `2` after migration.

### Risk: Duplicate text

Two turns can have identical formatted text.

Mitigation:

- Consume individual fallback proof by occurrence.
- Keep exact whole-bank proof.
- Retry an unproved duplicate through the content-idempotent store.

### Risk: Dirty shared tree

Other work owns 31 project paths outside E103.

Mitigation:

- Keep 1 active E103 builder.
- Use explicit file paths.
- Recheck Git status after each child.
- Do not reset, stash, or broadly stage.

### Risk: Long complete suite

The previous complete run took 1,986.08 seconds.

Mitigation:

- Run it once after both reviews approve.
- Use a tracked background process.
- Capture the real exit code.
- Write a handoff instead of repeated polling.

## Open Questions

No architecture question blocks implementation.

Andile approved code changes with `go` before this final plan review.

Andile must separately approve any commit.

No remote deployment can occur without a deployment target.

External integration tests may require unavailable credentials.

The complete default suite remains the mandatory combined gate.

## Plan Validator Disposition

The assumption linter now reports 5 findings after wording corrections.

The parent reviewed all 5 findings one by one.

- Findings 1, 4, and 5 inspect the owner home path. The path does not identify an application actor.
- Finding 2 inspects an exact runtime control string. The test requires the exact text.
- Finding 3 inspects the conventional commit prefix. The repository requires that prefix.

These 5 findings are false positives.

No unresolved assumption remains from the linter report.

The goal verifier reports `STRONG` with a score of `34/42`.

The goal verifier reports no missing verification step.

## Final Plan Review Checklist

- The plan names exact project paths.
- The plan limits project edits to 2 files.
- The plan defines the excluded paths.
- The plan defines valid RED evidence.
- The plan defines state invariants.
- The plan handles legacy version-1 state.
- The plan handles state-write failures.
- The plan handles malformed memory results.
- The plan handles duplicate fallback content.
- The plan handles memory-disabled agents.
- The plan defines 3 independent review passes.
- The plan requires one complete green test run.
- The plan preserves the dirty shared tree.
- The plan stops before commit.

## Final End-to-End Verification

1. Run the final end-to-end full test suite and verify the release evidence.

Verify: Run Task 14, Task 15, and Task 16 in sequence.

Expected: Pytest exits with code `0` and reports `0 failed`.

Expected: The wheel build exits with code `0` and has 0 missing required paths.

Expected: The bounded secret scan reports `0` matches.

Expected: Review Pass 3 reports `APPROVED` with an empty `open_issues` list.
