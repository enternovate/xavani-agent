# Business workflow coverage (R2 Task 20)

Scope: the B01–B12 inventory from the reliability master plan, as 36 harness
cases. This document is the coverage record; it does not claim real-model
behavior. Task 25 measures real-model behavior separately.

## What runs

- Fixture: `tests/fixtures/business/workflows.json` — synthetic data only
  (labelled `SYNTHETIC TEST DATA`; nothing derived from real records).
- Suite: `tests/business/test_workflow_acceptance.py` — each case runs its
  script through the REAL agent loop with the scripted provider
  (`tests.harness.faux_provider`), so the `write_file` tool writes real
  artifacts into a temporary workspace, and the case's checks assert
  objective file facts (existence, exact content markers, absence).
  A phrase such as `invoice complete` is never a check.
- The `unapproved` case of every workflow then exercises the real approval
  gate (Task 19): the drafted consequential action must NOT execute without
  an approval, and the same action WITH a valid approval must execute — so
  a refusal cannot masquerade as broken plumbing.

Command and result (2026-09-14):

```sh
XAVANI_TEST_WORKERS=0 bash scripts/run_tests.sh tests/business/test_workflow_acceptance.py -q
# 49 passed (36 cases + 12 per-workflow aggregates + 1 coverage guard)
```

## Coverage matrix

Each workflow has exactly 3 cases: valid source data; missing/contradictory
source data; a consequential action without approval. Status is
`Draft support` until real-model cases pass (plan rule).

| Workflow | Cases | Restricted action (gated) | Key artifact checks |
| --- | --- | --- | --- |
| B01 Finance analysis | valid / missing period / unapproved | place_investment_order | report reconciles assets = liabilities + equity; missing period blocks the report |
| B02 Invoice review | valid / duplicate / unapproved | execute_payment | extracted rows carry page + total; duplicate flagged by identity |
| B03 Daily operations | valid / missing source / unapproved | post_schedule | brief carries owner, deadline, source; missing source shows Unavailable (not an empty schedule) |
| B04 Inbox support | valid / contradictory facts / unapproved | send_email | draft binds recipient + body_sha256; contradictions block the reply |
| B05 Meetings | valid / ownerless segment / unapproved | publish_decisions | every action links to a source timestamp; owners never invented |
| B06 Sales | valid / consent missing / unapproved | launch_campaign | consented recipients only; unsubscribe included; no autonomous publication |
| B07 People | valid / missing jurisdiction / unapproved | make_eligibility_decision | access scope + retention stated; no eligibility decision without approval |
| B08 Procurement | valid / contradictory units / unapproved | issue_purchase_order | units and shortfall quantified; no PO without approval |
| B09 Legal | valid / missing jurisdiction / unapproved | claim_certification | cited obligation + source date; no certification claim |
| B10 Engineering | valid / missing acceptance criteria / unapproved | release | tests + acceptance evidence recorded; no release without approval |
| B11 Executive | valid / contradictory totals / unapproved | publish_board_decision | totals source-linked; contradictions block the brief |
| B12 Safety | valid / missing scope / unapproved | execute_containment | evidence + scope + recovery check; containment never executes without authorization |

## Bench registration

`scripts/task_bench/tasks/baseline_tasks.json` carries one task per
workflow (`biz-workflow-B01` … `biz-workflow-B12`). Each verifier is the
existing `pytest:` verifier on the per-workflow aggregate node, e.g.
`pytest:tests/business/test_workflow_acceptance.py::test_workflow_all_cases[B01]`.
In `--faux` mode these run the harness suite; real-model workflow runs are
Task 25's corpus, not this file.

## Extending

Add cases to `workflows.json` only with objective artifact checks. Keep the
fixture synthetic. Do not weaken a check to make a case pass; a blocked
workflow must produce a block note, not a silent empty artifact.
