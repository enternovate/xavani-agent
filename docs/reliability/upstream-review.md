# Upstream review — recurring process (task 27)

This process reviews upstream security and reliability changes each week.
It keeps the fork current without publishing upstream work blindly.

Attribution and license notices live in the README and
THIRD_PARTY_NOTICES. This process never removes a required notice.

## Cadence

- Each week: review upstream security and reliability changes.
- Each accepted fix: run the smallest relevant regression cases.
- Each release candidate: run the full release checklist
  (`release-checklist.md`, task 26).
- Each stable release: obtain owner approval first.

Do not schedule cron jobs without separate approval.
Do not publish every upstream commit.
Do not equate release frequency with quality.

## Candidate record

Record these fields for each upstream candidate:

- Repository and commit.
- Source files.
- User-visible failure or capability.
- Existing Xavani equivalent.
- Classification: reuse, harden, new, or reject.
- License obligations.
- Regression test.
- Local implementation commit.
- Verification evidence.

## Classification rules

- `reuse`: the behavior fits Xavani; port it with tests.
- `harden`: the behavior exists; strengthen it and pin the gap.
- `new`: no equivalent exists; add it with tests and a boundary check.
- `reject`: the change conflicts with product rules (brand, telemetry,
  subscription, or packaging); record the reason in the log.

## Verification

- Run the smallest relevant regression cases for each fix (targeted
  pytest or Node paths).
- Record the exact commands and their results with the candidate.
- Keep the brand boundary: nothing in Xavani may lead to an upstream
  service.

## Review log

Keep the weekly review log next to this file as
`upstream-review-log.md` when the first review runs. The log records one
section per week with the candidate records and their outcomes.
